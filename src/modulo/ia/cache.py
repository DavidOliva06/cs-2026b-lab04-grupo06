"""Decorator de caché para cualquier ClasificadorDanos.

Tras un sismo llegan muchas descripciones repetidas ("pared caída", "techo rajado"):
la caché evita pagar y esperar una consulta al LLM por cada una. Solo guarda
clasificaciones aceptadas; las bloqueadas se vuelven a consultar. Es una caché
por instancia y con capacidad limitada, para no crecer sin control en un servidor
con poca memoria.
"""
from __future__ import annotations

from collections import OrderedDict

from .puerto import Clasificacion, ClasificadorDanos


class ClasificadorConCache(ClasificadorDanos):
    def __init__(self, clasificador: ClasificadorDanos, capacidad: int = 1000) -> None:
        self._clasificador = clasificador
        self._capacidad = capacidad
        self._cache: OrderedDict[str, Clasificacion] = OrderedDict()

    def clasificar(self, descripcion: str) -> Clasificacion:
        clave = " ".join(descripcion.lower().split())
        if clave in self._cache:
            self._cache.move_to_end(clave)
            return self._cache[clave]
        resultado = self._clasificador.clasificar(descripcion)
        if not resultado.requiere_revision:
            self._cache[clave] = resultado
            if len(self._cache) > self._capacidad:
                self._cache.popitem(last=False)
        return resultado