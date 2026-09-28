"""Perillas de receta que transforman rásters que ELMFIRE ya lee (app/validation/cadena.py)."""
from datetime import UTC, datetime

import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.validation import almacen, cadena

UTM = "EPSG:32719"
GRILLA = from_origin(300000, 5300000, 30, 30)   # ~ -42,4 / -71,4


def _escribir(ruta, datos, transform=GRILLA, crs=UTM, dtype="float32"):
    datos = np.asarray(datos, dtype=dtype)
    datos = datos[None] if datos.ndim == 2 else datos
    with rasterio.open(ruta, "w", driver="GTiff", height=datos.shape[1], width=datos.shape[2],
                       count=datos.shape[0], dtype=dtype, crs=crs, transform=transform) as dst:
        dst.write(datos)


def _insumos(tmp_path, monkeypatch):
    monkeypatch.setattr(almacen, "_raiz", lambda: tmp_path / "objetos")
    ins = tmp_path / "insumos"
    ins.mkdir()
    for nombre, valor in (("dem", 400.0), ("slp", 0.0), ("asp", 0.0), ("cc", 0.0)):
        _escribir(ins / f"{nombre}.tif", np.full((4, 4), valor))
    for nombre in ("m1", "m10", "m100"):
        _escribir(ins / f"{nombre}.tif", np.full((3, 4, 4), 9.0))
    grueso = from_origin(-72.0, -42.0, 0.25, 0.25)
    archivos = {}
    for nombre, valor, bandas in (("t2m_gfs", 293.15, 3), ("rh_gfs", 40.0, 3),
                                  ("orog_gfs", 1000.0, 1)):
        ruta = tmp_path / f"{nombre}.tif"
        _escribir(ruta, np.full((bandas, 4, 4), valor), grueso, "EPSG:4326")
        archivos[f"{nombre}.tif"] = almacen.guardar(ruta)
    return ins, archivos


def _leer(ruta):
    with rasterio.open(ruta) as src:
        return src.read()


def test_altura_600_m_abajo_seca_los_tres(tmp_path, monkeypatch):
    ins, archivos = _insumos(tmp_path, monkeypatch)
    cadena._humedad_con_criterio("altura", archivos, ins,
                                 datetime(2025, 1, 15, 18, tzinfo=UTC), -71.4)
    m1, m10, m100 = (_leer(ins / f"{n}.tif") for n in ("m1", "m10", "m100"))
    # 20 °C y 40 % a 1.000 m → 23,9 °C y ~31 % a 400 m: Nelson ~5,5 %
    assert 4.5 < m1.mean() < 6.5
    assert np.allclose(m10 - m1, 2.0) and np.allclose(m100 - m1, 5.0)


def test_fosberg_cambia_solo_m1(tmp_path, monkeypatch):
    ins, archivos = _insumos(tmp_path, monkeypatch)
    cadena._humedad_con_criterio("fosberg", archivos, ins,
                                 datetime(2025, 1, 15, 18, tzinfo=UTC), -71.4)
    assert not np.allclose(_leer(ins / "m1.tif"), 9.0)
    assert np.allclose(_leer(ins / "m10.tif"), 9.0)


def test_adj_por_grupo_de_combustible():
    codigos = np.array([[102, 144, 165, 186, 98]])
    factor = cadena.factor_por_grupo(codigos, {"SH": 1.5, "TL": 0.75})
    assert factor.tolist() == [[1.0, 1.5, 1.0, 0.75, 1.0]]
