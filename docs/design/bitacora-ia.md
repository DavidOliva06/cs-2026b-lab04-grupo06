# Bitácora de uso de IA - SismoReporta AQP

- Herramienta: Claude (asistente de IA de Anthropic)
- Autor: Oliva Valdivia David Alexander
- Periodo: octubre y noviembre de 2026

## Interacciones

| # | Fecha | Herramienta | Objetivo | Prompt (resumen) | Propuesta de la IA | Verificación | Decisión |
|---|---|---|---|---|---|---|---|
| 1 | 2026-10-07 | Claude (Anthropic) | Diagrama de clases de la HU-01 | "Actúa como diseñador de software orientado a objetos... genera un diagrama de clases en PlantUML." El prompt mencionaba por error "estado del pedido" y "pasarela de pagos". | Diagrama con `Reporte`, `EstadoReporte` y tres puertos. Avisó que pedido y pagos no aparecían en la historia y usó sus equivalentes. | Se pidió una segunda revisión: la IA encontró 8 problemas en su propio diagrama, entre ellos un puerto compartido por celular y servidor y una comprobación de duplicados no atómica. | Se aplicaron las 8 correcciones. |
| 2 | 2026-10-11 | Claude (Anthropic) | Diagrama de estados de `Reporte` | "Escriba el diagrama en Mermaid (stateDiagram-v2)... 5 o más estados y 2 o más guardas." | Diagrama con seis estados, dos estados finales y siete guardas. | La lista de verificación mostró que los estados no coincidían con la enumeración, que tenía solo dos valores. | Se actualizó `clases.puml` a seis valores y se agregaron tres operaciones a `Reporte`. |
| 3 | 2026-10-11 | Claude (Anthropic) | Diagrama de actividades del proceso de brigadas | "Modele el proceso con PlantUML... 3 o más particiones, 2 o más decisiones y una ejecución paralela." | Diagrama con tres particiones, tres decisiones y un `fork`. | La IA revisó el proceso y encontró 6 problemas; el más grave, que el flujo atendía una sola zona y terminaba. Luego se validó con un compañero del curso, que señaló que faltaba el paso por "Verificado". | Se corrigieron 5 problemas, incluido el paso por "Verificado". Queda pendiente el caso de la brigada que no responde. |
| 4 | 2026-10-11 | Claude (Anthropic) | Diagrama de paquetes y regla sin ciclos | "Cree un paquete por cada módulo del ADR-001... verifique la regla C4. Si encuentra un ciclo, resuélvalo con un puerto." | Diagrama de paquetes con la nota de la regla de dependencias. Encontró un ciclo entre priorización y brigadas. | Se comprobó que, con el puerto, las dependencias quedan en un solo sentido. | Se usó el puerto `ConsultaZonasAsignadas` y se registró en el ADR-004. |
| 5 | 2026-10-11 | Claude (Anthropic) | Esqueleto en Python | "Genera el esqueleto en Python 3.10 (dataclasses y type hints) de nuestro diagrama de clases." El prompt mencionaba "Pedido" por error. | `reportes.py` con dataclasses, puertos como clases abstractas y tres adaptadores; la lógica mínima se puso en `Reporte`. | La IA probó las transiciones, pero en Python 3.13 y no en 3.10. | Se aceptó el esqueleto; queda pendiente probarlo en 3.10. |
| 6 | 2026-10-11 | Claude (Anthropic) | Round-trip entre diseño y código | "Compare ambos diagramas y registre en round-trip.md 3 o más diferencias, con su causa y la acción tomada." | Nueve diferencias entre `clases.puml` y `classes_en.puml` (pyreverse). | Siete se deben a límites de Python o de pyreverse; entre ellas, que pyreverse no reconstruye las multiplicidades. | Actualizar `clases.puml` con los adaptadores y los nombres de rol. Se aplicó en `v0.5.1-diseno`. |
| 7 | 2026-10-11 | Claude (Anthropic) | Revisión de consistencia de los cinco diagramas | "Actúa como revisor de diseño... verifica C1 a C5 y responde en una tabla. Cita la línea." | 17 hallazgos con archivo y línea, registrados en `consistencia.md`. | Se pidió buscar falsos positivos: 7 falsos positivos o discutibles y 3 mal clasificados (ver `consistencia.md`). | Quedaron 7 hallazgos sólidos; 5 se corrigieron en `v0.5.1-diseno` y quedan pendientes los 2 de C2. |
| 8 | 2026-11-13 | Claude (Anthropic) | Revisión del informe tras la retroalimentación | "Revisa la crítica del informe del Lab 05 y mejora el informe sin cambiar la plantilla." | Contrastó la crítica con el informe y el repositorio: 1 observación correcta, 2 en parte y 1 incorrecta (el ADR-004 sí está fechado en 2026). Además encontró 6 mensajes que incumplían C1, 7 enlaces rotos en el README y que la etiqueta `v0.5-diseno` no incluía el commit de E8. | Se comprobó con `verificar_c1.py` (de 6 mensajes sin operación a 0) y revisando cada enlace del README. | Correcciones en la rama `lab05-correcciones` y nueva etiqueta `v0.5.1-diseno`. |

## Lecciones aprendidas

- **Pedir una segunda revisión funciona:** en las interacciones 1, 3, 7 y 8 la IA encontró errores propios solo cuando se le pidió releer su respuesta.
- **La IA exagera hallazgos:** en la revisión de consistencia, 7 de 17 hallazgos eran falsos positivos. Uno de ellos proponía renombrar un estado que viene directamente de RF-05.
- **Los errores del prompt se propagan:** dos prompts mencionaban "pedido" y "pasarela de pagos" por error. La IA lo advirtió y adaptó, pero hay que revisar el enunciado antes de enviarlo.
- **Los diagramas se desincronizan:** al cambiar la enumeración, el diagrama de secuencia quedó con los nombres antiguos. Cada cambio en `clases.puml` obliga a revisar los demás diagramas.
- **La IA no publica cambios:** puede leer el repositorio público, pero los commits y las etiquetas los hace el autor. Tampoco comprobó el código en la versión exacta de Python pedida.
- **Verificar con herramientas, no a mano:** la regla C1 parecía cumplida en el informe, pero `verificar_c1.py` encontró 6 mensajes sin operación en la versión entregada.

## Pendientes

- C2: `recibir()` y `enviar()` en el diagrama de estados no son operaciones de `Reporte`.
- Comprobar el consentimiento antes de capturar la foto y la ubicación (criterio 4).
- Reasignar la zona cuando la brigada no responde (diagrama de actividades).
- Probar `reportes.py` en Python 3.10.
