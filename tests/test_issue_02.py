"""ISSUE-02: reportes duplicados al sincronizar con el almacén en memoria (issues/ISSUE-02.md)."""
import externos
import pytest

from modulo.entrada import URL_INGESTA, Ciudadano, ServicioIngesta, ServicioReportes
from modulo.fabrica import fabrica_por_defecto
from modulo.puertos import AlmacenServidorReportes

FOTO = b"\xff\xd8\xff foto de prueba"
AREQUIPA = (-16.3989, -71.5350)


@pytest.fixture(autouse=True)
def red_limpia():
    red = externos.red_movil
    red.hay_senal, red.perder_proxima_respuesta = True, False
    red._rutas.clear()
    yield red
    red._rutas.clear()


def test_issue_02_reenvio_tras_respuesta_perdida_no_duplica(red_limpia):
    almacen = fabrica_por_defecto().crear(AlmacenServidorReportes, "memoria")
    ingesta = ServicioIngesta(almacen=almacen)
    red_limpia.publicar(URL_INGESTA, ingesta.manejar_post)
    servicio = ServicioReportes()
    servicio.crear_reporte(Ciudadano("c-1", consentimiento_aceptado=True), FOTO, AREQUIPA)

    red_limpia.perder_proxima_respuesta = True   # el servidor guarda, pero la confirmación se pierde
    assert servicio.sincronizar_pendientes() == 0
    assert servicio.sincronizar_pendientes() == 1  # al reintentar, el celular reenvía el mismo id

    assert ingesta.contar_reportes() == 1


def test_issue_02_mismo_reporte_dos_veces_devuelve_false_la_segunda():
    from modulo.modelo import Reporte
    almacen = fabrica_por_defecto().crear(AlmacenServidorReportes, "memoria")
    reporte = Reporte("r-1", "c-1", FOTO, AREQUIPA)
    assert almacen.guardar_si_no_existe(reporte) is True
    assert almacen.guardar_si_no_existe(reporte) is False
    assert almacen.contar() == 1
