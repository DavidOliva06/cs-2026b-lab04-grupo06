"""Pruebas del componente de IA con un LLM simulado que da respuestas válidas e inválidas."""
import json

import pytest

from modulo.ia.adaptador_llm import ClasificadorLLM
from modulo.ia.cache import ClasificadorConCache
from modulo.ia.guardrails import (
    FormatoValido,
    Guardrail,
    NoDeclararSeguro,
    RespuestaBloqueada,
    SalidaLLM,
    SinDatosPersonales,
)
from modulo.ia.puerto import ClasificadorDanos
from externos import LLMSimulado


def respuesta(gravedad="grave", resumen="Pared de adobe colapsada sobre la vereda."):
    return json.dumps({"gravedad": gravedad, "resumen": resumen})


def clasificar(texto_llm, descripcion="Se cayó la pared de mi casa"):
    return ClasificadorLLM(LLMSimulado([texto_llm])).clasificar(descripcion)


# --- Respuestas válidas -----------------------------------------------------


def test_respuesta_valida_se_acepta():
    resultado = clasificar(respuesta())
    assert resultado.gravedad == "grave"
    assert resultado.resumen == "Pared de adobe colapsada sobre la vereda."
    assert resultado.requiere_revision is False


def test_el_llm_recibe_las_instrucciones_y_la_descripcion():
    llm = LLMSimulado([respuesta()])
    ClasificadorLLM(llm).clasificar("Techo rajado")
    assert llm.ultimos_mensajes[0]["rol"] == "sistema"
    assert llm.ultimos_mensajes[1] == {"rol": "usuario", "contenido": "Techo rajado"}


# --- Respuestas inválidas: los guardrails las bloquean ----------------------


@pytest.mark.parametrize(
    "texto_llm, guardrail",
    [
        ("La pared se cayó, es grave.", "FormatoValido"),
        (respuesta(gravedad="apocalíptico"), "FormatoValido"),
        (respuesta(resumen=""), "FormatoValido"),
        (respuesta(resumen="x" * 281), "FormatoValido"),
        (respuesta(gravedad="leve", resumen="Fisura menor, la casa es segura."), "NoDeclararSeguro"),
        (respuesta(gravedad="leve", resumen="Daño leve, pueden volver a dormir ahí."), "NoDeclararSeguro"),
        (respuesta(resumen="Llamar al vecino al 959000111."), "SinDatosPersonales"),
        (respuesta(resumen="Reportado por el ciudadano con DNI 45678912."), "SinDatosPersonales"),
    ],
)
def test_respuesta_invalida_se_bloquea_y_pasa_a_revision_humana(texto_llm, guardrail):
    resultado = clasificar(texto_llm)
    assert resultado.requiere_revision is True
    assert resultado.gravedad is None and resultado.resumen is None
    assert resultado.motivo.startswith(guardrail)


def test_si_el_llm_falla_el_reporte_pasa_a_revision_humana():
    resultado = ClasificadorLLM(LLMSimulado([])).clasificar("Se cayó la pared")
    assert resultado.requiere_revision is True
    assert "LLM no disponible" in resultado.motivo


# --- Cadena de responsabilidad ----------------------------------------------


class Espia(Guardrail):
    nombre = "Espia"

    def __init__(self, siguiente=None):
        super().__init__(siguiente)
        self.revisadas = 0

    def _verificar(self, salida):
        self.revisadas += 1


def test_la_cadena_se_detiene_en_el_primer_guardrail_que_bloquea():
    espia = Espia()
    cadena = FormatoValido(NoDeclararSeguro(espia))
    with pytest.raises(RespuestaBloqueada) as error:
        cadena.revisar(SalidaLLM("texto libre", None))
    assert error.value.guardrail == "FormatoValido"
    assert espia.revisadas == 0


def test_una_respuesta_valida_recorre_toda_la_cadena():
    espia = Espia()
    texto = respuesta()
    FormatoValido(NoDeclararSeguro(SinDatosPersonales(espia))).revisar(
        SalidaLLM(texto, json.loads(texto))
    )
    assert espia.revisadas == 1


# --- Decorator de caché -----------------------------------------------------


def test_la_cache_evita_consultar_dos_veces_la_misma_descripcion():
    llm = LLMSimulado([respuesta()])
    clasificador = ClasificadorConCache(ClasificadorLLM(llm))
    primera = clasificador.clasificar("Pared caída")
    segunda = clasificador.clasificar("  pared   CAÍDA ")
    assert primera == segunda
    assert llm.llamadas == 1


def test_la_cache_no_guarda_respuestas_bloqueadas():
    llm = LLMSimulado([respuesta(resumen="Todo bien, es seguro."), respuesta()])
    clasificador = ClasificadorConCache(ClasificadorLLM(llm))
    assert clasificador.clasificar("Pared caída").requiere_revision is True
    assert clasificador.clasificar("Pared caída").requiere_revision is False
    assert llm.llamadas == 2


def test_la_cache_respeta_su_capacidad():
    llm = LLMSimulado([respuesta(), respuesta(), respuesta()])
    clasificador = ClasificadorConCache(ClasificadorLLM(llm), capacidad=1)
    clasificador.clasificar("Pared caída")
    clasificador.clasificar("Techo rajado")  # expulsa "pared caída"
    clasificador.clasificar("Pared caída")
    assert llm.llamadas == 3


def test_cada_cache_es_independiente():
    llm = LLMSimulado([respuesta(), respuesta()])
    ClasificadorConCache(ClasificadorLLM(llm)).clasificar("Pared caída")
    ClasificadorConCache(ClasificadorLLM(llm)).clasificar("Pared caída")
    assert llm.llamadas == 2


def test_el_decorador_y_el_adaptador_cumplen_el_mismo_puerto():
    clasificador = ClasificadorLLM(LLMSimulado([]))
    assert isinstance(clasificador, ClasificadorDanos)
    assert isinstance(ClasificadorConCache(clasificador), ClasificadorDanos)
