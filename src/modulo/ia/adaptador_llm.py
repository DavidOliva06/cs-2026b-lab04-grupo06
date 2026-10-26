"""Adapter del LLM: arma la consulta, lee la respuesta y la pasa por los guardrails.

Si el LLM falla o un guardrail bloquea la respuesta, el reporte no se pierde:
queda marcado para revisión humana.
"""
from __future__ import annotations

import json

from externos import LLMSimulado

from .guardrails import Guardrail, RespuestaBloqueada, SalidaLLM, cadena_por_defecto
from .puerto import Clasificacion, ClasificadorDanos

INSTRUCCIONES = (
    "Clasifica el daño que describe un ciudadano tras un sismo. "
    'Responde solo con JSON: {"gravedad": "leve|moderado|grave|colapso", "resumen": "..."}. '
    "No afirmes que una estructura es segura y no incluyas datos personales."
)


class ClasificadorLLM(ClasificadorDanos):
    def __init__(
        self,
        llm: LLMSimulado,
        guardrails: Guardrail | None = None,
        temperatura: float = 0.0,
    ) -> None:
        self._llm = llm
        self._guardrails = guardrails or cadena_por_defecto()
        self._temperatura = temperatura

    def clasificar(self, descripcion: str) -> Clasificacion:
        mensajes = [
            {"rol": "sistema", "contenido": INSTRUCCIONES},
            {"rol": "usuario", "contenido": descripcion},
        ]
        try:
            respuesta = self._llm.generar(mensajes, temperatura=self._temperatura)
            texto = respuesta["salida"]["texto"]
        except Exception as error:  # cualquier falla del proveedor
            return Clasificacion(None, None, True, f"LLM no disponible: {error}")

        salida = SalidaLLM(texto, self._leer_json(texto))
        try:
            self._guardrails.revisar(salida)
        except RespuestaBloqueada as bloqueo:
            return Clasificacion(None, None, True, str(bloqueo))
        return Clasificacion(salida.datos["gravedad"], salida.datos["resumen"].strip(), False)

    @staticmethod
    def _leer_json(texto: str) -> dict | None:
        try:
            datos = json.loads(texto)
        except ValueError:
            return None
        return datos if isinstance(datos, dict) else None