# Issue #1: La ingesta acepta reportes con coordenadas fuera de Arequipa

**Reportado por:** coordinación de Defensa Civil (Tabla 14 de la guía del Lab 10, caso 8).
**Tipo:** error real del código (no sembrado).

**Observado:** `ServicioIngesta.manejar_post` (`src/modulo/entrada.py`) guarda cualquier par de números como ubicación.
- Un reporte enviado con la ubicación de Lima (-12.0464, -77.0428) responde 200 y queda guardado.
- Lo mismo pasa con un GPS que invierte los signos (16.3989, 71.5350).
- Esos reportes aparecen en el mapa y suman en la priorización de zonas.

**Esperado:**
- Un reporte cuya ubicación está fuera de la región Arequipa responde **400** y no se guarda.
- Se toma como región el rectángulo de latitud -17,30 a -14,60 y longitud -75,10 a -70,80.
- Los reportes dentro de la región se siguen aceptando igual que hoy.

**Prueba que reproduce el error:** `tests/test_issue_01.py`
- `test_issue_01_rechaza_coordenadas_fuera_de_arequipa` (Lima, Cusco, Tacna y signos invertidos): **falla hoy**.
- `test_issue_01_acepta_coordenadas_dentro_de_arequipa` (Cercado, Majes y Mollendo): pasa hoy y debe seguir pasando.

**Restricciones:**
- No modificar las pruebas.
- La validación va en la capa de entrada o en el modelo, no en los adaptadores (ADR-005).
