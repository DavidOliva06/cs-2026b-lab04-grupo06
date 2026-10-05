# ADR-002: Cola de trabajos en PostgreSQL para el procesamiento asíncrono
- Estado: Aceptado
- Fecha: 2026-10-02
- Decisores: Oliva Valdivia David Alexander
## Contexto
El ADR-001 difiere el procesamiento de fotos y el recálculo de la priorización (RF-03) a un worker, por lo que se necesita un mecanismo para encolar trabajos. Ningún reporte aceptado puede quedar sin procesar ni duplicarse (QA-01), y la priorización debe actualizarse en ≤ 60 s (QA-02).

El equipo no usará tecnologías fuera de Python, JavaScript, CSS y PostgreSQL (R-02), y todo debe ejecutarse en un solo servidor de bajo costo (R-03).
## Alternativas consideradas
1. Tabla de trabajos en PostgreSQL, consumida con `SELECT ... FOR UPDATE SKIP LOCKED`.
2. Broker dedicado (por ejemplo, Redis o RabbitMQ): ofrece mayor rendimiento, pero añade una tecnología fuera de R-02 y consume RAM del servidor único (R-03).
3. Tarea periódica sin cola (cron): basta para recalcular la priorización, pero no lleva el estado ni los reintentos de cada foto.
## Decisión
Usaremos una tabla de trabajos en la misma base de datos PostgreSQL. La ingesta insertará el reporte y su trabajo en una sola transacción, y el worker tomará los trabajos pendientes con `SKIP LOCKED`.

Cada trabajo registrará su estado y su número de intentos, y los trabajos fallidos se reintentarán hasta un máximo definido.
## Consecuencias
- Positivas:
  - El reporte y su trabajo se guardan de forma atómica, así que no puede existir uno sin el otro (QA-01).
  - No se añade ninguna tecnología ni proceso nuevo que aprender, desplegar o monitorear (R-02, R-03).
  - El estado de la cola se inspecciona con consultas SQL, lo que simplifica el diagnóstico.
- Negativas / riesgos:
  - La cola compite con las consultas del mapa por los recursos de la misma base de datos (QA-02).
  - El worker consulta la tabla por sondeo, lo que añade segundos de latencia al procesamiento.
  - Las filas completadas deben limpiarse de forma periódica para que la tabla no crezca y degrade las consultas.
  - El rendimiento es menor que el de un broker; se asume suficiente para unos 6 reportes por segundo, pero debe confirmarse con una prueba de carga.