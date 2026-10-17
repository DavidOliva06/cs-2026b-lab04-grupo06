# Inventario de elementos C4 - SismoReporta AQP

| Elemento | Tipo C4 | Origen |
|---|---|---|
| Ciudadano, brigadista, coordinador | Persona | drivers.md (Lab 04) |
| SismoReporta AQP | Sistema de software | Caso (README.md) |
| Servicio de teselas de mapa (OpenStreetMap o proveedor) | Sistema externo | Diagrama de arquitectura (Lab 04) |
| Aplicación web progresiva (PWA), con la cola local en IndexedDB | Contenedor | ADR-003 (Lab 04) |
| Proxy inverso | Contenedor | Diagrama de arquitectura (Lab 04) |
| API (monolito modular en Python) | Contenedor | ADR-001 (Lab 04) |
| Worker en segundo plano | Contenedor | ADR-001 (Lab 04) |
| Base de datos PostgreSQL, con la cola de trabajos | Contenedor | ADR-001 y ADR-002 (Lab 04) |
| Almacenamiento de fotos en disco | Contenedor | Diagrama de arquitectura (Lab 04) |
| Módulos Reportes, Mapa, Priorización, Brigadas y Compartido | Componente (de la API) | ADR-001 (Lab 04) y paquetes.puml (Lab 05) |
| API HTTP, Autenticación y roles | Componente (de la API) | Diagrama de arquitectura (Lab 04) |
| Formulario de reporte, Vista de brigadista, Panel del coordinador, Sincronizador | Componente (de la PWA) | Diagrama de arquitectura (Lab 04) y secuencia-reporte.puml (Lab 05) |
| Puertos AlmacenServidorReportes, ConsultaReportes, ConsultaZonasAsignadas, ColaTrabajos | Interfaz entre componentes | paquetes.puml y ADR-004 (Lab 05) |
| Clases Reporte, Ciudadano, Consentimiento, Foto, Ubicacion, EstadoReporte, ServicioReportes, ServicioIngesta | Código | clases.puml y reportes.py (Lab 05) |
| Flujo "enviar un reporte sin señal y sincronizarlo" | Vista dinámica | secuencia-reporte.puml (Lab 05) |
| Proceso "priorización y asignación de brigadas" | Vista dinámica | actividades-brigada.puml (Lab 05) |
| Servidor único en la nube y celular del usuario | Vista de despliegue | ADR-001 y diagrama de arquitectura (Lab 04) |

## Criterios de clasificación

- **IndexedDB:** forma parte del contenedor PWA, porque vive en el navegador y no se despliega por separado.
- **Cola de trabajos:** no es un contenedor propio, sino una tabla de PostgreSQL (ADR-002).
- **API y worker:** son contenedores distintos aunque compartan código, porque se ejecutan como procesos separados (ADR-001).
- **Proxy inverso:** es un contenedor de infraestructura que solo se configura, no se programa.
- **Diagrama de arquitectura:** es el diagrama Mermaid de `docs/architecture/diagramas/`, también embebido en el README.