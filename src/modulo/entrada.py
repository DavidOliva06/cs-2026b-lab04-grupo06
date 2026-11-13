"""Capa de entrada del flujo HU-01: endpoint HTTP de la ingesta, controlador de la PWA y demostración.

Es la única parte del flujo que conoce HTTP y la red simulada; el servicio solo conoce
puertos (ADR-005). Lo verifica el contrato adr005-servicio-sin-infraestructura de .importlinter.
"""
from __future__ import annotations

import base64
import json

from externos import RespuestaHttp, red_movil

from .adaptadores import DSN_SERVIDOR, URL_INGESTA
from .fabrica import FabricaEstrategias, fabrica_por_defecto
from .ia.puerto import ClasificadorDanos  # VIOLACIÓN DE PRUEBA: la ingesta llama a la IA (ADR-001)
from .eventos import Observador
from .modelo import ENVIADO, PENDIENTE_DE_ENVIO, Ciudadano, Reporte
from .observadores import ContadorPendientes, VistaConsola
from .puertos import AlmacenServidorReportes
from .servicio import ConsentimientoNoAceptado, ServicioReportes

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

ALMACEN_SERVIDOR_POR_DEFECTO = "postgres"


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
