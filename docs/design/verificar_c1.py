"""Regla C1: cada mensaje del diagrama de secuencia es una operación de la clase receptora.

Uso (desde la raíz del repositorio):
    python docs/design/verificar_c1.py docs/design/secuencia-reporte.puml docs/design/clases.puml

Lee los participantes y los mensajes de llamada (-> y ->>) de la secuencia, y busca cada
operación en la clase o interfaz del mismo nombre en clases.puml. Los mensajes de retorno
(-->), los que envía el actor y las creaciones (<<create>>) no se verifican.
Devuelve código de salida 1 si algún mensaje no tiene operación.
"""
from __future__ import annotations

import re
import sys

PARTICIPANTE = re.compile(
    r'^\s*(actor|boundary|control|participant|entity)\s+"([^"]+)"\s+as\s+(\w+)'
)
MENSAJE = re.compile(r"^\s*(\w+)\s*(->>|->)\s*(\w+)\s*:\s*(.+)$")
CLASE = re.compile(r"^\s*(?:abstract\s+class|class|interface|enum)\s+(\w+)")


def leer_participantes(texto: str) -> dict[str, tuple[str, str]]:
    participantes = {}
    for linea in texto.splitlines():
        m = PARTICIPANTE.match(linea)
        if m:
            tipo, nombre, alias = m.groups()
            nombre = nombre.split("\\n")[0]
            if ":" in nombre:  # "reporte: Reporte" -> Reporte
                nombre = nombre.split(":")[1]
            participantes[alias] = (tipo, nombre.strip())
    return participantes


def leer_operaciones(texto: str) -> dict[str, set[str]]:
    clases: dict[str, set[str]] = {}
    actual = None
    for linea in texto.splitlines():
        m = CLASE.match(linea)
        if m:
            actual = m.group(1)
            clases[actual] = set()
            if "{" not in linea:
                actual = None
            continue
        if actual and linea.strip() == "}":
            actual = None
        elif actual:
            op = re.match(r"^\s*[+\-#~]?\s*(?:\{abstract\}\s*)?(\w+)\s*\(", linea)
            if op:
                clases[actual].add(op.group(1))
    return clases


if __name__ == "__main__":
    secuencia = open(sys.argv[1], encoding="utf-8").read()
    participantes = leer_participantes(secuencia)
    operaciones = leer_operaciones(open(sys.argv[2], encoding="utf-8").read())

    errores = 0
    print("| Línea | Mensaje | Clase receptora | ¿Existe la operación? |")
    print("|---|---|---|---|")
    for numero, linea in enumerate(secuencia.splitlines(), start=1):
        m = MENSAJE.match(linea)
        if not m:
            continue
        origen, _, destino, texto = m.groups()
        if participantes.get(origen, ("",))[0] == "actor" or "<<create>>" in texto:
            continue
        operacion = re.match(r"(\w+)\s*\(", texto.strip())
        if not operacion:
            continue
        clase = participantes[destino][1]
        existe = operacion.group(1) in operaciones.get(clase, set())
        errores += not existe
        print(f"| {numero} | `{texto.strip()}` | {clase} | {'Sí' if existe else 'NO'} |")
    print(f"\nMensajes sin operación: {errores}")
    sys.exit(1 if errores else 0)
