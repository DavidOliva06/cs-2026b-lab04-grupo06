# ADR-003: PWA offline-first como cliente del ciudadano
- Estado: Aceptado
- Fecha: 2026-10-03
- Decisores: Oliva Valdivia David Alexander
## Contexto
El ciudadano debe poder reportar sin señal y que el reporte se envíe al recuperarla (RF-01), desde celulares de gama baja con red intermitente (R-05). QA-01 exige que el servidor guarde los reportes sin duplicados y que no se pierdan en el dispositivo.

El equipo es de un solo desarrollador con JavaScript y sin experiencia en desarrollo nativo (R-02), el plazo es de 1 mes (R-01) y la Ley 29733 exige consentimiento para usar ubicación y fotos (R-04).
## Alternativas consideradas
1. PWA offline-first, con service worker y almacenamiento local en IndexedDB.
2. App nativa para Android e iOS: da mejor control del almacenamiento y del envío en segundo plano, pero exige tecnologías fuera de R-02 y publicación en tiendas, lo que no cabe en R-01.
3. Web tradicional sin modo offline: es la más simple, pero incumple RF-01 porque no permite reportar sin señal.
## Decisión
Usaremos una PWA offline-first. La aplicación guardará cada reporte en IndexedDB con un UUID generado en el cliente, que el servidor usará para descartar duplicados.

La PWA reenviará los reportes pendientes al detectar conexión y al abrirse, con espera exponencial y aleatoria entre reintentos. No dependeremos de la sincronización en segundo plano del navegador.

Enviaremos primero los datos del reporte y después la foto, y pediremos el consentimiento explícito antes de capturar la ubicación y la foto (R-04).
## Consecuencias
- Positivas:
  - Una sola base de código en JavaScript sirve para todos los celulares, dentro de R-01 y R-02.
  - El ciudadano puede usarla desde el navegador sin pasar por una tienda de aplicaciones.
  - El UUID del cliente hace que los reintentos sean seguros y evita duplicados (QA-01).
- Negativas / riesgos:
  - La sincronización en segundo plano no está disponible en todos los navegadores (por verificar, en especial en iOS), así que un reporte puede quedar pendiente hasta que el usuario reabra la app.
  - El navegador puede borrar el almacenamiento local si falta espacio, por lo que la meta de 0 reportes perdidos en el dispositivo (QA-01) no puede garantizarse; se mitiga mostrando los pendientes en pantalla hasta su confirmación.
  - Quien no haya abierto la PWA antes del sismo necesita red para cargarla por primera vez.
  - El comportamiento offline debe probarse en celulares de gama baja reales, lo que consume parte del plazo (R-01).