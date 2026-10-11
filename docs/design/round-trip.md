# Round-trip: diagrama de diseño vs. diagrama generado desde el código

- Fecha: 2026-10-11
- Diagrama de diseño: `clases.puml` (escrito a mano, fuente de verdad del diseño)
- Diagrama generado: `classes_en.puml` (ingeniería inversa de `reportes.py`)

## Diferencias encontradas

| # | Diferencia | Causa | Acción tomada |
|---|---|---|---|
| 1 | El diagrama generado tiene tres clases que no existen en el diseño: `AdaptadorAlmacenLocalReportes`, `AdaptadorAlmacenServidorReportes` y `AdaptadorEnvioReportes`. | Se añadieron al escribir el código, porque el esqueleto exigía adaptadores que lanzaran `NotImplementedError`. El diseño solo llegaba hasta los puertos. | Se actualiza `clases.puml`: se agregan los tres adaptadores con una relación de realización (`..|>`) hacia su puerto. |
| 2 | Los tres puertos aparecen como `class` en el generado, sin el estereotipo `<<puerto>>`; en el diseño son `interface`. | Python no tiene interfaces: un puerto es una clase que hereda de `ABC`, y la herramienta la dibuja como clase normal. | Se mantiene el diseño. No se cambia el código, porque `ABC` con `@abstractmethod` es la forma correcta de expresar una interfaz en Python. |
| 3 | `EstadoReporte` aparece como clase con un solo atributo `name`; en el diseño es una enumeración con seis valores. | La herramienta no reconoce `Enum` y no lista sus valores. El atributo `name` es el que el código lee del estado en el mensaje de error de las transiciones. | Se mantiene el diseño. Se comprobó a mano que los seis valores de `reportes.py` coinciden con los de `clases.puml`. |
| 4 | Se pierden las multiplicidades y la composición: todas las relaciones del generado son flechas simples (`-->`), frente a `"1" *-- "1"` y `"0..*"` del diseño. | Python no distingue composición de asociación ni declara multiplicidades; la herramienta solo ve atributos con un tipo. | Se mantiene el diseño. En el código las multiplicidades quedan como comentarios y como tipos (`list[Reporte]` para `0..*`, `datetime \| None` para `0..1`). |
| 5 | Faltan las tres dependencias de uso del diseño: `ServicioReportes ..> Ciudadano`, `ServicioReportes ..> Reporte` y `ServicioIngesta ..> Reporte`. | Son usos por parámetro o valor de retorno, y la herramienta solo dibuja herencia y atributos. | Se mantiene el diseño. Las dependencias existen en el código, en las firmas de `crear_reporte` y `recibir`. |
| 6 | Operaciones de clases concretas aparecen como `{abstract}` en el generado (por ejemplo `puede_reportar`, `aceptar`, `crear_reporte`, `recibir`); en el diseño son operaciones normales. | La herramienta marca como abstracto todo método que lanza `NotImplementedError`. Las operaciones de `Reporte` no llevan la marca porque sí están implementadas. | Ninguna sobre el diseño. La marca desaparecerá al implementar cada operación, y sirve como lista de lo pendiente. |
| 7 | El generado muestra atributos que el diseño no tiene: `consentimiento`, `reportes`, `ciudadano`, `foto`, `ubicacion`, `estado`, `almacen_local`, `puerto_envio` y `almacen_servidor`. | Son las asociaciones del diseño convertidas en atributos. El diseño las dibujaba sin nombre de rol, así que el nombre se eligió al programar. | Se actualiza `clases.puml`: se añade el nombre de rol a cada asociación para que coincida con el código. |
| 8 | Los nombres y tipos difieren: `puedeReportar(): Boolean` frente a `puede_reportar() -> bool`, y `Double`, `String`, `DateTime`, `Byte[]`, `List<Reporte>` frente a `float`, `str`, `datetime`, `bytes`, `list[Reporte]`. | El código sigue la convención `snake_case` de Python y usa sus tipos nativos; el diseño usa nombres y tipos genéricos de UML. | Ninguna. Es una traducción uno a uno y no cambia el modelo. |
| 9 | El generado no muestra visibilidad; el diseño marca los atributos como privados (`-`) y las operaciones como públicas (`+`). | Python no tiene modificadores de acceso y los campos de un `dataclass` son públicos. | Se acepta la diferencia. La visibilidad del diseño queda como intención, no como restricción del lenguaje. |

## Conclusión

El código respeta el diseño: no falta ninguna clase, atributo ni operación de `clases.puml`. De las nueve diferencias, siete se deben a límites de Python o de la herramienta y no requieren cambios. Las otras dos (1 y 7) son decisiones tomadas al programar que el diseño no recogía, y se corrigen actualizando `clases.puml`.