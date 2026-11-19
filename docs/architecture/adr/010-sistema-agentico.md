# ADR-010: Arquitectura del sistema agéntico para resolver issues
- Estado: Aceptado
- Fecha: 2026-11-19
- Decisores: Oliva Valdivia David Alexander

## Contexto
Queremos que un agente de IA resuelva issues del propio repositorio de SismoReporta. Un issue trae una prueba que lo reproduce y se considera resuelto cuando esa prueba pasa sin modificar las pruebas (definición de SWE-bench).

Los 3 issues del Lab 10 ([issues/](../../../issues)) tocan módulos distintos:
- la entrada (validación de coordenadas);
- un adaptador (deduplicación);
- el dominio (priorización de zonas).

Las condiciones que pesan en la decisión:
- **Lo que no se puede negociar:** la arquitectura de ADR-001 y ADR-005, que se verifica con `lint-imports`, y las pruebas, que el agente no debe poder "arreglar".
- **Cómo funciona el modelo:** es un asistente sin clave de API (Claude Opus 5.5 en Claude.ai, con `ModeloInteractivo`), así que cada decisión cuesta una acción humana de copiar y pegar.
- **Cómo debe verificarse:** cada ejecución se reproduce en CI con `ModeloGrabado`.

El diseño completo está en [agentes/diseno/lienzo.md](../../../agentes/diseno/lienzo.md).

## Alternativas consideradas
1. **Flujo fijo (sin agente):** un prompt por issue con el archivo ya elegido. Es más barato, pero exige saber de antemano dónde está el error.
2. **Agente único ReAct**, que lee, edita y verifica.
3. **Gestor + actor-crítico:** un planificador sin herramientas, un ejecutor y un revisor de solo lectura, con máximo 2 rondas.
4. **Coordinación democrática:** tres revisores (corrección, diseño y seguridad) que votan.
5. **Agente autónomo** que fusiona su propio PR.

## Decisión
**Arquetipo.** Usaremos un **agente único ReAct** (alternativa 2) como configuración por defecto.
- El orquestador **gestor + actor-crítico** (alternativa 3) queda disponible, en `agentes/orquestador.py --variante multi`, solo para cambios en archivos de riesgo: `adaptadores.py`, `entrada.py` y `dispositivos.py`.

**Herramientas.** El agente tiene:
- las de lectura: `listar_archivos`, `leer_archivo`, `buscar` y `mapa_repo`;
- `ejecutar_pruebas` con una ruta opcional;
- `editar_archivo`, que exige que el fragmento aparezca exactamente una vez;
- `ver_cambios`;
- `ejecutar_comando`, solo con la lista permitida: pytest, radon, lint-imports, git status y git diff. Se bloquea cualquier comando con `; & | $ ` < >`.

**Memoria.** La de corto plazo (el historial) y una pizarra de notas (`notas.md`) en el sandbox. No hay memoria entre issues.

**Límites.**
- Contrato JSON en cada decisión.
- Política por rol: el revisor y el planificador no editan, y `tests/` está protegida con la ruta normalizada.
- Máximo 15 pasos para el agente único y 12 + 8 para el ejecutor y el revisor, con máximo 2 rondas.
- Sandbox en una copia del repositorio, que es su propio repositorio git, en `agentes/trabajo`.

**Rol humano.** Revisor: aprueba cada edición con `s` o `n` y fusiona el PR. La hoja de ruta hacia colaborador y gobernador está en [agentes/delegacion.md](../../../agentes/delegacion.md).

## Evidencia
Métricas en [agentes/observacion.md](../../../agentes/observacion.md):
- Los 3 issues se resolvieron con el agente único: las 12 pruebas de los issues pasan y la suite completa queda en verde después de aplicar los 3 cambios.
- En el issue 2, la variante actor-crítico llegó al mismo resultado con 2,5 veces más contexto: 43 491 caracteres frente a 17 138.
  - Su ejecutor agotó el presupuesto de 12 pasos sin resumen.
  - El revisor no encontró nada que el agente único hubiera pasado por alto.
- Lo que sí detectó errores fue lo determinista:
  - **El contrato:** 4 respuestas mal formadas.
  - **Las pruebas de E3:** 2 errores del framework.
  - **El primer intento multi:** expuso el `git diff` vacío del sandbox.

## Alternativas descartadas
- **Flujo fijo:** sirve para tareas de pasos conocidos, como la clasificación de prioridad del Lab 09, pero no cuando hay que localizar la causa.
- **Coordinación democrática:** triplica el costo del revisor sin evidencia de que un solo revisor se haya equivocado.
- **Agente autónomo:** no hay trazas suficientes para delegar la fusión (etapa 4 de `delegacion.md`); además, el error de las pruebas lo cometería sin que nadie lo viera.

## Consecuencias
**Positivas:**
- Cada ejecución es reproducible en CI (trayectorias y aprobaciones grabadas) y auditable (traza JSONL, diagrama de secuencia y métricas).
- El agente no puede tocar las pruebas, salir del sandbox ni encadenar comandos.
- El humano ve cada cambio antes de que ocurra.

**Negativas y riesgos:**
- Con `ModeloInteractivo`, cada paso cuesta una acción humana: entre 10 y 15 por issue con el agente único y alrededor de 21 con el multi.
- La aprobación por edición no escala más allá de la etapa 2.
- La lista de comandos y el detector de rutas son defensas sintácticas.
- Un issue malicioso con instrucciones escondidas sigue siendo un riesgo, mitigado por el sandbox, el revisor humano y la regla de que el contenido de los archivos es dato.
- El presupuesto de pasos del ejecutor (12) resultó justo: hay que subirlo o pedirle que termine apenas verifique.
- `mapa_repo` y las notas no se usaron en estos issues, que nombran el archivo; se mantienen para issues sin ubicación.
- ADR-009 no existe: el Lab 09 no tuvo decisiones de arquitectura, y la numeración sigue a la guía.
