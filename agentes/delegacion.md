# Delegación progresiva del agente de SismoReporta (Lab 10, E6)

**Estado actual:** el humano es **revisor**.
- El agente propone y verifica.
- Un integrante aprueba cada edición desde la consola. La respuesta tiene que ser `s` o `n`: cualquier otra se rechaza y se vuelve a preguntar (`agente/aprobacion.py`).
- El Pull Request lo fusiona siempre una persona.

La confianza se gana con evidencia de las trazas, no con el tiempo. Cada etapa amplía los permisos solo si se cumplen los criterios de la anterior. Si después ocurre un incidente, se vuelve a la etapa previa.

## Los cuatro roles

| Etapa (rol del humano) | Qué hace el agente | Permisos del agente (política) | Qué hace el humano | Evidencia de las trazas para pasar a la siguiente etapa |
|---|---|---|---|---|
| **1. Ejecutor** (el humano hace el trabajo) | Solo sugiere: lee el issue y el código y propone un plan o un diff en su respuesta final | Solo lectura: `listar_archivos`, `leer_archivo`, `buscar`, `mapa_repo`; sin `editar_archivo` ni `ejecutar_comando` | Aplica a mano el cambio que decida, ejecuta las pruebas y abre el PR | En **10 issues**, al menos 8 diffs propuestos que, aplicados tal cual, hacen pasar la prueba del issue sin romper otras. 0 propuestas que toquen `tests/` |
| **2. Revisor** (estado actual) | Edita y verifica en el sandbox | Lectura + `editar_archivo` con **aprobación humana de cada edición** + `ejecutar_pruebas` + comandos de la lista permitida; `tests/` protegida; máx. 15 pasos (agente único) o 12 + 8 (ejecutor y revisor) | Aprueba o rechaza cada edición (`s`/`n`) y fusiona el PR | En **20 ejecuciones**: ≥ 90 % de ediciones aprobadas en el primer intento; 0 acciones bloqueadas por intentar tocar `tests/` o salir de la lista de comandos; ≤ 1 decisión rechazada por el contrato por ejecución, en promedio; 0 PR revertidos |
| **3. Colaborador** (el humano decide en los puntos de control) | Edita sin pedir aprobación por edición dentro de un **presupuesto**; pide aprobación solo en los puntos de control | Ediciones libres en `src/modulo` salvo `adaptadores.py`, `entrada.py` y `dispositivos.py`, que tocan datos, red o seguridad; límite de 3 archivos y 60 líneas por issue; revisor de solo lectura obligatorio; las pruebas completas y `lint-imports` deben pasar antes del final | Revisa el diff completo y el veredicto del revisor antes de fusionar | En **30 ejecuciones**: 0 regresiones en la suite completa después de fusionar; el revisor coincide con el humano en ≥ 95 % de los veredictos; ningún cambio fuera del presupuesto. Revisión semestral del equipo |
| **4. Gobernador** (el humano fija las reglas y audita) | Resuelve issues de tipo "error con prueba que lo reproduce" de principio a fin y **abre** el PR | Igual que la etapa 3, más abrir el PR; nunca fusionar en `main` ni cambiar la política, las pruebas, `.importlinter` o los workflows | Define la política y los presupuestos, revisa una muestra de las trazas cada semana y fusiona | Etapa de destino; se vuelve a la 3 ante cualquier regresión en producción, un cambio fuera de la política o un PR revertido |

## Regla para actuar sin aprobación (desde la etapa 3)

El agente puede editar **sin** pedir aprobación solo si se cumplen todas estas condiciones:

1. El issue tiene una prueba que lo reproduce y esa prueba falla antes del cambio.
2. El archivo está en `src/modulo` y no es `adaptadores.py`, `entrada.py` ni `dispositivos.py`.
3. El cambio acumulado del issue es de 3 archivos y 60 líneas como máximo.
4. Ninguna acción anterior de la ejecución fue bloqueada por la política.

Si se rompe una sola de estas condiciones, la política vuelve a pedir aprobación humana (`aprobar_edicion`).

## Dónde estamos con la evidencia actual

Ejecuciones grabadas con Claude Opus 5.5 (detalle en [observacion.md](observacion.md)):

| Criterio de la etapa 2 → 3 | Evidencia actual | ¿Cumple? |
|---|---|---|
| ≥ 20 ejecuciones | 5 ejecuciones completas (issues 1, 2 y 3) | No |
| ≥ 90 % de ediciones aprobadas en el primer intento | 4 de 4 aprobadas en las ejecuciones del 17 al 19/11. La quinta ejecución tiene un rechazo **provocado** para probar el flujo de E6 | Sí, con pocos datos |
| 0 acciones bloqueadas por `tests/` o por comandos | 0 | Sí |
| ≤ 1 decisión rechazada por el contrato por ejecución | 3 en las 4 primeras ejecuciones: 2 por una llave de cierre de más y 1 por dos objetos JSON en la misma respuesta; en los 3 casos el modelo corrigió en el turno siguiente | Sí |
| Ejecuciones que terminan con resumen | 1 ejecutor terminó en `LIMITE_ALCANZADO` (issue 2, multi) | Atención: hace falta más presupuesto o una instrucción de terminar antes |

**Conclusión:** seguimos en la etapa 2 (revisor). La evidencia es buena pero escasa, y la etapa 3 exige al menos 20 ejecuciones.
