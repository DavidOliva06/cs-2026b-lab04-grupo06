"""Prototipo de medición del escenario R2 (Lab 08, E4, iteración 2 de ADD).

Mide, para cada alternativa de la API del mapa, el tamaño de la respuesta y el tiempo
de servidor (consulta, JSON y gzip) sobre 20 000 reportes activos, y estima con Monte
Carlo el tiempo de carga del mapa que ve un coordinador en una red congestionada.

Usa SQLite de la biblioteca estándar como sustituto de PostgreSQL: los bytes de cada
respuesta no dependen del motor, los milisegundos de consulta sí (ver iteracion-2.md).

Uso:
    python fitness/prototipo_r2.py
"""
import gzip
import json
import math
import random
import sqlite3
import statistics
import sys
import time
import uuid
from dataclasses import dataclass, replace
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA_TABLAS = RAIZ / "fitness" / "resultados" / "r2.md"


@dataclass(frozen=True)
class Supuestos:
    # Datos del escenario R2
    reportes_activos: int = 20_000
    regiones: int = 25
    zonas: int = 1_874
    coordinadores: int = 30
    refresco_s: float = 30.0
    # Red del coordinador (oficina regional durante el simulacro)
    rtt_mediana_s: float = 0.3
    rtt_sigma: float = 0.5
    bajada_mediana_mbps: float = 2.0
    bajada_sigma: float = 0.8
    # Alternativas T6 y T7
    periodo_resumen_s: float = 15.0
    ttl_cache_s: float = 15.0
    # Medición
    repeticiones: int = 50
    muestras_red: int = 20_000
    semilla: int = 1


