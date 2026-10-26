"""Pruebas de los patrones de la versión después (Strategy + Adapter + Factory).

Abierto/cerrado: se agrega una variante nueva de un puerto sin modificar servicio.py,
fabrica.py ni adaptadores.py. La variante vive solo en este archivo, se registra en
la fábrica y el servicio la usa a través del puerto. La versión antes no tiene
puertos, así que estas pruebas solo corren sobre la versión después.
"""
import pytest

import externos
from modulo.fabrica import fabrica_por_defecto
from modulo.modelo import Reporte
from modulo.puertos import AlmacenServidorReportes
from modulo.servicio import URL_INGESTA, Ciudadano, ServicioIngesta, ServicioReportes

FOTO = b"\xff\xd8\xff foto de prueba"
AREQUIPA = (-16.3989, -71.5350)


class AlmacenServidorEnMemoria(AlmacenServidorReportes):
    """Variante nueva: guarda los reportes en un diccionario, sin PostgreSQL."""

    def __init__(self) -> None:
        self.reportes: dict[str, Reporte] = {}

    def guardar_si_no_existe(self, reporte: Reporte) -> bool:
        if reporte.id in self.reportes:
            return False
        self.reportes[reporte.id] = reporte
        return True

    def contar(self) -> int:
        return len(self.reportes)


@pytest.fixture(autouse=True)
def red_limpia():
    """Deja la red simulada igual en cada prueba: con señal, sin pérdidas y sin rutas."""
    red = externos.red_movil
    red.hay_senal = True
    red.perder_proxima_respuesta = False
    red._rutas.clear()
    yield red
    red._rutas.clear()


def test_open_closed_nuevo_almacen_del_servidor_sin_modificar_el_servicio(red_limpia):
    fabrica = fabrica_por_defecto()
    fabrica.registrar(AlmacenServidorReportes, "memoria", AlmacenServidorEnMemoria)
    almacen = fabrica.crear(AlmacenServidorReportes, "memoria")

    ingesta = ServicioIngesta(almacen=almacen)
    red_limpia.publicar(URL_INGESTA, ingesta.manejar_post)
    servicio = ServicioReportes()

    # Mismo flujo HU-01: sin señal, confirmación perdida y reenvío.
    red_limpia.hay_senal = False
    reporte = servicio.crear_reporte(Ciudadano("c-1", consentimiento_aceptado=True), FOTO, AREQUIPA)
    assert servicio.sincronizar_pendientes() == 0

    red_limpia.hay_senal = True
    red_limpia.perder_proxima_respuesta = True
    assert servicio.sincronizar_pendientes() == 0
    assert servicio.sincronizar_pendientes() == 1

    # El reporte llegó a la variante nueva, una sola vez.
    assert ingesta.almacen is almacen
    assert list(almacen.reportes) == [reporte.id]
    assert ingesta.contar_reportes() == 1
