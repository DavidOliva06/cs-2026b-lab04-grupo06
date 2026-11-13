"""Pruebas del patrón State contra el diagrama estado-estadoReporte.mmd.

Solo aplican a la versión "después": la versión "antes" no tiene máquina de estados.
Cubre las 7 transiciones del diagrama y comprueba que todas las demás
combinaciones de estado y operación están prohibidas.
"""
import pytest

from modulo.estados import (
    Atendido,
    Borrador,
    CicloReporte,
    Encolado,
    EstadoReporte,
    Rechazado,
    Recibido,
    TransicionInvalida,
    Verificado,
)
from modulo.modelo import Reporte

OPERACIONES = ["encolar", "enviar", "recibir", "verificar", "rechazar", "marcar_atendido"]
ESTADOS = [Borrador, Encolado, Recibido, Verificado, Atendido, Rechazado]

# Transiciones permitidas, copiadas del diagrama de estados del Lab 05.
PERMITIDAS = {
    (Borrador, "encolar"): Encolado,
    (Encolado, "enviar"): Encolado,
    (Encolado, "recibir"): Recibido,
    (Recibido, "verificar"): Verificado,
    (Recibido, "rechazar"): Rechazado,
    (Verificado, "marcar_atendido"): Atendido,
}


def reporte(foto=b"foto", ubicacion=(-16.3989, -71.5350)):
    return Reporte("r-1", "c-1", foto, ubicacion)


def test_la_clase_base_prohibe_todas_las_transiciones():
    for operacion in OPERACIONES:
        with pytest.raises(TransicionInvalida):
            getattr(EstadoReporte(), operacion)(reporte())


@pytest.mark.parametrize("estado, operacion", sorted(PERMITIDAS, key=str))
def test_transicion_permitida_lleva_al_estado_del_diagrama(estado, operacion):
    siguiente = getattr(estado(), operacion)(reporte())
    assert siguiente == PERMITIDAS[(estado, operacion)]()


@pytest.mark.parametrize(
    "estado, operacion",
    [(e, o) for e in ESTADOS for o in OPERACIONES if (e, o) not in PERMITIDAS],
)
def test_transicion_no_dibujada_esta_prohibida(estado, operacion):
    with pytest.raises(TransicionInvalida):
        getattr(estado(), operacion)(reporte())


def test_no_se_encola_un_reporte_sin_foto_o_sin_ubicacion():
    with pytest.raises(TransicionInvalida):
        Borrador().encolar(reporte(foto=b""))
    with pytest.raises(TransicionInvalida):
        Borrador().encolar(reporte(ubicacion=None))


def test_solo_atendido_y_rechazado_son_finales():
    assert [e.nombre for e in ESTADOS if e.es_final] == ["Atendido", "Rechazado"]


def test_ciclo_completo_hasta_atendido():
    ciclo = CicloReporte(reporte())
    assert ciclo.estado == Borrador()
    ciclo.encolar()
    ciclo.enviar()  # el servidor no confirma: sigue encolado
    assert ciclo.estado == Encolado()
    ciclo.recibir()
    ciclo.verificar()
    ciclo.marcar_atendido()
    assert ciclo.estado == Atendido()


def test_un_error_no_cambia_el_estado_del_contexto():
    ciclo = CicloReporte(reporte())
    with pytest.raises(TransicionInvalida):
        ciclo.verificar()
    assert ciclo.estado == Borrador()
