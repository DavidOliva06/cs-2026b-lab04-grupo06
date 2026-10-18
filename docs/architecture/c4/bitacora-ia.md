## E2: workspace.dsl correciones
| Propuesta de la IA | Decisión | Justificación |
|---|---|---|
| "Proxy inverso" como contenedor dentro de SismoReporta AQP | Corregida | Es infraestructura que solo se configura, no se programa: va como nodo de infraestructura en la vista de despliegue, no como contenedor. |
| Tecnología "Por definir (fuera del ADR-001)" para el proxy | Corregida | No figura en el ADR-001. Al pasar el proxy a infraestructura se quitó la tecnología; elegir uno requiere su propio ADR. |
| Relaciones PWA → proxy → API en la vista de contenedores | Corregida | En contenedores la PWA se comunica con la API ("a través del proxy inverso"). El proxy solo aparece en despliegue, y ahí se excluye la relación directa PWA → API para no mostrar dos caminos. |
| "1 vCPU y 2 GB de RAM" en el nodo del servidor | Corregida | El dato venía de despliegue.py; el ADR-001 y R-03 solo fijan el costo. Se dejó "US$ 20-30 al mes". |
| Nginx, Gunicorn, Prometheus y Grafana (de despliegue.py, Lab 04) | Rechazada | No figuran en el ADR-001, así que no se pasaron al DSL. Para conservarlas hay que registrarlas en un ADR o quitarlas de despliegue.py. |
| "Servicio de teselas de mapa" con la etiqueta "Externo" | Aceptada | Es un sistema externo que no construimos ni desplegamos, y está fuera del límite de SismoReporta AQP. |
| Nodo "Proveedor de teselas" en la vista de despliegue | Aceptada | Se marca "Externo" y su descripción aclara que el equipo no lo despliega. |
| "Almacenamiento de fotos" como contenedor | Aceptada | En C4, un sistema de archivos donde el sistema guarda datos es un contenedor, igual que una base de datos. La tecnología quedó como "Sistema de archivos", sin nombre de producto. |
| Worker como contenedor separado de la API | Aceptada | Comparte código con la API, pero se ejecuta como otro proceso (ADR-001). |
| IndexedDB y la cola de trabajos sin contenedor propio | Aceptada | IndexedDB vive en el navegador, dentro de la PWA (ADR-003). La cola es una tabla de PostgreSQL (ADR-002). |
| Tecnologías Python, JavaScript, CSS y PostgreSQL en los contenedores | Aceptada | Las cuatro figuran en el ADR-001 y en R-02. |
| Protocolo en las relaciones | Aceptada | Todas las relaciones tienen protocolo: HTTPS, HTTPS (JSON), HTTP local, SQL, E/S de archivos y llamada en proceso. |

## Workspace Produccion:
Prompt: Defina deploymentEnvironment "Producción" con nodos anidados: dispositivo del usuario, servidor o nube, Docker u otro entorno de ejecución.
Coloque una instancia (containerInstance) de cada contenedor del nivel 2 en algún nodo.
Indique sistema operativo, tamaño o servicio de nube de cada nodo, y compruebe que sea coherente con la restricción de presupuesto de su drivers.md.
Resultado:
        produccion = deploymentEnvironment "Producción" {

            # Costo mensual (R-03, US$ 20-30): droplet US$ 12 + respaldos diarios US$ 3,60 + volumen US$ 10 = US$ 25,60.
            # No se usa Docker: el entorno de ejecución son procesos de Python administrados por systemd.

            celular = deploymentNode "Celular del ciudadano o del brigadista" "Celular de gama baja con red móvil intermitente (R-05)." "Android" {
                navegador = deploymentNode "Navegador web" "Ejecuta la PWA y guarda la cola local en IndexedDB." "Chrome para Android" {
                    pwa = containerInstance sismo.pwa
                }
            }

            computadora = deploymentNode "Computadora del coordinador" "Equipo de oficina de Defensa Civil." "Windows o Linux" {
                navegador = deploymentNode "Navegador web" "Ejecuta el panel del coordinador de la PWA." "Navegador moderno (Chrome, Edge o Firefox)" {
                    pwa = containerInstance sismo.pwa
                }
            }

            nube = deploymentNode "DigitalOcean" "Proveedor de nube. Región fuera de la zona sísmica de Arequipa." "Región Nueva York (NYC3)" {

                droplet = deploymentNode "Droplet Basic" "1 vCPU, 2 GiB de RAM, 50 GiB de SSD y 2 000 GiB de transferencia. US$ 12/mes más respaldos diarios (30 %): US$ 3,60/mes." "Ubuntu 24.04 LTS" {

                    proxy = infrastructureNode "Proxy inverso" "Termina TLS 1.2 o superior (QA-03), recibe las subidas lentas y limita las peticiones."

                    python = deploymentNode "Entorno de ejecución Python" "Dos servicios de systemd con un entorno virtual compartido, sin Docker." "Python 3.12 y systemd" {
                        api = containerInstance sismo.api
                        worker = containerInstance sismo.worker
                    }

                    postgres = deploymentNode "Servidor PostgreSQL" "Instalado en el mismo droplet; no es un servicio administrado (R-03)." "PostgreSQL 16" {
                        bd = containerInstance sismo.bd
                    }

                    volumen = deploymentNode "Volumen de bloques" "100 GiB para fotos, separado del disco del sistema. US$ 10/mes." "DigitalOcean Volumes, ext4" {
                        fotos = containerInstance sismo.fotos
                    }
                }
            }

            externo = deploymentNode "Proveedor de teselas" "Servicio externo de mapas, no desplegado por el equipo." "Internet" "Externo" {
                teselas = softwareSystemInstance teselas
            }

            celular.navegador.pwa -> nube.droplet.proxy "Envía reportes y consultas" "HTTPS/JSON"
            computadora.navegador.pwa -> nube.droplet.proxy "Envía consultas y asignaciones" "HTTPS/JSON"
            nube.droplet.proxy -> nube.droplet.python.api "Reenvía las peticiones" "HTTP/JSON local"
        }