def crear_base(s, rng):
    db = sqlite3.connect(":memory:")
    db.execute("""CREATE TABLE reporte (id TEXT PRIMARY KEY, lat REAL, lon REAL, gravedad INTEGER,
                  estado TEXT, zona INTEGER, region INTEGER, recibido TEXT)""")
    db.execute("CREATE INDEX reporte_zona ON reporte (zona)")
    db.execute("CREATE INDEX reporte_region ON reporte (region)")
    centros = [(rng.uniform(-18.3, -3.4), rng.uniform(-81.3, -68.7)) for _ in range(s.zonas)]
    region_de = [z * s.regiones // s.zonas for z in range(s.zonas)]
    pesos = [rng.lognormvariate(0, 1) for _ in range(s.zonas)]
    filas = []
    for zona in rng.choices(range(s.zonas), weights=pesos, k=s.reportes_activos):
        lat, lon = centros[zona]
        filas.append((
            str(uuid.UUID(int=rng.getrandbits(128))), lat + rng.gauss(0, 0.02), lon + rng.gauss(0, 0.02),
            rng.choices([1, 2, 3], weights=[6, 3, 1])[0], "Recibido", zona, region_de[zona],
            f"2026-11-05T10:{rng.randrange(60):02d}:{rng.randrange(60):02d}-05:00",
        ))
    db.executemany("INSERT INTO reporte VALUES (?, ?, ?, ?, ?, ?, ?, ?)", filas)
    db.execute("""CREATE TABLE resumen_zona (zona INTEGER PRIMARY KEY, region INTEGER, lat REAL, lon REAL,
                  total INTEGER, g1 INTEGER, g2 INTEGER, g3 INTEGER)""")
    db.commit()
    return db


SQL_AGRUPADO = """SELECT zona, region, ROUND(AVG(lat), 4), ROUND(AVG(lon), 4), COUNT(*),
                         SUM(gravedad = 1), SUM(gravedad = 2), SUM(gravedad = 3)
                  FROM reporte {filtro} GROUP BY zona, region"""


def refrescar_resumen(db):
    db.execute("DELETE FROM resumen_zona")
    db.execute("INSERT INTO resumen_zona " + SQL_AGRUPADO.format(filtro=""))
    db.commit()


def json_comprimido(datos):
    cuerpo = json.dumps(datos, separators=(",", ":")).encode()
    return cuerpo, gzip.compress(cuerpo, 6)


def zonas_json(filas):
    return [{"zona": z, "region": r, "lat": la, "lon": lo, "total": t, "g": [g1, g2, g3]}
            for z, r, la, lo, t, g1, g2, g3 in filas]


def respuesta_listado(db, region=None):
    filtro, args = ("WHERE region = ?", (region,)) if region is not None else ("", ())
    filas = db.execute(f"SELECT id, lat, lon, gravedad, estado, zona, recibido FROM reporte {filtro}", args)
    return json_comprimido([{"id": i, "lat": round(la, 6), "lon": round(lo, 6), "gravedad": g, "estado": e,
                             "zona": z, "recibido": t} for i, la, lo, g, e, z, t in filas])


def respuesta_agrupada(db, region=None):
    filtro, args = ("WHERE region = ?", (region,)) if region is not None else ("", ())
    return json_comprimido(zonas_json(db.execute(SQL_AGRUPADO.format(filtro=filtro), args)))


def respuesta_resumen(db, region=None):
    filtro, args = ("WHERE region = ?", (region,)) if region is not None else ("", ())
    return json_comprimido(zonas_json(db.execute(f"SELECT * FROM resumen_zona {filtro}", args)))


def medir(funcion, repeticiones, *args):
    tiempos = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        cuerpo, comprimido = funcion(*args)
        tiempos.append(time.perf_counter() - inicio)
    return tiempos, len(cuerpo), len(comprimido)


def percentil(valores, p):
    ordenados = sorted(valores)
    return ordenados[math.ceil(p / 100 * len(ordenados)) - 1]


def carga_p95(s, rng, tiempos_servidor, bytes_gzip):
    muestras = []
    for _ in range(s.muestras_red):
        rtt = rng.lognormvariate(math.log(s.rtt_mediana_s), s.rtt_sigma)
        bajada_bps = rng.lognormvariate(math.log(s.bajada_mediana_mbps), s.bajada_sigma) * 1e6
        muestras.append(rng.choice(tiempos_servidor) + rtt + bytes_gzip * 8 / bajada_bps)
    return percentil(muestras, 95)


ALTERNATIVAS = {
    "Antes: listado de reportes": {"respuesta": respuesta_listado, "filtro_local": True, "retraso_extra": 0.0, "cache": False},
    "T5: agrupar en el servidor": {"respuesta": respuesta_agrupada, "filtro_local": False, "retraso_extra": 0.0, "cache": False},
    "T5 + T6: resumen del worker": {"respuesta": respuesta_resumen, "filtro_local": False, "retraso_extra": "periodo", "cache": False},
    "T5 + T7: caché compartida": {"respuesta": respuesta_agrupada, "filtro_local": False, "retraso_extra": "ttl", "cache": True},
}


def evaluar(s):
    rng = random.Random(s.semilla)
    db = crear_base(s, rng)
    refrescar_resumen(db)
    inicio = time.perf_counter()
    for _ in range(20):
        refrescar_resumen(db)
    costo_resumen = (time.perf_counter() - inicio) / 20
    resultados = {}
    for nombre, alt in ALTERNATIVAS.items():
        tiempos, crudo, comprimido = medir(alt["respuesta"], s.repeticiones, db)
        consultas_por_s = s.coordinadores / s.refresco_s
        if alt["cache"]:
            # Solo la primera petición de cada TTL consulta la base; las demás leen bytes ya comprimidos.
            consultas_por_s = 1 / s.ttl_cache_s
            aciertos = 1 - consultas_por_s / (s.coordinadores / s.refresco_s)
            tiempos_vistos = [t if rng.random() > aciertos else 1e-5 for t in tiempos]
        else:
            tiempos_vistos = tiempos
        carga = carga_p95(s, rng, tiempos_vistos, comprimido)
        if alt["filtro_local"]:
            filtro = 0.0
        else:
            region = rng.randrange(s.regiones)
            t_filtro, _, gz_filtro = medir(alt["respuesta"], 50, db, region)
            filtro = carga_p95(s, rng, t_filtro, gz_filtro)
        extra = {"periodo": s.periodo_resumen_s, "ttl": s.ttl_cache_s}.get(alt["retraso_extra"], 0.0)
        cpu = statistics.fmean(tiempos) * consultas_por_s
        if alt["retraso_extra"] == "periodo":
            cpu += costo_resumen / s.periodo_resumen_s
        resultados[nombre] = {
            "crudo_kb": crudo / 1024,
            "gzip_kb": comprimido / 1024,
            "servidor_p95_ms": percentil(tiempos, 95) * 1000,
            "carga_p95_s": carga,
            "filtro_p95_s": filtro,
            "retraso_max_s": s.refresco_s + extra + carga,
            "cpu_pct": cpu * 100,
        }
    return resultados, costo_resumen


def decimal(valor, digitos=1):
    return f"{valor:,.{digitos}f}".replace(",", " ").replace(".", ",")


def marca(cumple):
    return "Sí" if cumple else "**No**"


def tabla(resultados):
    filas = [
        "| Alternativa | Respuesta (KB) | Con gzip (KB) | Servidor p95 (ms) | Carga del mapa p95 (s) | Cambio de filtro p95 (s) | Retraso máximo (s) | CPU del servidor (% de 1 núcleo) | ¿Cumple R2? |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for nombre, r in resultados.items():
        cumple = r["carga_p95_s"] <= 3 and r["filtro_p95_s"] <= 1 and r["retraso_max_s"] <= 60
        filtro = "0 (en el navegador)" if r["filtro_p95_s"] == 0 else decimal(r["filtro_p95_s"], 2)
        filas.append(
            f"| {nombre} | {decimal(r['crudo_kb'], 0)} | {decimal(r['gzip_kb'], 0)} | {decimal(r['servidor_p95_ms'])} "
            f"| {decimal(r['carga_p95_s'], 2)} | {filtro} | {decimal(r['retraso_max_s'], 0)} | {decimal(r['cpu_pct'], 2)} | {marca(cumple)} |"
        )
    return "\n".join(filas)


VARIANTES = {
    "Base (2 Mbps, 20 000 reportes)": {},
    "Bajada de 1 Mbps": {"bajada_mediana_mbps": 1.0},
    "Bajada de 5 Mbps": {"bajada_mediana_mbps": 5.0},
    "40 000 reportes activos": {"reportes_activos": 40_000},
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    s = Supuestos()
    resultados, costo_resumen = evaluar(s)
    texto = ["## Resultados con los supuestos base", "", tabla(resultados), "",
             f"Recalcular la tabla resumen_zona (T6) cuesta {decimal(costo_resumen * 1000)} ms por ejecución.", "",
             "## Sensibilidad: carga del mapa p95 (s)", "",
             "| Variante | " + " | ".join(ALTERNATIVAS) + " |",
             "|---|" + "---|" * len(ALTERNATIVAS)]
    for nombre, cambios in VARIANTES.items():
        r, _ = evaluar(replace(s, **cambios))
        texto.append(f"| {nombre} | " + " | ".join(decimal(r[a]["carga_p95_s"], 2) for a in ALTERNATIVAS) + " |")
    salida = "\n".join(texto) + "\n"
    print(salida)
    SALIDA_TABLAS.parent.mkdir(parents=True, exist_ok=True)
    SALIDA_TABLAS.write_text("# Resultados de fitness/prototipo_r2.py\n\n" + salida, encoding="utf-8")


if __name__ == "__main__":
    main()
