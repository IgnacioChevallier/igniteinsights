"""Aritmética del diagnóstico de isotropía (scripts/diagnostico_isotropia.py), sintética."""
import math

import numpy as np
import pytest

from app.validation import copa
from scripts import diagnostico_isotropia as di


def test_isotropia_sintetica():
    forma = (101, 101)
    f, c = np.mgrid[:101, :101]
    r = np.hypot(f - 50, c - 50)
    semilla = r <= 5
    anillo = (r > 5) & (r <= 15)                          # predicho: crece parejo
    cuna = anillo & (c > 50) & (np.abs(f - 50) < (c - 50))  # observado: sólo al E (±45°)

    sec = di.sectores(semilla, anillo, rumbo_obs=90.0)
    oeste = anillo & (np.abs(f - 50) < (50 - c))
    assert (sec[cuna] == 0).all() and (sec[oeste] == 2).all()
    todo = np.ones(forma, dtype=bool)
    n = di.cuentas(sec, anillo, cuna, todo, todo)
    e = di.exceso(n["n_pred"], n["lados_pred"], n["n_obs"], n["lados_obs"])
    assert n["lados_obs"] == 0 and e == pytest.approx(0.75, abs=0.03)   # 3/4 del anillo
    assert math.isnan(di.exceso(5, 1, 100, 0))                          # estrato chico

    # criterios registrados
    assert di.veredicto(0.30, 0.10, 0.2, 0.2) == "abrigo"
    assert di.veredicto(0.20, 0.20, 0.40, 0.10) == "método"
    assert di.veredicto(0.20, 0.20, 0.20, 0.20) == "supresión/límite"
    assert di.veredicto(0.10, 0.30, 0.40, 0.10) == "supresión/límite"   # al revés no es método

    # viento del O (270) sobre una ladera que mira al O (asp 270): sopla cuesta arriba
    wd = np.full((3, *forma), 270.0)
    slp, asp = np.full(forma, 20.0), np.full(forma, 270.0)
    assert (di.viento_pendiente(wd, np.zeros(forma), slp, asp, todo) == 0).all()
    assert (di.viento_pendiente(wd, np.zeros(forma), slp, asp + 180 - 360, todo) == 1).all()

    # crecimiento al E de una semilla cuya mitad E cae fuera de la cicatriz
    cic = c < 50
    assert di.brota_fuera(semilla, cic, cuna)[cuna].all()


def test_waf_crown_ratio():
    # bajo dosel denso el WAF escala como 1/√CROWN_RATIO (elmfire_init.f90:620)
    w1, w05 = copa.waf_elmfire(0.8, 20, 1.0), copa.waf_elmfire(0.8, 20, 1.0, crown_ratio=0.5)
    assert float(w05 / w1) == pytest.approx(math.sqrt(2), rel=1e-6)
    # CC ≥ 15 % sin altura de dosel: la tabla da 0 y ELMFIRE deja la celda sin viento
    assert float(copa.waf_elmfire(0.5, 0, 1.0)) == 0.0
