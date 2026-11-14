"""Gráfico de la tasa de aprobación por versión de las dos tareas (Lab 09, E8).

Uso (desde la raíz, después de evaluar):  python prompts/grafico.py
Lee prompts/<tarea>/resultados.md y escribe docs/prompts/tasa-por-version.png.
"""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ.parent / "docs" / "prompts" / "tasa-por-version.png"
TAREAS = {"criterios": "Tarea A: criterios de aceptación (9 casos)",
          "prioridad": "Tarea B: prioridad de reportes (10 casos)"}
SERIE, TINTA, TINTA2, MUTED, GRILLA, FONDO = "#2a78d6", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"


def tasas(tarea: str) -> list[tuple[str, float]]:
    texto = (RAIZ / tarea / "resultados.md").read_text(encoding="utf-8")
    seccion = texto.split("## Resultado por caso")[0]
    return [(v, float(t)) for v, t in re.findall(r"^\| (v[\w.]+) \| \d+/\d+ \| ([\d.]+) % \|$", seccion, re.M)]


def main() -> None:
    fig, ejes = plt.subplots(1, 2, figsize=(10, 3.8), dpi=150, facecolor=FONDO,
                             gridspec_kw={"width_ratios": [4, 2.4]})
    for eje, (tarea, titulo) in zip(ejes, TAREAS.items()):
        datos = tasas(tarea)
        x = range(len(datos))
        eje.set_facecolor(FONDO)
        eje.bar(x, [t for _, t in datos], width=0.55, color=SERIE, zorder=2)
        for i, (_, t) in enumerate(datos):
            eje.text(i, t + 3, f"{t:.0f} %".replace(".", ","), ha="center", va="bottom", fontsize=9, color=TINTA)
        eje.axhline(85, color=TINTA2, linewidth=1, linestyle=(0, (4, 3)), zorder=3)
        eje.text(-0.4, 87, "meta 85 %", ha="left", va="bottom", fontsize=8, color=TINTA2)
        eje.set_xticks(list(x), [v for v, _ in datos], fontsize=9, color=TINTA2)
        eje.set_ylim(0, 112)
        eje.set_yticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100 %"], fontsize=8, color=MUTED)
        eje.grid(axis="y", color=GRILLA, linewidth=0.6, zorder=0)
        for lado in ("top", "right", "left"):
            eje.spines[lado].set_visible(False)
        eje.spines["bottom"].set_color(GRILLA)
        eje.tick_params(length=0)
        eje.set_title(titulo, fontsize=10, color=TINTA, loc="left")
    fig.suptitle("Casos aprobados por versión del prompt (Opus 5.5, respuestas grabadas)",
                 fontsize=11, color=TINTA, x=0.01, ha="left")
    fig.tight_layout()
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SALIDA, facecolor=FONDO)
    print(SALIDA)


if __name__ == "__main__":
    main()
