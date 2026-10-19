"""Variantes de reconstrucción y criterio de cierre de U (scripts/diagnostico_reconstruccion.py)."""
import numpy as np
import pandas as pd
from rasterio.transform import from_origin

from scripts import diagnostico_reconstruccion as dr
from scripts import diagnostico_semilla as ds


def test_variantes_de_semilla():
    # un anillo de detecciones cada 300 m (lado 1,2 km): el casco rellena el centro, las huellas no
    lado = (0, 300, 600, 900, 1200)
    xy = np.array([[2400.0 + x, 2400.0 + y] for x in lado for y in lado
                   if x in (0, 1200) or y in (0, 1200)])
    forma, tr = (200, 200), from_origin(0, 6000, 30, 30)
    casco, nucleo = ds.reconstruir(xy)
    hue = ds.huellas(xy, np.full(len(xy), 0.4), np.full(len(xy), 0.4))
    s = {n: dr.semilla_variante(n, casco, nucleo, hue, forma, tr) for n in dr.VARIANTES}
    assert s["huellas"].sum() < min(s["conexa"].sum(), s["nucleo_huellas"].sum())
    assert not (s["nucleo_huellas"] & ~(s["conexa"] | s["huellas"])).any()


def test_veredicto_reconstruccion():
    filas = [{"variante": v, "extremo": "voronoi", "mediana_delta_vs_conexa": x}
             for v, x in (("huellas", 0.01), ("nucleo_huellas", 0.019))]
    assert dr.veredicto(pd.DataFrame(filas)).startswith("cierra")
    filas[0]["mediana_delta_vs_conexa"] = 0.03
    assert dr.veredicto(pd.DataFrame(filas)).endswith("huellas")
