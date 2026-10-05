## 1. Prompt 1
| Criterio | A. Monolito síncrono | B. Monolito modular + cola | C. Microservicios + broker |
|---|---|---|---|
| **Fortalezas** | Es el más simple y rápido de construir. Un solo despliegue, fácil de depurar. | Absorbe ráfagas porque la ingesta es rápida y el trabajo pesado se difiere. Sigue siendo un solo despliegue y una sola base de datos. | Aísla fallos y permite escalar cada servicio por separado. |
| **Debilidades** | El procesamiento de fotos bloquea las peticiones. Un pico degrada también el mapa y la asignación. | El mapa y la priorización se actualizan con segundos de retraso (consistencia eventual). Hay que monitorear la cola y los workers. | Sobrecarga operativa alta: broker, varios despliegues, trazabilidad distribuida. En un solo servidor no se aprovecha el escalado. |
| **Riesgos** | Timeouts en la primera hora provocan reintentos masivos desde los celulares y un efecto bola de nieve. | La cola puede crecer si los workers no dan abasto. Sin idempotencia, los reintentos crean duplicados. | No se llega al MVP en 1 mes con 1 desarrollador. El broker y los servicios compiten por la RAM del mismo servidor. |
| **Favorece** | Tiempo de entrega, simplicidad, costo, consistencia inmediata. | Disponibilidad de la ingesta, rendimiento bajo picos, resiliencia, costo, mantenibilidad. | Escalabilidad, aislamiento de fallos y despliegue independiente (solo con más infraestructura). |
| **Penaliza** | Rendimiento bajo carga, disponibilidad, escalabilidad. | Consistencia inmediata y, levemente, la simplicidad operativa. | Tiempo de entrega, costo, simplicidad, facilidad de pruebas y operación. |
| **Encaje con las restricciones** | Cumple plazo y costo, pero falla en el escenario crítico. | Cumple plazo, costo y el escenario crítico. | No cumple plazo ni presupuesto de forma realista. |
1. se recomienda la alternativa B, un monolito modular con ingesta asíncrona, porque es la única que cumple a la vez el plazo de un mes, el presupuesto de un solo servidor y el escenario crítico de la primera hora. Los 20 000 reportes llegarán en ráfagas al volver la señal, y B los absorbe porque el endpoint de ingesta solo valida, guarda y responde, mientras unos workers procesan después las fotos y la priorización desde una cola en la misma PostgreSQL. El monolito síncrono es más simple, pero se degrada justo cuando el sistema más importa, y los microservicios exigen un equipo y una infraestructura que el proyecto no tiene. El costo de B es que el mapa se actualiza con unos segundos de retraso, y el servidor único sigue siendo un punto único de falla.
## 2. Prompt 2
La alternativa B optimiza la parte fácil del problema, el backend, y deja casi sin tratar las partes donde el sistema fallará de verdad.

1. Supuestos que no se cumplen

- **"Aceptar un reporte es barato":** lo caro es subir la foto por una red congestionada, y eso ocurre antes de que la cola intervenga.
- **"La cola da capacidad":** en un solo servidor, los workers compiten con la ingesta por la misma CPU, RAM y disco, así que la cola solo reordena el trabajo.
- **"El ciudadano ya tiene la PWA":** quien no la instaló antes del sismo tendrá que descargarla con la red caída.
- **"Un desarrollador puede con esto en un mes":** la sincronización offline confiable es lo más difícil del proyecto y consumirá buena parte del plazo.

2. Costos ocultos

- **Operación:** monitoreo, respaldos, alertas y guardia recaen en una sola persona, que quizá también sea damnificada el día del sismo.
- **Pruebas:** hacen falta pruebas de carga y pruebas en celulares de gama baja reales, que no están en el plan de un mes.
- **Desuso:** el sistema pasa meses sin tráfico y se usa de golpe, de modo que certificados vencidos, disco lleno o dependencias rotas se descubren el peor día.

3. Los 5 riesgos más graves

31. **La PWA no está disponible cuando se necesita.**
   - Falla: no está instalada, el navegador borró los reportes pendientes o el usuario cerró la app antes de que se enviaran. En iOS, además, no hay sincronización en segundo plano, hasta donde sé.
   - Táctica: degradación elegante. Un formulario web mínimo de pocos KB funciona sin instalación, el reenvío se dispara al abrir la app y los pendientes se muestran en pantalla hasta confirmarse.

32. **Las subidas lentas agotan la ingesta.**
   - Falla: miles de conexiones que tardan minutos en subir una foto ocupan todos los procesos de Python, y los reportes dejan de entrar.
   - Táctica: separar la carga crítica. Primero se envían el texto y las coordenadas (alrededor de 1 KB) y la foto va después, en una subida aparte. Un proxy inverso delante recibe las conexiones lentas.

33. **Ingesta, workers y base de datos se ahogan entre sí.**
   - Falla: el procesamiento de fotos le quita recursos a la ingesta durante el pico, y si el disco se llena con las fotos, PostgreSQL se cae.
   - Táctica: gobierno de recursos. Durante el pico los workers solo calculan la priorización y las fotos se procesan después. Las fotos van en un volumen separado, y al superar un umbral de disco se rechazan fotos pero se siguen aceptando datos.

34. **Una caída provoca una tormenta de reintentos.**
   - Falla: si el servidor cae, todos los celulares reintentan a la vez y lo tumban de nuevo al levantarse.
   - Táctica: reintentos con espera exponencial y aleatoria en el cliente, límite de peticiones en el servidor con rechazo temprano, y recuperación automatizada mediante un script de despliegue y respaldos probados.

35. **El endpoint abierto recibe basura y expone datos personales.**
   - Falla: reportes falsos o duplicados desvían brigadas, y una fuga de fotos y ubicaciones incumple la Ley 29733.
   - Táctica: límite por dispositivo, agrupación de reportes cercanos para que la prioridad dependa de varias fuentes, y validación por el brigadista. Las fotos se sirven solo a usuarios autenticados y con un plazo de borrado definido.

4. Veredicto

B sigue siendo la mejor de las tres, pero la recomendación estaba incompleta. Para que sea viable en un mes hay que recortar el alcance: en el MVP entran el reporte sin foto obligatoria, el mapa y la asignación manual, y la priorización automática queda para después.