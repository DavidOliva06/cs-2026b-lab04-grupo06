"""Servicio del celular del flujo HU-01 (Strategy + Adapter + Factory, Observer y Decorator).

Solo conoce puertos (ADR-005): el endpoint HTTP, el controlador y la demostración están en
entrada.py desde el Lab 08 (contrato adr005-servicio-sin-infraestructura de .importlinter).
Publica eventos (Observer, en eventos.py) a los que se suscriben la vista y el contador de
pendientes (observadores.py), y el envío por defecto queda registrado con un Decorator.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .eventos import (
    ConsentimientoRechazado,
    Observador,
    Publicador,
    ReporteGuardado,
    SincronizacionTerminada,
)
from .fabrica import FabricaEstrategias, fabrica_por_defecto
from .adaptadores import AdaptadorIndexedDB  # VIOLACIÓN DE PRUEBA: el servicio conoce un adaptador (ADR-005)
from .modelo import ENVIADO, PENDIENTE_DE_ENVIO, Ciudadano, Reporte
from .puertos import AlmacenLocalReportes, PuertoEnvioReportes

__all__ = [
    "PENDIENTE_DE_ENVIO",
    "ENVIADO",
    "ConsentimientoNoAceptado",
    "Ciudadano",
    "Reporte",
    "ServicioReportes",
]

ALMACEN_LOCAL_POR_DEFECTO = "indexeddb"
ENVIO_POR_DEFECTO = "http_con_registro"


class ConsentimientoNoAceptado(Exception):
    """El ciudadano no aceptó el uso de su ubicación y sus fotos (criterio 4)."""


# --- Lado del celular -------------------------------------------------------


class ServicioReportes:
    """Crea reportes, los guarda en el celular y los envía al recuperar la señal."""

    def __init__(
        self,
        almacen_local: AlmacenLocalReportes | None = None,
        envio: PuertoEnvioReportes | None = None,
        fabrica: FabricaEstrategias | None = None,
    ) -> None:
        fabrica = fabrica or fabrica_por_defecto()
        self.almacen_local = almacen_local or fabrica.crear(
            AlmacenLocalReportes, ALMACEN_LOCAL_POR_DEFECTO
        )
        self.envio = envio or fabrica.crear(PuertoEnvioReportes, ENVIO_POR_DEFECTO)
        self._eventos = Publicador()

    def suscribir(self, observador: Observador) -> None:
        self._eventos.suscribir(observador)

    def desuscribir(self, observador: Observador) -> None:
        self._eventos.desuscribir(observador)

    def crear_reporte(
        self, ciudadano: Ciudadano, foto: bytes, ubicacion: tuple[float, float]
    ) -> Reporte:
        if not ciudadano.puede_reportar():
            self._eventos.publicar(ConsentimientoRechazado(ciudadano.id))
            raise ConsentimientoNoAceptado("El ciudadano no aceptó el uso de ubicación y fotos")
        reporte = Reporte(str(uuid.uuid4()), ciudadano.id, foto, ubicacion)
        self.almacen_local.guardar(reporte)
        self._eventos.publicar(ReporteGuardado(reporte.id))
        return reporte

    def sincronizar_pendientes(self) -> int:
        """Envía los reportes pendientes y devuelve cuántos quedaron enviados."""
        pendientes = self.almacen_local.buscar_por_estado(PENDIENTE_DE_ENVIO)
        enviados = 0
        for reporte in pendientes:
            if self.envio.enviar(reporte):
                reporte.marcar_enviado(datetime.now(timezone.utc))
                self.almacen_local.guardar(reporte)
                enviados += 1
        self._eventos.publicar(SincronizacionTerminada(enviados, len(pendientes) - enviados))
        return enviados

