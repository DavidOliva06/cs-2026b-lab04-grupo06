# Revisión de consistencia entre diagramas

- Fecha: 2026-10-11
- Diagramas revisados: `clases.puml`, `secuencia-reporte.puml`, `estado-estadoReporte.mmd`, `actividades-brigada.puml`, `paquetes.puml`

## Reglas verificadas

| Regla | Descripción | Resultado |
|---|---|---|
| C1 | Cada mensaje de secuencia es una operación de la clase receptora | 4 hallazgos |
| C2 | Cada transición de estados corresponde a una operación de la clase | 3 hallazgos |
| C3 | Multiplicidades coherentes con los criterios de aceptación | 2 hallazgos |
| C4 | Paquetes sin ciclos | Se cumple, con 2 observaciones |
| C5 | Nombres consistentes | 6 hallazgos |

La mayoría de los hallazgos tiene una misma causa: el diagrama de secuencia no se actualizó cuando la enumeración `EstadoReporte` pasó de dos a seis valores.

## Hallazgos

| Regla | Elemento | Problema | Corrección sugerida |
|---|---|---|---|
| C1 | `secuencia-reporte.puml:55` `marcarEnviado(fecha)` | `Reporte` no tiene esa operación; la que existe es `marcarRecibido(fecha)` (`clases.puml:34`). | Renombrar el mensaje a `marcarRecibido(fecha)`. |
| C1 | `secuencia-reporte.puml:24-26` | El reporte se crea y se guarda sin llamar a `encolar()`, así que queda en `BORRADOR` y la búsqueda de la línea 43 nunca lo encontraría. | Agregar el mensaje `SVC -> REP: encolar()` entre la creación y `guardar(reporte)`. |
| C1 | `secuencia-reporte.puml:18` y `:41` `enviarReporte()`, `alRecuperarConexion()` | La receptora `ControladorReportes` no existe en `clases.puml`. | Agregar la clase `ControladorReportes` con esas dos operaciones. |
| C1 | `secuencia-reporte.puml:29`, `:33` y `:63` `mostrarEstado()`, `mostrarConsentimiento()` | La receptora `FormularioReporte` no existe en `clases.puml`. | Agregar la clase `FormularioReporte` con esas dos operaciones. |
| C2 | `estado-estadoReporte.mmd:10` `recibir()` | Es una operación de `ServicioIngesta` (`clases.puml:61`), no de `Reporte`. | Etiquetar la transición con `marcarRecibido()` (`clases.puml:34`). |
| C2 | `estado-estadoReporte.mmd:9` `enviar()` | Es una operación de `PuertoEnvioReportes` (`clases.puml:80`), y `Reporte` no tiene ninguna para un envío fallido. | Quitar la autotransición, o dejarla como evento externo sin paréntesis y aclararlo en un comentario. |
| C2 | `estado-estadoReporte.mmd:5` `crearReporte()` | Es una operación de `ServicioReportes` (`clases.puml:54`), no de `Reporte`. | Etiquetarla como la creación del objeto (`<<create>>`), igual que en `secuencia-reporte.puml:24`. |
| C3 | `secuencia-reporte.puml:24` frente a `clases.puml:84` | El reporte se crea sin ciudadano, pero la multiplicidad exige exactamente un `Ciudadano` por `Reporte`. | Pasar el ciudadano en la creación: `Reporte(id, ciudadano, foto, ubicacion)`. |
| C3 | `clases.puml:29` `id: UUID` | El criterio 3 exige que el servidor conserve un solo reporte por reenvío, pero el diagrama no declara que el `id` sea único. | Marcar el atributo como `{unique}` o `{id}`. |
| C4 | `paquetes.puml:40-54` | Sin ciclos. El orden compartido, reportes, priorización y luego brigadas y mapa respeta todas las flechas, incluida la realización de la línea 54. | Ninguna. |
| C4 | `paquetes.puml:59` frente a `:41`, `:42`, `:45`, `:46` | La nota describe una cadena estricta, pero mapa y brigadas también dependen directamente de reportes y compartido. No hay ciclo, solo un texto impreciso. | Reformular la regla 1: "un módulo solo depende de los que están por debajo de él". |
| C4 | `paquetes.puml:45` frente a `:61` | Brigadas modifica la entidad `Reporte` de otro módulo, lo que roza la regla 3 de la propia nota. No hay ciclo, pero sí acoplamiento fuerte. | Exponer en reportes un puerto con `verificar`, `rechazar` y `marcarAtendido` por id de reporte. |
| C5 | `secuencia-reporte.puml:29` y `:43` `PENDIENTE_DE_ENVIO` | Ese valor no existe en `EstadoReporte`; el equivalente es `ENCOLADO` (`clases.puml:6`). | Reemplazar por `ENCOLADO` en ambas líneas. |
| C5 | `secuencia-reporte.puml:63` `ENVIADO` | Ese valor no existe en `EstadoReporte`; el equivalente es `RECIBIDO` (`clases.puml:7`). | Reemplazar por `RECIBIDO`. Los textos para el ciudadano de las líneas 30 y 64 pueden quedarse. |
| C5 | `paquetes.puml:10-38` frente a `clases.puml:13`, `:19` y `:41` | `Ciudadano`, `Consentimiento` y `Foto` no están en ningún paquete, aunque `Reporte` los usa en el servidor. | Ubicarlos en reportes, o declarar en el comentario de las líneas 4-8 que quedan fuera. |
| C5 | `actividades-brigada.puml:41` frente a `clases.puml:9` | "Atendido" nombra el estado de la asignación y también el de `Reporte`, que son entidades distintas. | Renombrar el estado de la asignación, por ejemplo a "Finalizada". |
| C5 | `actividades-brigada.puml:28` y `:41` frente a `paquetes.puml:32` | La asignación tiene estados ("En camino", "Atendido"), pero la clase `Asignacion` no tiene enumeración ni operaciones que los respalden. | Agregar una enumeración `EstadoAsignacion` y sus operaciones a `Asignacion`. |
| C5 | `estado-estadoReporte.mmd:5-18` frente a `clases.puml:5-10` | Los estados van como `Borrador`, `Encolado` y la enumeración como `BORRADOR`, `ENCOLADO`, pese a que la línea 3 afirma que coinciden. | Unificar la escritura, o precisar en la línea 3 que solo cambia el uso de mayúsculas. |

