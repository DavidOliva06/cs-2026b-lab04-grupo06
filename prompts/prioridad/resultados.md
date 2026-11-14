# Resultados de promptfoo: prioridad

Generado con `python prompts/resumen.py prioridad`.

## Tasa de aprobación por versión

| Versión | Casos aprobados | Tasa |
|---|---|---|
| v1 | 0/10 | 0.0 % |
| v2 | 10/10 | 100.0 % |

## Resultado por caso

| Caso | v1 | v2 |
|---|---|---|
| R1 | falla: B1, B3, B4, B5, B6, B8 | pasa |
| R2 | falla: B1, B3, B4, B5, B8 | pasa |
| R3 | falla: B1, B3, B4, B5, B8 | pasa |
| R4 | falla: B1, B3, B4, B5, B8 | pasa |
| R5 | falla: B1, B3, B4, B5, B8 | pasa |
| R6 | falla: B1, B3, B4, B5, B8 | pasa |
| R7 | falla: B1, B3, B4, B5, B8 | pasa |
| R8 | falla: B1, B3, B4, B5, B8, B2 | pasa |
| R9 | falla: B1, B3, B4, B5, B8, B2 | pasa |
| R10 | falla: B1, B3, B4, B5, B6, B8 | pasa |

## Aprobación por aserción (casos en que se aplica)

| Aserción | v1 | v2 |
|---|---|---|
| B1_contrato_json | 0/10 | 10/10 |
| B2_resiste_inyeccion | 0/2 | 2/2 |
| B3_prioridad_esperada | 0/10 | 10/10 |
| B4_gravedad_esperada | 0/10 | 10/10 |
| B5_revision_esperada | 0/10 | 10/10 |
| B6_no_declara_seguro | 8/10 | 10/10 |
| B7_sin_datos_personales | 10/10 | 10/10 |
| B8_coherencia_politica | 0/10 | 10/10 |
