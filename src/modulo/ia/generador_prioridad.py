"""Generador de la Tarea B (Lab 09): sugiere la prioridad de un reporte con un prompt versionado.

- Carga la plantilla prompts/prioridad/<version>.txt, la misma que evalúa promptfoo, y reemplaza
  {{id}} y {{reporte}} igual que promptfoo y prompts/renderizar.py.
- La envía al modelo por el puerto ProveedorLLM; no conoce a ningún proveedor concreto.
- Valida la respuesta con prompts/prioridad/esquema.json y con los guardrails del Lab 07
  (NoDeclararSeguro y SinDatosPersonales). Si algo falla, lanza SalidaInvalida y el reporte
  debe ir a revisión humana: una salida del LLM nunca se usa sin validar.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import jsonschema

from .guardrails import NoDeclararSeguro, RespuestaBloqueada, SalidaLLM, SinDatosPersonales
from .puerto import ProveedorLLM

RAIZ_PROMPTS = Path(__file__).resolve().parents[3] / "prompts"
TAREA = "prioridad"
# La versión con la mayor tasa de aprobación en prompts/prioridad/resultados.md.
VERSION_VIGENTE = "v2"


class SalidaInvalida(Exception):
    """La respuesta del modelo no cumple el contrato; no se usa."""


@dataclass(frozen=True)
class SugerenciaPrioridad:
    reporte_id: str
    gravedad: str | None
    prioridad: str | None
    personas_en_riesgo: bool
    requiere_revision: bool
    motivo: str


def renderizar(plantilla: str, variables: dict[str, str]) -> str:
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: str(variables[m.group(1)]), plantilla)


class GeneradorPrioridad:
    def __init__(
        self,
        proveedor: ProveedorLLM,
        version: str = VERSION_VIGENTE,
        raiz: Path = RAIZ_PROMPTS,
        temperatura: float = 0.0,
    ) -> None:
        carpeta = raiz / TAREA
        self.version = version
        self._proveedor = proveedor
        self._temperatura = temperatura
        self._plantilla = (carpeta / f"{version}.txt").read_text(encoding="utf-8")
        esquema = json.loads((carpeta / "esquema.json").read_text(encoding="utf-8"))
        self._validador = jsonschema.Draft7Validator(esquema)
        self._guardrails = NoDeclararSeguro(SinDatosPersonales())

    def prompt(self, reporte_id: str, texto: str) -> str:
        return renderizar(self._plantilla, {"id": reporte_id, "reporte": texto}).strip()

    def generar(self, reporte_id: str, texto: str) -> SugerenciaPrioridad:
        mensajes = [{"rol": "usuario", "contenido": self.prompt(reporte_id, texto)}]
        respuesta = self._proveedor.generar(mensajes, temperatura=self._temperatura)
        salida = respuesta["salida"]["texto"].strip()

        try:
            datos = json.loads(salida)
        except ValueError as error:
            raise SalidaInvalida(f"la respuesta no es JSON: {error}") from None
        errores = sorted(self._validador.iter_errors(datos), key=lambda e: list(e.path))
        if errores:
            raise SalidaInvalida(f"no cumple el esquema: {errores[0].message}")
        if datos["reporte_id"] != reporte_id:
            raise SalidaInvalida(f"responde por otro reporte: {datos['reporte_id']!r}")
        try:
            self._guardrails.revisar(SalidaLLM(salida, datos))
        except RespuestaBloqueada as bloqueo:
            raise SalidaInvalida(str(bloqueo)) from None
        return SugerenciaPrioridad(**datos)
