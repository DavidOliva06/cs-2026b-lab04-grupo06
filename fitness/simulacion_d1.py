"""Simulación de eventos discretos del escenario D1 (Lab 08, E2).

Compara la ingesta de SismoReporta AQP antes y después de las tácticas aceptadas
en docs/architecture/add/iteracion-1.md: T2 (degradación, modo pico) y T1 (limitar
la respuesta a eventos), por separado y juntas. Solo usa la biblioteca estándar.

Uso:
    python fitness/simulacion_d1.py           # 10 réplicas, sensibilidad, tablas y gráfico
    python fitness/simulacion_d1.py --rapido  # 3 réplicas, sin sensibilidad
"""
import argparse
import heapq
import math
import random
import statistics
import sys
from collections import deque
from dataclasses import dataclass, replace
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA_TABLAS = RAIZ / "fitness" / "resultados" / "d1.md"
SALIDA_GRAFICO = RAIZ / "docs" / "architecture" / "add" / "img" / "d1-antes-despues.svg"


@dataclass(frozen=True)
class Supuestos:
    # Carga del escenario D1
    reportes_fondo: int = 18_000
    reportes_rafaga: int = 2_000
    inicio_rafaga_s: float = 1_200.0
    duracion_rafaga_s: float = 60.0
    duracion_s: float = 3_600.0
    ventana_d1_s: float = 900.0
    # Red móvil congestionada
    latencia_mediana_s: float = 1.5
    latencia_sigma: float = 0.5
    subida_mediana_kbps: float = 50.0
    subida_sigma: float = 0.6
    cortes_por_s: float = 0.01
    datos_kb: float = 1.0
    foto_kb: float = 300.0
    # PWA (ADR-003)
    espera_respuesta_s: float = 30.0
    reintento_base_s: float = 2.0
    reintento_tope_s: float = 120.0
    # Servidor único (ADR-001, R-03)
    conexiones_max: int = 1_000
    nucleos: int = 2
    servicio_datos_s: float = 0.030
    servicio_duplicado_s: float = 0.010
    servicio_guardar_foto_s: float = 0.020
    servicio_procesar_foto_s: float = 0.150
    caida_inicio_s: float = 0.0
    caida_duracion_s: float = 0.0
    # T1: limitar la respuesta a eventos
    limite_por_s: float = 35.0
    balde_limite: int = 70
    retry_after_min_s: float = 5.0
    retry_after_max_s: float = 60.0
    # T2: degradación (modo pico)
    umbral_modo_pico: float = 0.70
    muestreo_s: float = 5.0


CONFIGURACIONES = {
    "Antes": (False, False),
    "Solo T1": (True, False),
    "Solo T2": (False, True),
    "T1 + T2": (True, True),
}
DECISION = "Solo T2"


class Reporte:
    __slots__ = ("t0", "guardado", "foto_guardada", "foto_diferida", "intento", "esperando", "fallos")

    def __init__(self, t0):
        self.t0 = t0
        self.guardado = None
        self.foto_guardada = False
        self.foto_diferida = False
        self.intento = 0
        self.esperando = None
        self.fallos = {"datos": 0, "foto": 0}