## Worskpace Secuencia:
Prompt: secuencia-reporte.PUML
Tome el mismo flujo del diagrama de secuencia del Laboratorio 05.
Escriba una vista dynamic con 4 o más pasos entre contenedores o componentes; cada paso debe corresponder a una relación ya existente en el modelo.
Resultado:
        # Mismo flujo que docs/design/secuencia-reporte.puml (Lab 05): HU-01, reporte sin señal y sincronización.
        # Equivalencias: ServicioIngesta y AlmacenServidorReportes viven en el componente Reportes;
        # ServicioReportes, AlmacenLocalReportes y PuertoEnvioReportes viven dentro de la PWA.
        dynamic sismo.api "SincronizarReporte" "HU-01: enviar un reporte sin señal y sincronizarlo." {
            ciudadano -> sismo.pwa "Registra el reporte con foto y ubicación; sin señal queda en la cola local"
            sismo.pwa -> sismo.api.reportes "Al recuperar la señal, envía cada reporte pendiente con su UUID"
            sismo.api.reportes -> sismo.bd "Guarda el reporte solo si su UUID no existe (guardarSiNoExiste)"
            sismo.api.reportes -> sismo.fotos "Guarda la foto original"
            sismo.api.reportes -> sismo.api.compartido "Encola el procesamiento de la foto mediante ColaTrabajos"
            sismo.api.compartido -> sismo.bd "Inserta el trabajo en la misma transacción que el reporte"
            autolayout lr
        }
## Prompt IA 2:
Prompt: Actúa como revisor de diagramas de arquitectura. Evalúa estas vistas exportadas de un modelo C4
con la lista de revisión de c4model.com: generales, elementos y relaciones.
Responde en una tabla (vista, pregunta de la lista, cumple sí/no, evidencia, corrección sugerida).
No inventes problemas: si algo cumple, indícalo.
Resultado:

