"""Factory (registro): crea la estrategia adecuada para cada puerto a partir de un nombre.

El registro es un objeto que se crea y se pasa; no hay estado global ni Singleton.
"""
from __future__ import annotations

from typing import Callable, TypeVar

from .adaptadores import AdaptadorEnvioHttp, AdaptadorIndexedDB, AdaptadorPostgres
from .puertos import AlmacenLocalReportes, AlmacenServidorReportes, PuertoEnvioReportes

P = TypeVar("P")


class FabricaEstrategias:
    def __init__(self) -> None:
        self._registro: dict[tuple[type, str], Callable[..., object]] = {}

    def registrar(self, puerto: type[P], nombre: str, constructor: Callable[..., P]) -> None:
        self._registro[(puerto, nombre)] = constructor

    def crear(self, puerto: type[P], nombre: str, **opciones: object) -> P:
        try:
            constructor = self._registro[(puerto, nombre)]
        except KeyError:
            raise ValueError(f"No hay una estrategia '{nombre}' para {puerto.__name__}") from None
        estrategia = constructor(**opciones)
        if not isinstance(estrategia, puerto):
            raise TypeError(f"'{nombre}' no implementa {puerto.__name__}")
        return estrategia


def fabrica_por_defecto() -> FabricaEstrategias:
    """Registro con un adaptador por cada servicio externo simulado."""
    fabrica = FabricaEstrategias()
    fabrica.registrar(AlmacenLocalReportes, "indexeddb", AdaptadorIndexedDB)
    fabrica.registrar(PuertoEnvioReportes, "http", AdaptadorEnvioHttp)
    fabrica.registrar(AlmacenServidorReportes, "postgres", AdaptadorPostgres)
    return fabrica