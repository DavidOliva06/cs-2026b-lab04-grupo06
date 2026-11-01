# ADR-007: API del mapa agregada por zona
- Estado: Aceptado
- Fecha: 2026-10-31
- Decisores: Oliva Valdivia David Alexander
## Contexto
En el simulacro nacional, 30 coordinadores abren el mapa nacional y lo refrescan cada 30 s, con 20 000 reportes activos y la ingesta en curso. El escenario R2, que extiende QA-02, exige:
- carga del mapa p95 ≤ 3 s;
- cambio de filtro p95 ≤ 1 s;
- ≤ 60 s de retraso entre que un reporte se guarda y aparece en el mapa.

Su dificultad se corrigió a H en E1, porque el mapa comparte el servidor único y la base de datos con la ingesta (ADR-001, ADR-002).

Hoy la API devuelve el listado de reportes activos, y el panel los agrupa y filtra en el navegador. El análisis está en la [iteración 2 de ADD](../add/iteracion-2.md).
## Alternativas consideradas
1. Aumentar la eficiencia (T5): la API agrupa por zona en la consulta (un registro por zona, con el total y el conteo por gravedad) y el proxy comprime la respuesta con gzip.
2. T5 más copias de los datos (T6): el worker recalcula cada 15 s una tabla `resumen_zona` y la API la lee.
3. T5 más copias del cómputo (T7): una caché de la respuesta compartida por los coordinadores durante 15 s.
4. Aumentar recursos (T8): una réplica de lectura de PostgreSQL en un segundo servidor. Se descarta porque incumple R-03 y no ataca la causa medida.
## Decisión
Usaremos una API del mapa agregada por zona (T5):
- `GET /api/mapa/zonas?region=&gravedad=` devuelve un registro por zona;
- `GET /api/mapa/zonas/{zona}/reportes` devuelve el detalle de una zona cuando el coordinador se acerca;
- el proxy comprime las respuestas JSON con gzip.

El panel dibujará un marcador por zona. No adoptaremos T6 ni T7.

**Evidencia:** el prototipo [fitness/prototipo_r2.py](../../../fitness/prototipo_r2.py) mide la respuesta real (consulta, JSON y gzip) sobre 20 000 reportes y estima la red del coordinador con Monte Carlo. Los supuestos están en la iteración 2, paso 7.

| Alternativa | Con gzip | Carga del mapa p95 (≤ 3 s) | Filtro p95 (≤ 1 s) | Retraso máximo (≤ 60 s) | CPU (% de 1 núcleo) |
|---|---|---|---|---|---|
| Antes: listado | 826 KB | **13,46 s: no cumple** | 0 s (en el navegador) | 43 s | 35,8 |
| **T5** | 28 KB | **1,00 s** | 0,68 s | 31 s | 6,7 |
| T5 + T6 | 28 KB | 0,97 s | 0,69 s | 46 s | 2,6 |
| T5 + T7 | 28 KB | 0,94 s | 0,69 s | 46 s | 0,5 |

Con una bajada de 1 Mbps, T5 queda en 1,36 s, y con 40 000 reportes en 1,01 s, porque la respuesta crece con las zonas, no con los reportes. T6 y T7 mejoran ≤ 0,06 s, pero gastan 15 s del margen de retraso.
## Consecuencias
- Positivas:
  - R2 se cumple con margen: la carga del mapa baja de 13,46 s a 1,00 s.
  - La respuesta no depende de cuántos reportes haya, solo de cuántas zonas (≈ 1 874).
  - La CPU del mapa baja de 35,8 % a 6,7 % de un núcleo, lo que deja recursos para la ingesta en el servidor único.
  - Se implementa dentro del módulo de mapa (ADR-001) en 1–2 días-persona, sin tecnología nueva.
- Negativas / riesgos:
  - **Trade-off aceptado:** se pierde detalle a cambio de tiempo de carga. La vista nacional no muestra cada reporte; para verlo hay que acercarse a una zona, con una petición más. El filtro deja de ser instantáneo (0,68 s), y es la parte de R2 con menos margen (RI-09).
  - Si los coordinadores pasan de ≈ 150, la CPU del mapa llegaría a ≈ 33 % de un núcleo y habría que reconsiderar T7.
  - Los tiempos de servidor se midieron en SQLite y sin la ingesta en paralelo (RI-07); el tiempo de dibujo del panel no se midió (RI-08).