| Vista | Pregunta de la lista | Cumple (PUML / MMD) | Evidencia | Corrección sugerida |
|---|---|---|---|---|
| Todas | ¿Tiene título? | Sí / Sí | PUML, línea 2 de cada archivo (por ejemplo, "System Context View: SismoReporta AQP"); MMD, línea 4 (`subgraph diagram [...]`). | Ninguna. |
| Contexto, Contenedores, Componentes, Despliegue | ¿Se entiende el tipo de diagrama y su alcance? | Sí / Sí | Los títulos nombran el tipo y el alcance: "Container View: SismoReporta AQP", "Component View: SismoReporta AQP - API", "Deployment View: SismoReporta AQP - Producción". | Ninguna. |
| Dinámica | ¿Se entiende el tipo de diagrama y su alcance? | Sí / No | PUML, línea 2: incluye "HU-01: enviar un reporte sin señal y sincronizarlo". MMD, línea 4: solo dice "Dynamic View: SismoReporta AQP - API", sin indicar qué flujo muestra. | Agregar `title "HU-01: enviar un reporte sin señal y sincronizarlo"` a la vista dinámica; comprobé que el exportador Mermaid lo usa como título. |
| Todas | ¿Tiene leyenda? | Sí / No | PUML: `SHOW_LEGEND(true)` y la leyenda aparece al renderizar. MMD: ningún archivo define leyenda. | Usar las exportaciones PlantUML en el informe, o acompañar las de Mermaid con una leyenda aparte. |
| Todas | ¿Cada elemento tiene nombre? | Sí / Sí | Todas las cajas y nodos tienen nombre. | Ninguna. |
| Contexto, Contenedores, Componentes, Dinámica | ¿Cada elemento indica su tipo? | Sí / Sí | PUML: macros `Person`, `System`, `Container`, `ContainerDb`, `Component` y fronteras `[system]` / `[container]`. MMD: rótulos `[Person]`, `[Software System]`, `[Container: …]`, `[Component: …]`. | Ninguna. |
| Contexto, Contenedores, Componentes, Dinámica | ¿Cada elemento describe lo que hace? | Sí / Sí | Todos los elementos llevan `$descr` (PUML) o el texto de descripción (MMD). | Ninguna. |
| Despliegue | ¿Cada nodo indica tipo, descripción y tecnología? | Sí / No | PUML: cada `Deployment_Node` trae `$type` y `$descr` (líneas 19-53). MMD: los nodos son `subgraph` con solo el nombre (líneas 7, 10, 22, 31, 34, 39, 48, 55, 66), así que se pierden Android, Ubuntu 24.04 LTS, PostgreSQL 16 y los costos. | Usar la exportación PlantUML para la vista de despliegue. |
| Contexto | ¿Indica la tecnología, si corresponde? | Sí / Sí | No corresponde: personas y sistemas de software no llevan tecnología. | Ninguna. |
| Contenedores, Componentes, Dinámica | ¿Indica la tecnología, si corresponde? | Sí / Sí | Todos los contenedores y componentes la indican (Python, PostgreSQL, Sistema de archivos, JavaScript, CSS…). | Ninguna. |
| Despliegue | ¿Indica la tecnología, si corresponde? | No / No | El proxy inverso no tiene tecnología: PUML línea 35 (`$type=""`); MMD línea 37 (solo `[Infrastructure Node]`). | Elegir el proxy, registrarlo en un ADR e indicarlo en el nodo. |
| Contexto | ¿Se entienden los acrónimos? | Sí / Sí | Solo aparece "AQP", que es parte del nombre del producto. | Ninguna. |
| Contenedores, Componentes, Dinámica, Despliegue | ¿Se entienden los acrónimos? | No / No | Sin explicar: EXIF y SKIP LOCKED (Contenedores); UUID y ADR-004 (Componentes); UUID (Dinámica); NYC3, TLS, QA-03, R-03, R-05, GiB, vCPU y SSD (Despliegue). | Explicarlos en las descripciones o en una nota junto a los diagramas. |
| Contexto | ¿Se entienden colores y formas? | No / No | PUML línea 18: el servicio de teselas sale como `System` azul, igual que SismoReporta AQP, porque la etiqueta "Externo" no se exporta. MMD línea 10: sale gris, pero sin leyenda que lo explique. | Agregar en `views` la propiedad `"c4plantuml.tags" "true"`; comprobé que así el servicio sale gris y la leyenda muestra "Externo". |
| Contenedores | ¿Se entienden colores y formas? | No / No | El servicio de teselas sale azul como si fuera interno (PUML línea 21). La forma de navegador de la PWA se pierde en ambas exportaciones (PUML línea 27, MMD línea 25). En MMD las personas son rectángulos. | Misma propiedad `c4plantuml.tags`. La forma de navegador no se conserva en ningún formato: basta con que la descripción diga que corre en el navegador. |
| Componentes, Dinámica | ¿Se entienden colores y formas? | Sí / No | PUML: la leyenda distingue contenedor y componente, y las bases de datos son cilindros. MMD: dos tonos de azul sin leyenda. | Ninguna en PUML; leyenda aparte para MMD. |
| Despliegue | ¿Se entienden colores, bordes y tamaños? | No / No | PUML línea 54: el servicio de teselas sale azul como interno. MMD línea 67: el nodo "Proveedor de teselas" tiene texto blanco sobre fondo blanco y su nombre no se ve al renderizar; además, los nombres de nodos salen cortados ("Droplet B", "Servidor Postgre", "Volumen de bloqu"). | PUML: propiedad `c4plantuml.tags`. MMD: quitar la etiqueta "Externo" del nodo de despliegue (`workspace.dsl`, línea 124) o darle un estilo con texto oscuro. |
| Todas | ¿Cada flecha tiene una etiqueta que describe su intención? | Sí / Sí | Todas las relaciones tienen texto (4, 9, 18, 6 y 9 por vista). | Ninguna. |
| Componentes | ¿Se puede leer cada etiqueta en su flecha? | Sí / Sí | Al renderizar, 18 flechas se cruzan y las dos etiquetas "Usa Zona" cuestan de asociar con su flecha, aunque todas son legibles. | Opcional: excluir de esta vista las dependencias hacia Compartido o mostrarlas en una vista aparte. |
| Dinámica | ¿Se puede leer cada etiqueta en su flecha? | Sí / Sí | En el PNG de PlantUML, el borde del contenedor API cruza la etiqueta del paso 3; aun así se lee. | Ninguna obligatoria. |
| Todas | ¿La etiqueta coincide con la dirección de la flecha? | Sí / Sí | Cada etiqueta se lee desde el origen: "Reenvía las peticiones" (proxy → API), "Obtiene el mapa base" (SismoReporta AQP → teselas), "Inserta el trabajo…" (Compartido → base de datos). | Ninguna. |
| Todas | ¿Se indica la tecnología o el protocolo? | Sí / Sí | Todas las `Rel` tienen `$techn` (PUML) y todas las flechas muestran `[…]` (MMD): HTTPS, HTTPS/JSON, HTTPS/PNG, HTTP/JSON local, SQL/TCP, E/S de archivos y llamada en proceso. | Ninguna. |

