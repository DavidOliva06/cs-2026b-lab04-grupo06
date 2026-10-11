## HU-01: Enviar un reporte sin señal y sincronizarlo
Como ciudadano afectado por un sismo, quiero registrar un reporte de daños con foto y ubicación aunque no tenga señal,
para que Defensa Civil lo reciba en cuanto mi celular recupere la conexión.

### Criterios de aceptación

- Dado que el ciudadano aceptó el consentimiento de uso de ubicación y fotos, y su celular no tiene señal, cuando completa el reporte con foto y ubicación y pulsa "Enviar", entonces la app guarda el reporte en el celular y lo muestra con el estado "Pendiente de envío".

- Dado que existe al menos un reporte con estado "Pendiente de envío", cuando el celular recupera la señal o el ciudadano abre la app con conexión, entonces la app envía el reporte sin que el ciudadano haga nada más, y el estado cambia a "Enviado" en un máximo de 15 minutos.

- Dado que un reporte llegó al servidor pero la confirmación se perdió por la mala conexión, cuando la app vuelve a enviar el mismo reporte, entonces el servidor conserva un solo reporte y la app lo marca como "Enviado".

- Dado que el ciudadano no aceptó el consentimiento de uso de ubicación y fotos, cuando intenta crear un reporte, entonces la app no captura la ubicación ni la foto, no guarda el reporte y le muestra de nuevo el consentimiento.