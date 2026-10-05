## 1. Requisitos funcionales clave

| ID | Requisito | Actor | Prioridad |
|-------|-----------|-------|-----------|
| RF-01 | Enviar un reporte de daños con foto y geolocalización; si no hay señal, se guarda en el celular y se envía al recuperarla | Ciudadano | Alta |
| RF-02 | Visualizar en un mapa los daños reportados, filtrados por zona y gravedad | Coordinador | Alta |
| RF-03 | Priorizar zonas automáticamente según cantidad y gravedad de reportes | Sistema / Coordinador | Alta |
| RF-04 | Asignar brigadas a las zonas priorizadas | Coordinador | Alta |
| RF-05 | Ver la asignación recibida y marcar su estado (en camino, atendido) | Brigadista | Media |
| RF-06 | Iniciar sesión con roles (ciudadano, brigadista, coordinador) | Todos | Media |
| RF-07 | Consultar el estado de un reporte propio | Ciudadano | Baja |

## 2. Atributos de calidad (ordenados por prioridad)

1. **Disponibilidad ante picos:** es el atributo crítico del caso. Tras un sismo llegan 20 000 reportes en la primera hora con la red congestionada, y perder reportes retrasa la ayuda.
2. **Rendimiento:** el coordinador necesita el mapa y la priorización a tiempo para decidir dónde enviar brigadas.
3. **Usabilidad:** el ciudadano reporta en situación de estrés y con un celular de gama baja, así que el flujo debe ser corto.
4. **Seguridad y privacidad:** la ubicación exacta y las fotos son datos personales, y un acceso indebido o reportes falsos dañan la confianza.
5. **Mantenibilidad:** con un solo desarrollador, el código debe poder corregirse rápido durante y después del MVP.

## 3. Restricciones

| ID | Tipo | Restricción |
|------|------|-------------|
| R-01 | Plazo | MVP en producción en 1 mes |
| R-02 | Equipo | 1 desarrollador, con dominio de Python, JavaScript, CSS y PostgreSQL; no se usan tecnologías fuera de este conjunto |
| R-03 | Presupuesto | Un solo servidor en la nube de bajo costo (aprox. US$ 20–30/mes), sin servicios administrados costosos |
| R-04 | Normativa | Ley 29733 de protección de datos personales (consentimiento para usar ubicación y fotos) |
| R-05 | Dispositivo/red | Debe funcionar en celulares de gama baja y con red móvil intermitente, por lo que se plantea una PWA (sin app nativa) |

## 4. Escenarios de atributos de calidad

| ID | Atributo | Fuente | Estímulo | Entorno | Artefacto | Respuesta | Medida |
|----|----------|--------|----------|---------|-----------|-----------|--------|
| QA-01 | Disponibilidad ante picos | Ciudadanos de Arequipa | Envían 20 000 reportes en 60 min tras un sismo | Red móvil congestionada, celular de gama baja | PWA (cola local) y API de recepción | La PWA guarda cada reporte localmente y lo reenvía al recuperar señal; la API lo guarda sin duplicados | ≥ 99,5 % de reportes (≥ 19 900) guardados en el servidor ≤ 15 min tras recuperar señal; 0 reportes perdidos en el dispositivo |
| QA-02 | Rendimiento | Coordinador de Defensa Civil | Abre el mapa de daños con 5 000 reportes activos | Operación en pico, 10 coordinadores conectados | Panel web y API del mapa | Muestra el mapa con reportes agrupados y zonas priorizadas | p95 ≤ 3 s en cargar el mapa; priorización actualizada ≤ 60 s tras un nuevo reporte |
| QA-03 | Seguridad y privacidad | Usuario con rol ciudadano (no autorizado) | Intenta consultar la ubicación y la foto de reportes de otros usuarios | Operación normal | API de reportes y control de roles | Rechaza la petición y registra el intento | 100 % de 50 intentos de acceso no autorizado rechazados (HTTP 403); 100 % del tráfico por TLS 1.2 o superior |