from __future__ import annotations
 
import json
from dataclasses import dataclass
from typing import Callable
 
 
# --- Navegador del celular: IndexedDB -------------------------------------
 
 
class CuotaExcedida(Exception):
    """El navegador no tiene espacio para guardar más datos."""
 
 
class AlmacenIndexedDB:
    """Simula IndexedDB: almacenes con pares clave-valor y una cuota de espacio."""
 
    def __init__(self, cuota_bytes: int = 5_000_000) -> None:
        self.cuota_bytes = cuota_bytes
        # Los valores se guardan serializados, como el navegador guarda una copia.
        self._almacenes: dict[str, dict[str, str]] = {}
 
    def put(self, almacen: str, clave: str, valor: dict) -> None:
        texto = json.dumps(valor)
        datos = self._almacenes.setdefault(almacen, {})
        usado = sum(len(t) for a in self._almacenes.values() for t in a.values())
        usado = usado - len(datos.get(clave, "")) + len(texto)
        if usado > self.cuota_bytes:
            raise CuotaExcedida(f"Se superó la cuota de {self.cuota_bytes} bytes")
        datos[clave] = texto
 
    def get_all(self, almacen: str) -> list[dict]:
        return [json.loads(t) for t in self._almacenes.get(almacen, {}).values()]
 
 
# --- Red móvil: HTTP --------------------------------------------------------
 
 
@dataclass(frozen=True)
class RespuestaHttp:
    status: int
    texto: str
 
 
class RedSimulada:
    """Red móvil intermitente que conecta el celular con el servidor."""
 
    def __init__(self) -> None:
        self.hay_senal = True
        self.perder_proxima_respuesta = False
        self._rutas: dict[str, Callable[[str], RespuestaHttp]] = {}
 
    def publicar(self, url: str, manejador: Callable[[str], RespuestaHttp]) -> None:
        """Registra el manejador del servidor que atiende los POST a esa URL."""
        self._rutas[url] = manejador
 
 
red_movil = RedSimulada()
 
 
class ClienteHttp:
    """Simula el envío de peticiones POST desde el celular."""
 
    def __init__(self, red: RedSimulada = red_movil) -> None:
        self.red = red
 
    def post(self, url: str, cuerpo_json: str) -> RespuestaHttp:
        if not self.red.hay_senal:
            raise ConnectionError("Sin señal: no se pudo conectar con el servidor")
        manejador = self.red._rutas.get(url)
        if manejador is None:
            return RespuestaHttp(404, "No encontrado")
        respuesta = manejador(cuerpo_json)
        if self.red.perder_proxima_respuesta:
            self.red.perder_proxima_respuesta = False
            raise TimeoutError("El servidor procesó la petición, pero la respuesta se perdió")
        return respuesta
 
 
# --- Servidor: PostgreSQL ---------------------------------------------------
 
 
class ErrorSql(Exception):
    """Error devuelto por la base de datos."""
 
 
class Cursor:
    """Cursor mínimo: solo entiende las sentencias que usa el flujo HU-01."""
 
    def __init__(self, conexion: ConexionPostgres) -> None:
        self._conexion = conexion
        self._filas: list[tuple] = []
        self.rowcount = -1
 
    def execute(self, sql: str, params: tuple = ()) -> None:
        normal = " ".join(sql.split()).upper()
        tabla = self._conexion._tablas["reportes"]
        pendientes = self._conexion._pendientes
 
        if normal.startswith("INSERT INTO REPORTES"):
            id_reporte = params[0]
            if id_reporte in tabla or id_reporte in pendientes:
                if "ON CONFLICT (ID) DO NOTHING" in normal:
                    self.rowcount = 0
                    return
                raise ErrorSql(f"Llave duplicada: id={id_reporte}")
            pendientes[id_reporte] = params
            self.rowcount = 1
        elif normal.startswith("SELECT COUNT(*) FROM REPORTES"):
            self._filas = [(len(tabla),)]
            self.rowcount = 1
        else:
            raise ErrorSql(f"Sentencia no soportada por la simulación: {sql}")
 
    def fetchone(self) -> tuple | None:
        return self._filas.pop(0) if self._filas else None
 
 
class ConexionPostgres:
    """Simula una conexión a PostgreSQL con transacciones."""
 
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._tablas: dict[str, dict[str, tuple]] = {"reportes": {}}
        self._pendientes: dict[str, tuple] = {}
 
    def cursor(self) -> Cursor:
        return Cursor(self)
 
    def commit(self) -> None:
        self._tablas["reportes"].update(self._pendientes)
        self._pendientes.clear()
 
    def rollback(self) -> None:
        self._pendientes.clear()