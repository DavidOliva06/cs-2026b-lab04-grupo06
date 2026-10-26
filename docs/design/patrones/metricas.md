# Métricas y trade-off del refactor

- Fecha: 2026-10-25
- Herramienta: radon (`radon cc -s -a` para complejidad ciclomática y `radon raw -s` para líneas de código)
- Alcance: `antes/servicio.py` frente a `despues/`. Las pruebas están fuera de la medición.
- Para comparar lo mismo, "Después (flujo equivalente)" incluye solo los archivos que reemplazan a `antes/servicio.py`: `servicio`, `modelo`, `puertos`, `adaptadores`, `fabrica`, `eventos`, `observadores` y `decoradores`. La máquina de estados y el componente de IA son funciones nuevas y se miden aparte.

## Resumen

| Versión | Archivos | Bloques analizados | Complejidad promedio | Complejidad máxima | SLOC |
|---|---|---|---|---|---|
| Antes | 1 | 27 | A (1,67) | A (5): `ServicioReportes.sincronizar_pendientes` | 189 |
| Después (flujo equivalente) | 8 | 67 | A (1,88) | A (5): `VistaConsola.notificar` | 381 |
| Después: máquina de estados (State) | 1 | 33 | A (1,33) | A (3): `Borrador.encolar` | 74 |
| Después: componente de IA | 4 | 25 | A (2,56) | B (6): `FormatoValido._verificar` | 139 |
| **Después (total)** | **13** | **125** | **A (1,87)** | **B (6): `FormatoValido._verificar`** | **594** |

Pruebas: 12 pruebas de caracterización antes del refactor; 37 funciones de prueba después, que generan 90 ejecuciones gracias a la parametrización, y todas pasan.

## Complejidad por método (misma responsabilidad, antes y después)

| Responsabilidad | Antes: método | CC | Después: método | CC |
|---|---|---|---|---|
| Crear el servicio del celular | `ServicioReportes.__init__` | 1 | `ServicioReportes.__init__` | 4 |
| Crear un reporte | `ServicioReportes.crear_reporte` | 2 | `ServicioReportes.crear_reporte` | 2 |
| Sincronizar pendientes | `ServicioReportes.sincronizar_pendientes` | 5 | `ServicioReportes.sincronizar_pendientes` | 3 |
| Buscar pendientes en el celular | (dentro de `sincronizar_pendientes`) | — | `AdaptadorIndexedDB.buscar_por_estado` | 3 |
| Guardar en IndexedDB | `ServicioReportes._guardar_en_indexeddb` | 2 | `AdaptadorIndexedDB.guardar` | 2 |
| Leer de IndexedDB | `ServicioReportes._desde_registro_indexeddb` | 2 | `AdaptadorIndexedDB._desde_registro` | 2 |
| Enviar por HTTP | `ServicioReportes._enviar_por_http` | 2 | `AdaptadorEnvioHttp.enviar` | 2 |
| Registrar cada envío | — | — | `EnvioConRegistro.enviar` | 2 |
| Crear el servicio del servidor | `ServicioIngesta.__init__` | 1 | `ServicioIngesta.__init__` | 3 |
| Recibir el POST | `ServicioIngesta.manejar_post` | 2 | `ServicioIngesta.manejar_post` | 2 |
| Guardar sin duplicar | `ServicioIngesta._guardar_si_no_existe` | 1 | `AdaptadorPostgres.guardar_si_no_existe` | 1 |
| Contar reportes | `ServicioIngesta.contar_reportes` | 1 | `AdaptadorPostgres.contar` | 1 |
| Elegir la implementación | — | — | `FabricaEstrategias.crear` | 3 |
| Crear el controlador | `ControladorReportes.__init__` | 1 | `ControladorReportes.__init__` | 3 |
| Enviar desde el controlador | `ControladorReportes.enviar_reporte` | 2 | `ControladorReportes.enviar_reporte` | 2 |
| Sincronizar desde el controlador | `ControladorReportes.al_recuperar_conexion` | 2 | `ControladorReportes.al_recuperar_conexion` | 1 |
| Mostrar mensajes al ciudadano | `_mostrar_estado` y `_mostrar_consentimiento` | 1 y 1 | `VistaConsola.notificar` | 5 |
| Contar pendientes en pantalla | — | — | `ContadorPendientes.notificar` | 3 |

## Trade-off

Ganamos aislamiento: el servicio ya no conoce IndexedDB, HTTP ni PostgreSQL, y cambiar de almacenamiento, de canal o de proveedor de LLM se reduce a escribir un adaptador y registrarlo en la fábrica.
También ganamos facilidad para probar: el Observer, el Decorator y la IA se prueban con dobles sin usar la red simulada, y el método más complejo del flujo, `sincronizar_pendientes`, bajó de 5 a 3.
El costo es tamaño e indirección: el flujo equivalente pasó de 189 a 381 SLOC y de 1 a 8 archivos, y para seguir un envío hay que recorrer servicio, puerto, fábrica, decorador y adaptador.
La complejidad promedio no bajó (de 1,67 a 1,88), porque no se eliminó sino que se repartió: los constructores con valores por defecto suman ramas y los mensajes pasaron a `VistaConsola.notificar` (5).
La versión antes habría sido suficiente para un prototipo que valide la idea con Defensa Civil, con un solo almacenamiento y un solo canal que no van a cambiar, sin IA y sin necesidad de probar las piezas por separado.
En ese escenario, con un desarrollador y un mes de plazo, un archivo de 189 líneas se lee y se corrige más rápido que trece.

## Patrones que decidimos NO aplicar

| Patrón | Dónde se propuso | Por qué no se aplicó |
|---|---|---|
| Abstract Factory | Crear juntas la "familia" de adaptadores del celular y la del servidor | No hay familias intercambiables: cada puerto tiene una sola implementación, y los adaptadores del celular y del servidor nunca se crean juntos porque corren en dispositivos distintos. Un registro simple (`FabricaEstrategias`) basta. |
| Singleton | Convertir la red simulada o la fábrica en instancia única | Sería estado global: obligaría a limpiarlo en cada prueba y a compartir la caché del LLM entre servicios. Cada servicio recibe o crea sus propias instancias. |
| Decorator de reintentos | Reintentar el envío dentro de la misma sincronización | Cambiaría el comportamiento observable (la prueba de caracterización espera `[0, 0, 1]` tras dos respuestas perdidas). Hoy el reintento ocurre en la siguiente sincronización, y eso cumple el plazo de 15 minutos de QA-01. |
| Command | Convertir cada reporte pendiente en un comando | Los pendientes son datos, no acciones: no hay deshacer, historial ni cola de operaciones que lo justifiquen. |