"""MODIS MCD64A1 v061: una banda por año calendario (1 = quemado ese año), ~463 m, sobre el AOI.

Ver docs/resultados/LO-YA-QUEMADO-PROPUESTA.md §5 (paso 2) y §11. Lo combina
scripts/anio_quema.py. Todos los años y no sólo el último: una celda que se quemó en 2021 y
otra vez en 2026 tiene que seguir viéndose quemada en 2021 al simular el incendio de 2026. La
versión de LYQ-2 (commit 8ddff5a) bajaba sólo el último año a mcd64a1_anio_quema_aoi.tif.

Necesita `earthengine-api`, que no es dependencia de este repo: se corre con el venv de
../mask-dataset-gen, que ya tiene las credenciales del proyecto de Earth Engine.

    ../mask-dataset-gen/.venv/bin/python scripts/exportar_mcd64a1.py

Es una sola imagen chica (~200 × 300 celdas): no consume cuota apreciable.
"""
import urllib.request
from pathlib import Path

import ee
import rasterio

PROYECTO = "ee-nachochevallier"
SINUSOIDAL_MODIS = "+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +R=6371007.181 +units=m +no_defs"
# La grilla extendida del benchmark (benchmark-2026-09-28, que cubre settings.aoi_*) con un
# margen de una celda MODIS.
AOI = (-72.18, -43.24, -71.04, -41.86)
DESDE = "2001-01-01"   # el primer año de Hansen lossyear
SALIDA = Path("data/raw/mcd64a1/mcd64a1_anios_aoi.tif")


if __name__ == "__main__":
    ee.Initialize(project=PROYECTO)
    coleccion = ee.ImageCollection("MODIS/061/MCD64A1").filterDate(DESDE, "2100-01-01")
    ultimo = ee.Date(coleccion.aggregate_max("system:time_start")).format("YYYY-MM").getInfo()
    proyeccion = coleccion.first().projection()
    bandas = [coleccion.filterDate(f"{a}-01-01", f"{a + 1}-01-01")
              .map(lambda img: img.select("BurnDate").gt(0)).max().unmask(0)
              .toByte().rename(f"a{a}")
              for a in range(int(DESDE[:4]), int(ultimo[:4]) + 1)]
    imagen = ee.Image.cat(bandas).reproject(proyeccion)
    url = imagen.getDownloadURL({"region": ee.Geometry.Rectangle(list(AOI)),
                                 "crs": proyeccion.crs().getInfo(),
                                 "crs_transform": proyeccion.getInfo()["transform"],
                                 "format": "GEO_TIFF"})
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, SALIDA)
    # Earth Engine escribe la sinusoidal de MODIS con datum WGS84; MODIS usa una esfera de
    # R = 6.371.007,181 m. Sin esto todo queda ~18,6 km al sur a -42° (LO-YA-QUEMADO §11).
    with rasterio.open(SALIDA, "r+") as dst:
        dst.crs = SINUSOIDAL_MODIS
    print(f"{SALIDA} (MCD64A1 {DESDE} a {ultimo})")
