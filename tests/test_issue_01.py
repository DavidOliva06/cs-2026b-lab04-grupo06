"""ISSUE-01: la ingesta acepta coordenadas fuera de Arequipa (issues/ISSUE-01.md)."""
import base64
import json

import pytest

from modulo.entrada import ServicioIngesta
from modulo.fabrica import fabrica_por_defecto
from modulo.puertos import AlmacenServidorReportes

FOTO = base64.b64encode(b"\xff\xd8\xff foto de prueba").decode("ascii")


def cuerpo(latitud, longitud, id_reporte="r-1"):
    return json.dumps({"id": id_reporte, "ciudadano_id": "c-1", "foto_b64": FOTO,
                       "latitud": latitud, "longitud": longitud})


@pytest.fixture
def ingesta():
    almacen = fabrica_por_defecto().crear(AlmacenServidorReportes, "postgres")
    return ServicioIngesta(almacen=almacen)


@pytest.mark.parametrize("latitud, longitud, lugar", [
    (-12.0464, -77.0428, "Lima"),
    (-13.5320, -71.9675, "Cusco"),
    (-18.0146, -70.2536, "Tacna"),
    (16.3989, 71.5350, "Arequipa con los signos invertidos"),
])
def test_issue_01_rechaza_coordenadas_fuera_de_arequipa(ingesta, latitud, longitud, lugar):
    respuesta = ingesta.manejar_post(cuerpo(latitud, longitud))
    assert respuesta.status == 400, f"aceptó un reporte en {lugar}"
    assert ingesta.contar_reportes() == 0


@pytest.mark.parametrize("latitud, longitud, lugar", [
    (-16.3989, -71.5350, "Plaza de Armas de Arequipa"),
    (-15.6420, -72.5050, "Majes (Caylloma)"),
    (-17.0280, -71.6950, "Mollendo (Islay)"),
])
def test_issue_01_acepta_coordenadas_dentro_de_arequipa(ingesta, latitud, longitud, lugar):
    respuesta = ingesta.manejar_post(cuerpo(latitud, longitud))
    assert respuesta.status == 200, f"rechazó un reporte en {lugar}"
    assert ingesta.contar_reportes() == 1
