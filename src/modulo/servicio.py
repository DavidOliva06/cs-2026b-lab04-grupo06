"""Flujo crítico HU-01 refactorizado con Strategy + Adapter + Factory.

Variación principal: el servicio externo que atiende cada paso del flujo
(almacenamiento en el celular, envío por la red y almacenamiento en el servidor).
Cada paso es un puerto (Strategy, en puertos.py); cada servicio externo simulado
tiene su Adapter (adaptadores.py), y la Factory (fabrica.py) crea el adecuado.

Además, el servicio publica eventos (Observer, en eventos.py) a los que se
suscriben la vista y el contador de pendientes (observadores.py), y cada envío
queda registrado mediante un Decorator (decoradores.py).

El comportamiento observable es el mismo que en antes/servicio.py.
Requiere Python 3.10 o superior. Demostración: python -m modulo.servicio (con PYTHONPATH=src/modulo:src)
"""
from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone

from externos import RespuestaHttp, red_movil

from .adaptadores import DSN_SERVIDOR, URL_INGESTA
from .eventos import (
    ConsentimientoRechazado,
    Observador,
    Publicador,
    ReporteGuardado,
    SincronizacionTerminada,
)
from .fabrica import FabricaEstrategias, fabrica_por_defecto
from .modelo import ENVIADO, PENDIENTE_DE_ENVIO, Ciudadano, Reporte
from .observadores import ContadorPendientes, VistaConsola
from .puertos import AlmacenLocalReportes, AlmacenServidorReportes, PuertoEnvioReportes

__all__ = [
    "PENDIENTE_DE_ENVIO",
    "ENVIADO",
    "URL_INGESTA",
    "DSN_SERVIDOR",
    "ConsentimientoNoAceptado",
    "Ciudadano",
    "Reporte",
    "ServicioReportes",
    "ServicioIngesta",
    "ControladorReportes",
]

ALMACEN_LOCAL_POR_DEFECTO = "indexeddb"
ENVIO_POR_DEFECTO = "http_con_registro"
ALMACEN_SERVIDOR_POR_DEFECTO = "postgres"


class ConsentimientoNoAceptado(Exception):
    """El ciudadano no aceptó el uso de su ubicación y sus fotos (criterio 4)."""


# --- Lado del celular -------------------------------------------------------


class ServicioReportes:
    """Crea reportes, los guarda en el celular y los envía al recuperar la señal."""

    def __init__(
        self,
        almacen_local: AlmacenLocalReportes | None = None,
        envio: PuertoEnvioReportes | None = None,
        fabrica: FabricaEstrategias | None = None,
    ) -> None:
        fabrica = fabrica or fabrica_por_defecto()
        self.almacen_local = almacen_local or fabrica.crear(
            AlmacenLocalReportes, ALMACEN_LOCAL_POR_DEFECTO
        )
        self.envio = envio or fabrica.crear(PuertoEnvioReportes, ENVIO_POR_DEFECTO)
        self._eventos = Publicador()

    def suscribir(self, observador: Observador) -> None:
        self._eventos.suscribir(observador)

    def desuscribir(self, observador: Observador) -> None:
        self._eventos.desuscribir(observador)

    def crear_reporte(
        self, ciudadano: Ciudadano, foto: bytes, ubicacion: tuple[float, float]
    ) -> Reporte:
        if not ciudadano.puede_reportar():
            self._eventos.publicar(ConsentimientoRechazado(ciudadano.id))
            raise ConsentimientoNoAceptado("El ciudadano no aceptó el uso de ubicación y fotos")
        reporte = Reporte(str(uuid.uuid4()), ciudadano.id, foto, ubicacion)
        self.almacen_local.guardar(reporte)
        self._eventos.publicar(ReporteGuardado(reporte.id))
        return reporte

    def sincronizar_pendientes(self) -> int:
        """Envía los reportes pendientes y devuelve cuántos quedaron enviados."""
        pendientes = self.almacen_local.buscar_por_estado(PENDIENTE_DE_ENVIO)
        enviados = 0
        for reporte in pendientes:
            if self.envio.enviar(reporte):
                reporte.marcar_enviado(datetime.now(timezone.utc))
                self.almacen_local.guardar(reporte)
                enviados += 1
        self._eventos.publicar(SincronizacionTerminada(enviados, len(pendientes) - enviados))
        return enviados


