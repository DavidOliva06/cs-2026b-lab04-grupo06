# Fitness functions (Lab 08, E5)

Se ejecutan en cada Pull Request con [.github/workflows/fitness.yml](../../.github/workflows/fitness.yml): primero `lint-imports` (estructurales) y después `pytest` (de calidad y el resto de la suite).

```bash
# desde la raíz del repositorio
PYTHONPATH=src:src/modulo lint-imports
python -m pytest -v
```

## 1. Estructurales (E5.1): contratos de import-linter

Archivo: [.importlinter](../../.importlinter).

| Contrato | Regla | ADR | Degradación que detecta |
|---|---|---|---|
| `adr001-ingesta-sin-ia` | La ingesta (entrada, servicio, fábrica, adaptadores, decoradores, puertos, modelo, estados, eventos y observadores) no importa `modulo.ia` | ADR-001 | Que la ingesta llame al LLM y quede expuesta a su latencia y sus fallas (D1) |
| `adr001-ia-aislada` | `modulo.ia` no importa ningún módulo del flujo de reportes | ADR-001 | Que el componente de IA deje de ser reemplazable (M3) |
| `adr005-capas` | entrada > servicio y observadores > fábrica > adaptadores y decoradores > puertos, estados y eventos > modelo | ADR-005 | Dependencias hacia arriba, que vuelven a acoplar el dominio con la infraestructura |
| `adr005-servicio-sin-infraestructura` | El servicio, el dominio y los puertos de IA no importan `externos`, `modulo.adaptadores` ni `modulo.ia.adaptador_llm` | ADR-005 | Que el servicio vuelva a conocer IndexedDB, HTTP o PostgreSQL (el olor principal del Lab 07) |

Estado en `v0.8-arquitectura`: **4 kept, 0 broken.**

## 2. Prueba de la violación (E5.2)

En la rama `prueba-violacion-fitness` se agregaron dos imports prohibidos (commit `3fd719e`) y después se revirtieron (commit `117b86b`). La rama se fusionó con `--no-ff` para que las dos operaciones queden en el historial.

```diff
# src/modulo/servicio.py
+from .adaptadores import AdaptadorIndexedDB  # VIOLACIÓN DE PRUEBA: el servicio conoce un adaptador (ADR-005)
# src/modulo/entrada.py
+from .ia.puerto import ClasificadorDanos  # VIOLACIÓN DE PRUEBA: la ingesta llama a la IA (ADR-001)
```

Salida de `lint-imports` sobre `3fd719e` (código de salida 1, así que el workflow queda en rojo):

```text
ADR-001: la ingesta solo valida, guarda y responde; no llama al clasificador de IA BROKEN
ADR-001: el componente de IA es un módulo con límites propios; no depende del flujo de reportes KEPT
ADR-005: las dependencias van en un solo sentido (entrada > servicio y observadores > fábrica > adaptadores y decoradores > puertos > modelo) KEPT
ADR-005: el servicio y el dominio dependen de puertos, no de adaptadores ni de servicios externos BROKEN

Contracts: 2 kept, 2 broken.

modulo.entrada is not allowed to import modulo.ia:
-   modulo.entrada -> modulo.ia.puerto (l.15)

modulo.servicio is not allowed to import modulo.adaptadores:
-   modulo.servicio -> modulo.adaptadores (l.21)
```

El contrato de capas sigue cumplido con esta violación porque `servicio → adaptadores` va hacia abajo; por eso existe el contrato `adr005-servicio-sin-infraestructura`, que sí la detecta. Sobre `117b86b` (revertido): `Contracts: 4 kept, 0 broken.`

## 3. De calidad (E5.3): escenarios convertidos en pruebas

Archivo: [tests/test_fitness.py](../../tests/test_fitness.py). Cada prueba usa el presupuesto de [escenarios.md](utilidad/escenarios.md) y comprueba además que la versión sin la táctica **no** cumple.

| Prueba | Escenario | Presupuesto | Evidencia que ejecuta |
|---|---|---|---|
| `test_d1_modo_pico_guarda_99_5_por_ciento_en_15_min_sin_duplicados` | D1 (ADR-006) | ≥ 99,5 % guardados ≤ 15 min; 0 duplicados | `fitness/simulacion_d1.py`, peor caso: 1 núcleo y caída de 10 min (2 réplicas) |
| `test_d1_sin_modo_pico_no_cumple` | D1 | — | La misma simulación sin T2 |
| `test_r2_mapa_agrupado_por_zona_cumple_el_presupuesto_de_p95` | R2 (ADR-007) | Carga p95 ≤ 3 s; filtro p95 ≤ 1 s; retraso ≤ 60 s | `fitness/prototipo_r2.py`: consultas reales sobre 20 000 reportes, medidas en el runner |
| `test_r2_listado_de_reportes_no_cumple` | R2 | — | El mismo prototipo con el listado |
| `test_s2_limite_y_voto_por_dispositivo_cumplen_el_escenario` | S2 (ADR-008) | ≤ 10 aceptados por dispositivo; 0 zonas alteradas; ≥ 99,5 % legítimos; aviso ≤ 300 s | `fitness/simulacion_s2.py` (3 réplicas) |
| `test_s2_sin_control_o_con_limite_por_ip_no_cumple` (2) | S2 | — | La misma simulación con T10 y sin control |
| `test_ingesta_no_pierde_ni_duplica_reportes_con_respuestas_perdidas` | 0 operaciones perdidas (D1, criterio 3 de HU-01) | 50 de 50 reportes enviados y 50 filas en el servidor | Código real de `src/modulo/entrada.py` con señal intermitente y 30 % de respuestas perdidas |

Resultado: 8 pasan en ≈ 5 s. La suite completa: 99 ejecuciones.

### Mutaciones: cada fitness function de calidad falla si se quita su táctica

| Mutación en una copia | Pruebas de `test_fitness.py` que fallan |
|---|---|
| Quitar `ON CONFLICT (id) DO NOTHING` en `AdaptadorPostgres` | 1 (`test_ingesta_no_pierde_ni_duplica_...`) |
| Quitar el modo pico (`DECISION = "Antes"`) | 1 (`test_d1_modo_pico_...`) |
| Volver al listado de reportes en el mapa | 1 (`test_r2_mapa_agrupado_...`) |
| Límite por dispositivo de 50 en lugar de 10 | 1 (`test_s2_limite_y_voto_...`) |

## 4. Limitaciones

- D1 y S2 prueban **modelos** de la arquitectura, no el sistema desplegado: fallan si alguien cambia la táctica o los supuestos del modelo, no si el servidor real se degrada. La prueba de carga real sigue planificada (riesgo R-02 de [atam-lite.md](atam-lite.md)).
- R2 mide tiempos en el runner de GitHub con SQLite: el presupuesto tiene margen (≈ 1 s frente a 3 s), pero un runner muy lento podría dar un falso negativo.
