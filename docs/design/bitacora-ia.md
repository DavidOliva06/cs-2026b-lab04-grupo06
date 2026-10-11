# Bitácora de uso de IA - SismoReporta AQP

- Herramienta: Claude (asistente de IA de Anthropic)
- Autor: Oliva Valdivia David Alexander
- Periodo: octubre de 2026

## Interacciones

| # | Fecha | Objetivo | Prompt (resumen) | Respuesta de la IA | Verificación y ajuste |
|---|---|---|---|---|---|
| 1 | 2026-10-07 | Diagrama de clases de la HU-01 | "Actúa como diseñador de software orientado a objetos... genera un diagrama de clases en PlantUML." El prompt mencionaba por error "estado del pedido" y "pasarela de pagos". | Diagrama de clases con `Reporte`, `EstadoReporte` y tres puertos. La IA avisó de que pedido y pagos no aparecían en la historia y usó sus equivalentes. | Se pidió una segunda revisión. La IA encontró 8 problemas en su propio diagrama, entre ellos un puerto compartido por celular y servidor y una comprobación de duplicados no atómica. Se aplicaron las 8 correcciones. |
| 2 | 2026-10-11 | Diagrama de estados de `Reporte` | "Escriba el diagrama en Mermaid (stateDiagram-v2)... 5 o más estados y 2 o más guardas." | Diagrama con seis estados, dos estados finales y siete guardas. | Con la lista de verificación se detectó que los estados no coincidían con la enumeración, que tenía solo dos valores. Se actualizó `clases.puml` a seis valores y se agregaron tres operaciones a `Reporte`. |
| 3 | 2026-10-11 | Diagrama de actividades del proceso de brigadas | "Modele el proceso con PlantUML... 3 o más particiones, 2 o más decisiones y una ejecución paralela." | Diagrama con tres particiones, tres decisiones y un `fork`. | Se pidió revisar el proceso. La IA encontró 6 problemas; el más grave, que el flujo atendía una sola zona y terminaba. Se corrigieron 5. Quedó pendiente el caso de la brigada que no responde. |
| 4 | 2026-10-11 | Diagrama de paquetes y regla sin ciclos | "Cree un paquete por cada módulo del ADR-001... verifique la regla C4. Si encuentra un ciclo, resuélvalo con un puerto." | Diagrama de paquetes con nota de la regla de dependencias. Encontró un ciclo entre priorización y brigadas. | El ciclo se resolvió con el puerto `ConsultaZonasAsignadas` y la decisión se registró en el ADR-004. |
| 5 | 2026-10-11 | Esqueleto en Python | "Genera el esqueleto en Python 3.10 (dataclasses y type hints) de nuestro diagrama de clases." El prompt mencionaba "Pedido" por error. | Archivo `reportes.py` con dataclasses, puertos como clases abstractas y tres adaptadores. La lógica mínima se puso en `Reporte`. | La IA ejecutó una prueba de las transiciones, pero en Python 3.13 y no en 3.10. Queda pendiente comprobarlo en 3.10. |
| 6 | 2026-10-11 | Round-trip entre diseño y código | "Compare ambos diagramas y registre en round-trip.md 3 o más diferencias, con su causa y la acción tomada." | Nueve diferencias entre `clases.puml` y el diagrama generado desde el código. | Siete se deben a límites de Python o de la herramienta. Dos exigen actualizar `clases.puml`: los adaptadores y los nombres de rol. La causa de una diferencia es una inferencia de la IA, no comprobada. |
| 7 | 2026-10-11 | Revisión de consistencia de los cinco diagramas | "Actúa como revisor de diseño... verifica C1 a C5 y responde en una tabla. Cita la línea." | 17 hallazgos con archivo y línea, registrados en `consistencia.md`. | Se pidió buscar falsos positivos. La IA reconoció 7 falsos positivos o discutibles y 3 mal clasificados. Quedaron 7 hallazgos sólidos: 3 de C1, 2 de C2 y 2 de C5. C3 y C4 se cumplen. |

## Lecciones aprendidas

- **Pedir una segunda revisión funciona:** en las interacciones 1, 4, 6 y 10 la IA encontró errores propios solo cuando se le pidió releer su respuesta.
- **La IA exagera hallazgos:** en la revisión de consistencia, 7 de 17 hallazgos eran falsos positivos. Uno de ellos proponía renombrar un estado que viene directamente de RF-05.
- **Los errores del prompt se propagan:** dos prompts mencionaban "pedido" y "pasarela de pagos" por error. La IA lo advirtió y adaptó, pero hay que revisar el enunciado antes de enviarlo.
- **Los diagramas se desincronizan:** al cambiar la enumeración, el diagrama de secuencia quedó con los nombres antiguos. Cada cambio en `clases.puml` obliga a revisar los demás diagramas.
- **La IA no puede hacer todo:** no tiene acceso al repositorio, así que los commits se hicieron a mano, y no comprobó el código en la versión exacta de Python pedida.

## Pendientes

- Aplicar en los diagramas los 7 hallazgos sólidos de `consistencia.md`.
- Actualizar `clases.puml` con los adaptadores y los nombres de rol del round-trip.
- Probar `reportes.py` en Python 3.10.