"""MODIS MCD64A1 v061: año de la última quema por celda (~463 m) sobre el AOI de la app.

Ver docs/resultados/LO-YA-QUEMADO-PROPUESTA.md §1 y §5 (paso 2). Codificación de Hansen
`lossyear`: 0 = sin quema, n = año 2000 + n. Lo combina scripts/anio_quema.py.

Necesita `earthengine-api`, que no es dependencia de este repo: se corre con el venv de
../mask-dataset-gen, que ya tiene las credenciales del proyecto de Earth Engine.

    ../mask-dataset-gen/.venv/bin/python scripts/exportar_mcd64a1.py

Es una sola imagen chica (~200 × 300 celdas): no consume cuota apreciable.
"""
import urllib.request
from pathlib import Path

import ee

PROYECTO = "ee-nachochevallier"
# La grilla extendida del benchmark (benchmark-2026-09-28, que cubre settings.aoi_*) con un
# margen de una celda MODIS.
AOI = (-72.18, -43.24, -71.04, -41.86)
DESDE = "2001-01-01"   # el primer año de Hansen lossyear
SALIDA = Path("data/raw/mcd64a1/mcd64a1_anio_quema_aoi.tif")


def anio_de_quema(img):
    anio = ee.Number(img.date().get("year")).subtract(2000)
    return img.select("BurnDate").gt(0).multiply(anio).toByte().rename("anio")


if __name__ == "__main__":
    ee.Initialize(project=PROYECTO)
    coleccion = ee.ImageCollection("MODIS/061/MCD64A1").filterDate(DESDE, "2100-01-01")
    ultimo = ee.Date(coleccion.aggregate_max("system:time_start")).format("YYYY-MM").getInfo()
    proyeccion = coleccion.first().projection()
    imagen = coleccion.map(anio_de_quema).max().reproject(proyeccion)   # la quema más reciente
    url = imagen.getDownloadURL({"region": ee.Geometry.Rectangle(list(AOI)),
                                 "crs": proyeccion.crs().getInfo(),
                                 "crs_transform": proyeccion.getInfo()["transform"],
                                 "format": "GEO_TIFF"})
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, SALIDA)
    print(f"{SALIDA} (MCD64A1 {DESDE} a {ultimo})")
