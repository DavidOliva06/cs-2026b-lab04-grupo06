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

## 6. Prompt 6 Creacion de clases(Sin Aceptar)
    Prompt:
    Actúa como diseñador de software orientado a objetos. Contexto: módulo almacenamiento de un monolito modular con ingesta asíncrona como estilo arquitectónico
    Historia y criterios: el archivo historia.md.
    Tarea: genera un diagrama de clases en PlantUML con atributos tipados, operaciones, multiplicidades,
    una enumeración para el estado del pedido y una interfaz (puerto) para la pasarela de pagos.
    Formato: solo el código PlantUML. No agregues clases que no se deriven de la historia; si asumes algo, indícalo en un
    comentario.
    Respuesta:
    

## 7. Prompt 7 (Lab 08, E1) Escenarios de calidad de seis partes
    Prompt:
    Actúa como arquitecto de software. Contexto: drivers.md, ADR-001 y el nuevo contexto [escenario de crecimiento].
    Tarea: propón escenarios de calidad de seis partes (fuente, estímulo, entorno, artefacto, respuesta, medida)
    para rendimiento, disponibilidad, seguridad y modificabilidad. Para cada uno sugiere (importancia, dificultad)
    con H/M/L y justifícalo. Restricciones: medidas numéricas; no propongas soluciones todavía.
    Respuesta:
    13 escenarios candidatos (D1 a D4, R1 a R3, S1 a S3, M1 a M3) con su calificación, el árbol de utilidad en
    Graphviz (arbol.dot) y escenarios.md.
Verificación y corrección:
- El primer contexto pegado (de 300 a 1 200 buses, 50 000 consultas de tiempo de llegada) era de otro caso. La IA lo
  detectó al compararlo con drivers.md y preguntó; el equipo lo corrigió por el simulacro nacional (20 000 reportes en
  1 hora con la red móvil congestionada).
- **Falso positivo de los escenarios:** al revisar la lista de verificación ("ninguna medida dice rápido, seguro o fácil"),
  la búsqueda automática de esas palabras marcó `escenarios.md`, línea 86. Era la propia línea de la lista de
  verificación, que cita las palabras entre comillas, no una medida. Ninguna medida se cambió.
- Corrección de la calificación: la IA calificó R2 como (H,M) porque el mapa "es una consulta de lectura". Se corrigió
  a (H,H): el servidor es único (R-03) y la consulta compite con ≈ 33 escrituras por segundo de la ingesta (ADR-001).
  Esa corrección también la redactó la IA, a pedido del equipo; el equipo debe confirmarla o reemplazarla por la suya.

## 8. Prompt 8 (Lab 08, E2) Tácticas candidatas para el escenario objetivo
    Prompt:
    Elija como objetivo el escenario de mayor prioridad y dificultad. Propón 4 tácticas candidatas del catálogo de
    Bass et al. Para cada una indica qué mejora, qué empeora, costo aproximado y complejidad para un equipo de
    1 developer. Respeta el ADR-001; si recomiendas cambiar el estilo, justifícalo con números.
    Respuesta:
    Objetivo D1. Tácticas T1 (limitar la respuesta a eventos), T2 (degradación), T3 (aumentar recursos de forma
    temporal) y T4 (redundancia pasiva). Recomendó T2 + T1, con T3 como margen, y mantener el estilo de ADR-001.
Verificación y corrección:
- El equipo pidió reanalizar los trade-offs y rechazar al menos una táctica. Al reanalizar, la IA cambió su propia
  recomendación: T3 pasó de "margen útil" a **rechazada**, porque un simulacro con 4 veces los recursos aprueba D1 con
  una capacidad que no existirá en un sismo real. T4 se rechazó por costo (US$ 40–60 al mes, fuera de R-03).
- Varias cifras de partida (foto de 300 KB, subida de 50 kbps, 30 ms por petición) son supuestos de la IA y quedaron
  escritos como tales en iteracion-1.md.

## 9. Prompt 9 (Lab 08, E2) Evidencia del escenario antes y después
    Prompt:
    Genere evidencia: adapte una de las simulaciones del ejemplo con datos de su caso (tasa de llegada, tiempos de
    servicio, probabilidad de falla) o construya un prototipo mínimo. Debe mostrar el escenario antes y después de la táctica.
    Respuesta:
    Simulación de eventos discretos fitness/simulacion_d1.py (solo biblioteca estándar), con tablas, sensibilidad y
    dos gráficos SVG.
Verificación y corrección:
- El resultado contradijo el análisis previo de la IA: con los supuestos base, la arquitectura "antes" ya cumplía D1
  (100 %). No se ajustaron los supuestos para que fallara; se agregó una caída del servidor de 10 min, donde "antes"
  baja a 97,47 % y T2 cumple.
- La simulación mostró que T1 no mejoraba D1 en ninguna variante. La decisión de la iteración 1 cambió de "T1 + T2" a
  "T2; T1 aplazada".
- Los gráficos se revisaron renderizados: las etiquetas al final de las líneas se encimaban y se quitaron.

## 10. Prompt 10 (Lab 08, E4) Iteraciones 2 y 3 de ADD
    Prompt:
    Realicen dos iteraciones más, cada una con un escenario (H,*) distinto. Al menos una debe atender disponibilidad
    o seguridad. Cada iteración sigue los 7 pasos de ADD y produce evidencia; se acepta una comparación de
    alternativas cuando el atributo no se puede simular.
    Respuesta:
    Iteración 2 (R2) con el prototipo fitness/prototipo_r2.py e iteración 3 (S2) con la simulación
    fitness/simulacion_s2.py, más una comparación de alternativas para la autenticación por SMS.
