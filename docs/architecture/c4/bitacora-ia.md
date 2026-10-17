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