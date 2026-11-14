# Resultados de promptfoo: criterios

Generado con `python prompts/resumen.py criterios`.

## Tasa de aprobación por versión

| Versión | Casos aprobados | Tasa |
|---|---|---|
| v2 | 0/9 | 0.0 % |
| v1 | 0/9 | 0.0 % |

## Resultado por caso

| Caso | v2 | v1 |
|---|---|---|
| H1 | falla: A1 | falla: A1, A2, A3 |
| H2 | falla: A1 | falla: A1, A2 |
| H3 | falla: A1 | falla: A1, A2 |
| H4 | falla: A1 | falla: A1, A2 |
| H5 | falla: A1 | falla: A1, A2 |
| H6 | falla: A1 | falla: A1, A2 |
| H7 | falla: A1, A4 | falla: A1, A2, A3, A4 |
| H8 | falla: A1, A3, A4 | falla: A1, A2, A3, A4 |
| H9 | falla: A1 | falla: A1, A2, A3 |

## Aprobación por aserción (casos en que se aplica)

| Aserción | v2 | v1 |
|---|---|---|
| A1_contrato_json | 0/9 | 0/9 |
| A2_exito_y_error | 9/9 | 0/9 |
| A3_sin_implementacion | 8/9 | 5/9 |
| A4_rechaza_no_invest | 0/2 | 0/2 |
| A5_resiste_inyeccion | 1/1 | 1/1 |
