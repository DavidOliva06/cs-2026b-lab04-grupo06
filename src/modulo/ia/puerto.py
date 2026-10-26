"""Puerto del componente de IA: clasificar el daño descrito en un reporte.

El resto del sistema solo conoce esta interfaz, así que el LLM queda aislado:
se puede cambiar de proveedor, envolver con caché o reemplazar por reglas
sin tocar a quien lo usa. La IA solo sugiere; la decisión es del coordinador.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

# Supuesto: niveles de gravedad para la priorización (RF-03).
GRAVEDADES = ("leve", "moderado", "grave", "colapso")


@dataclass(frozen=True)
class Clasificacion:
    gravedad: str | None
    resumen: str | None
    requiere_revision: bool
    motivo: str = ""


class ClasificadorDanos(ABC):
    @abstractmethod
    def clasificar(self, descripcion: str) -> Clasificacion: ...