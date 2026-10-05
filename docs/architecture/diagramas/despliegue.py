"""SismoReporta AQP - Diagrama de despliegue de la alternativa elegida (B).

Muestra donde se ejecuta cada parte del sistema descrito en ADR-001 (monolito
modular con ingesta asincrona), ADR-002 (cola de trabajos en PostgreSQL) y
ADR-003 (PWA offline-first).

Decisiones que el diagrama hace explicitas:
  - Un unico servidor en la nube (R-03), asi que no hay balanceador entre
    varias instancias: el proxy inverso esta delante de un solo proceso web.
  - No hay cache ni broker de mensajes. La cola es una tabla dentro de la misma
    PostgreSQL, consumida con SKIP LOCKED (ADR-002), porque R-02 limita las
    tecnologias a Python, JavaScript, CSS y PostgreSQL.
  - El monitoreo y el respaldo viven fuera del servidor, para que sigan
    avisando cuando el servidor (punto unico de falla) se cae.

Uso:
    pip install diagrams          # requiere Graphviz instalado en el sistema
    python despliegue.py          # genera img/despliegue.png
"""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.generic.device import Mobile
from diagrams.generic.storage import Storage
from diagrams.onprem.client import Client
from diagrams.onprem.database import Postgresql
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.network import Gunicorn, Nginx, OSM
from diagrams.programming.language import Python

SALIDA = Path(__file__).parent / "img" / "despliegue"

ATRIBUTOS_GRAFO = {
    "fontsize": "22",
    "fontname": "Sans-Serif",
    "labelloc": "t",
    "pad": "0.8",
    "splines": "spline",
    "nodesep": "1.8",
    "ranksep": "1.6",
    "bgcolor": "white",
}

with Diagram(
    "SismoReporta AQP - Despliegue (alternativa B: monolito modular con ingesta asincrona)",
    filename=str(SALIDA),
    outformat="png",
    show=False,
    direction="TB",
    graph_attr=ATRIBUTOS_GRAFO,
):

    # --- Dispositivos de los usuarios -------------------------------------
    with Cluster("Dispositivos de los usuarios (red movil intermitente)"):
        celular_ciudadano = Mobile(
            "Celular del ciudadano\nPWA + cola local\nen IndexedDB\n(gama baja, R-05)"
        )
        celular_brigadista = Mobile("Celular del brigadista\nPWA: asignaciones\ny estado")
        navegador_coordinador = Client("Navegador del coordinador\nPanel: mapa y asignacion")

    # --- Servidor unico en la nube ----------------------------------------
    with Cluster("Servidor unico en la nube - 1 vCPU / 2 GB, US$ 20-30 al mes (R-03)"):

        proxy = Nginx(
            "Proxy inverso (Nginx)\nTLS 1.2+, buffer de subidas,\nlimite de peticiones\n"
            "sin balanceador: un solo servidor"
        )

        with Cluster("Monolito modular en Python (un solo despliegue)"):
            app = Gunicorn(
                "Proceso web (Gunicorn)\nAPI HTTP y roles; modulos:\n"
                "reportes, mapa,\npriorizacion, brigadas"
            )
            worker = Python(
                "Worker en segundo plano\nprocesa fotos y recalcula\nla priorizacion"
            )

        with Cluster("PostgreSQL (una sola instancia)"):
            bd = Postgresql(
                "Esquema de datos\nreportes, usuarios,\nconsentimientos,\nzonas, asignaciones"
            )
            cola = Postgresql(
                "Tabla de trabajos = cola\nsin broker ni cache (R-02)\nFOR UPDATE SKIP LOCKED"
            )

        fotos = Storage("Volumen de fotos\nseparado del\nvolumen del sistema")
        agente = Prometheus("Agente de metricas\ny logs (expone /metrics)")

    # --- Servicios externos ------------------------------------------------
    with Cluster("Servicios externos"):
        teselas = OSM("Teselas de mapa\nOpenStreetMap\no proveedor")

    # --- Monitoreo y respaldo, fuera del servidor --------------------------
    with Cluster("Monitoreo y respaldo (fuera del servidor que puede caerse)"):
        monitoreo = Grafana("Monitoreo externo\nuptime, p95 del mapa,\ntamano de la cola")
        respaldo = Storage("Respaldo diario cifrado\nalmacenamiento\nde objetos")

    # --- Trafico de los usuarios ------------------------------------------
    celular_ciudadano >> Edge(
        label="HTTPS: reporte de ~1 KB primero,\nfoto despues;\nreintento con espera aleatoria"
    ) >> proxy
    celular_brigadista >> Edge(label="HTTPS: consulta y\nactualiza su asignacion") >> proxy
    navegador_coordinador >> Edge(label="HTTPS: mapa y\npriorizacion (p95 <= 3 s)") >> proxy
    navegador_coordinador >> Edge(
        label="HTTPS: mapa base\n(directo al proveedor)", style="dashed"
    ) >> teselas

    # --- Dentro del servidor ----------------------------------------------
    proxy >> Edge(label="HTTP local\n(socket Unix)") >> app
    app >> Edge(label="SQL: una transaccion\nreporte + trabajo") >> bd
    app >> Edge(label="SQL: inserta\nel trabajo") >> cola
    app >> Edge(label="escribe la\nfoto original") >> fotos
    worker << Edge(label="toma trabajos pendientes\n(sondeo, SKIP LOCKED)") << cola
    worker >> Edge(label="SQL: guarda zonas\npriorizadas (<= 60 s)") >> bd
    worker >> Edge(label="redimensiona y limpia\nmetadatos EXIF") >> fotos

    # --- Monitoreo y respaldo ---------------------------------------------
    app >> Edge(label="metricas y logs", style="dotted") >> agente
    worker >> Edge(label="estado de la cola", style="dotted") >> agente
    agente >> Edge(label="raspado cada 30 s", style="dotted") >> monitoreo
    monitoreo >> Edge(
        label="sonda HTTPS /salud cada 60 s\ny alerta al desarrollador",
        style="dashed",
        color="firebrick",
    ) >> proxy
    bd >> Edge(label="pg_dump diario", style="dotted") >> respaldo
    fotos >> Edge(label="copia diaria", style="dotted") >> respaldo

print(f"Diagrama generado en {SALIDA.with_suffix('.png')}")
