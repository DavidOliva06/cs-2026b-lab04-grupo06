"""Fitness functions de calidad (Lab 08, E5.3): cada escenario del árbol de utilidad como prueba.

Las estructurales (ADR-001 y ADR-005) están en .importlinter. Estas convierten escenarios en pruebas:

- D1 (disponibilidad, ADR-006): con el modo pico, ≥ 99,5 % de los reportes guardados ≤ 15 min
  después de recuperar la señal y 0 duplicados, en el droplet de 1 núcleo y con una caída de 10 min.
- R2 (rendimiento, ADR-007): carga del mapa p95 ≤ 3 s, cambio de filtro p95 ≤ 1 s y retraso ≤ 60 s,
  midiendo las consultas reales del prototipo sobre 20 000 reportes.
- S2 (seguridad, ADR-008): ≤ 10 reportes aceptados por dispositivo atacante, 0 zonas prioritarias
  alteradas, ≥ 99,5 % de reportes legítimos aceptados y aviso al operador ≤ 5 min.
- 0 operaciones perdidas: el código real de la ingesta (entrada.py) no pierde ni duplica reportes
  aunque la red pierda respuestas.

D1 y S2 usan las simulaciones de fitness/ con menos réplicas que las del informe, para que el
workflow termine en segundos; las réplicas completas están en fitness/resultados/.
Cada prueba comprueba también que la versión "antes" no cumple: así la fitness function
distingue entre la arquitectura con la táctica y sin ella, y fallaría si se quitara la táctica.
"""
from __future__ import annotations

import random
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fitness"))

import externos  # noqa: E402
import prototipo_r2  # noqa: E402
import simulacion_d1  # noqa: E402
import simulacion_s2  # noqa: E402
from modulo.entrada import (  # noqa: E402
    ENVIADO,
    PENDIENTE_DE_ENVIO,
    URL_INGESTA,
    Ciudadano,
    ServicioIngesta,
    ServicioReportes,
)

# Presupuestos de docs/architecture/utilidad/escenarios.md
D1_GUARDADOS_PCT = 99.5
R2_CARGA_P95_S = 3.0
R2_FILTRO_P95_S = 1.0
R2_RETRASO_MAX_S = 60.0
S2_MAX_POR_DISPOSITIVO = 10
S2_LEGITIMOS_PCT = 99.5
S2_AVISO_MAX_S = 300.0


# --- D1: disponibilidad de la ingesta en el simulacro (ADR-006) --------------


@pytest.fixture(scope="module")
def supuestos_d1():
    """Peor caso de la sensibilidad: droplet de 1 núcleo y caída de 10 min en plena ráfaga."""
    return replace(simulacion_d1.Supuestos(), **simulacion_d1.VARIANTES["1 núcleo y caída de 10 min"])


def test_d1_modo_pico_guarda_99_5_por_ciento_en_15_min_sin_duplicados(supuestos_d1):
    for semilla, sim in zip([1, 2], simulacion_d1.correr(supuestos_d1, simulacion_d1.DECISION, [1, 2])):
        m = sim.medidas()
        assert m["pct_a_tiempo"] >= D1_GUARDADOS_PCT, f"semilla {semilla}: {m['pct_a_tiempo']:.2f} %"
        assert m["filas_duplicadas"] == 0


def test_d1_sin_modo_pico_no_cumple(supuestos_d1):
    m = simulacion_d1.correr(supuestos_d1, "Antes", semillas=[1])[0].medidas()
    assert m["pct_a_tiempo"] < D1_GUARDADOS_PCT


# --- R2: rendimiento del mapa (ADR-007) --------------------------------------


@pytest.fixture(scope="module")
def resultados_r2():
    supuestos = replace(prototipo_r2.Supuestos(), repeticiones=10, muestras_red=5_000)
    resultados, _ = prototipo_r2.evaluar(supuestos)
    return resultados


def test_r2_mapa_agrupado_por_zona_cumple_el_presupuesto_de_p95(resultados_r2):
    r = resultados_r2["T5: agrupar en el servidor"]
    assert r["carga_p95_s"] <= R2_CARGA_P95_S
    assert r["filtro_p95_s"] <= R2_FILTRO_P95_S
    assert r["retraso_max_s"] <= R2_RETRASO_MAX_S


def test_r2_listado_de_reportes_no_cumple(resultados_r2):
    assert resultados_r2["Antes: listado de reportes"]["carga_p95_s"] > R2_CARGA_P95_S


# --- S2: reportes falsos desde un dispositivo (ADR-008) ----------------------


@pytest.fixture(scope="module")
def resultados_s2():
    return simulacion_s2.evaluar(replace(simulacion_s2.Supuestos(), replicas=3))


def test_s2_limite_y_voto_por_dispositivo_cumplen_el_escenario(resultados_s2):
    medidas = resultados_s2["T9 + T11: límite, marca y un voto por dispositivo"]
    for m in medidas:
        assert m["max_por_identidad"] <= S2_MAX_POR_DISPOSITIVO
        assert m["zonas_alteradas"] == 0
        assert m["legitimos_pct"] >= S2_LEGITIMOS_PCT
        assert m["aviso_s"] is not None and m["aviso_s"] <= S2_AVISO_MAX_S


@pytest.mark.parametrize("tactica", ["Antes: sin control", "T10: límite por IP"])
def test_s2_sin_control_o_con_limite_por_ip_no_cumple(resultados_s2, tactica):
    _, _, cumple = simulacion_s2.resumir(resultados_s2[tactica])
    assert not cumple


# --- 0 operaciones perdidas en el código real de la ingesta ------------------


@pytest.fixture
def red():
    red = externos.red_movil
    red.hay_senal = True
    red.perder_proxima_respuesta = False
    red._rutas.clear()
    yield red
    red.hay_senal = True
    red.perder_proxima_respuesta = False
    red._rutas.clear()


def test_ingesta_no_pierde_ni_duplica_reportes_con_respuestas_perdidas(red):
    """50 reportes, señal intermitente y 30 % de respuestas perdidas: todos llegan una sola vez."""
    rng = random.Random(8)
    ingesta = ServicioIngesta()
    red.publicar(URL_INGESTA, ingesta.manejar_post)
    servicio = ServicioReportes()
    ciudadano = Ciudadano("c-fitness", consentimiento_aceptado=True)

    red.hay_senal = False
    reportes = [servicio.crear_reporte(ciudadano, b"\xff\xd8\xff foto", (-16.4, -71.5)) for _ in range(50)]

    for _ in range(200):
        pendientes = servicio.almacen_local.buscar_por_estado(PENDIENTE_DE_ENVIO)
        if not pendientes:
            break
        red.hay_senal = rng.random() > 0.3
        red.perder_proxima_respuesta = rng.random() < 0.3
        servicio.sincronizar_pendientes()

    assert len(servicio.almacen_local.buscar_por_estado(ENVIADO)) == len(reportes)
    assert ingesta.contar_reportes() == len(reportes)