class Simulacion:
    def __init__(self, s, con_t1, con_t2, semilla):
        self.s = s
        self.con_t1 = con_t1
        self.con_t2 = con_t2
        self.rng = random.Random(semilla)
        self.ahora = 0.0
        self.eventos = []
        self.secuencia = 0
        self.conexiones = 0
        self.pico_conexiones = 0
        self.nucleos_libres = s.nucleos
        self.cola_api = deque()
        self.cola_worker = deque()
        self.worker_ocupado = False
        self.modo_pico = False
        self.inicio_modo_pico = None
        self.muestras_altas = 0
        self.fichas = float(s.balde_limite)
        self.t_fichas = 0.0
        self.cuenta = {"rechazadas": 0, "limitadas_429": 0, "cortes": 0, "expiradas": 0, "duplicados_descartados": 0}
        self.serie = []
        self.reportes = []

    # Motor de eventos
    def en(self, demora, funcion, *args):
        self.secuencia += 1
        heapq.heappush(self.eventos, (self.ahora + demora, self.secuencia, funcion, args))

    def ejecutar(self):
        s = self.s
        llegadas = [self.rng.uniform(0, s.duracion_s) for _ in range(s.reportes_fondo)]
        llegadas += [s.inicio_rafaga_s + self.rng.uniform(0, s.duracion_rafaga_s) for _ in range(s.reportes_rafaga)]
        for t0 in llegadas:
            reporte = Reporte(t0)
            self.reportes.append(reporte)
            self.en(t0, self.enviar, reporte, "datos")
        self.en(0, self.muestrear)
        horizonte = s.duracion_s + s.ventana_d1_s
        while self.eventos:
            t, _, funcion, args = heapq.heappop(self.eventos)
            if t > horizonte:
                break
            self.ahora = t
            funcion(*args)
        return self

    def lognormal_media(self, media, cv=0.5):
        sigma = math.sqrt(math.log(1 + cv * cv))
        return self.rng.lognormvariate(math.log(media) - sigma * sigma / 2, sigma)

    # PWA
    def enviar(self, r, tipo):
        s = self.s
        if tipo == "foto" and self.modo_pico:
            r.foto_diferida = True
            return
        caido = s.caida_inicio_s <= self.ahora < s.caida_inicio_s + s.caida_duracion_s
        if caido or self.conexiones >= s.conexiones_max:
            self.cuenta["rechazadas"] += 1
            self.reintentar(r, tipo)
            return
        self.conexiones += 1
        self.pico_conexiones = max(self.pico_conexiones, self.conexiones)
        r.intento += 1
        kb = s.datos_kb if tipo == "datos" else s.foto_kb
        latencia = self.rng.lognormvariate(math.log(s.latencia_mediana_s), s.latencia_sigma)
        subida_kbps = self.rng.lognormvariate(math.log(s.subida_mediana_kbps), s.subida_sigma)
        duracion = latencia + kb * 8 / subida_kbps
        corte = self.rng.expovariate(s.cortes_por_s)
        if corte < duracion:
            self.en(corte, self.cortar, r, tipo)
        else:
            self.en(duracion, self.llegar_al_servidor, r, tipo, r.intento)

    def cortar(self, r, tipo):
        self.conexiones -= 1
        self.cuenta["cortes"] += 1
        self.reintentar(r, tipo)

    def reintentar(self, r, tipo, espera=None):
        s = self.s
        if espera is None:
            espera = self.rng.uniform(0, min(s.reintento_tope_s, s.reintento_base_s * 2 ** r.fallos[tipo]))
        r.fallos[tipo] += 1
        self.en(espera, self.enviar, r, tipo)

    def expirar(self, r, tipo, intento):
        if r.esperando == intento:
            r.esperando = None
            self.conexiones -= 1
            self.cuenta["expiradas"] += 1
            self.reintentar(r, tipo)

    # Servidor
    def tomar_ficha(self):
        s = self.s
        self.fichas = min(s.balde_limite, self.fichas + (self.ahora - self.t_fichas) * s.limite_por_s)
        self.t_fichas = self.ahora
        if self.fichas >= 1:
            self.fichas -= 1
            return True
        return False

    def llegar_al_servidor(self, r, tipo, intento):
        s = self.s
        if self.con_t1 and tipo == "datos" and not self.tomar_ficha():
            self.conexiones -= 1
            self.cuenta["limitadas_429"] += 1
            self.reintentar(r, tipo, self.rng.uniform(s.retry_after_min_s, s.retry_after_max_s))
            return
        if tipo == "datos":
            ya_guardado = r.guardado is not None
            servicio = s.servicio_duplicado_s if ya_guardado else s.servicio_datos_s
        else:
            servicio = s.servicio_duplicado_s if r.foto_guardada else s.servicio_guardar_foto_s
        r.esperando = intento
        self.en(s.espera_respuesta_s, self.expirar, r, tipo, intento)
        self.cola_api.append((self.ahora, self.lognormal_media(servicio), r, tipo, intento))
        self.despachar()

    def despachar(self):
        while self.nucleos_libres > 0:
            usar_worker = (
                not self.worker_ocupado
                and self.cola_worker
                and (not self.cola_api or self.cola_worker[0][0] <= self.cola_api[0][0])
            )
            if usar_worker:
                _, servicio = self.cola_worker.popleft()
                self.worker_ocupado = True
                self.nucleos_libres -= 1
                self.en(servicio, self.terminar_worker)
            elif self.cola_api:
                trabajo = self.cola_api.popleft()
                self.nucleos_libres -= 1
                self.en(trabajo[1], self.terminar_api, trabajo)
            else:
                break

    def terminar_api(self, trabajo):
        _, _, r, tipo, intento = trabajo
        self.nucleos_libres += 1
        if tipo == "datos":
            if r.guardado is None:
                r.guardado = self.ahora
            else:
                self.cuenta["duplicados_descartados"] += 1
        elif not r.foto_guardada:
            r.foto_guardada = True
            self.cola_worker.append((self.ahora, self.lognormal_media(self.s.servicio_procesar_foto_s)))
        else:
            self.cuenta["duplicados_descartados"] += 1
        if r.esperando == intento:
            r.esperando = None
            self.conexiones -= 1
            if tipo == "datos":
                self.enviar(r, "foto")
        self.despachar()

    def terminar_worker(self):
        self.worker_ocupado = False
        self.nucleos_libres += 1
        self.despachar()

    def muestrear(self):
        s = self.s
        self.serie.append((self.ahora, self.conexiones))
        if self.con_t2 and not self.modo_pico:
            alto = self.conexiones >= s.umbral_modo_pico * s.conexiones_max
            self.muestras_altas = self.muestras_altas + 1 if alto else 0
            if self.muestras_altas >= 2:
                self.modo_pico = True
                self.inicio_modo_pico = self.ahora
        if self.ahora < s.duracion_s + s.ventana_d1_s:
            self.en(s.muestreo_s, self.muestrear)

    # Medidas de D1
    def tiempos(self):
        return [r.guardado - r.t0 if r.guardado is not None else math.inf for r in self.reportes]

    def medidas(self):
        tiempos = sorted(self.tiempos())
        total = len(tiempos)
        a_tiempo = sum(1 for t in tiempos if t <= self.s.ventana_d1_s)
        return {
            "total": total,
            "a_tiempo": a_tiempo,
            "pct_a_tiempo": 100 * a_tiempo / total,
            "p95_s": tiempos[math.ceil(0.95 * total) - 1],
            "max_s": tiempos[-1],
            "sin_guardar": sum(1 for t in tiempos if math.isinf(t)),
            "filas_duplicadas": 0,
            "fotos_guardadas": sum(1 for r in self.reportes if r.foto_guardada),
            "fotos_diferidas": sum(1 for r in self.reportes if r.foto_diferida and not r.foto_guardada),
            "pico_conexiones": self.pico_conexiones,
            "inicio_modo_pico_min": None if self.inicio_modo_pico is None else self.inicio_modo_pico / 60,
            **self.cuenta,
        }