| Hallazgo | Tipo | Por qué no se sostiene | Veredicto corregido |
|---|---|---|---|
| Dinámica en Mermaid: "No" en tipo y alcance | Falso positivo | El título dice "Dynamic View: SismoReporta AQP - API", así que el tipo (dinámica) y el alcance (el contenedor API) se entienden. Que no nombre el flujo HU-01 es una mejora deseable, pero no es lo que pregunta la lista. | Sí / Sí. Agregar el `title` queda como mejora opcional. |
| Contenedores: "la forma de navegador de la PWA se pierde" | Falso positivo | La lista pregunta si las formas se entienden, no si se conserva una forma concreta. La PWA sale como contenedor y la leyenda de PlantUML lo explica. Las personas en Mermaid son rectángulos, pero cada una dice `[Person]`. | No es un problema. La fila sigue en "No" solo por el color del servicio de teselas. |
| Despliegue en Mermaid: nombres de nodos cortados ("Droplet B", "Servidor Postgre") | Falso positivo | Lo vi en mi propio renderizado con mermaid-cli en un navegador sin interfaz. En el archivo los nombres están completos (líneas 34, 48 y 55), así que probablemente es un problema de fuentes de mi entorno. No lo comprobé en GitHub ni en Mermaid Live. | Se descarta. El texto blanco sobre blanco de "Proveedor de teselas" sí es real (línea 67: `color:#ffffff`). |
| Acrónimos sin explicar en Contenedores y Dinámica | Exagerado | SKIP LOCKED no es un acrónimo, es una cláusula de SQL. UUID, TLS, SSD, GiB y vCPU son términos estándar para un público técnico. EXIF es dudoso, porque depende del público. | Contenedores y Dinámica pasan a "Sí". Siguen en "No" Componentes (ADR-004) y Despliegue (NYC3, QA-03, R-03 y R-05). |
| Contexto en Mermaid: "No" en colores porque el gris no tiene leyenda | Exagerado | Es el mismo problema de la fila "¿Tiene leyenda?", así que lo conté dos veces. | Sí en colores; la falta de leyenda queda solo en su propia fila. |

## Prompt IA 3:
Prompt: Explica el  diagrama de contexto al publico general, que no es
técnico, en máximo 120 palabras: qué hace el sistema, quién lo usa y de qué servicios externos depende.
Evita la jerga técnica.
Resultado:SismoReporta AQP es una aplicación que ayuda a Defensa Civil a organizar la respuesta después de un sismo en Arequipa. La usan tres tipos de personas. Los ciudadanos envían desde su celular una foto y la ubicación de los daños que ven; si no hay señal, el reporte se guarda y se envía solo cuando vuelve la conexión. Los coordinadores ven todos los reportes en un mapa, saben qué zonas necesitan ayuda primero y envían brigadas. Los brigadistas reciben la zona que deben atender y avisan cuando van en camino y cuando terminan. El sistema depende de un único servicio externo: un proveedor de mapas que dibuja las calles sobre las que se muestran los daños.