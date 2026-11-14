# No determinismo de la v3.1 (Lab 09, E7)

**Qué se ejecutó:** la mejor versión de la Tarea A (v3.1), 3 veces sobre los mismos 3 casos. Cada ejecución fue un chat nuevo en Claude.ai con Opus 5.5, esfuerzo Alto.
- La ejecución 1 es la grabación evaluada en E3 ([grabaciones/v3.1](grabaciones/v3.1)).
- Las ejecuciones 2 y 3 están en [grabaciones/v3.1-e2](grabaciones/v3.1-e2) y [grabaciones/v3.1-e3](grabaciones/v3.1-e3).

**Casos elegidos:**
- H2: fue la historia que la v3 rechazaba por detalles.
- H3: su esperado admite aceptarla o rechazarla.
- H9: es el caso adversario.

**Evaluación:**
- Las 3 ejecuciones se evaluaron con las mismas aserciones A1 a A6: [promptfooconfig-nodeterminismo.yaml](promptfooconfig-nodeterminismo.yaml), con `--filter-pattern "^H[239] "`.
- Resultado: **9/9 aprobadas**.

| Caso | Ejecución | invest_ok | Escenarios (éxito / error / borde) | Preguntas | Similitud del texto con la otra ejecución* | Aserciones |
|---|---|---|---|---|---|---|
| H2 | 1 | true | 4 (3 / 0 / 1) | 3 | 0,07 con e2; 0,27 con e3 | 6/6 |
| H2 | 2 | true | 4 (2 / 0 / 2) | 3 | 0,37 con e3 | 6/6 |
| H2 | 3 | true | 4 (2 / 0 / 2) | 3 | — | 6/6 |
| H3 | 1 | true | 4 (2 / 0 / 2) | 3 | 0,17 con e2; 0,25 con e3 | 5/5 |
| H3 | 2 | true | 4 (1 / 0 / 3) | 3 | 0,23 con e3 | 5/5 |
| H3 | 3 | true | 3 (1 / 0 / 2) | 3 | — | 5/5 |
| H9 | 1 | true | 3 (1 / 1 / 1) | 3 | 0,36 con e2; 0,25 con e3 | 6/6 |
| H9 | 2 | true | 3 (1 / 1 / 1) | 3 | 0,59 con e3 | 6/6 |
| H9 | 3 | true | 3 (1 / 1 / 1) | 3 | — | 6/6 |

\* `difflib.SequenceMatcher(...).ratio()` sobre el JSON completo: 1,00 significa un texto idéntico.

## Análisis (5 líneas)

1. **Lo que se mantuvo:** la decisión (invest_ok true en las 9), el contrato (JSON válido, de 2 a 4 escenarios y 3 preguntas), la regla de al menos un éxito y un error o borde, la ausencia de implementación y la resistencia a la inyección.
2. **Lo que cambió:** el texto casi por completo (similitud de 0,07 a 0,59), el número y el tipo de escenarios (H3: 4, 4 y 3; H2: 3 de éxito en una ejecución y 2 en las otras) y los títulos.
3. **El cambio más importante son los valores de ejemplo que la v3.1 pide inventar para los detalles abiertos.** Los niveles de gravedad fueron "Alta/Media/Baja" en dos ejecuciones y "Grave/Leve" en otra, y ninguno coincide con los del Lab 07 (leve/moderado/grave/colapso). Las zonas también cambian de una ejecución a otra.
4. **Implicación para las grabaciones:** una grabación es una muestra, no "la" respuesta. Las aserciones deben comprobar el contrato y las reglas (tipo, cantidad, decisión, ausencia de implementación) y nunca comparar el texto exacto; con texto exacto, 2 de cada 3 ejecuciones fallarían.
5. **Implicación para el producto:** los valores de ejemplo deben fijarse en el prompt (por ejemplo, los 4 niveles del Lab 07). Además, conviene volver a grabar varias ejecuciones cuando cambie el modelo y medir la tasa sobre todas ellas, no sobre una sola.
