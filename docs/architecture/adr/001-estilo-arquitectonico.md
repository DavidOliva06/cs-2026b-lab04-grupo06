# ADR-001: Monolito modular con ingesta asíncrona como estilo arquitectónico
- Estado: Aceptado
- Fecha: 2026-10-01
- Decisores: Oliva Valdivia David Alexander
## Contexto
El sistema debe recibir reportes de daños con foto y geolocalización (RF-01) y soportar 20 000 reportes en 60 minutos con la red congestionada, guardando al menos el 99,5 % sin duplicados (QA-01). Al mismo tiempo, el coordinador necesita el mapa en p95 ≤ 3 s y la priorización actualizada en ≤ 60 s (QA-02, RF-02, RF-03).

Las restricciones acotan las opciones: MVP en 1 mes (R-01), un solo desarrollador con Python, JavaScript, CSS y PostgreSQL (R-02) y un único servidor de US$ 20–30 al mes (R-03).
## Alternativas consideradas
1. Monolito en capas síncrono: cada petición valida, guarda y procesa antes de responder. Es la más simple, pero el procesamiento compite con la ingesta durante el pico (QA-01).
2. Monolito modular con ingesta asíncrona: un solo despliegue con módulos separados; la ingesta solo guarda y el trabajo pesado se difiere a un worker.
3. Microservicios orientados a eventos: servicios independientes comunicados por un broker. Se descarta porque incumple R-01 y R-03 y exige tecnologías fuera de R-02.

En la matriz de decisión, la alternativa 2 obtuvo el mayor total ponderado (4,00 frente a 3,35 y 2,40). La ventaja sobre la alternativa 1 es estrecha y sensible a los puntajes.
## Decisión
Usaremos un monolito modular en Python con los módulos de reportes, mapa, priorización y brigadas, desplegado como una sola aplicación sobre PostgreSQL.

El endpoint de ingesta solo validará, guardará el reporte y responderá. Un worker en segundo plano procesará las fotos y recalculará la priorización de forma periódica.

Empezaremos con la versión mínima, de un solo worker, y añadiremos más solo si una prueba de carga lo justifica.
## Consecuencias
- Positivas:
  - La ingesta responde rápido durante el pico porque no espera al procesamiento (QA-01).
  - Hay un solo despliegue y una sola base de datos, lo que cabe en el servidor único (R-03) y en el plazo (R-01).
  - Los módulos con límites claros facilitan corregir una parte sin afectar a las demás (mantenibilidad, R-02).
- Negativas / riesgos:
  - El mapa y la priorización se actualizan con retraso de segundos (consistencia eventual), dentro del límite de 60 s de QA-02.
  - El worker comparte CPU, RAM y disco con la ingesta, así que la cola no añade capacidad; hay que limitar su trabajo durante el pico.
  - El servidor único es un punto único de falla y no ofrece alta disponibilidad real.
  - Las subidas lentas de fotos por red congestionada no se resuelven con este estilo y requieren medidas aparte.