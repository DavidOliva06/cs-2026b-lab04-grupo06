"""Arma, para una versión de un prompt, el texto exacto de cada caso para pegarlo en el asistente.

Uso (desde la raíz del repositorio):
    python prompts/renderizar.py criterios v1            # escribe prompts/criterios/ejecutar-v1.txt

Reemplaza {{id}} y {{historia}} (o cualquier variable de casos.yaml) igual que promptfoo y que
generador_*.py, y genera también la plantilla respuestas-v1.txt con un marcador por caso.
Las respuestas se pegan sin editar debajo de cada marcador y se importan con importar_respuestas.py.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent


def renderizar(plantilla: str, variables: dict) -> str:
    def reemplazo(m: re.Match) -> str:
        return str(variables[m.group(1)])

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", reemplazo, plantilla)


def main(tarea: str, version: str) -> None:
    carpeta = RAIZ / tarea
    plantilla = (carpeta / f"{version}.txt").read_text(encoding="utf-8")
    casos = yaml.safe_load((carpeta / "casos.yaml").read_text(encoding="utf-8"))
    ejecutar, respuestas = [], []
    for caso in casos:
        cid = caso["vars"]["id"]
        prompt = renderizar(plantilla, caso["vars"]).strip()
        ejecutar.append(f"########## {version}/{cid}: pegar en un chat NUEVO ##########\n{prompt}\n")
        respuestas.append(f"### RESPUESTA {version}/{cid} ###\n\n")
    (carpeta / f"ejecutar-{version}.txt").write_text("\n".join(ejecutar), encoding="utf-8")
    (carpeta / f"respuestas-{version}.txt").write_text("".join(respuestas), encoding="utf-8")
    print(f"{len(casos)} prompts en {carpeta / f'ejecutar-{version}.txt'}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
