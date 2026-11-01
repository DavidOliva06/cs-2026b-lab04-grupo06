# ATAM-lite: hallazgos y matriz de riesgos (Lab 08, E7)

## 1. Alcance y fuentes

- **Arquitectura evaluada:** ADR-001 a ADR-008, el modelo C4 actualizado ([workspace.dsl](c4/workspace.dsl)) y el código de `src/modulo`.
- **Escenarios:** el [árbol de utilidad](utilidad/arbol.png). Se analizaron en profundidad los tres atendidos por las iteraciones de ADD: D1 ([iteración 1](add/iteracion-1.md)), R2 ([iteración 2](add/iteracion-2.md)) y S2 ([iteración 3](add/iteracion-3.md)).
- **Evidencia:** [simulacion_d1.py](../../fitness/simulacion_d1.py), [prototipo_r2.py](../../fitness/prototipo_r2.py), [simulacion_s2.py](../../fitness/simulacion_s2.py), los contratos de [.importlinter](../../.importlinter) y las pruebas de `tests/`.

| Origen de los hallazgos | Cantidad |
|---|---|
| Propios: iteraciones de ADD, E5 (fitness functions) y E6 (ADR y C4) | 15 riesgos, 7 puntos de sensibilidad, 5 puntos de trade-off y 6 no riesgos |
| Recibidos de otro grupo | **Ninguno.** El equipo no realizó E3 (revisión cruzada), así que no hay hallazgos externos que registrar |

## 2. Riesgos

Escala: Baja = 1, Media = 2 y Alta = 3. **Zona crítica: probabilidad × impacto ≥ 6.** La tabla y la matriz se generan con [matriz_riesgos.py](riesgos/matriz_riesgos.py).

| ID | Riesgo | Probabilidad | Impacto | P × I | Zona | Origen |
|---|---|---|---|---|---|---|
| R-03 | La simulación de D1 suponía 2 núcleos; el droplet tiene 1 vCPU | Alta | Alta | 9 | **Crítica** | E6, ADR-006 |
| R-01 | Fotos diferidas que nunca llegan | Alta | Media | 6 | **Crítica** | RI-01, ADR-006 |
| R-02 | Evidencia de modelos, sin prueba de carga real | Media | Alta | 6 | **Crítica** | RI-03 |
| R-05 | 0 reportes perdidos en el celular, sin evidencia | Media | Alta | 6 | **Crítica** | RI-05, ADR-003 |
| R-10 | Ataque Sybil: muchas identidades de dispositivo | Media | Alta | 6 | **Crítica** | RI-10, ADR-008 |
| R-11 | El identificador de dispositivo es un dato personal | Alta | Media | 6 | **Crítica** | RI-11, ADR-008 |
| R-14 | D2 y D4 no tienen iteración propia | Media | Alta | 6 | **Crítica** | Árbol de utilidad |
| R-04 | Umbral del modo pico sin calibrar | Media | Media | 4 | Media | RI-04 |
| R-12 | Un voto por dispositivo subestima varios daños | Media | Media | 4 | Media | RI-12, ADR-008 |
| R-06 | Caídas del servidor de más de 10 min rompen D1 | Baja | Alta | 3 | Media | RI-06 |
| R-13 | El servidor único es un punto único de falla | Baja | Alta | 3 | Media | ADR-001 |
| R-15 | Documentación desactualizada tras separar entrada.py | Alta | Baja | 3 | Media | E5 |
| R-07 | Tiempos de R2 medidos en SQLite y sin ingesta en paralelo | Media | Baja | 2 | Baja | RI-07 |
| R-08 | Tiempo de dibujo del panel no medido | Baja | Media | 2 | Baja | RI-08 |
| R-09 | El filtro del mapa (0,68 s) tiene poco margen | Media | Baja | 2 | Baja | RI-09 |

### Matriz de probabilidad e impacto

![Matriz de probabilidad e impacto](riesgos/matriz-riesgos.svg)

## 3. Riesgos de la zona crítica: mitigación o aceptación

