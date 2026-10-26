"""Patrón State para el ciclo de vida del Reporte.

Sigue docs/design/estado-estadoReporte.mmd (Lab 05):

    [*] --> Borrador
    Borrador  --encolar()-->        Encolado   [foto y ubicación completas]
    Encolado  --enviar()-->         Encolado   [servidor no confirma]
    Encolado  --recibir()-->        Recibido   [servidor confirma el reporte]
    Recibido  --verificar()-->      Verificado [brigadista confirma el daño]
    Recibido  --rechazar()-->       Rechazado  [reporte falso o repetido]
    Verificado --marcar_atendido()--> Atendido [brigada terminó la atención]
    Atendido y Rechazado son estados finales.

La clase base EstadoReporte prohíbe todas las transiciones; cada subclase
redefine solo las que el diagrama permite desde ese estado. Cada transición
devuelve el estado siguiente, así que los estados no guardan datos y pueden
compartirse sin problema.

Requiere Python 3.10 o superior.
"""
from __future__ import annotations

from typing import NoReturn

from .modelo import Reporte


class TransicionInvalida(Exception):
    """La operación no está permitida en el estado actual del reporte."""


# --- Clase base: todo prohibido ---------------------------------------------


class EstadoReporte:
    nombre = "EstadoReporte"
    es_final = False

    def encolar(self, reporte: Reporte) -> EstadoReporte:
        self._prohibir("encolar")

    def enviar(self, reporte: Reporte) -> EstadoReporte:
        self._prohibir("enviar")

    def recibir(self, reporte: Reporte) -> EstadoReporte:
        self._prohibir("recibir")

    def verificar(self, reporte: Reporte) -> EstadoReporte:
        self._prohibir("verificar")

    def rechazar(self, reporte: Reporte) -> EstadoReporte:
        self._prohibir("rechazar")

    def marcar_atendido(self, reporte: Reporte) -> EstadoReporte:
        self._prohibir("marcar_atendido")

    def _prohibir(self, operacion: str) -> NoReturn:
        raise TransicionInvalida(f"No se puede {operacion}() un reporte en estado {self.nombre}")

    def __eq__(self, otro: object) -> bool:
        return type(self) is type(otro)

    def __hash__(self) -> int:
        return hash(type(self))

    def __repr__(self) -> str:
        return self.nombre


# --- Una subclase por estado: solo redefine lo permitido --------------------


class Borrador(EstadoReporte):
    nombre = "Borrador"

    def encolar(self, reporte: Reporte) -> EstadoReporte:
        # Guarda: [foto y ubicación completas]
        if not reporte.foto or reporte.ubicacion is None:
            raise TransicionInvalida("No se puede encolar() un reporte sin foto o sin ubicación")
        return Encolado()


class Encolado(EstadoReporte):
    nombre = "Encolado"

    def enviar(self, reporte: Reporte) -> EstadoReporte:
        # [servidor no confirma]: el reporte sigue en la cola local.
        return self

    def recibir(self, reporte: Reporte) -> EstadoReporte:
        # [servidor confirma el reporte]
        return Recibido()


class Recibido(EstadoReporte):
    nombre = "Recibido"

    def verificar(self, reporte: Reporte) -> EstadoReporte:
        return Verificado()

    def rechazar(self, reporte: Reporte) -> EstadoReporte:
        return Rechazado()


class Verificado(EstadoReporte):
    nombre = "Verificado"

    def marcar_atendido(self, reporte: Reporte) -> EstadoReporte:
        return Atendido()


class Atendido(EstadoReporte):
    nombre = "Atendido"
    es_final = True


class Rechazado(EstadoReporte):
    nombre = "Rechazado"
    es_final = True


# --- Contexto ---------------------------------------------------------------


class CicloReporte:
    """Contexto del patrón: guarda el estado actual de un reporte y delega en él."""

    def __init__(self, reporte: Reporte, estado: EstadoReporte | None = None) -> None:
        self.reporte = reporte
        self._estado = estado or Borrador()

    @property
    def estado(self) -> EstadoReporte:
        return self._estado

    def encolar(self) -> None:
        self._estado = self._estado.encolar(self.reporte)

    def enviar(self) -> None:
        self._estado = self._estado.enviar(self.reporte)

    def recibir(self) -> None:
        self._estado = self._estado.recibir(self.reporte)

    def verificar(self) -> None:
        self._estado = self._estado.verificar(self.reporte)

    def rechazar(self) -> None:
        self._estado = self._estado.rechazar(self.reporte)

    def marcar_atendido(self) -> None:
        self._estado = self._estado.marcar_atendido(self.reporte)