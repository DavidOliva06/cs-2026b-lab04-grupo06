"""Pruebas del generador de la Tarea B (Lab 09, E6) con un proveedor grabado.

El proveedor es LLMSimulado (Lab 07): devuelve respuestas fijadas, sin red ni clave de API.
"""
import json

import pytest

from externos import LLMSimulado
from modulo.ia.generador_prioridad import (
    RAIZ_PROMPTS,
    VERSION_VIGENTE,
    GeneradorPrioridad,
    SalidaInvalida,
)

REPORTE = "Se cayó una maceta del balcón, nada más."


def respuesta(**cambios):
    datos = {
        "reporte_id": "R1",
        "gravedad": "leve",
        "prioridad": "baja",
        "personas_en_riesgo": False,
        "requiere_revision": False,
        "motivo": "Solo cayó una maceta; no se describe daño en la estructura.",
    }
    datos.update(cambios)
    return json.dumps(datos, ensure_ascii=False)


def generar(texto_llm, reporte_id="R1", texto=REPORTE):
    return GeneradorPrioridad(LLMSimulado([texto_llm])).generar(reporte_id, texto)


def test_respuesta_valida_se_acepta():
    sugerencia = generar(respuesta())
    assert sugerencia.prioridad == "baja"
    assert sugerencia.gravedad == "leve"
    assert sugerencia.requiere_revision is False


def test_sin_dano_se_acepta_sin_clasificacion_y_con_revision():
    sugerencia = generar(respuesta(gravedad=None, prioridad=None, requiere_revision=True))
    assert sugerencia.prioridad is None and sugerencia.requiere_revision is True


def test_el_modelo_recibe_la_plantilla_vigente_con_el_reporte_delimitado():
    llm = LLMSimulado([respuesta()])
    GeneradorPrioridad(llm).generar("R1", REPORTE)
    contenido = llm.ultimos_mensajes[0]["contenido"]
    assert contenido.startswith("# ROL")
    assert contenido.endswith(f'<reporte id="R1">{REPORTE}</reporte>')
    assert "{{" not in contenido


@pytest.mark.parametrize(
    "texto_llm, motivo",
    [
        (respuesta(prioridad="urgente"), "esquema"),                      # valor fuera del enum
        (respuesta(prioridad=None), "esquema"),                           # sin prioridad ni revisión
        ("```json\n" + respuesta() + "\n```", "no es JSON"),              # bloque de código
        (respuesta().replace('"', "“"), "no es JSON"),               # comillas tipográficas
        (respuesta(reporte_id="R2"), "otro reporte"),
        (respuesta(motivo="La vivienda es segura, pueden volver a entrar."), "NoDeclararSeguro"),
        (respuesta(motivo="Llamar al ciudadano al 900111222 para confirmar."), "SinDatosPersonales"),
    ],
)
def test_respuesta_invalida_se_rechaza(texto_llm, motivo):
    with pytest.raises(SalidaInvalida, match=motivo):
        generar(texto_llm)


def test_la_version_vigente_existe_y_la_evalua_promptfoo():
    config = (RAIZ_PROMPTS / "prioridad" / "promptfooconfig.yaml").read_text(encoding="utf-8")
    assert (RAIZ_PROMPTS / "prioridad" / f"{VERSION_VIGENTE}.txt").exists()
    assert f"label: {VERSION_VIGENTE}\n" in config
