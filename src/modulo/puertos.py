"""Puertos (interfaces comunes) del flujo HU-01.

Cada puerto es una Strategy: el servicio solo conoce esta interfaz y la
implementación concreta se elige al crearlo. Los nombres vienen del
diagrama de clases del Lab 05.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .modelo import Reporte


class AlmacenLocalReportes(ABC):
    """Dónde guarda el celular los reportes mientras no hay señal."""

    @abstractmethod
    def guardar(self, reporte: Reporte) -> None:
        """Crea el reporte o actualiza el existente."""

    @abstractmethod
    def buscar_por_estado(self, estado: str) -> list[Reporte]: ...


class PuertoEnvioReportes(ABC):
    """Cómo viaja un reporte del celular al servidor."""

    @abstractmethod
    def enviar(self, reporte: Reporte) -> bool:
        """True solo si el servidor confirmó que tiene el reporte."""


class AlmacenServidorReportes(ABC):
    """Dónde guarda el servidor los reportes recibidos."""

    @abstractmethod
    def guardar_si_no_existe(self, reporte: Reporte) -> bool:
        """True si lo guardó; False si ya existía."""

    @abstractmethod
    def contar(self) -> int: ...