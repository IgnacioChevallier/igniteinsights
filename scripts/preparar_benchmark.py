"""Estáticos del benchmark sobre una caja más grande que el AOI de la app.

La preparación que usan los casos existentes (`data/elmfire/inputs/d1c0fa5b…`) cubre el AOI
de septiembre, que no llega a Las Golondrinas (norte) ni al borde oeste de Cerro Plataforma.
Esto arma una preparación nueva, en otro directorio, sin tocar la vieja: los casos ya
empaquetados siguen reproducibles.

    uv run python scripts/preparar_benchmark.py --caja -72.10 -43.20 -71.10 -41.90 \\
        --salida data/elmfire/inputs/benchmark-2026-09-28

Topografía (COP30 de OpenTopography, reproyectada y con pendiente y orientación), dosel
(Hansen + ETH, igual que `preparation/service.py`), ADJ uniforme 1 y los mapas de combustible
del benchmark: WorldCover 2021 (también es el relleno del hueco fronterizo) y CCS-BAP 2013 y
2017 con el mismo crosswalk.
"""
import argparse
import logging
from pathlib import Path

import numpy as np
import rasterio

from app.elmfire.builder import canopy_builder, raster_aligner
from app.elmfire.builder import fuels_builder as fb
from app.ingestion.topography.opentopography.client import OpenTopographyClient
from app.ingestion.topography.opentopography.schemas import BoundingBox

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

CANOPY = Path("data/static/canopy/2026-05-24")
WORLDCOVER = Path("data/raw/worldcover/esa_worldcover_v200_10m.tif")
CCSBAP = {2013: Path("datasets/CH_2013_Ver20190521_Subido202000316/cob_2013_N3_aok_CH.shp"),
          2017: Path("datasets/CH_2017_Ver20190521_Subido202000316/cob_2017_N3_aok_CH.shp")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--caja", type=float, nargs=4, metavar=("O", "S", "E", "N"), required=True)
    ap.add_argument("--salida", type=Path, required=True)
    args = ap.parse_args()
    salida: Path = args.salida
    salida.mkdir(parents=True, exist_ok=True)

    crudo = salida / "dem_cop30_raw.tif"
    if not crudo.exists():
        o, s, e, n = args.caja
        OpenTopographyClient().download_dem(BoundingBox(west=o, south=s, east=e, north=n), crudo)
    dem, _, _ = raster_aligner.reproject_and_derive_topo(crudo, salida)

    canopy_builder.reproject_canopy(CANOPY / "hansen_treecover2000.tif", dem, salida / "cc.tif")
    canopy_builder.reproject_canopy(CANOPY / "eth_canopy_height.tif", dem, salida / "ch.tif", 10.0)
    canopy_builder.derive_cbh_cbd(salida / "cc.tif", salida / "ch.tif", salida / "cbh.tif",
                                  salida / "cbd.tif")
    with rasterio.open(dem) as ref:
        perfil = ref.profile | {"dtype": "float32", "nodata": -9999.0}
        forma = (ref.height, ref.width)
    with rasterio.open(salida / "adj.tif", "w", **perfil) as dst:
        dst.write(np.ones(forma, dtype="float32"), 1)

    relleno = fb.raster_to_fbfm40(WORLDCOVER, dem, salida / "fbfm40_worldcover2021.tif",
                                  fb.WORLDCOVER_TO_FBFM40, fb.WORLDCOVER_SOURCE_ID)
    for anio, shp in CCSBAP.items():
        fb.ccsbap_to_fbfm40(shp, dem, salida / f"fbfm40_ccsbap{anio}.tif", fill_path=relleno)


if __name__ == "__main__":
    main()
