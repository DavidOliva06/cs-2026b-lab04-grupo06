# Issue #2: Reportes duplicados al sincronizar con el almacén del servidor en memoria

**Reportado por:** equipo de desarrollo, al usar la demostración sin PostgreSQL (Tabla 14 de la guía del Lab 10, caso 8).
**Tipo:** error sembrado: el adaptador nuevo se escribió con el error incluido, como permite la guía.

**Observado:**
- Cuando el servidor guarda un reporte pero la confirmación no llega al celular, el celular vuelve a enviar el **mismo** reporte (mismo id) al recuperar la señal.
- Con el almacén `"memoria"` (`AdaptadorMemoriaServidor` en `src/modulo/adaptadores.py`), el servidor termina con **2** reportes en lugar de 1.
- Además, `guardar_si_no_existe` devuelve `True` aunque el reporte ya existía.

**Esperado:** igual que `AdaptadorPostgres` (criterio 3 de la HU-01 y escenario D1 del Lab 08):
- `guardar_si_no_existe` guarda solo si no existe un reporte con ese id;
- devuelve `True` si lo guardó y `False` si ya existía;
- `contar()` cuenta reportes distintos.

**Prueba que reproduce el error:** `tests/test_issue_02.py`. **Las dos pruebas fallan hoy:**
- `test_issue_02_reenvio_tras_respuesta_perdida_no_duplica`;
- `test_issue_02_mismo_reporte_dos_veces_devuelve_false_la_segunda`.

**Restricciones:**
- No modificar las pruebas ni `AdaptadorPostgres`.
- El servicio del celular no debe cambiar: el reenvío con el mismo id es correcto. La deduplicación es responsabilidad del servidor.
