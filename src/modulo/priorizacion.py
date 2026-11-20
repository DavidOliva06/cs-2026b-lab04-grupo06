"""Priorización de zonas (RF-03): ordena las zonas según la gravedad de sus reportes.

Supuestos de docs/architecture/add/iteracion-3.md:
- puntaje de una zona = suma de pesos por gravedad (1, 2 y 4);
- táctica T11: un voto por dispositivo y zona (cuenta la mayor gravedad que reportó cada uno).
Los niveles de gravedad son los del componente de IA del Lab 07 (GRAVEDADES).
"""
from __future__ import annotations

from dataclasses import dataclass

PESOS = {"leve": 1, "moderado": 2, "grave": 4, "colapso": 4}
PESO_MAXIMO = max(PESOS.values())
PESO_MINIMO = min(PESOS.values())


@dataclass(frozen=True)
class ReporteClasificado:
    zona: str
    dispositivo: str
    gravedad: str | None  # None si todavía no se clasificó
    tiene_foto: bool


def peso(reporte: ReporteClasificado) -> int:
    if not reporte.tiene_foto:
        # Sin foto no se puede verificar el daño: aporta el peso mínimo hasta que llegue la foto (RI-02).
        return PESO_MINIMO
    return PESOS.get(reporte.gravedad or "", 0)


def puntajes(reportes: list[ReporteClasificado]) -> dict[str, int]:
    """Puntaje por zona con un voto por dispositivo (T11)."""
    mayor: dict[tuple[str, str], int] = {}
    for r in reportes:
        clave = (r.zona, r.dispositivo)
        mayor[clave] = max(mayor.get(clave, 0), peso(r))
    totales: dict[str, int] = {}
    for (zona, _), valor in mayor.items():
        totales[zona] = totales.get(zona, 0) + valor
    return totales


def zonas_priorizadas(reportes: list[ReporteClasificado], limite: int = 20) -> list[str]:
    """Las zonas de mayor a menor puntaje; empate por nombre de zona."""
    total = puntajes(reportes)
    return sorted(total, key=lambda zona: (-total[zona], zona))[:limite]
