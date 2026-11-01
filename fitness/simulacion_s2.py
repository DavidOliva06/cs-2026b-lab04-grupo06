"""Simulación por conteo del escenario S2 (Lab 08, E4, iteración 3 de ADD).

Un atacante envía 1 000 reportes falsos en 5 min desde un mismo dispositivo mientras
llegan los reportes legítimos del simulacro. Compara las tácticas de limitación y
detección según las cuatro medidas de S2. Solo usa la biblioteca estándar.

Uso:
    python fitness/simulacion_s2.py
"""
import random
import statistics
import sys
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, replace
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA_TABLAS = RAIZ / "fitness" / "resultados" / "s2.md"
PESO_GRAVEDAD = {1: 1, 2: 2, 3: 4}


@dataclass(frozen=True)
class Supuestos:
    # Tráfico legítimo en la ventana de 10 min (≈ 5,6 reportes por s, escenario D1)
    ventana_s: float = 600.0
    dispositivos_legitimos: int = 3_000
    reportes_legitimos: int = 3_333
    zonas: int = 1_874
    # CGNAT: los dispositivos comparten IP pública con distribución de Zipf
    ips_publicas: int = 200
    exponente_zipf: float = 1.0
    # Ataque del escenario S2
    inicio_ataque_s: float = 120.0
    duracion_ataque_s: float = 300.0
    reportes_ataque: int = 1_000
    zonas_objetivo: int = 5
    reportes_por_identidad: int = 0  # 0: un solo dispositivo; n > 0: identidad nueva cada n reportes (Sybil)
    # Tácticas
    limite_por_ventana: int = 10
    zonas_prioritarias: int = 20
    replicas: int = 10


def generar(s, rng):
    pesos_zona = [rng.lognormvariate(0, 1) for _ in range(s.zonas)]
    pesos_ip = [1 / (i + 1) ** s.exponente_zipf for i in range(s.ips_publicas)]
    zona_de = rng.choices(range(s.zonas), weights=pesos_zona, k=s.dispositivos_legitimos)
    ip_de = rng.choices(range(s.ips_publicas), weights=pesos_ip, k=s.dispositivos_legitimos)
    autores = list(range(s.dispositivos_legitimos))
    autores += rng.choices(autores, k=s.reportes_legitimos - s.dispositivos_legitimos)
    eventos = [
        (rng.uniform(0, s.ventana_s), f"d{d}", ip_de[d], zona_de[d], rng.choices([1, 2, 3], weights=[6, 3, 1])[0], False)
        for d in autores
    ]
    tranquilas = sorted(range(s.zonas), key=lambda z: pesos_zona[z])[: s.zonas_objetivo]
    ip_atacante = rng.choices(range(s.ips_publicas), weights=pesos_ip)[0]
    tiempos = sorted(rng.uniform(s.inicio_ataque_s, s.inicio_ataque_s + s.duracion_ataque_s) for _ in range(s.reportes_ataque))
    for i, t in enumerate(tiempos):
        identidad = i // s.reportes_por_identidad if s.reportes_por_identidad else 0
        eventos.append((t, f"atacante-{identidad}", ip_atacante, tranquilas[i % s.zonas_objetivo], 3, True))
    eventos.sort()
    return eventos, ip_atacante


def prioritarias(reportes, s, un_voto_por_dispositivo):
    puntaje = defaultdict(int)
    if un_voto_por_dispositivo:
        votos = {}
        for _, autor, _, zona, gravedad, _ in reportes:
            votos[(autor, zona)] = max(votos.get((autor, zona), 0), PESO_GRAVEDAD[gravedad])
        for (_, zona), peso in votos.items():
            puntaje[zona] += peso
    else:
        for _, _, _, zona, gravedad, _ in reportes:
            puntaje[zona] += PESO_GRAVEDAD[gravedad]
    return set(sorted(puntaje, key=lambda z: (-puntaje[z], z))[: s.zonas_prioritarias])


TACTICAS = {
    "Antes: sin control": {"clave": None, "marcar_sospechosos": False, "un_voto": False},
    "T10: límite por IP": {"clave": "ip", "marcar_sospechosos": False, "un_voto": False},
    "T9: límite por dispositivo": {"clave": "dispositivo", "marcar_sospechosos": False, "un_voto": False},
    "T9 + T11: límite, marca y un voto por dispositivo": {"clave": "dispositivo", "marcar_sospechosos": True, "un_voto": True},
}


