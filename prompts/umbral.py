"""Puerta de calidad de los prompts para la integración continua (Lab 09, E7).

Uso (desde la raíz del repositorio, después de `promptfoo eval -o resultados.json`):
    python prompts/umbral.py criterios v3.1 85

Falla (código 1) si:
- algún caso no tiene grabación o el proveedor dio un error (la evaluación no está completa), o
- la versión vigente aprueba menos casos que el mínimo (porcentaje).
Las versiones anteriores pueden fallar: son la línea base y se conservan para comparar.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def main(tarea: str, vigente: str, minimo: float) -> int:
    datos = json.loads((RAIZ / tarea / "resultados.json").read_text(encoding="utf-8"))
    resultados = datos["results"]["results"]
    errores = [r for r in resultados if r.get("error") and not r.get("gradingResult")]
    for r in errores:
        print(f"ERROR {r['prompt']['label'].split(':', 1)[0]}/{r['vars']['id']}: {r['error']}")

    por_version: dict[str, list[bool]] = {}
    for r in resultados:
        version = r["prompt"]["label"].split(":", 1)[0].strip()
        por_version.setdefault(version, []).append(bool(r.get("success")))
    def orden(texto: str):
        return [int(n) if n.isdigit() else n for n in re.findall(r"\d+|\D+", texto)]

    for version, pasos in sorted(por_version.items(), key=lambda kv: orden(kv[0])):
        marca = "  <- vigente" if version == vigente else ""
        print(f"{tarea} {version}: {sum(pasos)}/{len(pasos)} ({100 * sum(pasos) / len(pasos):.1f} %){marca}")

    if vigente not in por_version:
        print(f"FALLA: la versión vigente {vigente} no se evaluó")
        return 1
    tasa = 100 * sum(por_version[vigente]) / len(por_version[vigente])
    if errores or tasa < minimo:
        print(f"FALLA: {vigente} {tasa:.1f} % (mínimo {minimo:.0f} %), {len(errores)} errores")
        return 1
    print(f"OK: {vigente} {tasa:.1f} % >= {minimo:.0f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], float(sys.argv[3])))