Verificación y corrección:
- PostgreSQL pedía contraseña, así que el prototipo de R2 usa SQLite. Los bytes de cada respuesta no dependen del motor;
  los milisegundos sí, y quedó como riesgo (RI-07).
- **Falso positivo de la simulación de S2:** la columna "zonas que entran al top 20 por el ataque" mostraba 12 zonas
  para el límite por IP. Al revisarla, esas zonas no las movía el ataque, sino los reportes legítimos bloqueados por el
  CGNAT. Se renombró la medida a "zonas del top 20 distintas de las que darían solo los legítimos".
- Se agregó la variante "ataque concentrado en 1 zona" para comprobar si T11 aportaba algo sobre T9: sin ella, T11 no
  tenía evidencia propia.

## 11. Prompt 11 (Lab 08, E5) Fitness functions estructurales
    Prompt:
    Escriban 2 o más fitness functions estructurales que verifiquen las reglas de su ADR-001 y ADR-005 (import-linter).
    Respuesta:
    4 contratos en .importlinter: la ingesta no importa la IA, la IA está aislada, las capas van en un solo sentido y
    el servicio no depende de adaptadores ni de servicios externos.
Verificación y corrección:
- Prueba de mutación: en una copia del código se inyectaron 3 imports prohibidos y los 4 contratos fallaron, así que los
  que pasan no lo hacen sin verificar nada.
- El contrato del servicio falló sobre el código real: servicio.py importaba externos y adaptadores, en contra de lo
  que afirma ADR-005. El equipo eligió corregir el código: se separó entrada.py (endpoint HTTP, controlador y
  demostración) y las 25 pruebas siguieron pasando.

## 12. Prompt 12 (Lab 08, E6) ADR-006 a ADR-008 y workspace.dsl
    Prompt:
    Redacten un ADR por iteración (ADR-006 a ADR-008) con la plantilla de los anteriores, incluyendo la evidencia y el
    trade-off aceptado. Actualicen workspace.dsl: nuevos contenedores o tecnologías y, en la descripción de cada
    elemento, el escenario que atiende [QA-xx]. Ejecuten structurizr validate y exporten la vista de contenedores.
    Respuesta:
    Tres ADR, el componente Dispositivos, las etiquetas [QA-xx], la validación sin errores y la exportación a PlantUML,
    Mermaid y PNG.
Verificación y corrección:
- Al revisar la vista de despliegue, la IA encontró que **su propia simulación de D1 suponía 2 núcleos, pero el droplet
  del Lab 06 tiene 1 vCPU**. Se repitió con 1 núcleo: "antes" ya no cumple D1 ni sin fallas (98,82 %), T2 sigue
  cumpliendo (100 %; 99,86 % con la caída de 10 min), y T1 + T2 no cumple con la caída (99,28 %). La decisión de ADR-006 se mantiene y T1 pasa de
  aplazada a rechazada. Quedó como el riesgo R-03 de atam-lite.md.

## 13. Prompt 13 (Lab 08, E7) ATAM-lite y matriz de riesgos
    Prompt:
    Completen atam-lite.md con todos los hallazgos (propios y recibidos) y una matriz de probabilidad e impacto.
    Para cada riesgo de la zona crítica, indiquen la mitigación o la razón para aceptarlo.
    Respuesta:
    atam-lite.md con riesgos, puntos de sensibilidad, puntos de trade-off y no riesgos, y la matriz generada por
    docs/architecture/riesgos/matriz_riesgos.py.
Verificación y corrección:
- No hay hallazgos recibidos: el equipo no realizó E3 (revisión cruzada). La IA no los inventó; atam-lite.md lo indica.
- Las probabilidades e impactos son una propuesta de la IA a partir de la evidencia de las iteraciones; el equipo debe
  revisarlos.

## 14. Prompt 14 (Lab 08, revisión del 2026-11-13) Revisión de la entrega
    Prompt:
    Revisa la entrega del Lab 08 contra la guía y la crítica del informe: E1–E7 sin evidencia en texto, E8 sin
    evidencia, sin evaluación cruzada y restos del escenario de RutaSIT.
    Respuesta:
    .github/workflows/fitness.yml y tests/test_fitness.py estaban vacíos (0 bytes), así que E5.3 y E5.4 no se
    habían cumplido y el README no tenía insignia; no existía la etiqueta v0.8-arquitectura; paquetes.puml no tenía
    el módulo dispositivos de ADR-008; y el cuestionario del informe tenía las preguntas del Lab 05.
Verificación y corrección:
- Se escribieron 8 fitness functions de calidad y el workflow. Para comprobar que no pasan "porque sí", cada una
  verifica también que la versión sin la táctica no cumple, y 4 mutaciones (quitar ON CONFLICT, el modo pico, el
  mapa agregado y el límite de 10) hacen fallar una prueba cada una.
- La violación estructural se hizo en una rama, como pide la guía, con la salida de lint-imports documentada en
  fitness.md (2 de 4 contratos rotos) y revertida.
- La salida de lint-imports mostró que la violación servicio → adaptadores **no** rompe el contrato de capas (va
  hacia abajo, y las capas lo permiten); la detecta adr005-servicio-sin-infraestructura. Se documentó en fitness.md
  para que nadie quite ese contrato pensando que el de capas ya lo cubre.
- El restante "300 a 1 200 buses" solo queda en la interacción 7 de esta bitácora, donde se registra como error de
  contexto; se quitó del informe.

