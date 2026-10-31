"""Nota AC: elección del grupo de la app que corresponde a la semilla del benchmark."""
from scripts import diagnostico_semilla_app as ds


def test_elige_el_grupo_con_mas_detecciones_en_comun():
    assert ds.elegir_grupo([{1, 2}, {3, 4, 5}, {6}], {2, 3, 4}) == {3, 4, 5}


def test_sin_grupos_devuelve_vacio():
    assert ds.elegir_grupo([], {1}) == set()
