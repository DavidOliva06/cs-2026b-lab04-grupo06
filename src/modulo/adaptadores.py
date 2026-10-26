"""Adapters: traducen cada servicio externo simulado (externos.py) a su puerto.

Toda la traducción de formatos y errores que antes vivía dentro de los
servicios está aquí: diccionarios y base64 para IndexedDB, texto JSON y
códigos de estado para HTTP, y SQL para PostgreSQL.
"""
from __future__ import annotations

import base64
import json
from datetime import datetime

from externos import AlmacenIndexedDB, ClienteHttp, ConexionPostgres

from .modelo import Reporte
from .puertos import AlmacenLocalReportes, AlmacenServidorReportes, PuertoEnvioReportes

URL_INGESTA = "https://api.sismoreporta.example/reportes"
DSN_SERVIDOR = "postgresql://sismoreporta@localhost/sismoreporta"


class AdaptadorIndexedDB(AlmacenLocalReportes):
    ALMACEN = "reportes"

    def __init__(self, indexeddb: AlmacenIndexedDB | None = None) -> None:
        self._indexeddb = indexeddb or AlmacenIndexedDB()

    def guardar(self, reporte: Reporte) -> None:
        registro = {
            "id": reporte.id,
            "ciudadano_id": reporte.ciudadano_id,
            "foto_b64": base64.b64encode(reporte.foto).decode("ascii"),
            "latitud": reporte.ubicacion[0],
            "longitud": reporte.ubicacion[1],
            "estado": reporte.estado,
            "fecha_envio": reporte.fecha_envio.isoformat() if reporte.fecha_envio else None,
        }
        self._indexeddb.put(self.ALMACEN, reporte.id, registro)

    def buscar_por_estado(self, estado: str) -> list[Reporte]:
        return [
            self._desde_registro(r)
            for r in self._indexeddb.get_all(self.ALMACEN)
            if r["estado"] == estado
        ]

    @staticmethod
    def _desde_registro(registro: dict) -> Reporte:
        fecha = registro["fecha_envio"]
        return Reporte(
            id=registro["id"],
            ciudadano_id=registro["ciudadano_id"],
            foto=base64.b64decode(registro["foto_b64"]),
            ubicacion=(registro["latitud"], registro["longitud"]),
            estado=registro["estado"],
            fecha_envio=datetime.fromisoformat(fecha) if fecha else None,
        )


class AdaptadorEnvioHttp(PuertoEnvioReportes):
    def __init__(self, cliente: ClienteHttp | None = None, url: str = URL_INGESTA) -> None:
        self._cliente = cliente or ClienteHttp()
        self._url = url

    def enviar(self, reporte: Reporte) -> bool:
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
            respuesta = self._cliente.post(self._url, cuerpo)
        except (ConnectionError, TimeoutError):
            # Sin señal o sin confirmación: el reporte sigue pendiente.
            return False
        return respuesta.status == 200


class AdaptadorPostgres(AlmacenServidorReportes):
    def __init__(self, conexion: ConexionPostgres | None = None, dsn: str = DSN_SERVIDOR) -> None:
        self._conexion = conexion or ConexionPostgres(dsn)

    def guardar_si_no_existe(self, reporte: Reporte) -> bool:
        cursor = self._conexion.cursor()
        cursor.execute(
            "INSERT INTO reportes (id, ciudadano_id, latitud, longitud, foto) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (reporte.id, reporte.ciudadano_id, reporte.ubicacion[0], reporte.ubicacion[1], reporte.foto),
        )
        self._conexion.commit()
        return cursor.rowcount == 1

    def contar(self) -> int:
        cursor = self._conexion.cursor()
        cursor.execute("SELECT COUNT(*) FROM reportes")
        return cursor.fetchone()[0]