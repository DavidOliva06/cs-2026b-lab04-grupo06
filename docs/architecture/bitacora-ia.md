## 1. Prompt 1
| Criterio | A. Monolito síncrono | B. Monolito modular + cola | C. Microservicios + broker |
|---|---|---|---|
| **Fortalezas** | Es el más simple y rápido de construir. Un solo despliegue, fácil de depurar. | Absorbe ráfagas porque la ingesta es rápida y el trabajo pesado se difiere. Sigue siendo un solo despliegue y una sola base de datos. | Aísla fallos y permite escalar cada servicio por separado. |
| **Debilidades** | El procesamiento de fotos bloquea las peticiones. Un pico degrada también el mapa y la asignación. | El mapa y la priorización se actualizan con segundos de retraso (consistencia eventual). Hay que monitorear la cola y los workers. | Sobrecarga operativa alta: broker, varios despliegues, trazabilidad distribuida. En un solo servidor no se aprovecha el escalado. |
| **Riesgos** | Timeouts en la primera hora provocan reintentos masivos desde los celulares y un efecto bola de nieve. | La cola puede crecer si los workers no dan abasto. Sin idempotencia, los reintentos crean duplicados. | No se llega al MVP en 1 mes con 1 desarrollador. El broker y los servicios compiten por la RAM del mismo servidor. |
| **Favorece** | Tiempo de entrega, simplicidad, costo, consistencia inmediata. | Disponibilidad de la ingesta, rendimiento bajo picos, resiliencia, costo, mantenibilidad. | Escalabilidad, aislamiento de fallos y despliegue independiente (solo con más infraestructura). |
| **Penaliza** | Rendimiento bajo carga, disponibilidad, escalabilidad. | Consistencia inmediata y, levemente, la simplicidad operativa. | Tiempo de entrega, costo, simplicidad, facilidad de pruebas y operación. |
| **Encaje con las restricciones** | Cumple plazo y costo, pero falla en el escenario crítico. | Cumple plazo, costo y el escenario crítico. | No cumple plazo ni presupuesto de forma realista. |
1. se recomienda la alternativa B, un monolito modular con ingesta asíncrona, porque es la única que cumple a la vez el plazo de un mes, el presupuesto de un solo servidor y el escenario crítico de la primera hora. Los 20 000 reportes llegarán en ráfagas al volver la señal, y B los absorbe porque el endpoint de ingesta solo valida, guarda y responde, mientras unos workers procesan después las fotos y la priorización desde una cola en la misma PostgreSQL. El monolito síncrono es más simple, pero se degrada justo cuando el sistema más importa, y los microservicios exigen un equipo y una infraestructura que el proyecto no tiene. El costo de B es que el mapa se actualiza con unos segundos de retraso, y el servidor único sigue siendo un punto único de falla.
## 2. Prompt 2
La alternativa B optimiza la parte fácil del problema, el backend, y deja casi sin tratar las partes donde el sistema fallará de verdad.

1. Supuestos que no se cumplen

- **"Aceptar un reporte es barato":** lo caro es subir la foto por una red congestionada, y eso ocurre antes de que la cola intervenga.
- **"La cola da capacidad":** en un solo servidor, los workers compiten con la ingesta por la misma CPU, RAM y disco, así que la cola solo reordena el trabajo.
- **"El ciudadano ya tiene la PWA":** quien no la instaló antes del sismo tendrá que descargarla con la red caída.
- **"Un desarrollador puede con esto en un mes":** la sincronización offline confiable es lo más difícil del proyecto y consumirá buena parte del plazo.

2. Costos ocultos

- **Operación:** monitoreo, respaldos, alertas y guardia recaen en una sola persona, que quizá también sea damnificada el día del sismo.
- **Pruebas:** hacen falta pruebas de carga y pruebas en celulares de gama baja reales, que no están en el plan de un mes.
- **Desuso:** el sistema pasa meses sin tráfico y se usa de golpe, de modo que certificados vencidos, disco lleno o dependencias rotas se descubren el peor día.

3. Los 5 riesgos más graves

31. **La PWA no está disponible cuando se necesita.**
   - Falla: no está instalada, el navegador borró los reportes pendientes o el usuario cerró la app antes de que se enviaran. En iOS, además, no hay sincronización en segundo plano, hasta donde sé.
   - Táctica: degradación elegante. Un formulario web mínimo de pocos KB funciona sin instalación, el reenvío se dispara al abrir la app y los pendientes se muestran en pantalla hasta confirmarse.

32. **Las subidas lentas agotan la ingesta.**
   - Falla: miles de conexiones que tardan minutos en subir una foto ocupan todos los procesos de Python, y los reportes dejan de entrar.
   - Táctica: separar la carga crítica. Primero se envían el texto y las coordenadas (alrededor de 1 KB) y la foto va después, en una subida aparte. Un proxy inverso delante recibe las conexiones lentas.

33. **Ingesta, workers y base de datos se ahogan entre sí.**
   - Falla: el procesamiento de fotos le quita recursos a la ingesta durante el pico, y si el disco se llena con las fotos, PostgreSQL se cae.
   - Táctica: gobierno de recursos. Durante el pico los workers solo calculan la priorización y las fotos se procesan después. Las fotos van en un volumen separado, y al superar un umbral de disco se rechazan fotos pero se siguen aceptando datos.

34. **Una caída provoca una tormenta de reintentos.**
   - Falla: si el servidor cae, todos los celulares reintentan a la vez y lo tumban de nuevo al levantarse.
   - Táctica: reintentos con espera exponencial y aleatoria en el cliente, límite de peticiones en el servidor con rechazo temprano, y recuperación automatizada mediante un script de despliegue y respaldos probados.

