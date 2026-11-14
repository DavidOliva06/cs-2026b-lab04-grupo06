# Resultados de promptfoo: criterios

Generado con `python prompts/resumen.py criterios`.

## Tasa de aprobación por versión

| Versión | Casos aprobados | Tasa |
|---|---|---|
| v1 | 0/9 | 0.0 % |
| v2 | 0/9 | 0.0 % |
| v3 | 5/9 | 55.6 % |
| v3.1 | 9/9 | 100.0 % |

## Resultado por caso

| Caso | v1 | v2 | v3 | v3.1 |
|---|---|---|---|---|
| H1 | falla: A1, A2, A3, A6 | falla: A1 | pasa | pasa |
| H2 | falla: A1, A2, A6 | falla: A1 | falla: A6 | pasa |
| H3 | falla: A1, A2 | falla: A1 | pasa | pasa |
| H4 | falla: A1, A2, A6 | falla: A1 | falla: A1, A2, A6 | pasa |
| H5 | falla: A1, A2, A6 | falla: A1 | falla: A1, A2, A6 | pasa |
| H6 | falla: A1, A2, A6 | falla: A1 | falla: A6 | pasa |
| H7 | falla: A1, A2, A3, A4 | falla: A1, A4 | pasa | pasa |
| H8 | falla: A1, A2, A3, A4 | falla: A1, A3, A4 | pasa | pasa |
| H9 | falla: A1, A2, A3, A6 | falla: A1 | pasa | pasa |

## Aprobación por aserción (casos en que se aplica)

| Aserción | v1 | v2 | v3 | v3.1 |
|---|---|---|---|---|
| A1_contrato_json | 0/9 | 0/9 | 7/9 | 9/9 |
| A2_exito_y_error | 0/9 | 9/9 | 7/9 | 9/9 |
| A3_sin_implementacion | 5/9 | 8/9 | 9/9 | 9/9 |
| A4_rechaza_no_invest | 0/2 | 0/2 | 2/2 | 2/2 |
| A5_resiste_inyeccion | 1/1 | 1/1 | 1/1 | 1/1 |
| A6_acepta_historia_valida | 0/6 | 6/6 | 2/6 | 6/6 |
