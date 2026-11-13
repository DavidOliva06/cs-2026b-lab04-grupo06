# Revisión C4 - SismoReporta AQP

- Primera revisión: 2026-10-17 (entrega, commit `d8c2792`). Versión corregida: 2026-11-13 (rama `lab06-correcciones`, etiqueta `v0.6-c4`).
- Archivo revisado: `workspace.dsl` (validado con Structurizr CLI 2025.11.09 sin errores) y sus exportaciones de `export/` e `img/`.
- Vistas: Contexto (línea 141), Contenedores (línea 147), Componentes (línea 153), SincronizarReporte (dinámica, línea 159) y Despliegue (línea 170). Estilos: líneas 178-218.
- Método: los conteos de elementos y relaciones sin descripción o sin tecnología, la comparación con `paquetes.puml`, los ciclos y las instancias de despliegue salen de `verificar_c4.py`, que lee el modelo exportado a JSON; el resto, de la lectura del DSL y de los PNG exportados.

```bash
structurizr.sh export -w docs/architecture/c4/workspace.dsl -f json -o /tmp/c4
python docs/architecture/c4/verificar_c4.py /tmp/c4/workspace.json docs/design/paquetes.puml
```

## Lista de revisión (Tabla 3), versión corregida

| Grupo | Pregunta | Contexto | Contenedores | Componentes | Dinámica | Despliegue | Evidencia |
|---|---|---|---|---|---|---|---|
| General | ¿Tiene título? | Sí | Sí | Sí | Sí | Sí | Cada vista declara `title` (líneas 142, 148, 154, 160 y 171) y el título sale en español en las exportaciones. |
| General | ¿Se entiende el tipo de diagrama y su alcance? | Sí | Sí | Sí | Sí | Sí | El tipo lo fija la palabra clave (`systemContext`, `container`, `component`, `dynamic`, `deployment`) y el alcance, el elemento indicado: `sismo`, `sismo.api` o el entorno "Producción". El título lo repite, con el nivel C4. |
| General | ¿Tiene leyenda? | Sí | Sí | Sí | Sí | Sí | C4-PlantUML dibuja la leyenda con `SHOW_LEGEND(true)` a partir de las etiquetas exportadas. Las exportaciones Mermaid no tienen leyenda: para el informe y el README se usan los PNG de PlantUML. |
| Elementos | ¿Cada elemento tiene nombre? | Sí | Sí | Sí | Sí | Sí | Todos los elementos se declaran con nombre entre comillas. |
| Elementos | ¿Cada elemento indica su tipo? | Sí | Sí | Sí | Sí | Sí | Cada elemento se declara como `person`, `softwareSystem`, `container`, `component`, `deploymentNode` o `infrastructureNode`, y la exportación usa la macro de ese tipo (`Person`, `System`, `Container`, `ContainerDb`, `Component`, `Deployment_Node`). |
| Elementos | ¿Cada elemento describe lo que hace? | Sí | Sí | Sí | Sí | Sí | `verificar_c4.py`: 0 elementos sin descripción en las 5 vistas (5, 9, 8, 6 y 18 elementos; en Despliegue las instancias muestran la descripción de su contenedor). |
| Elementos | ¿Indica la tecnología, si corresponde? | Sí | Sí | Sí | Sí | No | En Contexto no corresponde: personas y sistemas no llevan tecnología. En Despliegue, el nodo "Proxy inverso" (línea 107) sigue sin tecnología porque ningún ADR elige el producto; su descripción lo indica. |
| Elementos | ¿Se entienden los acrónimos? | Sí | Sí | Sí | Sí | Sí | Se explicaron en las descripciones: "identificador único (UUID)", "metadatos EXIF (fecha, cámara y coordenadas GPS)", "SKIP LOCKED (sin que dos procesos tomen el mismo)", "decisión de arquitectura ADR-004", "Región Nueva York 3 (NYC3)", "escenario de seguridad QA-03 de drivers.md" y "restricción R-03 / R-05 de drivers.md". TLS, GiB, vCPU y SSD se dejan como términos estándar para el público técnico de estas vistas. |
| Elementos | ¿Se entienden colores, formas, íconos, bordes y tamaños? | Sí | Sí | Sí | Sí | Sí | Formas por etiqueta: persona (`Person`) y cilindro (`Database`). El servicio de teselas sale gris con la etiqueta "Externo" en la leyenda gracias a `"c4plantuml.tags" "true"` (línea 138); el nodo "Proveedor de teselas" usa el estilo "Nodo externo" con borde discontinuo. La forma de navegador (`Web Browser`) no la dibuja C4-PlantUML, pero la tecnología de la PWA dice que corre en el navegador. |
| Relaciones | ¿Cada flecha tiene una etiqueta que describe su intención? | Sí | Sí | Sí | Sí | Sí | `verificar_c4.py`: 0 relaciones sin descripción (4, 9, 18, 6 y 9 relaciones). En Componentes, las etiquetas "Usa Zona" o "Usa ConsultaReportes" describen una dependencia más que una intención (mejora opcional). |
| Relaciones | ¿La etiqueta coincide con la dirección de la flecha? | Sí | Sí | Sí | Sí | Sí | Cada etiqueta usa un verbo desde el origen, por ejemplo "Reenvía las peticiones" (proxy → API) y "Toma trabajos con SKIP LOCKED" (worker → base de datos). |
| Relaciones | ¿Se indica la tecnología o el protocolo? | Sí | Sí | Sí | Sí | Sí | `verificar_c4.py`: 0 relaciones sin tecnología. Se usan HTTPS, HTTPS/JSON, HTTPS/PNG, HTTP/JSON local, SQL/TCP, E/S de archivos y llamada en proceso. La vista dinámica toma el protocolo de la relación del modelo. |

## Resumen

| Vista | Sí (2026-10-17) | No (2026-10-17) | Sí (corregida) | No (corregida) |
|---|---|---|---|---|
| Contexto | 11 | 1 | 12 | 0 |
| Contenedores | 10 | 2 | 12 | 0 |
| Componentes | 10 | 2 | 12 | 0 |
| Dinámica | 10 | 2 | 12 | 0 |
| Despliegue | 9 | 3 | 11 | 1 |

## Correcciones aplicadas (2026-11-13)

1. `title` en las cinco vistas.
2. Acrónimos explicados en las descripciones de los elementos y relaciones.
3. Propiedad `"c4plantuml.tags" "true"`: en la entrega, el servicio de teselas salía azul en las exportaciones C4-PlantUML, como si fuera un sistema propio (la etiqueta "Externo" no se exportaba).
4. Estilo "Nodo externo" para el nodo "Proveedor de teselas": en Mermaid su nombre salía blanco sobre fondo blanco.
5. Números de línea de esta revisión: la versión entregada citaba las líneas 153 y 163 para la vista dinámica y el despliegue, que estaban en las 150 y 160.

## Pendiente

1. Elegir el producto del proxy inverso, registrarlo en un ADR e indicarlo como tecnología del nodo.
2. Opcional: cambiar las etiquetas "Usa X" de Componentes por la intención concreta, por ejemplo "Lee las zonas priorizadas".
