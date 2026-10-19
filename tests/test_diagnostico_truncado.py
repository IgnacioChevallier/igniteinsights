"""Aritmética del diagnóstico del truncado (scripts/diagnostico_truncado.py), sintética."""
import numpy as np

from app.validation import puntuacion as p
from scripts import diagnostico_truncado as dt


def test_truncado_sinteticos():
    forma = (40, 40)
    final = np.zeros(forma, dtype=bool)
    final[5:25, 5:25] = True
    final[12:16, 12:16] = False                     # una isla sin quemar
    perimetro = dt.rellenar(final)
    assert perimetro[12:16, 12:16].all() and perimetro.sum() == 400

    vistas = np.zeros(forma, dtype=bool)
    vistas[5:25, 5:11] = True                       # VIIRS vio sólo el borde oeste
    cic, exc = final & vistas, final & ~vistas      # la referencia truncada (A)
    e = dt.exclusiones(exc, ~vistas, perimetro)

    # el perímetro perfecto: A lo castiga por la isla no vista; B y C no
    techo = {r: p.metricas(perimetro, cic, 1.0, x)["dice"] for r, x in e.items()}
    assert techo["A"] < 1 and techo["B"] == techo["C"] == 1

    # quemar todo el dominio: B lo premia, C no
    todo = np.ones(forma, dtype=bool)
    dice = {r: p.metricas(todo, cic, 1.0, x)["dice"] for r, x in e.items()}
    assert dice["B"] == 1 and max(dice["A"], dice["C"]) < 0.2

    r = dt.perdonado_ha(todo, exc, ~vistas, perimetro, 1.0)
    assert r["perdonado_dentro_ha"] == 16           # la isla
    assert r["perdonado_fuera_ha"] == 1600 - 400
