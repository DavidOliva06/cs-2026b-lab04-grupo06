"""Generador de la Tarea B (Lab 09): sugiere la prioridad de un reporte con un prompt versionado.

- Carga la plantilla prompts/prioridad/<version>.txt, la misma que evalúa promptfoo, y reemplaza
  {{id}} y {{reporte}} igual que promptfoo y prompts/renderizar.py.
- La envía al modelo por el puerto ProveedorLLM; no conoce a ningún proveedor concreto.
- Valida la respuesta con prompts/prioridad/esquema.json y con los guardrails del Lab 07
  (NoDeclararSeguro y SinDatosPersonales). Si algo falla, lanza SalidaInvalida y el reporte
  debe ir a revisión humana: una salida del LLM nunca se usa sin validar.

Defensas en capas contra la inyección (Figura 4 de la guía; agregadas en E5, ver
prompts/seguridad/red-team.md):
  1. Delimitadores: el reporte va entre <reporte> y </reporte>, y antes se neutralizan los signos
     < y > del texto, para que el ciudadano no pueda cerrar la etiqueta ni esconder comentarios.
  2. Instrucción explícita en el prompt: el texto del reporte es un dato, no órdenes.
  3. Validación de salida: esquema JSON y guardrails.
  4. Mínimo privilegio: el generador solo sugiere; si el texto trae instrucciones para el sistema,
     el código fuerza requiere_revision = True aunque el modelo diga lo contrario, y la sugerencia
     no se aplica sin la revisión del coordinador.
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

# Capa 4: señales de que el texto del reporte le habla al sistema y no describe un daño.
SENALES_DE_INSTRUCCION = {
    "ignorar instrucciones": r"\bignor[ae]\w*\s+(todas\s+)?(tus|las|sus)\s+instrucciones",
    "instrucción para el sistema": r"\binstrucci[oó]n(es)?\s+(\w+\s+)?(para|del|al)\s+(el\s+)?sistema",
    "se hace pasar por el sistema": r"(^|[\s.;:])sistema\s*:",
    "nota para la IA": r"\b(nota|mensaje|orden)\s+para\s+(la\s+)?ia\b",
    "pide revelar el prompt": r"\binstrucciones\s+que\s+recibiste",
    "cambia el formato o el idioma": r"\bno\s+respondas\s+en\s+json|\banswer\s+only\b|\bfrom\s+now\s+on\b",
    "dicta la prioridad": r"\b(autorizo|marca\w*|asigna\w*)\b[^.]{0,60}\bprioridad\b|\bprioridad\s+(critica|crítica)\b",
    "pide evitar la revisión": r"\bno\s+lo(s)?\s+marques\s+para\s+revisi[oó]n|requiere_revision",
}


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
    alertas: tuple[str, ...] = ()


def neutralizar(texto: str) -> str:
    """Capa 1: el texto del ciudadano no puede abrir ni cerrar etiquetas del prompt."""
    return texto.replace("<", "‹").replace(">", "›")


def detectar_instrucciones(texto: str) -> tuple[str, ...]:
    """Capa 4: nombres de las señales de instrucción que aparecen en el texto del reporte."""
    return tuple(
        nombre for nombre, patron in SENALES_DE_INSTRUCCION.items()
        if re.search(patron, texto, re.IGNORECASE)
    )


def renderizar(plantilla: str, variables: dict[str, str]) -> str:
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: str(variables[m.group(1)]), plantilla)


class GeneradorPrioridad:
    def __init__(
        self,
        proveedor: ProveedorLLM,
        version: str = VERSION_VIGENTE,
        raiz: Path = RAIZ_PROMPTS,
        temperatura: float = 0.0,
        defensas: bool = True,
    ) -> None:
        carpeta = raiz / TAREA
        self.version = version
        self._proveedor = proveedor
        self._temperatura = temperatura
        self._defensas = defensas  # False solo para medir el "antes" del red teaming
        self._plantilla = (carpeta / f"{version}.txt").read_text(encoding="utf-8")
        esquema = json.loads((carpeta / "esquema.json").read_text(encoding="utf-8"))
        self._validador = jsonschema.Draft7Validator(esquema)
        self._guardrails = NoDeclararSeguro(SinDatosPersonales())

    def prompt(self, reporte_id: str, texto: str) -> str:
        if self._defensas:
            texto = neutralizar(texto)
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
        alertas = detectar_instrucciones(texto) if self._defensas else ()
        if alertas:
            datos["requiere_revision"] = True
        return SugerenciaPrioridad(**datos, alertas=alertas)
