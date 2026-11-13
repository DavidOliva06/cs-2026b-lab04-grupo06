"""Pruebas de los patrones de la versión después.

- Strategy + Adapter + Factory (abierto/cerrado): se agrega una variante nueva de un puerto
  sin modificar servicio.py, fabrica.py ni adaptadores.py.
- Observer: dos suscriptores reciben los mismos eventos del servicio.
- Decorator: EnvioConRegistro registra cada intento sin cambiar el resultado.
La versión antes no tiene puertos, así que estas pruebas solo corren sobre la versión después.
"""
import logging

import pytest

import externos
from modulo.decoradores import EnvioConRegistro
from modulo.eventos import (
    ConsentimientoRechazado,
    Observador,
    ReporteGuardado,
    SincronizacionTerminada,
)
from modulo.fabrica import fabrica_por_defecto
from modulo.modelo import Ciudadano, Reporte
from modulo.observadores import ContadorPendientes
from modulo.puertos import AlmacenLocalReportes, AlmacenServidorReportes, PuertoEnvioReportes
from modulo.servicio import (
    URL_INGESTA,
    ConsentimientoNoAceptado,
    ControladorReportes,
    ServicioIngesta,
    ServicioReportes,
)

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


# --- Observer y Decorator ----------------------------------------------------


class AlmacenEnMemoria(AlmacenLocalReportes):
    def __init__(self):
        self.reportes = {}

    def guardar(self, reporte):
        self.reportes[reporte.id] = reporte

    def buscar_por_estado(self, estado):
        return [r for r in self.reportes.values() if r.estado == estado]


class EnvioFalso(PuertoEnvioReportes):
    """Responde, en orden, lo que se le indique."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)

    def enviar(self, reporte):
        return self.respuestas.pop(0)


class Grabadora(Observador):
    def __init__(self):
        self.eventos = []

    def notificar(self, evento):
        self.eventos.append(evento)


def servicio_con(respuestas):
    return ServicioReportes(almacen_local=AlmacenEnMemoria(), envio=EnvioFalso(respuestas))


# --- Observer ---------------------------------------------------------------


def test_dos_suscriptores_reciben_los_mismos_eventos():
    servicio = servicio_con([True, False])
    grabadora, contador = Grabadora(), ContadorPendientes()
    servicio.suscribir(grabadora)
    servicio.suscribir(contador)

    ciudadano = Ciudadano("c-1", consentimiento_aceptado=True)
    servicio.crear_reporte(ciudadano, FOTO, AREQUIPA)
    servicio.crear_reporte(ciudadano, FOTO, AREQUIPA)
    assert contador.pendientes == 2

    servicio.sincronizar_pendientes()
    assert [type(e) for e in grabadora.eventos] == [
        ReporteGuardado,
        ReporteGuardado,
        SincronizacionTerminada,
    ]
    assert grabadora.eventos[-1] == SincronizacionTerminada(enviados=1, pendientes=1)
    assert contador.pendientes == 1


def test_el_rechazo_de_consentimiento_se_publica_antes_del_error():
    servicio = servicio_con([])
    grabadora = Grabadora()
    servicio.suscribir(grabadora)
    with pytest.raises(ConsentimientoNoAceptado):
        servicio.crear_reporte(Ciudadano("c-9"), FOTO, AREQUIPA)
    assert grabadora.eventos == [ConsentimientoRechazado("c-9")]


def test_un_suscriptor_desuscrito_deja_de_recibir_eventos():
    servicio = servicio_con([])
    grabadora = Grabadora()
    servicio.suscribir(grabadora)
    servicio.desuscribir(grabadora)
    servicio.crear_reporte(Ciudadano("c-1", consentimiento_aceptado=True), FOTO, AREQUIPA)
    assert grabadora.eventos == []


def test_el_controlador_suscribe_la_vista_y_el_contador(capsys):
    servicio = servicio_con([False, True])
    controlador = ControladorReportes(servicio)
    controlador.enviar_reporte(Ciudadano("c-1", consentimiento_aceptado=True), FOTO, AREQUIPA)
    controlador.al_recuperar_conexion()
    assert controlador.contador.pendientes == 1
    controlador.al_recuperar_conexion()
    assert controlador.contador.pendientes == 0
    assert capsys.readouterr().out.splitlines() == [
        "  [PWA] Pendiente de envío",
        "  [PWA] Sigue pendiente de envío",
        "  [PWA] Enviado (1 reporte(s))",
    ]


# --- Decorator --------------------------------------------------------------


def test_el_decorador_registra_cada_intento_sin_cambiar_el_resultado(caplog):
    caplog.set_level(logging.INFO, logger="sismoreporta.envio")
    servicio = servicio_con([])
    reporte = servicio.crear_reporte(Ciudadano("c-1", consentimiento_aceptado=True), FOTO, AREQUIPA)
    envio = EnvioConRegistro(EnvioFalso([False, True]))

    assert envio.enviar(reporte) is False
    assert envio.enviar(reporte) is True
    mensajes = [r.getMessage() for r in caplog.records]
    assert len(mensajes) == 2
    assert f"{reporte.id}: pendiente" in mensajes[0]
    assert f"{reporte.id}: confirmado" in mensajes[1]


def test_el_servicio_funciona_igual_con_el_envio_decorado():
    servicio = ServicioReportes(
        almacen_local=AlmacenEnMemoria(), envio=EnvioConRegistro(EnvioFalso([True]))
    )
    servicio.crear_reporte(Ciudadano("c-1", consentimiento_aceptado=True), FOTO, AREQUIPA)
    assert servicio.sincronizar_pendientes() == 1


def test_por_defecto_el_envio_queda_decorado():
    assert isinstance(ServicioReportes().envio, EnvioConRegistro)
