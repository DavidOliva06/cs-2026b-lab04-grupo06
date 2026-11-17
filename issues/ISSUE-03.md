# Issue #3: Prioridad errónea de una zona con reportes sin foto

**Reportado por:** coordinación de Defensa Civil (Tabla 14 de la guía del Lab 10, caso 8).
**Tipo:** error sembrado en el módulo nuevo de priorización (RF-03), como permite la guía.

**Observado:**
- En `src/modulo/priorizacion.py`, un reporte **sin foto** suma el peso máximo (4), sea cual sea su gravedad.
- Por eso 2 reportes leves sin foto en Cayma (8 puntos) ponen a Cayma por encima de un daño grave con foto en Yanahuara (4 puntos).
- Es justo el riesgo RI-02 de `docs/architecture/add/iteracion-1.md`: sin foto, los reportes falsos pesan más.

**Esperado:**
- Un reporte sin foto todavía no se puede verificar, así que aporta el **peso mínimo (1)** hasta que llegue su foto, aunque esté clasificado como más grave o sin clasificar.
- Los reportes con foto siguen sumando el peso de su gravedad (1, 2, 4 y 4).
- Se mantiene un voto por dispositivo y zona (T11).

**Prueba que reproduce el error:** `tests/test_issue_03.py`. **Las tres pruebas fallan hoy:**
- `test_issue_03_reportes_sin_foto_no_superan_a_un_dano_verificado`;
- `test_issue_03_sin_foto_y_sin_clasificar_aporta_el_peso_minimo`;
- `test_issue_03_sin_foto_no_sube_por_encima_de_su_gravedad`.

**Restricciones:**
- No modificar las pruebas.
- No cambiar los pesos de los reportes con foto ni la regla de un voto por dispositivo.