| ID | Respuesta | Mitigación o razón para aceptarlo |
|---|---|---|
| R-03 | **Mitigado** | Se repitió la simulación con 1 núcleo, como el droplet del Lab 06 (iteración 1, sección 9.7). "Antes" ya no cumple D1 ni sin fallas (98,82 %); con T2 se guarda el 100 %, y con una caída de 10 min, el 99,86 %. T1 + T2 no cumple con la caída (99,28 %). La decisión de ADR-006 se mantiene y el rechazo de T1 se refuerza. Queda un margen menor con la caída: se registra en la iteración 1 y se debe usar 1 núcleo como base en la próxima revisión de la evidencia. |
| R-01 | **Mitigado en parte y aceptado** | Mitigación: la PWA muestra cada foto pendiente y la reintenta al abrirse (ADR-003); se mide el porcentaje de fotos recibidas ≤ 24 h después del simulacro. Se acepta el resto porque D1 mide el reporte (datos y ubicación), que es lo que mueve a las brigadas, y sin el modo pico D1 no se cumple. |
| R-02 | **Mitigación planificada** | Prueba de carga sobre el sistema real con Locust, que está escrito en Python y no sale de R-02. Debe repetir la medida de D1 (% de reportes guardados ≤ 15 min) y la de R2 (carga del mapa p95), con 1 vCPU. |
| R-05 | **Mitigación planificada** | La PWA pide almacenamiento persistente al navegador (`navigator.storage.persist()`) y muestra los pendientes hasta que se confirmen (ADR-003). Se prueba en celulares de gama baja con el almacenamiento casi lleno. |
| R-10 | **Aceptado como riesgo residual del MVP** | La única táctica evaluada que lo frena, T12 (código por SMS), rompe el reporte sin señal (RF-01) y cuesta de 13 a 33 veces R-03 por simulacro (ADR-008). Para reducir el daño: aviso por zona cuando muchos dispositivos nuevos reportan una zona tranquila, y verificación del brigadista antes de asignar brigadas a una zona sin otros reportes. |
| R-11 | **Mitigado** | El identificador es seudónimo y no contiene el teléfono ni el nombre. Se incluye en el consentimiento (R-04) y se le aplica el mismo plazo de retención y borrado que a las fotos (escenario S3: 30 días después del cierre del simulacro). |
| R-14 | **Mitigación planificada** | D4 está cubierto en parte por la simulación con una caída de 10 min (iteración 1). La próxima iteración de ADD debe atender D2 (reiniciar la API en ≤ 60 s), porque es lo que protege a D1 de caídas más largas (R-06). |

## 4. Puntos de sensibilidad

| ID | Parámetro | Respuesta afectada | Evidencia |
|---|---|---|---|
| PS-1 | Tamaño de la foto y velocidad de subida | Conexiones simultáneas en el proxy (D1) | Foto de 600 KB: el p95 de "antes" sube de 10 s a 190 s (iteración 1, 9.5) |
| PS-2 | Núcleos del servidor | Si D1 se cumple sin el modo pico | Con 2 núcleos, "antes" cumple; con 1, no (R-03) |
| PS-3 | Umbral de activación del modo pico (70 %) | Cuántas fotos se difieren y cuándo se protege la ingesta | Sin calibrar (R-04) |
| PS-4 | Tope de espera entre reintentos de la PWA (120 s) | Caída tolerable del servidor (≈ 10–12 min) | Caída de 13 min: ni T2 cumple (iteración 1, 9.6) |
| PS-5 | Bajada de la red del coordinador | Carga del mapa con el listado (R2) | 5 Mbps: 5,59 s; 1 Mbps: 26,25 s (iteración 2) |
| PS-6 | Límite por dispositivo (10 en 10 min) | Reportes falsos aceptados y legítimos rechazados (S2) | Con 10, 100 % de legítimos aceptados (iteración 3) |
| PS-7 | IP públicas compartidas por CGNAT | Legítimos aceptados con el límite por IP | 50 IP: 14,82 %; 1 000 IP: 52,87 % (iteración 3) |

## 5. Puntos de trade-off

| ID | Decisión | Atributo que mejora | Atributo que empeora |
|---|---|---|---|
| PT-1 | Modo pico (ADR-006) | Disponibilidad de la ingesta (D1) | Integridad de la priorización sin foto (S2) y usabilidad: el 69 % de las fotos llega tarde o no llega |
| PT-2 | API del mapa agregada por zona (ADR-007) | Rendimiento del mapa (R2: de 13,46 s a 1,00 s) | Detalle de la vista nacional; el filtro deja de ser local (0,68 s) |
| PT-3 | Resumen del worker o caché del mapa (T6 y T7, rechazadas) | CPU del servidor | Frescura de los datos: el retraso sube de 31 s a 46 s |
| PT-4 | Identificador con límite y un voto (ADR-008) | Seguridad frente a reportes falsos (S2) | Precisión de la priorización (un voto por celular) y privacidad (un dato personal más) |
| PT-5 | Código por SMS (T12, rechazada) | Seguridad frente a Sybil | Disponibilidad sin señal (RF-01), costo (R-03), usabilidad y privacidad |

## 6. No riesgos

| ID | Hallazgo | Evidencia |
|---|---|---|
| NR-1 | Los reintentos no duplican reportes | `test_confirmacion_perdida_no_duplica_el_reporte` y `test_servidor_recibe_dos_veces_el_mismo_reporte_y_guarda_uno` |
| NR-2 | Las reglas estructurales de ADR-001 y ADR-005 se cumplen y se vigilan | 4 contratos de import-linter cumplidos; la prueba de mutación hace fallar los 4 |
| NR-3 | La base de datos no es el cuello de botella del mapa | Con T5, 6,7 % de un núcleo para 30 coordinadores (iteración 2) |
| NR-4 | La carga del mapa no depende del volumen de reportes | 40 000 reportes: 1,01 s con T5 (iteración 2) |
| NR-5 | El aviso de un dispositivo atacante llega a tiempo | 4 s frente al límite de 300 s (iteración 3) |
| NR-6 | Mantener el estilo de ADR-001 es suficiente para D1, R2 y S2 | Las tres tácticas aceptadas se implementan dentro de los contenedores existentes (workspace.dsl) |
