# ADR-006: Modo pico en la ingesta: datos primero y fotos diferidas
- Estado: Aceptado
- Fecha: 2026-10-31
- Decisores: Oliva Valdivia David Alexander
## Contexto
En el simulacro nacional llegan 20 000 reportes en una hora, con una ráfaga de 2 000 en 1 minuto, y la red móvil está congestionada. El escenario D1, que extiende QA-01, exige guardar ≥ 99,5 % de los reportes ≤ 15 min después de que el ciudadano recupera la señal, sin duplicados y sin perder reportes en el dispositivo. Es el escenario (H,H) del atributo crítico, la disponibilidad ([árbol de utilidad](../utilidad/arbol.png)).

Con la PWA de ADR-003, cada reporte sube sus datos (≈ 1 KB) y después su foto (≈ 300 KB). A 50 kbps, una foto tarda ≈ 48 s, y en la ráfaga eso equivale a ≈ 1 600 conexiones simultáneas en el proxy de un servidor único (ADR-001, R-03). El análisis está en la [iteración 1 de ADD](../add/iteracion-1.md).
## Alternativas consideradas
1. Limitar la respuesta a eventos (T1): por encima de un umbral, responder HTTP 429 con `Retry-After`.
2. Degradación (T2): un modo pico que acepta solo los datos de cada reporte, deja la foto en el celular para después y hace que el worker solo recalcule la priorización.
3. Aumentar recursos de forma temporal (T3): agrandar el servidor durante el simulacro. Se descarta porque invalida el simulacro como medición: en un sismo real nadie agranda el servidor antes, y si se olvida bajar el plan, el costo mensual se multiplica por 3 o 4 (R-03).
4. Redundancia pasiva (T4): un segundo servidor con réplica de PostgreSQL. Se descarta porque cuesta US$ 40–60 al mes (fuera de R-03), toma del 25 % al 40 % del plazo (R-01) y no ataca la causa, que son las fotos y las conexiones lentas.
## Decisión
Usaremos un modo pico (T2) en la ingesta. El servidor lo activa solo cuando el 70 % de las conexiones del proxy está ocupado durante 10 s. Mientras está activo:
- la API acepta los datos del reporte;
- la respuesta le indica a la PWA que guarde la foto para después;
- el worker deja de procesar fotos y solo recalcula la priorización.

No adoptaremos T1: la evidencia muestra que no mejora D1 y que, con 1 núcleo, lo empeora.

**Evidencia:** la simulación de eventos discretos [fitness/simulacion_d1.py](../../../fitness/simulacion_d1.py) corrió 10 réplicas con los supuestos escritos en la iteración 1, sección 9.2.

| Medida de D1: reportes guardados ≤ 15 min (peor réplica) | Antes | Con T2 |
|---|---|---|
| Supuestos base | 100 % (máximo 298 s) | 100 % (máximo 18 s) |
| Con una caída del servidor de 10 min | **97,47 %: no cumple** | **100 %: cumple** |
| Con una caída de 13 min | 90,90 % | 99,02 % |
| Con 1 núcleo, como el droplet del Lab 06 | **98,82 %: no cumple** | **100 %: cumple** |
| Con 1 núcleo y una caída de 10 min | 90,22 %: no cumple | **99,86 %: cumple** |

T1 no mejoró D1 en ninguna variante. Con 2 núcleos la CPU no fue el cuello de botella (0 esperas expiradas) y T1 solo agregó espera. Con 1 núcleo la CPU sí se satura, y aun así T1 empeora el resultado: con la caída de 10 min, T1 + T2 queda en 99,28 % y no cumple, mientras que solo T2 llega a 99,86 %.
## Consecuencias
- Positivas:
  - D1 se cumple con el servidor real de 1 vCPU, donde sin T2 no se cumple ni sin fallas (98,82 %), y también con una caída del servidor de hasta 10 min.
  - En la base, el máximo hasta guardar baja de 298 s a 18 s, así que el margen dentro de la ventana de 900 s pasa de 602 s a 882 s.
  - El disco de fotos deja de crecer durante el pico (D3), y el worker deja de competir con la ingesta por la CPU, un riesgo de ADR-001.
  - No agrega tecnología ni costo: US$ 0 y 2–3 días-persona.
- Negativas / riesgos:
  - **Trade-off aceptado:** disponibilidad de la ingesta a cambio de fotos tardías. En la simulación base se difiere el 69 % de las fotos (13 723 de 20 000). Durante el pico, el coordinador ve reportes sin foto y la verificación se retrasa.
  - La foto diferida solo se envía si el ciudadano vuelve a abrir la PWA (ADR-003 no usa la sincronización en segundo plano), y mientras tanto el navegador puede borrarla. No se sabe cuántas llegan (RI-01).
  - Sin foto, la priorización depende solo de cuántos reportes hay, así que los reportes falsos pesan más; lo atiende el ADR-008.
  - El ciclo de vida del reporte necesita un estado "foto pendiente" en `estados.py` (ADR-005).
  - D1 sigue sin tolerar caídas de más de ≈ 10 min; la protección contra caídas largas queda en D2 (reiniciar el proceso en ≤ 60 s). Con 1 núcleo y una caída de 10 min, el margen es de solo 0,36 puntos (99,86 % frente a 99,5 %).
  - La evidencia viene de un modelo con parámetros supuestos, no de una prueba de carga del sistema real (RI-03), y el umbral del 70 % no está calibrado (RI-04).