# --- Lado del servidor ------------------------------------------------------


class ServicioIngesta:
    """Recibe reportes y descarta duplicados (criterio 3)."""

    def __init__(
        self,
        almacen: AlmacenServidorReportes | None = None,
        fabrica: FabricaEstrategias | None = None,
    ) -> None:
        fabrica = fabrica or fabrica_por_defecto()
        self.almacen = almacen or fabrica.crear(
            AlmacenServidorReportes, ALMACEN_SERVIDOR_POR_DEFECTO
        )

    def manejar_post(self, cuerpo_json: str) -> RespuestaHttp:
        # INGENUO: lectura de HTTP, validación y lógica de negocio en el mismo método.
        try:
            datos = json.loads(cuerpo_json)
            reporte = Reporte(
                id=datos["id"],
                ciudadano_id=datos["ciudadano_id"],
                foto=base64.b64decode(datos["foto_b64"]),
                ubicacion=(float(datos["latitud"]), float(datos["longitud"])),
            )
        except (ValueError, KeyError, TypeError):
            return RespuestaHttp(400, "Reporte inválido")
        self.recibir(reporte)
        return RespuestaHttp(200, json.dumps({"id": reporte.id, "recibido": True}))

    def recibir(self, reporte: Reporte) -> bool:
        """Devuelve True porque, tras llamarlo, el servidor tiene el reporte."""
        self.almacen.guardar_si_no_existe(reporte)
        return True

    def contar_reportes(self) -> int:
        return self.almacen.contar()


# --- Controlador y UI de la PWA ---------------------------------------------


class ControladorReportes:
    """Conecta la PWA con el servicio. Ya no arma mensajes: los suscriptores reaccionan a los eventos."""

    def __init__(
        self,
        servicio: ServicioReportes,
        vista: Observador | None = None,
        contador: ContadorPendientes | None = None,
    ) -> None:
        self.servicio = servicio
        self.vista = vista or VistaConsola()
        self.contador = contador or ContadorPendientes()
        servicio.suscribir(self.vista)
        servicio.suscribir(self.contador)

    def enviar_reporte(
        self, ciudadano: Ciudadano, foto: bytes, ubicacion: tuple[float, float]
    ) -> Reporte | None:
        try:
            return self.servicio.crear_reporte(ciudadano, foto, ubicacion)
        except ConsentimientoNoAceptado:
            return None

    def al_recuperar_conexion(self) -> None:
        self.servicio.sincronizar_pendientes()


# --- Demostración de los criterios de aceptación ----------------------------


if __name__ == "__main__":
    ingesta = ServicioIngesta()
    red_movil.publicar(URL_INGESTA, ingesta.manejar_post)
    servicio = ServicioReportes()
    controlador = ControladorReportes(servicio)
    foto = b"\xff\xd8\xff foto de prueba"
    ubicacion = (-16.3989, -71.5350)

    def estados() -> list[str]:
        reportes = servicio.almacen_local.buscar_por_estado(PENDIENTE_DE_ENVIO)
        reportes += servicio.almacen_local.buscar_por_estado(ENVIADO)
        return [r.estado for r in reportes]

    print("Criterio 4: sin consentimiento no se guarda nada")
    controlador.enviar_reporte(Ciudadano("c-1"), foto, ubicacion)
    assert estados() == []

    print("Criterio 1: sin señal, el reporte queda pendiente en el celular")
    red_movil.hay_senal = False
    ciudadano = Ciudadano("c-2", consentimiento_aceptado=True)
    controlador.enviar_reporte(ciudadano, foto, ubicacion)
    controlador.al_recuperar_conexion()
    assert estados() == [PENDIENTE_DE_ENVIO]
    assert ingesta.contar_reportes() == 0

    print("Criterio 3: llega al servidor, pero la confirmación se pierde")
    red_movil.hay_senal = True
    red_movil.perder_proxima_respuesta = True
    controlador.al_recuperar_conexion()
    assert estados() == [PENDIENTE_DE_ENVIO]
    assert ingesta.contar_reportes() == 1

    print("Criterios 2 y 3: el reenvío se confirma y el servidor conserva un solo reporte")
    controlador.al_recuperar_conexion()
    assert estados() == [ENVIADO]
    assert ingesta.contar_reportes() == 1

    print("Todos los criterios se cumplen.")
