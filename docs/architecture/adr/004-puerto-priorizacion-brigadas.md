# ADR-004: Puerto ConsultaZonasAsignadas para eliminar el ciclo entre priorización y brigadas
- Estado: Aceptado
- Fecha: 2026-10-11
- Decisores: Oliva Valdivia David Alexander
## Contexto
El módulo de brigadas necesita las zonas priorizadas para asignar brigadas (RF-04), y el módulo de priorización necesita saber qué zonas ya tienen brigada asignada para calcular bien la prioridad (RF-03). Con llamadas directas, cada módulo depende del otro y se forma un ciclo, lo que incumple la regla de dependencias del diagrama de paquetes.

Un ciclo impide cambiar o probar un módulo sin el otro, y eso afecta la mantenibilidad con un solo desarrollador (R-02) y el plazo de 1 mes (R-01). El ADR-001 exige módulos con límites claros.
## Alternativas consideradas
1. Dependencia directa en ambos sentidos: es lo más rápido de programar, pero mantiene el ciclo y acopla los dos módulos.
2. Puerto definido en priorización e implementado por brigadas: priorización declara la interfaz `ConsultaZonasAsignadas` y brigadas la implementa.
3. Lectura directa de las tablas de brigadas desde priorización: evita el ciclo en el código, pero acopla priorización al esquema interno de otro módulo.
4. Fusionar priorización y brigadas en un solo módulo: elimina el ciclo, pero contradice la división de módulos del ADR-001.
## Decisión
Usaremos el puerto `ConsultaZonasAsignadas`, definido en el módulo de priorización e implementado por `ServicioAsignacion` en el módulo de brigadas. La implementación se conectará al arrancar la aplicación.

El módulo de priorización no importará ninguna clase del módulo de brigadas.
## Consecuencias
- Positivas:
  - El diagrama de paquetes queda sin ciclos y con dependencias en un solo sentido.
  - El módulo de priorización se puede probar con una implementación falsa del puerto, sin el módulo de brigadas.
  - El cálculo de prioridad puede excluir las zonas ya asignadas (RF-03) sin conocer cómo se guardan las asignaciones.
- Negativas / riesgos:
  - Hay una interfaz más que mantener y que conectar al arrancar la aplicación.
  - El flujo es menos evidente al leer el código, porque la llamada pasa por una interfaz.
  - Cada recálculo consulta las asignaciones, lo que añade una consulta a la base de datos y debe caber en el límite de 60 s de QA-02.