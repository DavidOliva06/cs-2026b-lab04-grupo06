import base64
import importlib
import json
import uuid

import pytest

import externos

FOTO = b"\xff\xd8\xff foto de prueba"
AREQUIPA = (-16.3989, -71.5350)


@pytest.fixture(params=["antes.servicio", "despues.servicio"])
def m(request):
    return importlib.import_module(request.param)


@pytest.fixture(autouse=True)
def red_limpia():
    """Deja la red simulada igual en cada prueba: con señal, sin pérdidas y sin rutas."""
    red = externos.red_movil
    red.hay_senal = True
    red.perder_proxima_respuesta = False
    red._rutas.clear()
    yield red
    red._rutas.clear()


def entorno(m):
    """Servidor publicado en la red simulada y servicio del celular listos para usar."""
    ingesta = m.ServicioIngesta()
    externos.red_movil.publicar(m.URL_INGESTA, ingesta.manejar_post)
    return ingesta, m.ServicioReportes()


def ciudadano(m, acepto=True):
    return m.Ciudadano("c-1", consentimiento_aceptado=acepto)


def cuerpo_json(id_reporte="r-1"):
    return json.dumps(
        {
            "id": id_reporte,
            "ciudadano_id": "c-1",
            "foto_b64": base64.b64encode(FOTO).decode("ascii"),
            "latitud": AREQUIPA[0],
            "longitud": AREQUIPA[1],
        }
    )


# --- Registro del reporte (criterios 1 y 4) ---------------------------------


def test_sin_consentimiento_lanza_error_y_no_guarda_nada(m):
    ingesta, servicio = entorno(m)
    with pytest.raises(m.ConsentimientoNoAceptado):
        servicio.crear_reporte(ciudadano(m, acepto=False), FOTO, AREQUIPA)
    assert servicio.sincronizar_pendientes() == 0
    assert ingesta.contar_reportes() == 0


def test_sin_senal_el_reporte_queda_pendiente_con_uuid(m, red_limpia):
    ingesta, servicio = entorno(m)
    red_limpia.hay_senal = False
    reporte = servicio.crear_reporte(ciudadano(m), FOTO, AREQUIPA)
    assert reporte.estado == m.PENDIENTE_DE_ENVIO
    assert str(uuid.UUID(reporte.id)) == reporte.id
    assert servicio.sincronizar_pendientes() == 0
    assert ingesta.contar_reportes() == 0


def test_foto_que_supera_la_cuota_del_navegador_lanza_error(m):
    _, servicio = entorno(m)
    foto_grande = b"x" * 4_000_000  # en base64 ocupa más de los 5 MB de la cuota
    with pytest.raises(externos.CuotaExcedida):
        servicio.crear_reporte(ciudadano(m), foto_grande, AREQUIPA)


# --- Sincronización (criterios 2 y 3) ---------------------------------------


def test_al_recuperar_senal_envia_y_no_reenvia(m, red_limpia):
    ingesta, servicio = entorno(m)
    red_limpia.hay_senal = False
    servicio.crear_reporte(ciudadano(m), FOTO, AREQUIPA)
    red_limpia.hay_senal = True
    assert servicio.sincronizar_pendientes() == 1
    assert servicio.sincronizar_pendientes() == 0
    assert ingesta.contar_reportes() == 1


def test_sincroniza_varios_pendientes_en_una_llamada(m, red_limpia):
    ingesta, servicio = entorno(m)
    red_limpia.hay_senal = False
    for _ in range(3):
        servicio.crear_reporte(ciudadano(m), FOTO, AREQUIPA)
    red_limpia.hay_senal = True
    assert servicio.sincronizar_pendientes() == 3
    assert ingesta.contar_reportes() == 3


def test_confirmacion_perdida_no_duplica_el_reporte(m, red_limpia):
    ingesta, servicio = entorno(m)
    servicio.crear_reporte(ciudadano(m), FOTO, AREQUIPA)
    red_limpia.perder_proxima_respuesta = True
    assert servicio.sincronizar_pendientes() == 0
    assert ingesta.contar_reportes() == 1
    assert servicio.sincronizar_pendientes() == 1
    assert ingesta.contar_reportes() == 1


def test_reintenta_en_cada_sincronizacion_tras_dos_respuestas_perdidas(m, red_limpia):
    ingesta, servicio = entorno(m)
    llamadas = []

    def servidor_espiado(cuerpo):
        llamadas.append(cuerpo)
        return ingesta.manejar_post(cuerpo)

    red_limpia.publicar(m.URL_INGESTA, servidor_espiado)
    servicio.crear_reporte(ciudadano(m), FOTO, AREQUIPA)
    resultados = []
    for perder in (True, True, False):
        red_limpia.perder_proxima_respuesta = perder
        resultados.append(servicio.sincronizar_pendientes())
    assert resultados == [0, 0, 1]
    assert len(llamadas) == 3
    assert ingesta.contar_reportes() == 1


def test_servidor_no_publicado_deja_el_reporte_pendiente(m, red_limpia):
    _, servicio = entorno(m)
    red_limpia._rutas.clear()  # la URL responde 404
    servicio.crear_reporte(ciudadano(m), FOTO, AREQUIPA)
    assert servicio.sincronizar_pendientes() == 0


# --- Servidor ---------------------------------------------------------------


def test_servidor_recibe_dos_veces_el_mismo_reporte_y_guarda_uno(m):
    ingesta = m.ServicioIngesta()
    primera = ingesta.manejar_post(cuerpo_json("r-1"))
    segunda = ingesta.manejar_post(cuerpo_json("r-1"))
    assert (primera.status, segunda.status) == (200, 200)
    assert json.loads(segunda.texto) == {"id": "r-1", "recibido": True}
    assert ingesta.contar_reportes() == 1


def test_servidor_rechaza_cuerpo_invalido_con_400(m):
    ingesta = m.ServicioIngesta()
    assert ingesta.manejar_post("esto no es JSON").status == 400
    assert ingesta.manejar_post(json.dumps({"id": "r-1"})).status == 400
    assert ingesta.contar_reportes() == 0


def test_recibir_devuelve_true_aunque_el_reporte_ya_exista(m):
    ingesta = m.ServicioIngesta()
    reporte = m.Reporte("r-1", "c-1", FOTO, AREQUIPA)
    assert ingesta.recibir(reporte) is True
    assert ingesta.recibir(reporte) is True
    assert ingesta.contar_reportes() == 1


# --- Controlador (lo que ve el ciudadano) -----------------------------------


def test_controlador_muestra_los_estados_del_flujo(m, red_limpia, capsys):
    _, servicio = entorno(m)
    controlador = m.ControladorReportes(servicio)

    assert controlador.enviar_reporte(ciudadano(m, acepto=False), FOTO, AREQUIPA) is None
    red_limpia.hay_senal = False
    assert controlador.enviar_reporte(ciudadano(m), FOTO, AREQUIPA) is not None
    controlador.al_recuperar_conexion()
    red_limpia.hay_senal = True
    controlador.al_recuperar_conexion()

    assert capsys.readouterr().out.splitlines() == [
        "  [PWA] Debe aceptar el uso de su ubicación y sus fotos",
        "  [PWA] Pendiente de envío",
        "  [PWA] Sigue pendiente de envío",
        "  [PWA] Enviado (1 reporte(s))",
    ]