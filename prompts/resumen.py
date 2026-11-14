"""Resume resultados.json de promptfoo en tablas Markdown (por versión, por caso y por aserción).

Uso (desde la raíz del repositorio):
    python prompts/resumen.py criterios     # lee prompts/criterios/resultados.json
                                            # escribe prompts/criterios/resultados.md
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def cargar(tarea: str):
    datos = json.loads((RAIZ / tarea / "resultados.json").read_text(encoding="utf-8"))
    filas = []
    for r in datos["results"]["results"]:
        version = r["prompt"]["label"].split(":", 1)[0].strip()
        fallas = [
            (c.get("assertion") or {}).get("metric") or (c.get("assertion") or {}).get("type")
            for c in (r.get("gradingResult") or {}).get("componentResults", [])
            if not c.get("pass")
        ]
        metricas = {
            (c.get("assertion") or {}).get("metric"): c.get("pass")
            for c in (r.get("gradingResult") or {}).get("componentResults", [])
        }
        filas.append({"version": version, "caso": r["vars"]["id"], "pasa": bool(r.get("success")),
                      "fallas": fallas, "metricas": metricas, "error": r.get("error")})
    return filas


def tablas(filas) -> str:
    versiones = list(dict.fromkeys(f["version"] for f in filas))
    casos = list(dict.fromkeys(f["caso"] for f in filas))
    metricas = sorted({m for f in filas for m in f["metricas"] if m})
    out = ["## Tasa de aprobación por versión", "",
           "| Versión | Casos aprobados | Tasa |", "|---|---|---|"]
    for v in versiones:
        fs = [f for f in filas if f["version"] == v]
        ok = sum(f["pasa"] for f in fs)
        out.append(f"| {v} | {ok}/{len(fs)} | {100 * ok / len(fs):.1f} % |")
    out += ["", "## Resultado por caso", "",
            "| Caso | " + " | ".join(versiones) + " |", "|---|" + "---|" * len(versiones)]
    por = {(f["version"], f["caso"]): f for f in filas}
    for c in casos:
        celdas = []
        for v in versiones:
            f = por.get((v, c))
            if f is None:
                celdas.append("—")
            elif f["pasa"]:
                celdas.append("pasa")
            else:
                celdas.append("falla: " + ", ".join(m.split("_")[0] for m in f["fallas"] if m))
        out.append(f"| {c} | " + " | ".join(celdas) + " |")
    out += ["", "## Aprobación por aserción (casos en que se aplica)", "",
            "| Aserción | " + " | ".join(versiones) + " |", "|---|" + "---|" * len(versiones)]
    for m in metricas:
        celdas = []
        for v in versiones:
            vals = [f["metricas"][m] for f in filas if f["version"] == v and m in f["metricas"]]
            celdas.append(f"{sum(vals)}/{len(vals)}" if vals else "—")
        out.append(f"| {m} | " + " | ".join(celdas) + " |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    tarea = sys.argv[1]
    texto = f"# Resultados de promptfoo: {tarea}\n\nGenerado con `python prompts/resumen.py {tarea}`.\n\n"
    texto += tablas(cargar(tarea))
    (RAIZ / tarea / "resultados.md").write_text(texto, encoding="utf-8")
    print(texto)
