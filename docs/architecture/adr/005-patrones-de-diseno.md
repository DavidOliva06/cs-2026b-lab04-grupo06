# ADR-005: Patrones de diseño adoptados y rechazados en el flujo HU-01
- Estado: Aceptado
- Fecha: 2026-10-25
- Decisores: Oliva Valdivia David Alexander
## Contexto
La versión `antes/servicio.py` resuelve la HU-01 en un solo archivo, pero el servicio conoce los detalles de cada servicio externo: diccionarios y base64 para IndexedDB, texto JSON y códigos de estado para HTTP, y SQL para PostgreSQL. Además, crea sus propias dependencias concretas y mezcla la lectura de HTTP con la lógica de negocio. Cambiar el almacenamiento o el canal de envío obliga a modificar el servicio. Los olores están detallados en `docs/design/patrones/olores.md`.

A esto se suman tres necesidades nuevas: validar el ciclo de vida de seis estados del `Reporte` definido en el Lab 05, registrar cada intento de envío para medir QA-01, y clasificar el daño con un LLM sin que una falla o una respuesta indebida del proveedor afecte el flujo ni exponga datos personales (Ley 29733).

Las restricciones limitan cuánta estructura conviene agregar: un solo desarrollador y un mes de plazo (R-01, R-02). Además, el refactor no debe cambiar el comportamiento: las 12 pruebas de caracterización de `tests/test_comportamiento.py` deben pasar en las dos versiones.
## Alternativas consideradas
1. Mantener `antes/servicio.py` con refactors simples (*Extract Function* e inyección por constructor): es lo más corto, pero el servicio sigue atado a IndexedDB, HTTP y PostgreSQL.
2. Aplicar un patrón solo donde hay un olor o un requisito concreto: puertos (Strategy) con adaptadores (Adapter) y una fábrica simple para los servicios externos, y State, Decorator, Observer y Chain of Responsibility para las necesidades nuevas.
3. Aplicar todos los patrones que propuso la IA, incluidos Abstract Factory, Singleton, Command, un Decorator de reintentos y un Observer para avisar a la priorización: cubre más casos hipotéticos, pero agrega indirección sin un olor que la justifique, y algunos de esos patrones cambian el comportamiento.
## Decisión
Usaremos la alternativa 2. Cada patrón adoptado responde a un olor del código o a un requisito:

| Patrón | Dónde | Motivo |
|---|---|---|
| Strategy | `puertos.py`: `AlmacenLocalReportes`, `PuertoEnvioReportes` y `AlmacenServidorReportes`; `ia/puerto.py`: `ClasificadorDanos` | El servicio depende de interfaces y no de IndexedDB, HTTP, PostgreSQL ni de un proveedor de LLM. Los nombres de los puertos vienen del diagrama de clases del Lab 05. |
| Adapter | `adaptadores.py`: `AdaptadorIndexedDB`, `AdaptadorEnvioHttp` y `AdaptadorPostgres`; `ia/adaptador_llm.py`: `ClasificadorLLM` | La traducción de formatos y errores de cada servicio externo sale del servicio y queda en un solo lugar. |
| Factory (registro) | `fabrica.py`: `FabricaEstrategias` | Crea la implementación de cada puerto a partir de un nombre y comprueba que implemente el puerto. Es un objeto que se crea y se pasa, sin estado global. |
| State | `estados.py`: `EstadoReporte`, una subclase por estado y `CicloReporte` como contexto | Cada estado permite solo las transiciones del diagrama del Lab 05 y rechaza las demás con `TransicionInvalida`. |
| Decorator | `decoradores.py`: `EnvioConRegistro`; `ia/cache.py`: `ClasificadorConCache` | Agregan el registro de cada intento de envío (QA-01) y una caché de clasificaciones sin modificar el envío ni el clasificador que envuelven. |
| Observer | `eventos.py`: `Publicador`, `Observador` y los eventos del flujo | Separa los avisos del flujo (consentimiento rechazado, reporte guardado, sincronización terminada) de quien los muestra. |
| Chain of Responsibility | `ia/guardrails.py`: `FormatoValido` → `NoDeclararSeguro` → `SinDatosPersonales` | Cada guardrail revisa una sola regla sobre la respuesta del LLM. El primero que encuentra un problema la bloquea, y el reporte queda marcado para revisión humana. |

No aplicaremos estos patrones:

| Patrón | Propuesta | Motivo del rechazo |
|---|---|---|
| Abstract Factory | Crear juntas la familia de adaptadores del celular y la del servidor | No hay familias intercambiables: cada puerto tiene una sola implementación, y los adaptadores del celular y del servidor nunca se crean juntos porque corren en dispositivos distintos. |
| Singleton | Hacer de instancia única la red simulada o la fábrica | Sería estado global, que ya obliga a limpiar `red_movil` en cada prueba. Lo correcto es inyectar las dependencias. |
| Decorator de reintentos | Reintentar el envío dentro de la misma sincronización | Cambiaría el comportamiento: la prueba de caracterización espera `[0, 0, 1]` tras dos respuestas perdidas. El reintento ocurre en la siguiente sincronización. |
| Command | Convertir cada reporte pendiente en un comando | Los reportes pendientes son datos, no acciones: no hay deshacer, historial ni cola de operaciones que lo justifiquen. |
| Observer entre módulos | Avisar a la priorización cada vez que llega un reporte | La cola de trabajos en PostgreSQL (ADR-002) ya lo resuelve y sobrevive a una caída. Un Observer en memoria perdería avisos y acoplaría la ingesta con la priorización. |
| Proxy de protección | Comprobar el consentimiento antes de recibir la foto y la ubicación | Es un defecto de comportamiento (criterio 4), no un olor de estructura. Se corrige aparte, con su propia prueba, porque un refactor no debe cambiar lo que el sistema hace. |

En `olores.md`, State y Observer figuran como rechazados para el flujo de sincronización, que solo tiene dos estados y un destinatario de los mensajes. Se adoptan con otro alcance: State para el ciclo completo de seis estados, donde cada estado sí tiene transiciones propias, y Observer para separar los avisos del flujo de la vista.
## Consecuencias
- Positivas:
  - El servicio ya no conoce IndexedDB, HTTP ni PostgreSQL. Una variante nueva se agrega con un adaptador registrado en la fábrica, sin modificar el servicio, como comprueba `tests/test_patrones.py`.
  - Las 12 pruebas de caracterización pasan sobre las dos versiones (24 ejecuciones), así que el refactor conservó el comportamiento.
  - El método más complejo del flujo, `sincronizar_pendientes`, bajó de 5 a 3 de complejidad ciclomática.
  - Una falla del LLM o una respuesta bloqueada por los guardrails no pierde el reporte: queda marcado para revisión humana.
- Negativas / riesgos:
  - El código creció: el flujo equivalente pasó de 1 a 7 archivos y de 189 a 331 líneas de código. La complejidad promedio subió de 1,67 a 1,77, porque los constructores con valores por defecto suman ramas.
  - Hay más indirección: para seguir un envío hay que recorrer servicio, puerto, fábrica y adaptador.
  - `EnvioConRegistro`, `Publicador` y `CicloReporte` todavía no están conectados al flujo, porque `servicio.py` no los usa.
  - State, Observer, los dos Decorator y los guardrails no tienen pruebas automatizadas propias.
