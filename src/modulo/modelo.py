"""Entidades del flujo HU-01, separadas para que servicio y adaptadores las compartan."""
from __future__ import annotations

from datetime import datetime

PENDIENTE_DE_ENVIO = "PENDIENTE_DE_ENVIO"
ENVIADO = "ENVIADO"


class Ciudadano:
    def __init__(self, id: str, consentimiento_aceptado: bool = False) -> None:
        self.id = id
        self.consentimiento_aceptado = consentimiento_aceptado

    def puede_reportar(self) -> bool:
        return self.consentimiento_aceptado


class Reporte:
    def __init__(
        self,
        id: str,
        ciudadano_id: str,
        foto: bytes,
        ubicacion: tuple[float, float],
        estado: str = PENDIENTE_DE_ENVIO,
        fecha_envio: datetime | None = None,
    ) -> None:
        self.id = id
        self.ciudadano_id = ciudadano_id
        self.foto = foto
        self.ubicacion = ubicacion
        self.estado = estado
        self.fecha_envio = fecha_envio

    def marcar_enviado(self, fecha: datetime) -> None:
        self.estado = ENVIADO
        self.fecha_envio = fecha