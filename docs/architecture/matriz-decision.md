## 1. Alternativas de estilo

**A. Monolito en capas síncrono**
- Una sola aplicación Python con PostgreSQL, en un único despliegue.
- Cada petición valida, guarda la foto y recalcula la priorización antes de responder.
- Es la más simple y rápida de construir, pero se degrada bajo el pico de reportes.

**B. Monolito modular con ingesta asíncrona**
- Un solo despliegue dividido en módulos: reportes, mapa, priorización y brigadas.
- La ingesta solo valida, guarda y responde; unos workers procesan después desde una cola en PostgreSQL.
- Absorbe ráfagas sin añadir infraestructura, a cambio de unos segundos de retraso en el mapa.

**C. Microservicios orientados a eventos**
- Servicios separados (ingesta, medios, priorización, asignación) comunicados por un broker de mensajes.
- Aísla fallos y permite escalar cada servicio, siempre que haya varios servidores.
- Con un servidor y un desarrollador, su carga operativa no cabe en el plazo ni en el presupuesto.

## 2. Criterios y pesos

| # | Criterio | Peso | Drivers |
|---|---|---|---|
| C1 | Disponibilidad ante picos | 30 % | QA-01, RF-01, R-05 |
| C2 | Tiempo de entrega | 20 % | R-01, R-02 |
| C3 | Rendimiento del mapa y la priorización | 15 % | QA-02, RF-02, RF-03, RF-04 |
| C4 | Costo y simplicidad operativa | 15 % | R-03, R-02 |
| C5 | Seguridad y privacidad | 10 % | R-04, QA-03, RF-06 |
| C6 | Modificabilidad | 10 % | Mantenibilidad, R-02 |

## 3. Matriz de decisión (escala 1 a 5)

| Criterio | Peso | A. Monolito síncrono | B. Monolito modular + cola | C. Microservicios + broker |
|---|---|---|---|---|
| C1. Disponibilidad ante picos | 30 % | 2 | 4 | 3 |
| C2. Tiempo de entrega | 20 % | 5 | 4 | 1 |
| C3. Rendimiento del mapa y la priorización | 15 % | 2 | 4 | 3 |
| C4. Costo y simplicidad operativa | 15 % | 5 | 4 | 1 |
| C5. Seguridad y privacidad | 10 % | 4 | 4 | 3 |
| C6. Modificabilidad | 10 % | 3 | 4 | 4 |
| **Total ponderado** | **100 %** | **3,35** | **4,00** | **2,40** |

## 4. Justificación de los puntajes

- **C1:** A bloquea la ingesta con el procesamiento de fotos. B la desacopla, pero el servidor único le impide el 5. C desacopla igual, pero el broker y los servicios compiten por la RAM del mismo servidor.
- **C2:** A es lo más rápido de construir. B añade la cola y los workers. C no es realista en un mes con un desarrollador.
- **C3:** en A, el pico de ingesta frena también el mapa. B precalcula la priorización en segundo plano. C lo hace igual, con latencia extra entre servicios.
- **C4:** A tiene un proceso y una base de datos. B suma workers que monitorear. C exige broker, varios despliegues y trazabilidad distribuida.
- **C5:** A y B aplican roles y TLS en un solo punto. C tiene más superficie de ataque y más configuración entre servicios.
- **C6:** A tiende a acoplar sus capas. B tiene módulos con límites claros. C aísla servicios, pero los cambios que cruzan varios son costosos.

## 5. Resultado

Gana la alternativa B con 4,00, frente a 3,35 de A y 2,40 de C. B no obtiene el máximo en ningún criterio; gana por equilibrio, porque es la única sin puntajes bajos en los criterios de mayor peso. C se puntúa solo como referencia, ya que incumple R-01 y quedaría descartada antes de la matriz.