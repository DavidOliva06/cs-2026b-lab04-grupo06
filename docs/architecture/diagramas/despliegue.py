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
    "fontsize": "20",
    "labelloc": "t",
    "pad": "0.6",
    "splines": "spline",
    "nodesep": "0.6",
    "ranksep": "1.1",
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
            "Celular del ciudadano\nPWA + cola local en IndexedDB\n(gama baja, R-05)"
        )
        celular_brigadista = Mobile("Celular del brigadista\nPWA: asignaciones y estado")
        navegador_coordinador = Client("Navegador del coordinador\nPanel: mapa y asignacion")

    # --- Servidor unico en la nube ----------------------------------------
    with Cluster("Servidor unico en la nube - 1 vCPU / 2 GB, US$ 20-30 al mes (R-03)"):

        proxy = Nginx("Proxy inverso (Nginx)\nTLS 1.2+, buffer de subidas,\nlimite de peticiones")

        with Cluster("Monolito modular en Python (un solo despliegue)"):
            app = Gunicorn(
                "Proceso web (Gunicorn)\nAPI HTTP, roles,\nreportes | mapa | priorizacion | brigadas"
            )
            worker = Python("Worker en segundo plano\nprocesa fotos y\nrecalcula la priorizacion")

        with Cluster("PostgreSQL (una sola instancia)"):
            bd = Postgresql(
                "Esquema de datos\nreportes, usuarios, consentimientos,\nzonas, asignaciones"
            )
            cola = Postgresql("Tabla de trabajos = cola\nSELECT ... FOR UPDATE SKIP LOCKED")

        fotos = Storage("Volumen de fotos\nseparado del volumen del sistema")
        agente = Prometheus("Agente de metricas y logs\n(expone /metrics)")

    # --- Servicios externos ------------------------------------------------
    with Cluster("Servicios externos"):
        teselas = OSM("Teselas de mapa\nOpenStreetMap o proveedor")

    # --- Monitoreo y respaldo, fuera del servidor --------------------------
    with Cluster("Monitoreo y respaldo (fuera del servidor caido)"):
        monitoreo = Grafana("Monitoreo externo\nuptime, p95 del mapa,\ntamano de la cola")
        respaldo = Storage("Respaldo diario cifrado\nalmacenamiento de objetos")

    # --- Trafico de los usuarios ------------------------------------------
    celular_ciudadano >> Edge(label="HTTPS: reporte de ~1 KB primero,\nfoto despues; reintento con espera aleatoria") >> proxy
    celular_brigadista >> Edge(label="HTTPS: consulta y\nactualiza su asignacion") >> proxy
    navegador_coordinador >> Edge(label="HTTPS: mapa y\npriorizacion (p95 <= 3 s)") >> proxy
    navegador_coordinador >> Edge(label="HTTPS: mapa base\n(directo al proveedor)", style="dashed") >> teselas

    # --- Dentro del servidor ----------------------------------------------
    proxy >> Edge(label="HTTP local (socket Unix)") >> app
    app >> Edge(label="SQL: una transaccion\nreporte + trabajo") >> bd
    app >> Edge(label="SQL: inserta el trabajo") >> cola
    app >> Edge(label="escribe la foto original") >> fotos
    worker << Edge(label="toma trabajos pendientes\n(sondeo, SKIP LOCKED)") << cola
    worker >> Edge(label="SQL: guarda zonas priorizadas\n(<= 60 s)") >> bd
    worker >> Edge(label="redimensiona y\nlimpia metadatos EXIF") >> fotos

    # --- Monitoreo y respaldo ---------------------------------------------
    app >> Edge(label="metricas y logs", style="dotted") >> agente
    worker >> Edge(label="estado de la cola", style="dotted") >> agente
    agente >> Edge(label="raspado cada 30 s", style="dotted") >> monitoreo
    monitoreo >> Edge(label="sonda HTTPS /salud cada 60 s\ny alerta al desarrollador", style="dashed", color="firebrick") >> proxy
    bd >> Edge(label="pg_dump diario", style="dotted") >> respaldo
    fotos >> Edge(label="copia diaria", style="dotted") >> respaldo

print(f"Diagrama generado en {SALIDA.with_suffix('.png')}")
