# Lienzo de diseño del sistema agéntico (Lab 10, E1)

**Caso:** SismoReporta AQP.

**Objetivo del sistema:** resolver issues del propio repositorio. Cada issue trae una prueba en rojo, y el issue se da por resuelto cuando esa prueba pasa sin haber modificado las pruebas (la definición de SWE-bench).

**Issues para el agente:**

| Issue | Problema | Módulo | Origen |
|---|---|---|---|
| [ISSUE-01](../../issues/ISSUE-01.md) | La ingesta acepta coordenadas fuera de Arequipa | `entrada.py` | Error real |
| [ISSUE-02](../../issues/ISSUE-02.md) | Reportes duplicados al sincronizar con el almacén en memoria | `adaptadores.py` | Sembrado |
| [ISSUE-03](../../issues/ISSUE-03.md) | Prioridad errónea de una zona con reportes sin foto | `priorizacion.py` | Sembrado |

## Las 7 decisiones

| # | Decisión de diseño | Elección para SismoReporta | Justificación (sección de la guía) |
|---|---|---|---|
| 1 | ¿Agente o flujo de trabajo? | **Agente** para resolver los 3 issues | La causa no se conoce de antemano: hay que leer el issue, ejecutar la prueba, localizar el código y verificar. Los pasos dependen de lo que se observa (1.1). |
| 2 | Arquetipo | **Planificador-ejecutor + ReAct** | El planificador escribe un plan corto y legible antes de tocar el código, y el ejecutor explora con ReAct porque no sabe en qué archivo está el error. La alternativa de **reflexión** solo se justificaría en cambios de alto riesgo; aquí la cubre el revisor (1.3). |
| 3 | Herramientas | `listar_archivos`, `leer_archivo`, `buscar`, `ejecutar_pruebas`, `editar_archivo`, `ver_cambios` y `ejecutar_comando` con lista permitida (pytest, radon, lint-imports, git status y diff). En E4 se agregan `mapa_repo` y las notas. | Lo mínimo para leer, cambiar y verificar. `editar_archivo` exige que el fragmento aparezca exactamente una vez, y `lint-imports` deja verificar que el cambio respeta ADR-001 y ADR-005 (1.5). |
| 4 | Memoria | **Corto plazo** (historial de la tarea) y, desde E4, **notas** (`notas.md`) | Cada issue es corto y no depende de ejecuciones anteriores. Las notas guardan hipótesis y archivos revisados para no releer código (1.6). La memoria procedimental es la propia política del agente; no se usa memoria episódica entre issues. |
| 5 | Coordinación | **Por gestor** (el planificador) + **actor-crítico** (ejecutor y revisor de solo lectura), con máximo 2 rondas | Se separa quién cambia el código de quién lo revisa. Por parsimonia, en E5 se compara con un agente único: si el revisor no encuentra nada que el agente único haya pasado por alto, el costo extra no se justifica (1.7). |
| 6 | Rol humano | **Revisor:** aprueba cada edición (E6) y el Pull Request | Es el primer uso del sistema y la confianza aún es baja. El agente nunca fusiona su propio cambio. La hoja de ruta hacia colaborador y gobernador está en `delegacion.md` (1.8). |
| 7 | Control | Contrato JSON en cada decisión; política por rol (el revisor solo lee; `tests/` está protegida); máximo 12 pasos para el ejecutor y 8 para el revisor; máximo 2 rondas; sandbox en una copia del repositorio | Evita acciones indebidas, bucles y costos sin límite. Además impide que el agente "arregle" las pruebas para que pasen (1.4 y Figura 7). |

## ¿Qué tareas de SismoReporta van mejor con un flujo fijo?

| Tarea | Por qué no necesita un agente |
|---|---|
| Clasificar la prioridad de un reporte ciudadano (Tarea B del Lab 09) | Una entrada, una salida y una política conocida. Basta un prompt validado con esquema: es un arquetipo **reflexivo** dentro de un flujo fijo. Un agente solo agregaría costo y superficie de ataque, porque el texto del reporte lo escribe cualquier ciudadano. |
| Sincronizar los reportes pendientes del celular | Los pasos son siempre los mismos (leer pendientes, enviar, marcar enviado) y deben ser deterministas y verificables. |
| Calcular el puntaje de las zonas (RF-03) | Es una fórmula (suma de pesos con un voto por dispositivo). Un LLM no debe decidirla en cada ejecución. |
