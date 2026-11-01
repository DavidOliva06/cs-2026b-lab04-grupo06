from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .fabrica import FabricaEstrategias, fabrica_por_defecto
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
ENVIO_POR_DEFECTO = "http"


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

    def crear_reporte(
        self, ciudadano: Ciudadano, foto: bytes, ubicacion: tuple[float, float]
    ) -> Reporte:
        if not ciudadano.puede_reportar():
            raise ConsentimientoNoAceptado("El ciudadano no aceptó el uso de ubicación y fotos")
        reporte = Reporte(str(uuid.uuid4()), ciudadano.id, foto, ubicacion)
        self.almacen_local.guardar(reporte)
        return reporte

    def sincronizar_pendientes(self) -> int:
        """Envía los reportes pendientes y devuelve cuántos quedaron enviados."""
        enviados = 0
        for reporte in self.almacen_local.buscar_por_estado(PENDIENTE_DE_ENVIO):
            if self.envio.enviar(reporte):
                reporte.marcar_enviado(datetime.now(timezone.utc))
                self.almacen_local.guardar(reporte)
                enviados += 1
        return enviados