def correr(s, configuracion, semillas):
    con_t1, con_t2 = CONFIGURACIONES[configuracion]
    return [Simulacion(s, con_t1, con_t2, semilla).ejecutar() for semilla in semillas]


def resumir(simulaciones):
    medidas = [sim.medidas() for sim in simulaciones]
    media = lambda clave: statistics.fmean(m[clave] for m in medidas)
    return {
        "pct_media": media("pct_a_tiempo"),
        "pct_min": min(m["pct_a_tiempo"] for m in medidas),
        "a_tiempo_min": min(m["a_tiempo"] for m in medidas),
        "p95_s": media("p95_s"),
        "max_s": max(m["max_s"] for m in medidas),
        "filas_duplicadas": max(m["filas_duplicadas"] for m in medidas),
        "pico_conexiones": media("pico_conexiones"),
        "rechazadas": media("rechazadas"),
        "limitadas_429": media("limitadas_429"),
        "expiradas": media("expiradas"),
        "duplicados_descartados": media("duplicados_descartados"),
        "fotos_guardadas": media("fotos_guardadas"),
        "fotos_diferidas": media("fotos_diferidas"),
        "inicio_modo_pico_min": [m["inicio_modo_pico_min"] for m in medidas if m["inicio_modo_pico_min"] is not None],
        "cumple": all(m["pct_a_tiempo"] >= 99.5 and m["filas_duplicadas"] == 0 for m in medidas),
    }


