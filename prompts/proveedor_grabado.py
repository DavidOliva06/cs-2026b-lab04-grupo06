"""Proveedor de promptfoo que devuelve respuestas grabadas, sin clave de API (Lab 09).

Cada respuesta se grabó a mano desde el asistente (Claude.ai, Opus 5.5, esfuerzo Alto), en un chat
nuevo por caso, y se guardó sin editar en <tarea>/grabaciones/<version>/<id>.txt.
promptfoo llama a call_api por cada combinación de prompt y caso:
- la versión sale de la etiqueta del prompt (label: v1, v2, ...), y
- el caso, de la variable id de casos.yaml.
Se reemplaza por un modelo real cambiando el proveedor en promptfooconfig.yaml (temperatura 0).
"""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def ruta_grabacion(tarea: str, version: str, caso: str) -> Path:
    return RAIZ / tarea / "grabaciones" / version / f"{caso}.txt"


def call_api(prompt: str, options: dict, context: dict) -> dict:
    tarea = options.get("config", {}).get("tarea", "criterios")
    # Con prompts de archivo, promptfoo arma la etiqueta como "v1: v1.txt: <texto>"; la versión
    # es lo que va antes de los primeros dos puntos.
    version = context["prompt"]["label"].split(":", 1)[0].strip()
    caso = context["vars"]["id"]
    ruta = ruta_grabacion(tarea, version, caso)
    if not ruta.exists():
        return {"error": f"No hay grabación para {tarea}/{version}/{caso} ({ruta})"}
    return {"output": ruta.read_text(encoding="utf-8").rstrip("\n")}