def aplicar(s, eventos, ip_atacante, tactica):
    t = TACTICAS[tactica]
    ventanas = defaultdict(deque)
    aceptados, alertas, sospechosos = [], {}, set()
    for evento in eventos:
        momento, autor, ip, _, _, _ = evento
        clave = {"ip": ip, "dispositivo": autor}.get(t["clave"])
        if clave is not None:
            ventana = ventanas[clave]
            while ventana and ventana[0] <= momento - s.ventana_s:
                ventana.popleft()
            if len(ventana) >= s.limite_por_ventana:
                alertas.setdefault(clave, momento)
                if t["marcar_sospechosos"]:
                    sospechosos.add(autor)
                continue
            ventana.append(momento)
        aceptados.append(evento)

    legitimos = [e for e in eventos if not e[5]]
    contados = [e for e in aceptados if e[1] not in sospechosos]
    base = prioritarias(legitimos, s, t["un_voto"])
    con_ataque = prioritarias(contados, s, t["un_voto"])
    por_identidad = Counter(e[1] for e in aceptados if e[5])
    es_del_ataque = lambda clave: clave == ip_atacante if t["clave"] == "ip" else str(clave).startswith("atacante")
    alertas_ataque = [m for clave, m in alertas.items() if es_del_ataque(clave)]
    return {
        "max_por_identidad": max(por_identidad.values(), default=0),
        "aceptados_ataque": sum(por_identidad.values()),
        "zonas_alteradas": len(con_ataque - base),
        "legitimos_pct": 100 * sum(1 for e in aceptados if not e[5]) / len(legitimos),
        "aviso_s": min(alertas_ataque) - s.inicio_ataque_s if alertas_ataque else None,
        "falsas_alarmas": sum(1 for clave in alertas if not es_del_ataque(clave)),
    }


def evaluar(s):
    resultados = {nombre: [] for nombre in TACTICAS}
    for semilla in range(1, s.replicas + 1):
        eventos, ip_atacante = generar(s, random.Random(semilla))
        for nombre in TACTICAS:
            resultados[nombre].append(aplicar(s, eventos, ip_atacante, nombre))
    return resultados


def decimal(valor, digitos=1):
    return f"{valor:,.{digitos}f}".replace(",", " ").replace(".", ",")


def resumir(medidas):
    avisos = [m["aviso_s"] for m in medidas]
    aviso = "sin aviso" if None in avisos else f"{decimal(max(avisos))} s"
    peor = {
        "max_por_identidad": max(m["max_por_identidad"] for m in medidas),
        "aceptados_ataque": max(m["aceptados_ataque"] for m in medidas),
        "zonas_alteradas": max(m["zonas_alteradas"] for m in medidas),
        "legitimos_pct": min(m["legitimos_pct"] for m in medidas),
        "falsas_alarmas": statistics.fmean(m["falsas_alarmas"] for m in medidas),
    }
    cumple = (peor["max_por_identidad"] <= 10 and peor["zonas_alteradas"] == 0 and peor["legitimos_pct"] >= 99.5
              and None not in avisos and max(avisos) <= 300)
    return peor, aviso, cumple


def tabla(resultados):
    filas = [
        "| Táctica | Máx. aceptados por dispositivo atacante (≤ 10) | Reportes falsos aceptados | Zonas del top 20 distintas de las que darían solo los legítimos (0) "
        "| Legítimos aceptados (≥ 99,5 %) | Aviso al operador (≤ 300 s) | Falsas alarmas (media) | ¿Cumple S2? |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for nombre, medidas in resultados.items():
        peor, aviso, cumple = resumir(medidas)
        filas.append(
            f"| {nombre} | {peor['max_por_identidad']} | {peor['aceptados_ataque']} | {peor['zonas_alteradas']} "
            f"| {decimal(peor['legitimos_pct'], 2)} % | {aviso} | {decimal(peor['falsas_alarmas'])} | {'Sí' if cumple else '**No**'} |"
        )
    return "\n".join(filas)


VARIANTES = {
    "50 IP públicas (más CGNAT)": {"ips_publicas": 50},
    "1 000 IP públicas (menos CGNAT)": {"ips_publicas": 1_000},
    "Ataque concentrado en 1 zona": {"zonas_objetivo": 1},
    "Ataque repartido en 20 zonas": {"zonas_objetivo": 20},
    "Sybil: identidad nueva cada 10 reportes": {"reportes_por_identidad": 10},
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    s = Supuestos()
    texto = [f"## Resultados con los supuestos base (peor de {s.replicas} réplicas)", "", tabla(evaluar(s))]
    for nombre, cambios in VARIANTES.items():
        texto += ["", f"## Variante: {nombre}", "", tabla(evaluar(replace(s, **cambios)))]
    salida = "\n".join(texto) + "\n"
    print(salida)
    SALIDA_TABLAS.parent.mkdir(parents=True, exist_ok=True)
    SALIDA_TABLAS.write_text("# Resultados de fitness/simulacion_s2.py\n\n" + salida, encoding="utf-8")


if __name__ == "__main__":
    main()
