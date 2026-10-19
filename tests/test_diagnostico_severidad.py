"""Aritmética del frente 2 (scripts/diagnostico_severidad.py) con rásters sintéticos."""
import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

from app.validation import puntuacion as p
from scripts import diagnostico_severidad as ds


def pila(nir: float, swir: float, forma=(8, 8)) -> np.ndarray:
    """Seis bandas (B2, B3, B4, B8, B11, B12) constantes."""
    a = np.zeros((6, *forma))
    a[ds.B8], a[ds.B12] = nir, swir
    return a


def test_dnbr_escala_y_fraccion():
    # NBR_pre = 2000/4000 = 0,5; NBR_post = -1000/3000 = -1/3 -> dNBR 0,8333 (escala 0-1)
    d = ds.dnbr(pila(3000, 1000), pila(1000, 2000))
    assert d[0, 0] == pytest.approx(0.5 + 1 / 3)
    assert np.isnan(ds.dnbr(pila(0, 0), pila(1, 1))[0, 0])   # suma 0 -> sin dato

    alta = np.array([[1, 0], [1, 1]], bool)
    valido = np.array([[1, 1], [1, 0]], bool)
    region = np.ones((2, 2), bool)
    assert ds.fraccion(alta, valido, region) == {"n_celdas": 3, "frac_alta": pytest.approx(2 / 3)}
    assert ds.fraccion(alta, valido, ~region)["frac_alta"] is None

    assert ds.evaluar_criterio(0.5, 0.33) and not ds.evaluar_criterio(0.49, 0.1)
    assert not ds.evaluar_criterio(0.6, 0.5) and not ds.evaluar_criterio(None, 0.1)


def test_dias_y_traer_dnbr(tmp_path):
    t0 = pd.Timestamp("2025-01-01 12:00", tz="UTC")
    horas = [0, 1, 30]
    df = pd.DataFrame({"acq_datetime": [t0 + pd.Timedelta(hours=h) for h in horas]})
    corte, primera = ds.dias(df)
    assert primera == t0 + pd.Timedelta(hours=1) and corte == primera + pd.Timedelta(hours=24)
    corte_ign, _ = ds.dias(df, desde=t0 - pd.Timedelta(hours=2))
    assert corte_ign == t0 + pd.Timedelta(hours=22)

    # un tile pre/post: la mitad izquierda se quema fuerte (dNBR 0,83), la derecha no (0)
    run = tmp_path
    (run / "imagenes_pre").mkdir()
    (run / "imagenes_post").mkdir()
    tr = from_origin(0, 8, 1, 1)
    perfil = {"driver": "GTiff", "count": 6, "dtype": "float64", "width": 8, "height": 8,
              "crs": "EPSG:32719", "transform": tr}
    post = pila(1000, 2000)
    post[:, :, 4:] = pila(3000, 1000)[:, :, 4:]
    for carpeta, datos in (("imagenes_pre", pila(3000, 1000)), ("imagenes_post", post)):
        with rasterio.open(run / carpeta / "t.tif", "w", **perfil) as dst:
            dst.write(datos)
    ref = tmp_path / "ref.tif"
    with rasterio.open(ref, "w", driver="GTiff", count=1, dtype="uint8", width=8, height=8,
                       crs="EPSG:32719", transform=tr) as dst:
        dst.write(np.zeros((1, 8, 8), "uint8"))
    valido, alta, medio, rd = ds.traer_dnbr(run, p.Grilla(ref))
    assert valido.all() and alta[:, :4].all() and not alta[:, 4:].any()
    assert medio[0, 0] == pytest.approx(0.5 + 1 / 3, abs=1e-4)
    assert medio[0, 7] == pytest.approx(0, abs=1e-4)
    assert rd[0, 0] == pytest.approx((0.5 + 1 / 3) / np.sqrt(0.5), abs=1e-4)   # RdNBR


def test_veredicto_tres_salidas():
    # discrimina y cumple en los dos: SÍ
    assert ds.veredicto([True, True], [[], []]) == "SÍ"
    # no cumple y nada lo vuelve indiscriminado: NO
    assert ds.veredicto([True, False], [[], []]) == "NO"
    # cualquier causa de indiscriminado prevalece
    assert ds.veredicto([False, False], [[], ["x"]]) == "INDISCRIMINADO"
    assert ds.motivos_indiscriminado(0.4, 0.70, 0.1, 20)            # siguientes > 0,67
    assert ds.motivos_indiscriminado(0.4, 0.2, 0.33, 20)            # SH4 >= 0,8 x bosque
    assert not ds.motivos_indiscriminado(0.4, 0.2, 0.31, 20)
    assert ds.motivos_indiscriminado(0.4, 0.2, 0.0, 30)             # Landsat
