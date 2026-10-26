from __future__ import annotations
 
import base64
import json
import uuid
from datetime import datetime, timezone
 
from externos import (
    AlmacenIndexedDB,
    ClienteHttp,
    ConexionPostgres,
    RespuestaHttp,
    red_movil,
)
PENDIENTE_DE_ENVIO = "PENDIENTE_DE_ENVIO"
ENVIADO = "ENVIADO"
 
# INGENUO: la URL y la cadena de conexión están fijas en el código.
URL_INGESTA = "https://api.sismoreporta.example/reportes"
DSN_SERVIDOR = "postgresql://sismoreporta@localhost/sismoreporta"
 

class ConsentimientoNoAceptado(Exception):
    """El ciudadano no aceptó el uso de su ubicación y sus fotos (criterio 4)."""
 
 
# --- Entidades --------------------------------------------------------------
 
 
class Ciudadano:
    def __init__(self, id: str, consentimiento_aceptado: bool = False) -> None:
        self.id = id
        self.consentimiento_aceptado = consentimiento_aceptado
 
    def puede_reportar(self) -> bool:
        return self.consentimiento_aceptado
 
 
class Reporte:
    def __init__(
        self,
        id: str,
        ciudadano_id: str,
        foto: bytes,
        ubicacion: tuple[float, float],
        estado: str = PENDIENTE_DE_ENVIO,
        fecha_envio: datetime | None = None,
    ) -> None:
        self.id = id
        self.ciudadano_id = ciudadano_id
        self.foto = foto
        self.ubicacion = ubicacion
        self.estado = estado
        self.fecha_envio = fecha_envio
 
    def marcar_enviado(self, fecha: datetime) -> None:
        self.estado = ENVIADO
        self.fecha_envio = fecha
 
 
# --- Lado del celular -------------------------------------------------------
 
 
class ServicioReportes:
    """Crea reportes, los guarda en el celular y los envía al recuperar la señal."""
 
    def __init__(self) -> None:
        # INGENUO: el servicio crea sus dependencias concretas en lugar de recibirlas.
        self.indexeddb = AlmacenIndexedDB()
        self.http = ClienteHttp()
 
    def crear_reporte(
        self, ciudadano: Ciudadano, foto: bytes, ubicacion: tuple[float, float]
    ) -> Reporte:
        if not ciudadano.puede_reportar():
            raise ConsentimientoNoAceptado("El ciudadano no aceptó el uso de ubicación y fotos")
        reporte = Reporte(str(uuid.uuid4()), ciudadano.id, foto, ubicacion)
        self._guardar_en_indexeddb(reporte)
        return reporte
 
    def sincronizar_pendientes(self) -> int:
        """Envía los reportes pendientes y devuelve cuántos quedaron enviados."""
        # INGENUO: trae todo el almacén y filtra en memoria.
        registros = self.indexeddb.get_all("reportes")
        pendientes = [
            self._desde_registro_indexeddb(r)
            for r in registros
            if r["estado"] == PENDIENTE_DE_ENVIO
        ]
        enviados = 0
        for reporte in pendientes:
            if self._enviar_por_http(reporte):
                reporte.marcar_enviado(datetime.now(timezone.utc))
                self._guardar_en_indexeddb(reporte)
                enviados += 1
        return enviados
 
    # INGENUO: la traducción al formato de cada servicio externo vive dentro del servicio.
 
    def _guardar_en_indexeddb(self, reporte: Reporte) -> None:
        registro = {
            "id": reporte.id,
            "ciudadano_id": reporte.ciudadano_id,
            "foto_b64": base64.b64encode(reporte.foto).decode("ascii"),
            "latitud": reporte.ubicacion[0],
            "longitud": reporte.ubicacion[1],
            "estado": reporte.estado,
            "fecha_envio": reporte.fecha_envio.isoformat() if reporte.fecha_envio else None,
        }
        self.indexeddb.put("reportes", reporte.id, registro)
 
    def _desde_registro_indexeddb(self, registro: dict) -> Reporte:
        fecha = registro["fecha_envio"]
        return Reporte(
            id=registro["id"],
            ciudadano_id=registro["ciudadano_id"],
            foto=base64.b64decode(registro["foto_b64"]),
            ubicacion=(registro["latitud"], registro["longitud"]),
            estado=registro["estado"],
            fecha_envio=datetime.fromisoformat(fecha) if fecha else None,
        )
 
    def _enviar_por_http(self, reporte: Reporte) -> bool:
        cuerpo = json.dumps(
            {
                "id": reporte.id,
                "ciudadano_id": reporte.ciudadano_id,
                "foto_b64": base64.b64encode(reporte.foto).decode("ascii"),
                "latitud": reporte.ubicacion[0],
                "longitud": reporte.ubicacion[1],
            }
        )
        try:
            respuesta = self.http.post(URL_INGESTA, cuerpo)
        except (ConnectionError, TimeoutError):
            # Sin señal o sin confirmación: el reporte sigue pendiente.
            return False
        return respuesta.status == 200
 
 
