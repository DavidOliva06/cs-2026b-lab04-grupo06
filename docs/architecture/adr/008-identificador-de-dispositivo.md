# ADR-008: Identificador de dispositivo con límite y un voto por zona
- Estado: Aceptado
- Fecha: 2026-10-31
- Decisores: Oliva Valdivia David Alexander
## Contexto
El endpoint de ingesta está abierto a cualquier ciudadano. Un atacante con un script puede enviar 1 000 reportes falsos en 5 min y desviar brigadas. El modo pico de ADR-006 agrava el riesgo: sin foto, la priorización depende solo de cuántos reportes hay por zona (RI-02).

El escenario S2 exige:
- ≤ 10 reportes aceptados por dispositivo en 10 min;
- 0 zonas cuya prioridad cambie por un único dispositivo;
- ≥ 99,5 % de los reportes legítimos aceptados;
- aviso al operador ≤ 5 min.

Hay dos condiciones del caso que lo complican:
- Muchos ciudadanos comparten IP pública por la red del operador móvil (CGNAT).
- El reporte debe poder crearse sin señal (RF-01), sin pasos extra para alguien en situación de estrés y sin recoger más datos personales de los necesarios (Ley 29733, R-04).

El análisis está en la [iteración 3 de ADD](../add/iteracion-3.md).
## Alternativas consideradas
1. Identificar actores (T9): la PWA obtiene un identificador de dispositivo firmado por el servidor, y la API acepta como máximo 10 reportes por dispositivo en una ventana deslizante de 10 min.
2. Limitar el acceso por IP (T10): como máximo 10 reportes por IP pública en 10 min.
3. Detectar y reaccionar (T11), junto con T9: el dispositivo que supera el límite queda marcado como sospechoso y sus reportes no cuentan; cada dispositivo vale un voto por zona; se avisa al operador.
4. Autenticar actores (T12): verificar el número de teléfono con un código por SMS antes de reportar.
## Decisión
Usaremos T9 + T11:
- **PWA:** la primera vez que se abre con red, pide su identificador en `POST /api/dispositivos` y lo envía en cada reporte (`X-Dispositivo`).
- **API de ingesta:** verifica la firma, responde 429 al reporte n.º 11 de un dispositivo en 10 min y marca ese dispositivo como sospechoso.
- **Priorización:** cuenta un voto por dispositivo y zona (la mayor gravedad reportada) y excluye a los sospechosos.
- **Aviso:** el evento `DispositivoSospechoso` llega al operador a través del Observer de ADR-005.

Rechazamos dos alternativas:
- **T10:** la simulación muestra que, con CGNAT, solo acepta del 14,82 % al 52,87 % de los reportes legítimos.
- **T12:** la comparación de alternativas muestra que el código se pide y se verifica con red, lo que rompe RF-01. Además, cuesta ≈ US$ 400–1 000 por simulacro (supuesto: US$ 0,02–0,05 por SMS), de 13 a 33 veces R-03; agrega pasos al flujo; recoge el número de teléfono; y exige un proveedor fuera de R-02.

**Evidencia:** la simulación por conteo [fitness/simulacion_s2.py](../../../fitness/simulacion_s2.py) corrió 10 réplicas con 3 333 reportes legítimos de 3 000 dispositivos detrás de 200 IP públicas.

| Táctica (peor réplica, supuestos base) | Aceptados del atacante | Zonas del top 20 alteradas | Legítimos aceptados | Aviso | ¿Cumple S2? |
|---|---|---|---|---|---|
| Antes: sin control | 1 000 | 5 | 100 % | sin aviso | No |
| T10: límite por IP | 10 | 12 | **36,69 %** | 3,4 s | No |
| T9: límite por dispositivo | 10 | 0 | 100 % | 4,0 s | Sí |
| **T9 + T11** | 10 | 0 | 100 % | 4,0 s | **Sí** |

Si el atacante concentra sus 10 reportes en una sola zona, T9 por sí solo la mete en el top 20 y T9 + T11 no: ese es el aporte de T11. Si el atacante pide un identificador nuevo cada 10 reportes (Sybil), ambas fallan: acepta 1 000 reportes, altera 5 zonas y no hay aviso.
## Consecuencias
- Positivas:
  - S2 se cumple en todas las variantes del estímulo del escenario: con 50, 200 o 1 000 IP públicas, y con el ataque concentrado en una zona o repartido en 20.
  - Los ciudadanos legítimos no notan nada: 100 % aceptados, sin pasos extra y sin conexión al crear el reporte.
  - El atacante se detecta en 4 s, frente al límite de 300 s.
  - Cierra RI-02 para un atacante con un solo dispositivo.
  - Usa Python, PostgreSQL y el Observer existente: US$ 0 y 3–4 días-persona.
- Negativas / riesgos:
  - **Trade-off aceptado:** se resiste a un atacante con un dispositivo, pero no a uno con muchas identidades. El ataque Sybil sigue abierto (RI-10). Limitar la emisión de identificadores por IP choca con el CGNAT, y T12 se rechazó. Se acepta como riesgo residual del MVP, con dos mitigaciones por evaluar: avisos por zona y verificación del brigadista antes de asignar.
  - Con un voto por dispositivo, varios daños reportados desde un mismo celular pesan como uno en esa zona (RI-12).
  - El identificador de dispositivo vincula los reportes de una persona. Es un dato personal más: necesita retención y borrado (S3, RI-11).
  - La PWA necesita red la primera vez para obtener el identificador; ADR-003 ya la necesita para cargarse.
  - Hay una cola de dispositivos sospechosos que alguien debe revisar durante el simulacro.
