"""Separa un archivo de respuestas pegadas en grabaciones/<version>/<id>.txt, sin editarlas.

Uso (desde la raíz del repositorio):
    python prompts/importar_respuestas.py criterios respuestas-v1.txt

Cada respuesta va debajo de un marcador "### RESPUESTA <version>/<id> ###". Solo se quitan las
líneas vacías del principio y del final que agrega el pegado; el contenido se guarda tal cual.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
MARCADOR = re.compile(r"^### RESPUESTA (\S+)/(\S+) ###[ \t]*$", re.M)


def main(tarea: str, archivo: str) -> None:
    texto = Path(archivo).read_text(encoding="utf-8")
    partes = MARCADOR.split(texto)
    guardadas = 0
    for i in range(1, len(partes), 3):
        version, cid, cuerpo = partes[i], partes[i + 1], partes[i + 2].strip("\r\n")
        if not cuerpo.strip():
            print(f"AVISO: {version}/{cid} está vacía; no se guarda")
            continue
        destino = RAIZ / tarea / "grabaciones" / version / f"{cid}.txt"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(cuerpo + "\n", encoding="utf-8")
        guardadas += 1
    print(f"{guardadas} respuestas guardadas en {RAIZ / tarea / 'grabaciones'}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
