"""Orientación: la dirección hacia la que mira la ladera, como la lee ELMFIRE.

ELMFIRE 2025.0212 empuja la propagación por pendiente hacia ASP − 180°
(elmfire_level_set.f90, SINASPM180): ASP tiene que ser la dirección cuesta ABAJO.
"""
import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.elmfire.builder import raster_aligner


def _ladera(tmp_path, z):
    dem = tmp_path / "dem.tif"
    with rasterio.open(dem, "w", driver="GTiff", height=z.shape[0], width=z.shape[1], count=1,
                       dtype="float32", crs="EPSG:32719",
                       transform=from_origin(300000, 5300000, 30, 30)) as dst:
        dst.write(z.astype("float32"), 1)
    raster_aligner._derive_slope_aspect(dem, tmp_path / "slp.tif", tmp_path / "asp.tif", 30.0)
    with rasterio.open(tmp_path / "asp.tif") as src:
        return int(np.median(src.read(1)[2:-2, 2:-2]))


def test_ladera_que_sube_al_norte_mira_al_sur(tmp_path):
    filas, cols = np.indices((10, 10))
    assert _ladera(tmp_path, 1000 - 10.0 * filas) == 180   # la fila 0 es la del norte


def test_ladera_que_sube_al_este_mira_al_oeste(tmp_path):
    filas, cols = np.indices((10, 10))
    assert _ladera(tmp_path, 1000 + 10.0 * cols) == 270