# --- Lado del servidor ------------------------------------------------------
 
 
class ServicioIngesta:
    """Recibe reportes y descarta duplicados (criterio 3)."""
 
    def __init__(self) -> None:
        # INGENUO: abre su propia conexión concreta a la base de datos.
        self.bd = ConexionPostgres(DSN_SERVIDOR)
 
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
        self._guardar_si_no_existe(reporte)
        return True
 
    def _guardar_si_no_existe(self, reporte: Reporte) -> bool:
        """Devuelve False si el reporte ya existía."""
        cursor = self.bd.cursor()
        cursor.execute(
            "INSERT INTO reportes (id, ciudadano_id, latitud, longitud, foto) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (reporte.id, reporte.ciudadano_id, reporte.ubicacion[0], reporte.ubicacion[1], reporte.foto),
        )
        self.bd.commit()
        return cursor.rowcount == 1
 
    def contar_reportes(self) -> int:
        cursor = self.bd.cursor()
        cursor.execute("SELECT COUNT(*) FROM reportes")
        return cursor.fetchone()[0]
 
 
# --- Controlador y UI de la PWA ---------------------------------------------
 
 
class ControladorReportes:
    def __init__(self, servicio: ServicioReportes) -> None:
        self.servicio = servicio
 
    def enviar_reporte(
        self, ciudadano: Ciudadano, foto: bytes, ubicacion: tuple[float, float]
    ) -> Reporte | None:
        try:
            reporte = self.servicio.crear_reporte(ciudadano, foto, ubicacion)
        except ConsentimientoNoAceptado:
            self._mostrar_consentimiento()
            return None
        self._mostrar_estado("Pendiente de envío")
        return reporte
 
    def al_recuperar_conexion(self) -> None:
        enviados = self.servicio.sincronizar_pendientes()
        if enviados:
            self._mostrar_estado(f"Enviado ({enviados} reporte(s))")
        else:
            self._mostrar_estado("Sigue pendiente de envío")
 
    # INGENUO: la "pantalla" es un print dentro del controlador.
    def _mostrar_estado(self, texto: str) -> None:
        print(f"  [PWA] {texto}")
 
    def _mostrar_consentimiento(self) -> None:
        print("  [PWA] Debe aceptar el uso de su ubicación y sus fotos")
 
 
# --- Demostración de los criterios de aceptación ----------------------------
 
 
if __name__ == "__main__":
    ingesta = ServicioIngesta()
    red_movil.publicar(URL_INGESTA, ingesta.manejar_post)
    servicio = ServicioReportes()
    controlador = ControladorReportes(servicio)
    foto = b"\xff\xd8\xff foto de prueba"
    ubicacion = (-16.3989, -71.5350)
 
    def estados() -> list[str]:
        return [r["estado"] for r in servicio.indexeddb.get_all("reportes")]
 
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
 