35. **El endpoint abierto recibe basura y expone datos personales.**
   - Falla: reportes falsos o duplicados desvían brigadas, y una fuga de fotos y ubicaciones incumple la Ley 29733.
   - Táctica: límite por dispositivo, agrupación de reportes cercanos para que la prioridad dependa de varias fuentes, y validación por el brigadista. Las fotos se sirven solo a usuarios autenticados y con un plazo de borrado definido.

4. Veredicto

B sigue siendo la mejor de las tres, pero la recomendación estaba incompleta. Para que sea viable en un mes hay que recortar el alcance: en el MVP entran el reporte sin foto obligatoria, el mapa y la asignación manual, y la priorización automática queda para después.
## 3. Prompt 3 Creacion de arquitectura.mmd
%% SismoReporta AQP - Arquitectura elegida: B (monolito modular con ingesta asincrona)
%% Convencion: la flecha A --> B significa "A depende de B" (A llama o lee a B)
flowchart TB
    ciudadano(["Ciudadano"])
    brigadista(["Brigadista"])
    coordinador(["Coordinador"])

    subgraph CLIENTE["Cliente: PWA en el navegador"]
        direction TB
        uiReporte["Formulario de reporte<br/>foto, ubicacion, consentimiento"]
        uiBrigada["Vista de brigadista<br/>asignaciones y estado"]
        uiPanel["Panel del coordinador<br/>mapa, zonas, asignacion"]
        sync["Sincronizador<br/>reintentos con espera aleatoria"]
        colaLocal[("Cola local<br/>IndexedDB")]
    end

    subgraph EXTERNO["Servicios externos"]
        teselas["Servicio de teselas de mapa<br/>OpenStreetMap o proveedor"]
    end

    subgraph SERVIDOR["Servidor unico en la nube"]
        direction TB
        proxy["Proxy inverso<br/>TLS, bufer, limite de peticiones"]

        subgraph MONOLITO["Monolito modular en Python"]
            direction TB

            subgraph ENTRADA["Capa de entrada"]
                api["API HTTP"]
                auth["Autenticacion y roles"]
            end

            subgraph DOMINIO["Modulos de dominio"]
                reportes["Reportes<br/>ingesta idempotente por UUID"]
                mapa["Mapa de danos"]
                priorizacion["Priorizacion de zonas"]
                brigadas["Brigadas<br/>asignacion y estado"]
            end

            worker["Worker en segundo plano<br/>fotos y recalculo periodico"]
        end

        subgraph DATOS["Almacenamiento"]
            pg[("PostgreSQL<br/>reportes, usuarios, consentimientos,<br/>asignaciones, cola de trabajos")]
            fotos[("Disco<br/>fotos")]
        end
    end

    %% Actores
    ciudadano --> uiReporte
    brigadista --> uiBrigada
    coordinador --> uiPanel

    %% Cliente
    uiReporte -->|"guarda el reporte"| colaLocal
    sync -->|"lee pendientes"| colaLocal
    sync -->|"HTTPS"| proxy
    uiBrigada -->|"HTTPS"| proxy
    uiPanel -->|"HTTPS"| proxy
    uiPanel -->|"mapa base"| teselas

    %% Capa de entrada
    proxy --> api
    api --> auth
    api --> reportes
    api --> mapa
    api --> brigadas

    %% Dominio
    mapa -->|"lee zonas priorizadas"| priorizacion
    brigadas -->|"lee zonas priorizadas"| priorizacion
    worker -->|"ejecuta el recalculo"| priorizacion
    worker -->|"procesa fotos"| reportes

    %% Datos
    auth --> pg
    reportes -->|"reporte y trabajo en una transaccion"| pg
    reportes --> fotos
    mapa --> pg
    priorizacion --> pg
    brigadas --> pg
    worker -->|"toma trabajos"| pg
## 4. Prompt 4 Creacion de alternativa.uml
@startuml
title SismoReporta AQP - Alternativa A descartada: monolito en capas síncrono

actor Ciudadano
actor Brigadista
actor Coordinador

node "Celular o navegador" {
  component "PWA offline-first" as PWA
  database "Cola local\n(IndexedDB)" as IDB
}

cloud "Servicio de teselas de mapa" as Teselas

node "Servidor único en la nube" {
  component "Proxy inverso (TLS)" as Proxy

  package "Monolito en capas síncrono (Python)" {
    component "Capa de presentación\nAPI HTTP, autenticación y roles" as Presentacion
    component "Capa de lógica de negocio\nreportes, mapa, priorización, brigadas" as Negocio
    component "Capa de acceso a datos" as Datos
  }

  database "PostgreSQL" as PG
  folder "Disco de fotos" as Fotos
}

Ciudadano --> PWA
Brigadista --> PWA
Coordinador --> PWA

PWA --> IDB : guarda reportes pendientes
PWA --> Proxy : HTTPS
PWA --> Teselas : mapa base

Proxy --> Presentacion
Presentacion --> Negocio : llamada síncrona
Negocio --> Datos
Datos --> PG : SQL
Datos --> Fotos : archivos

note right of Negocio
  Descartada: obtuvo 3,35 en la matriz de decisión, frente a 4,00 de la alternativa B.
  Puntuó 2 de 5 en disponibilidad ante picos (C1, peso 30 %) y en rendimiento (C3, peso 15 %).
  Cada petición procesa la foto y la priorización antes de responder,
  así que el pico de QA-01 frena a la vez la ingesta y el mapa.
  Sus 5 de 5 en tiempo de entrega (C2) y simplicidad (C4) no compensan el atributo crítico.
end note
@enduml
## 5. Prompt 5 Creacion de despliegue.py(Corregida)
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

Modificacion: El diagrama funcionaba pero las etiquetas de nodos vecinos se solapan. Se ajusto la separacion y se acorto las lineas para mejorar la vista.


