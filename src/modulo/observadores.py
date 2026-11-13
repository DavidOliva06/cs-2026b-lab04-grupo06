"""Suscriptores de la PWA a los eventos del flujo HU-01."""
from __future__ import annotations

from .eventos import (
    ConsentimientoRechazado,
    Evento,
    Observador,
    ReporteGuardado,
    SincronizacionTerminada,
)


class VistaConsola(Observador):
    """Muestra al ciudadano los mensajes del flujo (los mismos que antes armaba el controlador)."""

    def notificar(self, evento: Evento) -> None:
        if isinstance(evento, ConsentimientoRechazado):
            self._mostrar("Debe aceptar el uso de su ubicación y sus fotos")
        elif isinstance(evento, ReporteGuardado):
            self._mostrar("Pendiente de envío")
        elif isinstance(evento, SincronizacionTerminada):
            if evento.enviados:
                self._mostrar(f"Enviado ({evento.enviados} reporte(s))")
            else:
                self._mostrar("Sigue pendiente de envío")

    def _mostrar(self, texto: str) -> None:
        print(f"  [PWA] {texto}")


class ContadorPendientes(Observador):
    """Indicador de reportes que aún no llegan al servidor, visible hasta que se confirman."""

    def __init__(self, pendientes: int = 0) -> None:
        self.pendientes = pendientes

    def notificar(self, evento: Evento) -> None:
        if isinstance(evento, ReporteGuardado):
            self.pendientes += 1
        elif isinstance(evento, SincronizacionTerminada):
            self.pendientes = evento.pendientes