def segundos(valor):
    return "no guardado" if math.isinf(valor) else f"{valor:,.0f} s".replace(",", " ")


def miles(valor):
    return f"{valor:,.0f}".replace(",", " ")


def decimal(valor, digitos=2):
    return f"{valor:.{digitos}f}".replace(".", ",")


def tabla_principal(resumenes, n):
    filas = [
        f"| Configuración | Guardados ≤ 15 min (media de {n}) | Peor réplica | p95 hasta guardar | Máximo | Filas duplicadas | ¿Cumple D1? |",
        "|---|---|---|---|---|---|---|",
    ]
    for nombre, r in resumenes.items():
        filas.append(
            f"| {nombre} | {decimal(r['pct_media'])} % | {decimal(r['pct_min'])} % ({miles(r['a_tiempo_min'])} de 20 000) "
            f"| {segundos(r['p95_s'])} | {segundos(r['max_s'])} | {r['filas_duplicadas']} | {'Sí' if r['cumple'] else 'No'} |"
        )
    filas += [
        "",
        "| Configuración | Pico de conexiones | Conexiones rechazadas | Respuestas 429 | Esperas expiradas | Duplicados descartados | Fotos guardadas | Fotos diferidas | Inicio del modo pico |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for nombre, r in resumenes.items():
        inicio = r["inicio_modo_pico_min"]
        inicio = f"min {decimal(statistics.fmean(inicio), 1)}" if inicio else "—"
        filas.append(
            f"| {nombre} | {miles(r['pico_conexiones'])} | {miles(r['rechazadas'])} | {miles(r['limitadas_429'])} "
            f"| {miles(r['expiradas'])} | {miles(r['duplicados_descartados'])} | {miles(r['fotos_guardadas'])} "
            f"| {miles(r['fotos_diferidas'])} | {inicio} |"
        )
    return "\n".join(filas)


VARIANTES = {
    "Base": {},
    "500 conexiones": {"conexiones_max": 500},
    "2 000 conexiones": {"conexiones_max": 2_000},
    "Cortes ×2 (0,02 por s)": {"cortes_por_s": 0.02},
    "Foto de 600 KB": {"foto_kb": 600.0},
    "Procesar foto 400 ms": {"servicio_procesar_foto_s": 0.400},
    "Ráfaga de 4 000 en 1 min": {"reportes_fondo": 16_000, "reportes_rafaga": 4_000},
    "Caída de 10 min en el minuto 20": {"caida_inicio_s": 1_200.0, "caida_duracion_s": 600.0},
    "Caída de 13 min en el minuto 20": {"caida_inicio_s": 1_200.0, "caida_duracion_s": 780.0},
}


def tabla_sensibilidad(semillas):
    filas = [
        "| Variante (un supuesto cambia) | Antes: guardados ≤ 15 min (peor réplica) | Después (T2): guardados ≤ 15 min (peor réplica) | Antes: p95 | Después (T2): p95 |",
        "|---|---|---|---|---|",
    ]
    for nombre, cambios in VARIANTES.items():
        s = replace(Supuestos(), **cambios)
        antes = resumir(correr(s, "Antes", semillas))
        despues = resumir(correr(s, DECISION, semillas))
        filas.append(
            f"| {nombre} | {decimal(antes['pct_min'])} % | {decimal(despues['pct_min'])} % "
            f"| {segundos(antes['p95_s'])} | {segundos(despues['p95_s'])} |"
        )
    return "\n".join(filas)


# Gráfico SVG sin dependencias
def p95_por_minuto(sim):
    grupos = {}
    for r, t in zip(sim.reportes, sim.tiempos()):
        grupos.setdefault(int(r.t0 // 60), []).append(t)
    puntos = []
    for minuto in sorted(grupos):
        valores = sorted(grupos[minuto])
        puntos.append((minuto + 0.5, valores[math.ceil(0.95 * len(valores)) - 1] / 60))
    return puntos


def svg_panel(y0, alto, titulo, series, y_max, referencia, etiqueta_ref, x_max, ticks_y, formato_y):
    izq, ancho = 64, 600
    x = lambda v: izq + v / x_max * ancho
    y = lambda v: y0 + alto - min(v, y_max) / y_max * alto
    partes = [f'<text class="titulo" x="{izq}" y="{y0 - 14}">{titulo}</text>']
    for tick in ticks_y:
        partes.append(f'<line class="rejilla" x1="{izq}" x2="{izq + ancho}" y1="{y(tick):.1f}" y2="{y(tick):.1f}"/>')
        partes.append(f'<text class="eje" x="{izq - 8}" y="{y(tick) + 4:.1f}" text-anchor="end">{formato_y(tick)}</text>')
    for tick in range(0, int(x_max) + 1, 15):
        partes.append(f'<text class="eje" x="{x(tick):.1f}" y="{y0 + alto + 18}" text-anchor="middle">{tick}</text>')
    partes.append(f'<line class="base" x1="{izq}" x2="{izq + ancho}" y1="{y0 + alto}" y2="{y0 + alto}"/>')
    partes.append(f'<line class="referencia" x1="{izq}" x2="{izq + ancho}" y1="{y(referencia):.1f}" y2="{y(referencia):.1f}"/>')
    partes.append(f'<text class="eje" x="{izq + ancho}" y="{y(referencia) - 6:.1f}" text-anchor="end">{etiqueta_ref}</text>')
    for clase, puntos in series:
        ruta = " ".join(f"{x(px):.1f},{y(py):.1f}" for px, py in puntos)
        partes.append(f'<polyline class="{clase}" points="{ruta}"/>')
    return "\n".join(partes)


def grafico(antes, despues, s, encabezado, pie):
    x_max = (s.duracion_s + s.ventana_d1_s) / 60
    conexiones = lambda sim: [(t / 60, c) for t, c in sim.serie]
    panel_a = svg_panel(
        100, 180, "Conexiones abiertas en el proxy", [
            ("serie-1", conexiones(antes)),
            ("serie-2", conexiones(despues)),
        ],
        s.conexiones_max * 1.1, s.conexiones_max, f"Límite: {miles(s.conexiones_max)} conexiones", x_max,
        [0, 250, 500, 750, 1000], miles,
    )
    p95_antes, p95_despues = p95_por_minuto(antes), p95_por_minuto(despues)
    y_max = max(16.0, math.ceil(max(v for _, v in p95_antes + p95_despues if not math.isinf(v)) + 1))
    panel_b = svg_panel(
        360, 180, "p95 del tiempo hasta guardar el reporte, por minuto en que se recupera la señal (min)", [
            ("serie-1", p95_antes),
            ("serie-2", p95_despues),
        ],
        y_max, 15, "D1: 15 min", x_max, list(range(0, int(y_max) + 1, 5)), lambda v: str(v),
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 600" width="760" height="600" role="img" aria-labelledby="t d">
<title id="t">{encabezado}</title>
<desc id="d">Simulación de 75 minutos con 20 000 reportes; {pie}. Réplica con semilla 1.</desc>
<style>
  svg {{ --superficie: #fcfcfb; --texto: #0b0b0b; --texto-2: #52514e; --rejilla: #e4e3df; --serie-1: #2a78d6; --serie-2: #eb6834; }}
  @media (prefers-color-scheme: dark) {{
    svg {{ --superficie: #1a1a19; --texto: #f0efec; --texto-2: #c3c2b7; --rejilla: #3a3a37; --serie-1: #3987e5; --serie-2: #d95926; }}
  }}
  .fondo {{ fill: var(--superficie); }}
  text {{ font-family: Helvetica, Arial, sans-serif; fill: var(--texto-2); }}
  .encabezado {{ font-size: 16px; font-weight: bold; fill: var(--texto); }}
  .titulo {{ font-size: 13px; font-weight: bold; fill: var(--texto); }}
  .eje, .nota {{ font-size: 11px; }}
  .rejilla {{ stroke: var(--rejilla); stroke-width: 1; }}
  .base {{ stroke: var(--texto-2); stroke-width: 1; }}
  .referencia {{ stroke: var(--texto-2); stroke-width: 1.5; stroke-dasharray: 5 4; }}
  .serie-1, .serie-2 {{ fill: none; stroke-width: 2; stroke-linejoin: round; }}
  .serie-1 {{ stroke: var(--serie-1); }}
  .serie-2 {{ stroke: var(--serie-2); }}
  .muestra-1 {{ fill: var(--serie-1); }}
  .muestra-2 {{ fill: var(--serie-2); }}
</style>
<rect class="fondo" width="760" height="600"/>
<text class="encabezado" x="64" y="28">{encabezado}</text>
<rect class="muestra-1" x="64" y="38" width="12" height="4" rx="2"/><text class="eje" x="82" y="43">Antes</text>
<rect class="muestra-2" x="130" y="38" width="12" height="4" rx="2"/><text class="eje" x="148" y="43">Después (T2, modo pico)</text>
{panel_a}
{panel_b}
<text class="eje" x="364" y="572" text-anchor="middle">Minuto de la simulación ({pie}; las llegadas terminan en el minuto 60)</text>
<text class="nota" x="64" y="592">Fuente: fitness/simulacion_d1.py, semilla 1. Supuestos en docs/architecture/add/iteracion-1.md.</text>
</svg>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rapido", action="store_true", help="3 réplicas y sin análisis de sensibilidad")
    args = parser.parse_args()
    s = Supuestos()
    semillas = range(1, 4) if args.rapido else range(1, 11)

    simulaciones = {nombre: correr(s, nombre, semillas) for nombre in CONFIGURACIONES}
    resumenes = {nombre: resumir(sims) for nombre, sims in simulaciones.items()}
    texto = [f"## Resultados ({len(semillas)} réplicas)", "", tabla_principal(resumenes, len(semillas))]
    graficos = {
        SALIDA_GRAFICO: (simulaciones, s, "D1: ingesta en el simulacro nacional, antes y después de T2 (modo pico)",
                         "ráfaga de 2 000 reportes en el minuto 20"),
    }
    if not args.rapido:
        texto += ["", "## Sensibilidad (5 réplicas por variante)", "", tabla_sensibilidad(range(1, 6))]
        s_caida = replace(s, **VARIANTES["Caída de 10 min en el minuto 20"])
        caida = {nombre: correr(s_caida, nombre, semillas) for nombre in CONFIGURACIONES}
        texto += [
            "", f"## Caída de 10 min en el minuto 20: aporte de cada táctica ({len(semillas)} réplicas)", "",
            tabla_principal({nombre: resumir(sims) for nombre, sims in caida.items()}, len(semillas)),
        ]
        graficos[SALIDA_GRAFICO.with_name("d1-caida-10min.svg")] = (
            caida, s_caida, "D1 con una caída del servidor de 10 min, antes y después de T2 (modo pico)",
            "servidor caído de los minutos 20 a 30, durante la ráfaga",
        )
    salida = "\n".join(texto) + "\n"
    sys.stdout.reconfigure(encoding="utf-8")
    print(salida)

    SALIDA_TABLAS.parent.mkdir(parents=True, exist_ok=True)
    SALIDA_TABLAS.write_text("# Resultados de fitness/simulacion_d1.py\n\n" + salida, encoding="utf-8")
    SALIDA_GRAFICO.parent.mkdir(parents=True, exist_ok=True)
    for ruta, (sims, supuestos, encabezado, pie) in graficos.items():
        svg = grafico(sims["Antes"][0], sims[DECISION][0], supuestos, encabezado, pie)
        ruta.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
