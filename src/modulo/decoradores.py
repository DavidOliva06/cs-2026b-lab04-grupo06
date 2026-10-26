"""Decorator: registro de cada intento de envío, sin tocar el adaptador ni el servicio.

Envuelve cualquier PuertoEnvioReportes y deja una línea por intento, con el
resultado y la duración, para poder medir la meta de QA-01 (reportes que llegan
al servidor). Devuelve exactamente lo que devuelve el envío envuelto.
"""
from __future__ import annotations

import logging
import time

from .modelo import Reporte
from .puertos import PuertoEnvioReportes

class EnvioConRegistro(PuertoEnvioReportes):
    def __init__(self, envio: PuertoEnvioReportes, registro: logging.Logger | None = None) -> None:
        self._envio = envio
        self._registro = registro or logging.getLogger("sismoreporta.envio")

    def enviar(self, reporte: Reporte) -> bool:
        inicio = time.perf_counter()
        confirmado = self._envio.enviar(reporte)
        duracion_ms = (time.perf_counter() - inicio) * 1000
        self._registro.info(
            "Envío del reporte %s: %s (%.1f ms)",
            reporte.id,
            "confirmado" if confirmado else "pendiente",
            duracion_ms,
        )
        return confirmado