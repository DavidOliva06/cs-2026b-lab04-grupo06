"""Chain of Responsibility: guardrails que revisan la respuesta del LLM antes de usarla.

Cada guardrail revisa una sola regla del dominio y, si la respuesta pasa,
la entrega al siguiente. El primero que encuentra un problema detiene la cadena.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import NoReturn

from .puerto import GRAVEDADES

LARGO_MAXIMO_RESUMEN = 280


@dataclass(frozen=True)
class SalidaLLM:
    texto: str
    datos: dict | None  # None si el texto no era JSON válido


class RespuestaBloqueada(Exception):
    def __init__(self, guardrail: str, motivo: str) -> None:
        super().__init__(f"{guardrail}: {motivo}")
        self.guardrail = guardrail
        self.motivo = motivo


class Guardrail(ABC):
    nombre = "Guardrail"

    def __init__(self, siguiente: Guardrail | None = None) -> None:
        self._siguiente = siguiente

    def revisar(self, salida: SalidaLLM) -> None:
        self._verificar(salida)
        if self._siguiente is not None:
            self._siguiente.revisar(salida)

    @abstractmethod
    def _verificar(self, salida: SalidaLLM) -> None: ...

    def _bloquear(self, motivo: str) -> NoReturn:
        raise RespuestaBloqueada(self.nombre, motivo)


class FormatoValido(Guardrail):
    """No inventar categorías: JSON con una gravedad permitida y un resumen breve."""

    nombre = "FormatoValido"

    def _verificar(self, salida: SalidaLLM) -> None:
        if not isinstance(salida.datos, dict):
            self._bloquear("la respuesta no es un objeto JSON")
        if salida.datos.get("gravedad") not in GRAVEDADES:
            self._bloquear(f"gravedad no permitida: {salida.datos.get('gravedad')!r}")
        resumen = salida.datos.get("resumen")
        if not isinstance(resumen, str) or not resumen.strip():
            self._bloquear("falta el resumen")
        if len(resumen) > LARGO_MAXIMO_RESUMEN:
            self._bloquear(f"el resumen supera {LARGO_MAXIMO_RESUMEN} caracteres")


class NoDeclararSeguro(Guardrail):
    """No afirmar que una estructura es segura: eso solo lo decide un evaluador en sitio."""

    nombre = "NoDeclararSeguro"
    PATRONES = [
        r"\b(es|está|esta|son|están|estan)\s+segur[oa]s?\b",
        r"\bpueden?\s+(ingresar|entrar|volver|regresar|habitar)",
        r"\b(sin|no\s+hay|ningún|ningun)\s+riesgo\b",
        r"\bhabitable\b",
    ]

    def _verificar(self, salida: SalidaLLM) -> None:
        for patron in self.PATRONES:
            if re.search(patron, salida.texto, re.IGNORECASE):
                self._bloquear("declara segura una estructura dañada")


class SinDatosPersonales(Guardrail):
    """No exponer datos personales (Ley 29733): ni DNI ni números de celular."""

    nombre = "SinDatosPersonales"
    PATRONES = {
        "un número de celular": r"\b9\d{8}\b",
        "un DNI": r"\b\d{8}\b",
    }

    def _verificar(self, salida: SalidaLLM) -> None:
        for dato, patron in self.PATRONES.items():
            if re.search(patron, salida.texto):
                self._bloquear(f"incluye {dato}")


def cadena_por_defecto() -> Guardrail:
    return FormatoValido(NoDeclararSeguro(SinDatosPersonales()))