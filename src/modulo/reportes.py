"""Esqueleto del diagrama de clases de la HU-01 (clases.puml).

Requiere Python 3.10 o superior.

Notas:
- Solo las operaciones de Reporte tienen lógica (transiciones del diagrama de estados).
- El resto de operaciones y los adaptadores lanzan NotImplementedError.
- No están en el diagrama: el método privado Reporte._transicionar, los tres
  adaptadores y los nombres de los atributos que materializan las asociaciones
  (consentimiento, reportes, ciudadano, foto, ubicacion, estado, almacen_local,
  puerto_envio, almacen_servidor).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class EstadoReporte(Enum):
    BORRADOR = "BORRADOR"
    ENCOLADO = "ENCOLADO"
    RECIBIDO = "RECIBIDO"
    VERIFICADO = "VERIFICADO"
    ATENDIDO = "ATENDIDO"
    RECHAZADO = "RECHAZADO"


@dataclass(kw_only=True)
class Consentimiento:
    # Si fecha_aceptacion tiene valor, el consentimiento está aceptado.
    fecha_aceptacion: datetime | None = None  # [0..1]

    def aceptar(self, fecha: datetime) -> None:
        raise NotImplementedError

    def esta_aceptado(self) -> bool:
        raise NotImplementedError


@dataclass(kw_only=True)
class Foto:
    contenido: bytes
    tipo_mime: str


@dataclass(kw_only=True)
class Ubicacion:
    latitud: float
    longitud: float


@dataclass(kw_only=True)
class Ciudadano:
    id: UUID = field(default_factory=uuid4)
    # Ciudadano "1" *-- "1" Consentimiento
    consentimiento: Consentimiento = field(default_factory=Consentimiento)
    # Ciudadano "1" -- "0..*" Reporte
    reportes: list[Reporte] = field(default_factory=list, repr=False, compare=False)

    def puede_reportar(self) -> bool:
        raise NotImplementedError


@dataclass(kw_only=True)
class Reporte:
    id: UUID = field(default_factory=uuid4)
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    fecha_recepcion: datetime | None = None  # [0..1]
    # Ciudadano "1" -- "0..*" Reporte
    ciudadano: Ciudadano = field(repr=False, compare=False)
    # Reporte "1" *-- "1" Foto
    foto: Foto
    # Reporte "1" *-- "1" Ubicacion
    ubicacion: Ubicacion
    # Reporte "0..*" --> "1" EstadoReporte
    estado: EstadoReporte = EstadoReporte.BORRADOR

    def _transicionar(self, origen: EstadoReporte, destino: EstadoReporte) -> None:
        if self.estado is not origen:
            raise ValueError(
                f"Transición inválida: de {self.estado.name} a {destino.name} "
                f"(se esperaba {origen.name})"
            )
        self.estado = destino

    def esta_encolado(self) -> bool:
        return self.estado is EstadoReporte.ENCOLADO

    def encolar(self) -> None:
        self._transicionar(EstadoReporte.BORRADOR, EstadoReporte.ENCOLADO)

    def marcar_recibido(self, fecha: datetime) -> None:
        self._transicionar(EstadoReporte.ENCOLADO, EstadoReporte.RECIBIDO)
        self.fecha_recepcion = fecha

    def verificar(self) -> None:
        self._transicionar(EstadoReporte.RECIBIDO, EstadoReporte.VERIFICADO)

    def rechazar(self) -> None:
        self._transicionar(EstadoReporte.RECIBIDO, EstadoReporte.RECHAZADO)

    def marcar_atendido(self) -> None:
        self._transicionar(EstadoReporte.VERIFICADO, EstadoReporte.ATENDIDO)


# --- Puertos (interfaces) ---


class AlmacenLocalReportes(ABC):
    """Puerto de almacenamiento en el celular."""

    @abstractmethod
    def guardar(self, reporte: Reporte) -> None:
        """Crea el reporte o actualiza el existente."""

    @abstractmethod
    def buscar_por_estado(self, estado: EstadoReporte) -> list[Reporte]: ...


class AlmacenServidorReportes(ABC):
    """Puerto de almacenamiento en el servidor."""

    @abstractmethod
    def guardar_si_no_existe(self, reporte: Reporte) -> bool:
        """Operación atómica: True si lo guardó, False si ya existía."""


class PuertoEnvioReportes(ABC):
    """Puerto de salida del celular hacia el servidor."""

    @abstractmethod
    def enviar(self, reporte: Reporte) -> bool:
        """True si el servidor confirmó que tiene el reporte."""


# --- Servicios ---


@dataclass(kw_only=True)
class ServicioReportes:
    """Lado del celular: crea el reporte, lo guarda y lo reenvía."""

    # ServicioReportes "1" --> "1" AlmacenLocalReportes
    almacen_local: AlmacenLocalReportes
    # ServicioReportes "1" --> "1" PuertoEnvioReportes
    puerto_envio: PuertoEnvioReportes

    def crear_reporte(
        self, ciudadano: Ciudadano, foto: Foto, ubicacion: Ubicacion
    ) -> Reporte:
        raise NotImplementedError

    def sincronizar_pendientes(self) -> None:
        raise NotImplementedError


@dataclass(kw_only=True)
class ServicioIngesta:
    """Lado del servidor: recibe el reporte y descarta duplicados."""

    # ServicioIngesta "1" --> "1" AlmacenServidorReportes
    almacen_servidor: AlmacenServidorReportes

    def recibir(self, reporte: Reporte) -> bool:
        """True si el servidor tiene el reporte, sea nuevo o repetido."""
        raise NotImplementedError


# --- Adaptadores (implementaciones pendientes de los puertos) ---


class AdaptadorAlmacenLocalReportes(AlmacenLocalReportes):
    def guardar(self, reporte: Reporte) -> None:
        raise NotImplementedError

    def buscar_por_estado(self, estado: EstadoReporte) -> list[Reporte]:
        raise NotImplementedError


class AdaptadorAlmacenServidorReportes(AlmacenServidorReportes):
    def guardar_si_no_existe(self, reporte: Reporte) -> bool:
        raise NotImplementedError


class AdaptadorEnvioReportes(PuertoEnvioReportes):
    def enviar(self, reporte: Reporte) -> bool:
        raise NotImplementedError