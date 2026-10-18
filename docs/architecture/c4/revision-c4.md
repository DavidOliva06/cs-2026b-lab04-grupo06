# Revisión C4 - SismoReporta AQP

- Fecha: 2026-10-17
- Archivo revisado: `workspace.dsl` (validado con Structurizr CLI sin errores)
- Vistas: Contexto (línea 135), Contenedores (línea 140), Componentes (línea 145), SincronizarReporte (dinámica, línea 153) y Despliegue (línea 163)
- Método: los conteos de elementos y relaciones sin descripción o sin tecnología salen de un script sobre el modelo exportado a JSON; el resto, de la lectura del DSL.

## Lista de revisión (Tabla 3)

| Grupo | Pregunta | Contexto | Contenedores | Componentes | Dinámica | Despliegue | Evidencia |
|---|---|---|---|---|---|---|---|
| General | ¿Tiene título? | No | No | No | No | No | Ninguna vista declara `title`; solo tienen clave y descripción (líneas 135, 140, 145, 153 y 163). |
| General | ¿Se entiende el tipo de diagrama y su alcance? | Sí | Sí | Sí | Sí | Sí | El tipo lo fija la palabra clave (`systemContext`, `container`, `component`, `dynamic`, `deployment`) y el alcance, el elemento indicado: `sismo`, `sismo.api` o el entorno "Producción". La descripción de cada vista lo repite. |
| General | ¿Tiene leyenda? | Sí | Sí | Sí | Sí | Sí | Structurizr genera la leyenda (diagram key) a partir del bloque `styles` (líneas 170-201). Si una imagen se exporta para usarla fuera de Structurizr, la leyenda debe exportarse junto a ella. |
| Elementos | ¿Cada elemento tiene nombre? | Sí | Sí | Sí | Sí | Sí | Todos los elementos se declaran con nombre entre comillas. |
| Elementos | ¿Cada elemento indica su tipo? | Sí | Sí | Sí | Sí | Sí | Cada elemento se declara como `person`, `softwareSystem`, `container`, `component`, `deploymentNode` o `infrastructureNode`, y Structurizr rotula el tipo en la caja. |
| Elementos | ¿Cada elemento describe lo que hace? | Sí | Sí | Sí | Sí | Sí | El script encontró 0 elementos sin descripción en las 5 vistas (5, 9, 8, 6 y 18 elementos). |
| Elementos | ¿Indica la tecnología, si corresponde? | Sí | Sí | Sí | Sí | No | En Contexto no corresponde: personas y sistemas no llevan tecnología. En Despliegue, el nodo "Proxy inverso" no tiene tecnología (línea 107), porque ninguna figura en el ADR-001. |
| Elementos | ¿Se entienden los acrónimos? | Sí | No | No | No | No | Contexto no usa acrónimos. Sin explicar: UUID, EXIF y SKIP LOCKED en Contenedores; UUID y ADR-004 en Componentes; UUID en la Dinámica; NYC3, TLS, GiB, R-03, R-05 y QA-03 en Despliegue. |
| Elementos | ¿Se entienden colores, formas, íconos, bordes y tamaños? | Sí | Sí | Sí | Sí | Sí | Formas por etiqueta: persona (`Person`), navegador (`Web Browser`) y cilindro (`Database`). Gris para "Externo" y blanco para el nodo de infraestructura. Bordes y tamaños son los de Structurizr por defecto. |
| Relaciones | ¿Cada flecha tiene una etiqueta que describe su intención? | Sí | Sí | Sí | Sí | Sí | El script encontró 0 relaciones sin descripción (4, 9, 18, 6 y 9 relaciones). En Componentes, las etiquetas "Usa Zona" o "Usa ConsultaReportes" describen una dependencia más que una intención. |
| Relaciones | ¿La etiqueta coincide con la dirección de la flecha? | Sí | Sí | Sí | Sí | Sí | Cada etiqueta usa un verbo desde el origen, por ejemplo "Reenvía las peticiones" (proxy → API) y "Toma trabajos con SKIP LOCKED" (worker → base de datos). |
| Relaciones | ¿Se indica la tecnología o el protocolo? | Sí | Sí | Sí | Sí | Sí | El script encontró 0 relaciones sin tecnología. Se usan HTTPS, HTTPS/JSON, HTTPS/PNG, HTTP/JSON local, SQL/TCP, E/S de archivos y llamada en proceso. La vista dinámica toma el protocolo de la relación del modelo. |

## Resumen

| Vista | Sí | No |
|---|---|---|
| Contexto | 11 | 1 |
| Contenedores | 10 | 2 |
| Componentes | 10 | 2 |
| Dinámica | 10 | 2 |
| Despliegue | 9 | 3 |

## Correcciones pendientes

1. Agregar `title` a las cinco vistas.
2. Explicar los acrónimos en las descripciones (por ejemplo, "identificador único (UUID)") o en una nota del README.
3. Definir la tecnología del proxy inverso y registrarla en un ADR, para poder indicarla en el nodo de despliegue.
4. Opcional: cambiar las etiquetas "Usa X" de Componentes por la intención concreta, por ejemplo "Lee las zonas priorizadas".