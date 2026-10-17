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

    model {
        ciudadano = person "Ciudadano" "Reporta daños con foto y ubicación tras un sismo."
        brigadista = person "Brigadista" "Atiende las zonas asignadas y actualiza su estado."
        coordinador = person "Coordinador" "Revisa el mapa de daños, prioriza zonas y asigna brigadas."

        sismo = softwareSystem "SismoReporta AQP" "Recibe reportes de daños, prioriza zonas y asigna brigadas." {

            pwa = container "Aplicación web progresiva" "Interfaz de los tres roles. Guarda los reportes sin señal en una cola local y los reenvía al recuperar la conexión." "JavaScript, CSS, Service Worker e IndexedDB" "Web Browser"

            api = container "API" "Monolito modular: ingesta idempotente, mapa, priorización y brigadas." "Python" {
                # Un componente por paquete de docs/design/paquetes.puml (Lab 05).
                compartido = component "Compartido" "Tipos comunes Ubicacion y Zona, y el puerto ColaTrabajos." "Python"
                reportes = component "Reportes" "Ingesta idempotente por UUID (ServicioIngesta) y puertos AlmacenServidorReportes y ConsultaReportes." "Python"
                priorizacion = component "Priorización" "Calcula ZonaPriorizada y define el puerto ConsultaZonasAsignadas (ADR-004)." "Python"
                brigadas = component "Brigadas" "Brigada, Asignacion y ServicioAsignacion; implementa ConsultaZonasAsignadas." "Python"
                mapa = component "Mapa" "ServicioMapa: arma el mapa de daños agrupado por zonas." "Python"
            }

            worker = container "Worker" "Procesa fotos y recalcula la priorización de forma periódica." "Python"

            bd = container "Base de datos" "Reportes, usuarios, consentimientos, zonas, asignaciones y la tabla de trabajos." "PostgreSQL" "Database"

            fotos = container "Almacenamiento de fotos" "Fotos de los reportes comprimidas y sin metadatos EXIF, en un volumen separado." "Sistema de archivos" "Database"
        }

        teselas = softwareSystem "Servicio de teselas de mapa" "Mapa base: OpenStreetMap o un proveedor de teselas." "Externo"

        # Personas
        ciudadano -> sismo.pwa "Envía reportes de daños con foto y ubicación" "HTTPS"
        brigadista -> sismo.pwa "Consulta su asignación y marca su estado" "HTTPS"
        coordinador -> sismo.pwa "Revisa el mapa y asigna brigadas" "HTTPS"

        # Contenedores
        sismo.pwa -> sismo.api "Envía reportes y consultas, a través del proxy inverso" "HTTPS/JSON"
        sismo.pwa -> teselas "Obtiene el mapa base" "HTTPS/PNG"
        sismo.api -> sismo.bd "Lee y escribe datos" "SQL/TCP"
        sismo.api -> sismo.fotos "Guarda la foto original" "E/S de archivos"
        sismo.worker -> sismo.bd "Toma trabajos con SKIP LOCKED y guarda las zonas priorizadas" "SQL/TCP"
        sismo.worker -> sismo.fotos "Redimensiona las fotos y elimina los metadatos EXIF" "E/S de archivos"

        # Componentes de la API: entradas desde la PWA
        sismo.pwa -> sismo.api.reportes "Envía reportes de daños" "HTTPS/JSON"
        sismo.pwa -> sismo.api.mapa "Pide el mapa de daños" "HTTPS/JSON"
        sismo.pwa -> sismo.api.brigadas "Consulta y actualiza asignaciones" "HTTPS/JSON"

        # Dependencias entre componentes (paquetes.puml, líneas 40-54). Sin ciclos:
        # mapa y brigadas -> priorización -> reportes -> compartido.
        sismo.api.mapa -> sismo.api.priorizacion "Usa ZonaPriorizada" "Llamada en proceso"
        sismo.api.mapa -> sismo.api.reportes "Usa ConsultaReportes" "Llamada en proceso"
        sismo.api.mapa -> sismo.api.compartido "Usa Zona" "Llamada en proceso"

        sismo.api.brigadas -> sismo.api.priorizacion "Usa ZonaPriorizada e implementa ConsultaZonasAsignadas (ADR-004)" "Llamada en proceso"
        sismo.api.brigadas -> sismo.api.reportes "Usa Reporte: verificar, rechazar, marcarAtendido" "Llamada en proceso"
        sismo.api.brigadas -> sismo.api.compartido "Usa Zona" "Llamada en proceso"

        sismo.api.priorizacion -> sismo.api.reportes "Usa ConsultaReportes" "Llamada en proceso"
        sismo.api.priorizacion -> sismo.api.compartido "Usa Zona y ColaTrabajos" "Llamada en proceso"

        sismo.api.reportes -> sismo.api.compartido "Usa Ubicacion y ColaTrabajos" "Llamada en proceso"

        # Dependencias hacia otros contenedores
        sismo.api.reportes -> sismo.bd "Guarda el reporte y su trabajo en una transacción" "SQL/TCP"
        sismo.api.reportes -> sismo.fotos "Guarda la foto original" "E/S de archivos"
        sismo.api.priorizacion -> sismo.bd "Lee reportes por zona y las zonas priorizadas" "SQL/TCP"
        sismo.api.brigadas -> sismo.bd "Lee y escribe brigadas y asignaciones" "SQL/TCP"
        sismo.api.mapa -> sismo.bd "Lee reportes agrupados por zona" "SQL/TCP"
        sismo.api.compartido -> sismo.bd "Inserta trabajos en la tabla de trabajos (ColaTrabajos)" "SQL/TCP"

        produccion = deploymentEnvironment "Producción" {

            dispositivo = deploymentNode "Dispositivo del usuario" "Celular de gama baja o computadora, con red móvil intermitente." "Navegador web" {
                pwa = containerInstance sismo.pwa
            }

            # Un solo servidor (ADR-001, R-03). Los nodos son el servidor y sus procesos, no contenedores Docker.
            servidor = deploymentNode "Servidor único en la nube" "Servidor de bajo costo, US$ 20-30 al mes." "Servidor virtual" {
                proxy = infrastructureNode "Proxy inverso" "Termina TLS, recibe las subidas lentas y limita las peticiones."
                api = containerInstance sismo.api
                worker = containerInstance sismo.worker
                bd = containerInstance sismo.bd
                fotos = containerInstance sismo.fotos
            }

            externo = deploymentNode "Proveedor de teselas" "Servicio externo de mapas, no desplegado por el equipo." "Internet" "Externo" {
                teselas = softwareSystemInstance teselas
            }

            dispositivo.pwa -> servidor.proxy "Envía reportes y consultas" "HTTPS/JSON"
            servidor.proxy -> servidor.api "Reenvía las peticiones" "HTTP/JSON local"
        }
    }

    views {
        systemContext sismo "Contexto" "Diagrama de contexto de SismoReporta AQP." {
            include *
            autolayout lr
        }

        container sismo "Contenedores" "Diagrama de contenedores de SismoReporta AQP." {
            include *
            autolayout lr
        }

        component sismo.api "Componentes" "Componentes del contenedor API, uno por paquete de paquetes.puml." {
            include *
            autolayout lr
        }

        deployment sismo "Producción" "Despliegue" "Despliegue en el entorno Producción." {
            include *
            exclude "produccion.dispositivo.pwa -> produccion.servidor.api"
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
        }
    }
}