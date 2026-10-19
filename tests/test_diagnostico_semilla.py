"""Aritmética del diagnóstico de la semilla P-24 (scripts/diagnostico_semilla.py), sintética."""
import numpy as np
import pytest
from rasterio.transform import from_origin
from shapely.geometry import Point, box

from scripts import diagnostico_semilla as ds


def test_semilla_sinteticos():
    forma, tr = (300, 300), from_origin(0, 9000, 30, 30)   # 9 × 9 km, celdas de 30 m
    cic = np.zeros(forma, dtype=bool)
    cic[150:200, 50:100] = True                            # x 1.500-3.000, y 3.000-4.500
    propias = np.array([[x, y] for x in (1500., 2250., 3000.) for y in (3000., 3750., 4500.)
                        if (x, y) != (2250., 3750.)])     # el borde de la cicatriz, cada 750 m
    ajena = np.array([[8000., 800.]])                      # otro foco a ~5,9 km
    xy = np.vstack([propias, ajena])
    ign = np.array([[2250., 3750.]])                       # al centro

    # tiempo real: la ajena no se une a la ignición
    assert ds.conexas(xy, ign, 1500.0).tolist() == [True] * 8 + [False]
    assert ds.conexas(xy, ign, 1500.0, ancla_m=500.0).tolist() == [False] * 9

    semilla, nucleo = ds.reconstruir(xy)
    s0, nuc = ds.rasterizar([semilla], forma, tr), ds.rasterizar([nucleo], forma, tr)
    sf = ds.rasterizar([ds.reconstruir(propias)[0]], forma, tr)
    nada = np.zeros(forma, dtype=bool)
    r = ds.descomponer(s0, sf, nuc, nada, cic, nada, nada, nada, 0.09)
    # a: el disco de 375 m de la ajena; b: el anillo de 187,5 m alrededor del casco (= cicatriz)
    assert r["a_ha"] == pytest.approx(np.pi * 375 ** 2 / 1e4, rel=0.05)
    assert r["b_ha"] == pytest.approx((4 * 1500 * 187.5 + np.pi * 187.5 ** 2) / 1e4, rel=0.08)
    assert r["c_ha"] == r["d_ha"] == r["e_ha"] == 0
    assert sum(r[f"{k}_ha"] for k in ds.CAUSAS) == pytest.approx(r["fuera_ha"])

    # re-puntaje: se va lo que creció desde la ajena, queda lo que creció desde la cicatriz
    desde_ajena = ds.rasterizar([Point(8000, 800).buffer(600)], forma, tr)
    desde_propia = ds.rasterizar([box(3000, 3000, 3600, 4500)], forma, tr)
    out = ds.recortar_prediccion(s0 | desde_ajena | desde_propia, s0, sf)
    assert not out[desde_ajena].any()
    assert out[desde_propia].all()
