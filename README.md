# <Nombre del caso> — Laboratorio 04: Fundamentos de arquitectura de software
Construcción de Software · EPIS-UNSA · 2026-B · Grupo 06
## Integrantes
| Nombre | Rol en el laboratorio (p. ej., redactor de ADR, diagramador, verificador de IA) |
|Oliva Valdivia David Alexander|Desarrollador,verificador de IA |
## Caso
SismoReporta AQP es una plataforma de reporte ciudadano de daños tras un sismo en Arequipa, pensada para apoyar a Defensa Civil.
El ciudadano envía reportes con foto y geolocalización desde una PWA que funciona sin señal y los reenvía al recuperarla.
El coordinador ve los daños en un mapa, recibe una priorización automática de zonas y asigna brigadas, y el brigadista actualiza el estado de su asignación.
El sistema lo construye un solo desarrollador en un mes, sobre un único servidor de bajo costo, y debe cumplir la Ley 29733 de protección de datos personales.
**Atributo de calidad crítico:** disponibilidad ante picos. Tras un sismo llegan unos 20 000 reportes en la primera hora con la red móvil congestionada, y cada reporte perdido retrasa la ayuda (QA-01).
## Arquitectura elegida
```mermaid
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
```
## Decisiones arquitectónicas
- [ADR-001: Estilo arquitectónico](docs/architecture/adr/001-estilo-arquitectonico.md)
- [ADR-002: Cola de Trabajos en PostgreSQL](docs/architecture/adr/002-cola-de-traajos-en-postgresql.md)
- [ADR-003: ...](docs/architecture/adr/003-pwa-offline-first.md)
## Reflexión sobre el uso de la IA (5–8 líneas)
La IA seleccionada en este caso Claude Opus 5.5 y Claude Sonnet 5.5, se encargaron de la creacion de los diagramas, el analisis de los drivers iniciales, y la construccion de la matriz de decision, ademas ayudaron a automatizar procesos como la conversion de texto a markdown.
En definitiva el trabajo se agilizo utilizandolas para los procesos que no se tiene tanto conocimiento como el uso de mermaid y de puml.