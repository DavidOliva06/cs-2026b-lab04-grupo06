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

## Estado de las correcciones

Los hallazgos están reportados, pero ninguno se ha corregido todavía en los diagramas.