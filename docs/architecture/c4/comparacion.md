# Secuencia UML frente a vista dinámica C4

La secuencia UML (`secuencia-reporte.puml`) muestra lo que la vista dinámica omite: la rama de error por consentimiento no aceptado (`alt`), el ciclo por cada reporte pendiente (`loop`), la condición de confirmación (`opt`), los mensajes de retorno y las clases internas de la PWA (`ControladorReportes`, `ServicioReportes`, `AlmacenLocalReportes`) con las operaciones y parámetros exactos que se invocan.
La vista dinámica `SincronizarReporte` solo numera los pasos del camino feliz entre contenedores y componentes, pero deja ver a qué almacenes llega el reporte (PostgreSQL y el disco de fotos) y que el trabajo se encola en la misma transacción.
La secuencia sirve a los desarrolladores que implementan y prueban la HU-01, porque cada mensaje corresponde a una operación del diagrama de clases.
La vista dinámica sirve a arquitectos, operadores y nuevos integrantes del equipo, que necesitan entender qué partes del sistema recorre el flujo sin entrar al código.

# Escritura a mano frente a modelo exportado

Se comparan `contexto-manual.puml`, escrito a mano con las macros de C4-PlantUML, y `export/structurizr-Contexto.puml`, generado desde `workspace.dsl` con Structurizr CLI. Los dos muestran el mismo diagrama de contexto.

## Errores encontrados

- **A mano:** PlantUML dibuja lo que recibe sin comprobar el modelo. En una prueba se cambió `Rel(sismo, teselas, ...)` por `Rel(sismo, tesela, ...)`. PlantUML terminó sin error y dibujó un círculo suelto llamado "tesela", mientras el sistema de teselas quedaba sin relaciones. Nada comprueba que el diagrama coincida con `workspace.dsl`, así que esa coincidencia se revisó a mano, relación por relación.
- **Modelo exportado:** Structurizr valida el modelo antes de dibujar. El mismo error en `workspace.dsl` (`sismo.pwa -> tesela`) se detiene con `The destination element "tesela" does not exist at line 52`. Además, la vista dinámica solo acepta pasos sobre relaciones que ya existen en el modelo. Por su parte, `structurizr inspect` señaló lo que falta: el alcance del workspace, la documentación, las decisiones y la tecnología del proxy inverso.
- **Defectos del exportador:** la exportación tiene problemas de presentación. El estilo "Externo" se pierde, y el servicio de teselas sale azul como el sistema propio, mientras que en la versión manual `System_Ext` lo muestra gris. Los títulos salen en inglés ("System Context View: ..."). Los alias se generan a partir de los nombres, como `SismoReportaAQP.Aplicaciónwebprogresiva`.
- **En ambos enfoques:** los íconos de la leyenda se ven como cuadros vacíos, porque PlantUML no encuentra esa fuente en Windows.

## Si mañana cambia el nombre de un contenedor

Se probó en una copia del workspace cambiando el nombre `"API"` por `"Servidor de aplicaciones"`.

- **Modelo:** solo cambia una línea. Las relaciones, las vistas y el despliegue usan el identificador `sismo.api`, que se mantiene, así que la validación pasa y basta volver a exportar para actualizar las cinco vistas y los PNG. Sin embargo, los alias exportados se forman con el nombre, por lo que el cambio se extiende a los `.puml` generados:

  | Vista | Líneas que cambian |
  |---|---|
  | Contexto | 0 |
  | Contenedores | 4 |
  | Despliegue | 4 |
  | SincronizarReporte | 9 |
  | Componentes | 25 (`SismoReportaAQP.API.Reportes` pasa a `SismoReportaAQP.Servidordeaplicaciones.Reportes`) |

  Por eso los archivos de `export/` nunca se editan a mano, ya que cualquier cambio se pierde en la siguiente exportación. El texto libre que menciona el nombre tampoco se actualiza solo, como la descripción "Componentes del contenedor API" de la vista de componentes o los comentarios del workspace.
- **A mano:** `contexto-manual.puml` no cambia, porque el diagrama de contexto no muestra contenedores. Si las vistas de contenedores, componentes, despliegue y dinámica también se escribieran a mano, habría que buscar el nombre en cada archivo (`Container(...)`, `Container_Boundary(...)` y los nodos de despliegue) y cambiarlo uno por uno. PlantUML no avisa si queda alguno sin cambiar. Si además se cambia el alias y queda un `Rel` con el alias anterior, aparece el mismo elemento suelto de la prueba de errores.

En resumen, escribir a mano da control sobre la presentación de un diagrama aislado: colores, títulos en español y forma de los elementos. El modelo exportado conviene cuando hay varias vistas del mismo sistema, porque es la única fuente que se valida y un cambio de nombre se hace en un solo lugar.