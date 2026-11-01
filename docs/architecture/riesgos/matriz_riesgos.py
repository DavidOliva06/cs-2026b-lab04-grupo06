"""Matriz de probabilidad e impacto de los riesgos de atam-lite.md (Lab 08, E7).

Los riesgos se definen una sola vez aquí; el script genera el gráfico SVG y la tabla en
Markdown que se copia en atam-lite.md. Solo usa la biblioteca estándar.

Uso:
    python docs/architecture/riesgos/matriz_riesgos.py
"""
import sys
from pathlib import Path

SALIDA = Path(__file__).resolve().parent / "matriz-riesgos.svg"
NIVELES = {1: "Baja", 2: "Media", 3: "Alta"}
UMBRAL_CRITICO = 6  # probabilidad × impacto

# (id, riesgo, probabilidad, impacto, origen)
RIESGOS = [
    ("R-01", "Fotos diferidas que nunca llegan", 3, 2, "RI-01, ADR-006"),
    ("R-02", "Evidencia de modelos, sin prueba de carga real", 2, 3, "RI-03"),
    ("R-03", "La simulación de D1 suponía 2 núcleos; el droplet tiene 1 vCPU", 3, 3, "E6, ADR-006"),
    ("R-04", "Umbral del modo pico sin calibrar", 2, 2, "RI-04"),
    ("R-05", "0 reportes perdidos en el celular, sin evidencia", 2, 3, "RI-05, ADR-003"),
    ("R-06", "Caídas del servidor de más de 10 min rompen D1", 1, 3, "RI-06"),
    ("R-07", "Tiempos de R2 medidos en SQLite y sin ingesta en paralelo", 2, 1, "RI-07"),
    ("R-08", "Tiempo de dibujo del panel no medido", 1, 2, "RI-08"),
    ("R-09", "El filtro del mapa (0,68 s) tiene poco margen", 2, 1, "RI-09"),
    ("R-10", "Ataque Sybil: muchas identidades de dispositivo", 2, 3, "RI-10, ADR-008"),
    ("R-11", "El identificador de dispositivo es un dato personal", 3, 2, "RI-11, ADR-008"),
    ("R-12", "Un voto por dispositivo subestima varios daños", 2, 2, "RI-12, ADR-008"),
    ("R-13", "El servidor único es un punto único de falla", 1, 3, "ADR-001"),
    ("R-14", "D2 y D4 no tienen iteración propia", 2, 3, "Árbol de utilidad"),
    ("R-15", "Documentación desactualizada tras separar entrada.py", 3, 1, "E5"),
]


def zona(puntaje):
    if puntaje >= UMBRAL_CRITICO:
        return "Crítica"
    return "Media" if puntaje >= 3 else "Baja"


def tabla():
    filas = ["| ID | Riesgo | Probabilidad | Impacto | P × I | Zona | Origen |", "|---|---|---|---|---|---|---|"]
    for rid, nombre, p, i, origen in sorted(RIESGOS, key=lambda r: (-r[2] * r[3], r[0])):
        nivel = zona(p * i)
        filas.append(f"| {rid} | {nombre} | {NIVELES[p]} | {NIVELES[i]} | {p * i} | "
                     f"{'**Crítica**' if nivel == 'Crítica' else nivel} | {origen} |")
    return "\n".join(filas)


def svg():
    izq, arriba, lado = 150, 90, 190
    partes = []
    for p in (3, 2, 1):
        for i in (1, 2, 3):
            x, y = izq + (i - 1) * lado, arriba + (3 - p) * lado
            nivel = zona(p * i)
            partes.append(f'<rect class="celda zona-{nivel.lower()}" x="{x}" y="{y}" width="{lado - 4}" height="{lado - 4}" rx="4"/>')
            partes.append(f'<text class="zona" x="{x + 10}" y="{y + 20}">{nivel} ({p * i})</text>')
            ids = [r[0] for r in RIESGOS if r[2] == p and r[3] == i]
            for n, rid in enumerate(ids):
                fila, col = divmod(n, 3)
                partes.append(f'<text class="riesgo" x="{x + 14 + col * 58}" y="{y + 52 + fila * 26}">{rid}</text>')
    for n, (valor, texto) in enumerate(NIVELES.items()):
        partes.append(f'<text class="eje" x="{izq + n * lado + lado / 2}" y="{arriba + 3 * lado + 22}" text-anchor="middle">{texto}</text>')
        partes.append(f'<text class="eje" x="{izq - 12}" y="{arriba + (3 - valor) * lado + lado / 2}" text-anchor="end">{texto}</text>')
    ancho, alto = izq + 3 * lado + 40, arriba + 3 * lado + 90
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" width="{ancho}" height="{alto}" role="img" aria-labelledby="t d">
<title id="t">Matriz de probabilidad e impacto</title>
<desc id="d">{len(RIESGOS)} riesgos de atam-lite.md; zona crítica cuando probabilidad × impacto ≥ {UMBRAL_CRITICO}.</desc>
<style>
  svg {{ --superficie: #fcfcfb; --texto: #0b0b0b; --texto-2: #52514e; --critica: #d03b3b; --media: #fab219; --baja: #e4e3df; }}
  @media (prefers-color-scheme: dark) {{
    svg {{ --superficie: #1a1a19; --texto: #f0efec; --texto-2: #c3c2b7; --baja: #3a3a37; }}
  }}
  .fondo {{ fill: var(--superficie); }}
  text {{ font-family: Helvetica, Arial, sans-serif; fill: var(--texto); }}
  .encabezado {{ font-size: 16px; font-weight: bold; }}
  .eje, .nota {{ font-size: 12px; fill: var(--texto-2); }}
  .titulo-eje {{ font-size: 13px; font-weight: bold; fill: var(--texto-2); }}
  .zona {{ font-size: 12px; font-weight: bold; }}
  .riesgo {{ font-size: 14px; font-weight: bold; }}
  .celda {{ stroke: var(--superficie); stroke-width: 2; }}
  .zona-crítica {{ fill: var(--critica); fill-opacity: 0.30; }}
  .zona-media {{ fill: var(--media); fill-opacity: 0.30; }}
  .zona-baja {{ fill: var(--baja); fill-opacity: 0.60; }}
</style>
<rect class="fondo" width="{ancho}" height="{alto}"/>
<text class="encabezado" x="{izq}" y="32">Matriz de probabilidad e impacto (ATAM-lite)</text>
<text class="nota" x="{izq}" y="54">Cada celda indica su zona y su puntaje P × I; zona crítica: P × I ≥ {UMBRAL_CRITICO}.</text>
{chr(10).join(partes)}
<text class="titulo-eje" x="{izq + 1.5 * lado}" y="{arriba + 3 * lado + 48}" text-anchor="middle">Impacto</text>
<text class="titulo-eje" x="24" y="{arriba + 1.5 * lado}" text-anchor="middle" transform="rotate(-90 24 {arriba + 1.5 * lado})">Probabilidad</text>
<text class="nota" x="{izq}" y="{alto - 12}">Fuente: docs/architecture/riesgos/matriz_riesgos.py</text>
</svg>
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    SALIDA.write_text(svg(), encoding="utf-8")
    print(tabla())


if __name__ == "__main__":
    main()
