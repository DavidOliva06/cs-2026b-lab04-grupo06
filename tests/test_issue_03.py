"""ISSUE-03: prioridad errónea de una zona con reportes sin foto (issues/ISSUE-03.md)."""
from modulo.priorizacion import ReporteClasificado as R
from modulo.priorizacion import puntajes, zonas_priorizadas


def test_issue_03_reportes_sin_foto_no_superan_a_un_dano_verificado():
    reportes = [
        R("Yanahuara", "d-1", "grave", tiene_foto=True),
        R("Cayma", "d-2", "leve", tiene_foto=False),
        R("Cayma", "d-3", "leve", tiene_foto=False),
    ]
    assert puntajes(reportes) == {"Yanahuara": 4, "Cayma": 2}
    assert zonas_priorizadas(reportes) == ["Yanahuara", "Cayma"]


def test_issue_03_sin_foto_y_sin_clasificar_aporta_el_peso_minimo():
    assert puntajes([R("Cercado", "d-1", None, tiene_foto=False)]) == {"Cercado": 1}


def test_issue_03_sin_foto_no_sube_por_encima_de_su_gravedad():
    reportes = [R("Cercado", "d-1", "leve", tiene_foto=False),
                R("Paucarpata", "d-2", "moderado", tiene_foto=True)]
    assert zonas_priorizadas(reportes) == ["Paucarpata", "Cercado"]