## Hallazgo fuera de las cinco reglas

En `secuencia-reporte.puml:17-20` la foto y la ubicación ya viajan en el mensaje antes de comprobar el consentimiento, pero el criterio 4 de la historia dice que sin consentimiento no se capturan. La comprobación debería ocurrir antes de la captura.

## Verificación de los hallazgos

Cada hallazgo se contrastó con los diagramas, la historia y los drivers. Siete no se sostienen:

| Regla | Hallazgo de la IA | Verificación |
|---|---|---|
| C3 | `id` de `Reporte` sin `{unique}` (`clases.puml:29`). | Falso positivo: la unicidad no es una multiplicidad, y el criterio 3 ya se cubre con `guardarSiNoExiste()`. |
| C4 | La nota de `paquetes.puml:59` describe una cadena estricta. | Falso positivo: la cadena describe el orden de las capas y las dependencias directas lo respetan. |
| C4 | Brigadas usa la entidad `Reporte` de otro módulo (`paquetes.puml:45`). | Falso positivo: la regla 3 permite usar clases públicas y `Reporte` lo es. |
| C5 | Renombrar "Atendido" de la asignación a "Finalizada" (`actividades-brigada.puml:41`). | Falso positivo: el nombre viene de RF-05 ("en camino, atendido"); renombrarlo rompería la trazabilidad con los drivers. |
| C5 | `Borrador` frente a `BORRADOR` entre estados y enumeración. | Falso positivo: es el mismo nombre con la convención de cada notación. |
| C5 | `Ciudadano`, `Consentimiento` y `Foto` fuera de los paquetes. | Falso positivo: un diagrama de paquetes no lista todas las clases y el alcance está declarado en su comentario. |
| C2 | `crearReporte()` en la transición inicial (`estado-estadoReporte.mmd:5`). | Discutible: es habitual etiquetar la transición inicial con el evento que crea el objeto. Se mantiene. |

Otros tres hallazgos son reales pero estaban en la regla equivocada (falta de `encolar()`, reporte creado sin ciudadano y estados de `Asignacion`).

## Estado de las correcciones

Aplicadas en la rama `lab05-correcciones` (etiqueta `v0.5.1-diseno`) y comprobadas con `docs/design/verificar_c1.py`, que pasó de 6 mensajes sin operación a 0:

- C1: `marcarEnviado(fecha)` pasa a `marcarRecibido(fecha)`, y se agrega `encolar()` después de crear el reporte.
- C1: `ControladorReportes` y `FormularioReporte` se agregan a `clases.puml` con sus operaciones.
- C5: `PENDIENTE_DE_ENVIO` y `ENVIADO` pasan a `ENCOLADO` y `RECIBIDO`.
- C3: el reporte se crea con su ciudadano: `Reporte(id, ciudadano, foto, ubicacion)`.

Pendientes:

- C2: `recibir()` y `enviar()` en el diagrama de estados no son operaciones de `Reporte`.
- Fuera de las reglas: la foto y la ubicación viajan antes de comprobar el consentimiento (criterio 4).
