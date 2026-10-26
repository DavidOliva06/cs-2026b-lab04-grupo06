
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union
@dataclass(frozen=True)
class ConsentimientoRechazado:
    ciudadano_id: str
@dataclass(frozen=True)
class ReporteGuardado:
    reporte_id: str
@dataclass(frozen=True)
class SincronizacionTerminada:
    enviados: int
    pendientes: int
Evento = Union[ConsentimientoRechazado, ReporteGuardado, SincronizacionTerminada]
class Observador(ABC):
    @abstractmethod
    def notificar(self, evento: Evento) -> None: ...


class Publicador:
    def __init__(self) -> None:
        self._observadores: list[Observador] = []

    def suscribir(self, observador: Observador) -> None:
        self._observadores.append(observador)

    def desuscribir(self, observador: Observador) -> None:
        self._observadores.remove(observador)

    def publicar(self, evento: Evento) -> None:
        for observador in list(self._observadores):
            observador.notificar(evento)