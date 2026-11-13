workspace "SismoReporta AQP" "Reporte ciudadano de daños tras un sismo, en apoyo a Defensa Civil" {

    !identifiers hierarchical

    # Supuestos:
    # - Tecnologías de los contenedores: las del ADR-001 (Python, JavaScript, CSS, PostgreSQL),
    #   más Service Worker e IndexedDB, que son APIs del navegador que exige la PWA (ADR-003).
    # - Contenedor C4 = unidad que se ejecuta o almacena datos por separado (proceso,
    #   aplicación en el navegador, base de datos, sistema de archivos). No se usa Docker:
    #   los procesos corren directamente en el servidor.
    # - Contenedores del ADR-001: API (monolito modular), Worker y Base de datos PostgreSQL.
    #   La PWA viene del ADR-003 y el almacenamiento de fotos, de las fotos que procesa el worker (ADR-001).
    # - El proxy inverso es infraestructura: solo se configura, no se programa. Va como
    #   nodo de infraestructura en la vista de despliegue, no como contenedor.
    # - La cola local (IndexedDB) es parte de la PWA y la cola de trabajos es una tabla
    #   de PostgreSQL (ADR-002), así que ninguna es un contenedor propio ni lleva la forma "Queue".
    #
    # Lab 08 (ADR-006 a ADR-008):
    # - [QA-xx] es el escenario de docs/architecture/utilidad/escenarios.md que atiende cada elemento.
    #   D1 extiende QA-01, R2 extiende QA-02 y S1 extiende QA-03 de drivers.md.
    # - No hay contenedores nuevos: las tres decisiones se implementan dentro de los existentes.
    #   Hay un componente nuevo (Dispositivos, ADR-008) y dos tecnologías nuevas: gzip en el proxy
    #   (ADR-007) y la firma HMAC-SHA256 del módulo hmac de Python (ADR-008). Ninguna sale de R-02.
    # - Las personas son fuentes de los estímulos; el brigadista no es fuente de ningún escenario del árbol.

    model {
        ciudadano = person "Ciudadano" "Reporta daños con foto y ubicación tras un sismo. Fuente de [QA-D1] y [QA-S1]."
        brigadista = person "Brigadista" "Atiende las zonas asignadas y actualiza su estado. No es fuente de ningún escenario del árbol de utilidad."
        coordinador = person "Coordinador" "Revisa el mapa de daños, prioriza zonas y asigna brigadas. Fuente de [QA-R2]; revisa los dispositivos sospechosos [QA-S2]."

        sismo = softwareSystem "SismoReporta AQP" "Recibe reportes de daños, prioriza zonas y asigna brigadas. [QA-D1] [QA-R2] [QA-S1] [QA-S2]" {

            pwa = container "Aplicación web progresiva" "Interfaz de los tres roles. Guarda los reportes sin señal en una cola local y los reenvía al recuperar la conexión; en modo pico deja la foto para después (ADR-006) [QA-D1]. Envía el identificador de dispositivo firmado (ADR-008) [QA-S2]. El panel dibuja un marcador por zona (ADR-007) [QA-R2]." "JavaScript, CSS, Service Worker e IndexedDB" "Web Browser"

            api = container "API" "Monolito modular: ingesta idempotente con modo pico [QA-D1], mapa agregado por zona [QA-R2], control de roles [QA-S1], límite por dispositivo [QA-S2], priorización y brigadas." "Python" {
                # Un componente por paquete de docs/design/paquetes.puml (Lab 05), más Dispositivos (ADR-008).
                compartido = component "Compartido" "Tipos comunes Ubicacion y Zona, y el puerto ColaTrabajos: el reporte y su trabajo se guardan en una transacción [QA-D1]." "Python"
                reportes = component "Reportes" "Ingesta idempotente por identificador único (UUID) en ServicioIngesta, y puertos AlmacenServidorReportes y ConsultaReportes [QA-D1]. En modo pico acepta solo los datos y difiere la foto (ADR-006) [QA-D1]; responde 429 al reporte n.º 11 de un dispositivo en 10 min (ADR-008) [QA-S2]." "Python"
                priorizacion = component "Priorización" "Calcula ZonaPriorizada y define el puerto ConsultaZonasAsignadas (decisión de arquitectura ADR-004). Cuenta un voto por dispositivo y zona y excluye a los sospechosos (ADR-008) [QA-S2]." "Python"
                brigadas = component "Brigadas" "Brigada, Asignacion y ServicioAsignacion; implementa ConsultaZonasAsignadas. No atiende ningún escenario del árbol de utilidad." "Python"
                mapa = component "Mapa" "ServicioMapa: GET /api/mapa/zonas devuelve un registro por zona y GET /api/mapa/zonas/{zona}/reportes el detalle (ADR-007) [QA-R2]." "Python"
                dispositivos = component "Dispositivos" "Emite identificadores de dispositivo firmados, cuenta los reportes de cada dispositivo en 10 min, marca a los sospechosos y publica DispositivoSospechoso al operador con el Observer de ADR-005 (ADR-008) [QA-S2]." "Python, HMAC-SHA256"
            }

            worker = container "Worker" "Procesa fotos y recalcula la priorización de forma periódica. En modo pico solo recalcula la priorización y deja las fotos para después (ADR-006) [QA-D1]." "Python"

            bd = container "Base de datos" "Reportes, usuarios, consentimientos, zonas, asignaciones y la tabla de trabajos [QA-D1]. Índices por zona y región para el mapa [QA-R2]; dispositivo_id en cada reporte y tabla de dispositivos [QA-S2]." "PostgreSQL" "Database"

            fotos = container "Almacenamiento de fotos" "Fotos de los reportes comprimidas y sin metadatos EXIF (fecha, cámara y coordenadas GPS), en un volumen separado [QA-D3]. En modo pico deja de crecer (ADR-006) [QA-D1]." "Sistema de archivos" "Database"
        }

        teselas = softwareSystem "Servicio de teselas de mapa" "Mapa base: OpenStreetMap o un proveedor de teselas. Externo: queda fuera de la medida de [QA-R2]." "Externo"

        # Personas
        ciudadano -> sismo.pwa "Envía reportes de daños con foto y ubicación" "HTTPS"
        brigadista -> sismo.pwa "Consulta su asignación y marca su estado" "HTTPS"
        coordinador -> sismo.pwa "Revisa el mapa y asigna brigadas" "HTTPS"

        # Contenedores
        sismo.pwa -> sismo.api "Envía reportes y consultas, a través del proxy inverso" "HTTPS/JSON"
        sismo.pwa -> teselas "Obtiene el mapa base" "HTTPS/PNG"
        sismo.api -> sismo.bd "Lee y escribe datos" "SQL/TCP"
        sismo.api -> sismo.fotos "Guarda la foto original" "E/S de archivos"
        sismo.worker -> sismo.bd "Toma trabajos con SKIP LOCKED (sin que dos procesos tomen el mismo) y guarda las zonas priorizadas" "SQL/TCP"
        sismo.worker -> sismo.fotos "Redimensiona las fotos y elimina los metadatos EXIF (fecha, cámara y GPS)" "E/S de archivos"

        # Componentes de la API: entradas desde la PWA
        sismo.pwa -> sismo.api.reportes "Envía reportes de daños" "HTTPS/JSON"
        sismo.pwa -> sismo.api.mapa "Pide el mapa de daños" "HTTPS/JSON"
        sismo.pwa -> sismo.api.brigadas "Consulta y actualiza asignaciones" "HTTPS/JSON"
        sismo.pwa -> sismo.api.dispositivos "Pide su identificador firmado; el panel lista los dispositivos sospechosos" "HTTPS/JSON"

        # Dependencias entre componentes (paquetes.puml, líneas 40-54). Sin ciclos:
        # mapa y brigadas -> priorización -> reportes -> compartido.
        sismo.api.mapa -> sismo.api.priorizacion "Usa ZonaPriorizada" "Llamada en proceso"
        sismo.api.mapa -> sismo.api.reportes "Usa ConsultaReportes" "Llamada en proceso"
        sismo.api.mapa -> sismo.api.compartido "Usa Zona" "Llamada en proceso"

        sismo.api.brigadas -> sismo.api.priorizacion "Usa ZonaPriorizada e implementa ConsultaZonasAsignadas (decisión ADR-004)" "Llamada en proceso"
        sismo.api.brigadas -> sismo.api.reportes "Usa Reporte: verificar, rechazar, marcarAtendido" "Llamada en proceso"
        sismo.api.brigadas -> sismo.api.compartido "Usa Zona" "Llamada en proceso"

        sismo.api.priorizacion -> sismo.api.reportes "Usa ConsultaReportes" "Llamada en proceso"
        sismo.api.priorizacion -> sismo.api.compartido "Usa Zona y ColaTrabajos" "Llamada en proceso"

        sismo.api.reportes -> sismo.api.compartido "Usa Ubicacion y ColaTrabajos" "Llamada en proceso"

        # ADR-008: reportes y priorización usan Dispositivos; Dispositivos no depende de ellos.
        sismo.api.reportes -> sismo.api.dispositivos "Verifica la firma y el límite por dispositivo" "Llamada en proceso"
        sismo.api.priorizacion -> sismo.api.dispositivos "Excluye los dispositivos sospechosos" "Llamada en proceso"

        # Dependencias hacia otros contenedores
        sismo.api.reportes -> sismo.bd "Guarda el reporte y su trabajo en una transacción" "SQL/TCP"
        sismo.api.reportes -> sismo.fotos "Guarda la foto original" "E/S de archivos"
        sismo.api.priorizacion -> sismo.bd "Lee reportes por zona y las zonas priorizadas" "SQL/TCP"
        sismo.api.brigadas -> sismo.bd "Lee y escribe brigadas y asignaciones" "SQL/TCP"
        sismo.api.mapa -> sismo.bd "Lee reportes agrupados por zona con GROUP BY" "SQL/TCP"
        sismo.api.dispositivos -> sismo.bd "Guarda los dispositivos y cuenta sus reportes de los últimos 10 min" "SQL/TCP"
        sismo.api.compartido -> sismo.bd "Inserta trabajos en la tabla de trabajos (ColaTrabajos)" "SQL/TCP"

        produccion = deploymentEnvironment "Producción" {

            # Costo mensual (R-03, US$ 20-30): droplet US$ 12 + respaldos diarios US$ 3,60 + volumen US$ 10 = US$ 25,60.
            # No se usa Docker: el entorno de ejecución son procesos de Python administrados por systemd.

            celular = deploymentNode "Celular del ciudadano o del brigadista" "Celular de gama baja con red móvil intermitente (restricción R-05 de drivers.md)." "Android" {
                navegador = deploymentNode "Navegador web" "Ejecuta la PWA y guarda la cola local en IndexedDB." "Chrome para Android" {
                    pwa = containerInstance sismo.pwa
                }
            }

            computadora = deploymentNode "Computadora del coordinador" "Equipo de oficina de Defensa Civil." "Windows o Linux" {
                navegador = deploymentNode "Navegador web" "Ejecuta el panel del coordinador de la PWA." "Navegador moderno (Chrome, Edge o Firefox)" {
                    pwa = containerInstance sismo.pwa
                }
            }

            nube = deploymentNode "DigitalOcean" "Proveedor de nube. Región fuera de la zona sísmica de Arequipa." "Región Nueva York 3 (NYC3)" {

                droplet = deploymentNode "Droplet Basic" "1 vCPU, 2 GiB de RAM, 50 GiB de SSD y 2 000 GiB de transferencia. US$ 12/mes más respaldos diarios (30 %): US$ 3,60/mes." "Ubuntu 24.04 LTS" {

                    proxy = infrastructureNode "Proxy inverso" "Termina TLS 1.2 o superior [QA-S1], recibe las subidas lentas, comprime las respuestas JSON (ADR-007) [QA-R2] y expone la ocupación de conexiones que activa el modo pico (ADR-006) [QA-D1]." "TLS 1.2+ y gzip"

                    python = deploymentNode "Entorno de ejecución Python" "Dos servicios de systemd con un entorno virtual compartido, sin Docker." "Python 3.12 y systemd" {
                        api = containerInstance sismo.api
                        worker = containerInstance sismo.worker
                    }

                    postgres = deploymentNode "Servidor PostgreSQL" "Instalado en el mismo droplet; no es un servicio administrado (restricción de presupuesto R-03 de drivers.md)." "PostgreSQL 16" {
                        bd = containerInstance sismo.bd
                    }

                    volumen = deploymentNode "Volumen de bloques" "100 GiB para fotos, separado del disco del sistema. US$ 10/mes." "DigitalOcean Volumes, ext4" {
                        fotos = containerInstance sismo.fotos
                    }
                }
            }

            externo = deploymentNode "Proveedor de teselas" "Servicio externo de mapas, no desplegado por el equipo." "Internet" "Nodo externo" {
                teselas = softwareSystemInstance teselas
            }

            celular.navegador.pwa -> nube.droplet.proxy "Envía reportes y consultas" "HTTPS/JSON"
            computadora.navegador.pwa -> nube.droplet.proxy "Envía consultas y asignaciones" "HTTPS/JSON"
            nube.droplet.proxy -> nube.droplet.python.api "Reenvía las peticiones" "HTTP/JSON local"
        }
    }

    views {
        # Exporta las etiquetas a C4-PlantUML: sin esto, "Externo" se pierde y el servicio
        # de teselas sale azul como un sistema propio (pregunta 7 del informe).
        properties {
            "c4plantuml.tags" "true"
        }

        systemContext sismo "Contexto" "Diagrama de contexto de SismoReporta AQP." {
            title "SismoReporta AQP - Diagrama de contexto (nivel 1)"
            include *
            autolayout lr
        }

        container sismo "Contenedores" "Diagrama de contenedores de SismoReporta AQP." {
            title "SismoReporta AQP - Diagrama de contenedores (nivel 2)"
            include *
            autolayout lr
        }

        component sismo.api "Componentes" "Componentes del contenedor API, uno por paquete de paquetes.puml." {
            title "SismoReporta AQP - Componentes de la API (nivel 3)"
            include *
            autolayout lr
        }

        dynamic sismo.api "SincronizarReporte" "HU-01: enviar un reporte sin señal y sincronizarlo." {
            title "SismoReporta AQP - Vista dinámica: sincronizar un reporte (HU-01)"
            ciudadano -> sismo.pwa "Registra el reporte con foto y ubicación; sin señal queda en la cola local"
            sismo.pwa -> sismo.api.reportes "Al recuperar la señal, envía cada reporte pendiente con su identificador único (UUID)"
            sismo.api.reportes -> sismo.bd "Guarda el reporte solo si su UUID no existe (guardarSiNoExiste)"
            sismo.api.reportes -> sismo.fotos "Guarda la foto original"
            sismo.api.reportes -> sismo.api.compartido "Encola el procesamiento de la foto mediante ColaTrabajos"
            sismo.api.compartido -> sismo.bd "Inserta el trabajo en la misma transacción que el reporte"
            autolayout lr
        }

        deployment sismo "Producción" "Despliegue" "Despliegue en el entorno Producción." {
            title "SismoReporta AQP - Despliegue en Producción (US$ 25,60 al mes)"
            include *
            exclude "produccion.celular.navegador.pwa -> produccion.nube.droplet.python.api"
            exclude "produccion.computadora.navegador.pwa -> produccion.nube.droplet.python.api"
            autolayout lr
        }

        styles {
            element "Person" {
                shape Person
                background #08427b
                color #ffffff
            }
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "Container" {
                background #438dd5
                color #ffffff
            }
            element "Component" {
                background #85bbf0
                color #000000
            }
            element "Infrastructure Node" {
                background #ffffff
                color #000000
            }
            element "Database" {
                shape Cylinder
            }
            element "Web Browser" {
                shape WebBrowser
            }
            element "Externo" {
                background #999999
                color #ffffff
            }
            # Nodo de despliegue externo: texto oscuro, porque Mermaid dibuja los nodos con
            # fondo blanco y con "Externo" el nombre quedaba blanco sobre blanco.
            element "Nodo externo" {
                background #eeeeee
                color #444444
                stroke #6b6b6b
                border dashed
            }
        }
    }
}