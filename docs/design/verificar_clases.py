"""Compara docs/design/clases.puml con el diagrama que pyreverse genera desde el código.

Uso (desde la raíz del repositorio):
    cd src && PYTHONPATH=modulo:. pyreverse -o puml -p despues -d ../build \
        modulo/servicio.py modulo/modelo.py modulo/puertos.py modulo/adaptadores.py \
        modulo/fabrica.py modulo/eventos.py modulo/observadores.py modulo/decoradores.py \
        modulo/estados.py modulo/ia/puerto.py modulo/ia/adaptador_llm.py modulo/ia/cache.py \
        modulo/ia/guardrails.py && cd ..
    python docs/design/verificar_clases.py docs/design/clases.puml build/classes_despues.puml

Compara las clases y, para cada una, sus métodos y atributos públicos por nombre.
Devuelve código de salida 1 si encuentra diferencias.
"""
from __future__ import annotations

import re
import sys

DECLARACION_MANUAL = re.compile(
    r'^\s*(?:abstract\s+class|class|interface|enum)\s+"?([A-Za-z_]\w*)"?'
)
DECLARACION_PYREVERSE = re.compile(r'^\s*class\s+"(?:<color:\w+>)?([A-Za-z_]\w*)(?:</color>)?"')


def leer(ruta: str, patron: re.Pattern) -> dict[str, tuple[set[str], set[str]]]:
    clases: dict[str, tuple[set[str], set[str]]] = {}
    actual = None
    with open(ruta, encoding="utf-8") as archivo:
        for linea in archivo:
            coincidencia = patron.match(linea)
            if coincidencia:
                actual = coincidencia.group(1)
                clases[actual] = (set(), set())
                if "{" not in linea or "}" in linea:
                    actual = None
                continue
            if actual is None:
                continue
            texto = linea.strip()
            if texto == "}":
                actual = None
                continue
            if not texto or texto.startswith("'"):
                continue
            texto = re.sub(r"^[+\-#~]\s*", "", texto)
            texto = texto.replace("{abstract}", "").strip()
            nombre = re.split(r"[\s(:]", texto, maxsplit=1)[0]
            metodos, atributos = clases[actual]
            (metodos if "(" in texto else atributos).add(nombre)
    return clases


def comparar(manual: dict, generado: dict) -> list[str]:
    diferencias = []
    for nombre in sorted(set(manual) | set(generado)):
        if nombre not in generado:
            diferencias.append(f"{nombre}: está en clases.puml pero no en el código")
            continue
        if nombre not in manual:
            diferencias.append(f"{nombre}: está en el código pero no en clases.puml")
            continue
        for tipo, i in (("método", 0), ("atributo", 1)):
            faltan = generado[nombre][i] - manual[nombre][i]
            sobran = manual[nombre][i] - generado[nombre][i]
            for miembro in sorted(faltan):
                diferencias.append(f"{nombre}: falta el {tipo} {miembro} en clases.puml")
            for miembro in sorted(sobran):
                diferencias.append(f"{nombre}: el {tipo} {miembro} no existe en el código")
    return diferencias


if __name__ == "__main__":
    manual = leer(sys.argv[1], DECLARACION_MANUAL)
    generado = leer(sys.argv[2], DECLARACION_PYREVERSE)
    diferencias = comparar(manual, generado)
    print(f"Clases en clases.puml: {len(manual)} | clases en el código: {len(generado)}")
    if diferencias:
        print(f"{len(diferencias)} diferencia(s):")
        for diferencia in diferencias:
            print(f"  - {diferencia}")
        sys.exit(1)
    print("Sin diferencias: el diagrama coincide con el código.")
