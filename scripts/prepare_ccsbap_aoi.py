"""Cut the CCS-BAP layer down to the AOI so the pipeline can carry it.

The delivered shapefile is the whole province (585 MB) and lives outside `data/`, which
is the only tree the API and runner containers mount. This writes an AOI-sized GeoPackage
under data/raw/ccsbap/ — one file instead of six, no 10-character field names, and no
encoding guessing, which matters for classes like "Ñire Bajo".

Native CRS (POSGAR94 Faja 1) is preserved: the raster builder reprojects once, to the
processing grid. Reprojecting here as well would move vertices twice for nothing.

    uv run python scripts/prepare_ccsbap_aoi.py
"""
import argparse
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from app.config import settings

SOURCE = Path("datasets/CH_2017_Ver20190521_Subido202000316/cob_2017_N3_aok_CH.shp")
MARGEN_GRADOS = 0.02  # ~2 km, para que el recorte no muerda el borde del dominio


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=SOURCE)
    ap.add_argument("--out", type=Path, default=Path("data/raw/ccsbap/ccsbap_2017_aoi.gpkg"))
    args = ap.parse_args()

    aoi = gpd.GeoSeries([box(
        settings.aoi_west - MARGEN_GRADOS, settings.aoi_south - MARGEN_GRADOS,
        settings.aoi_east + MARGEN_GRADOS, settings.aoi_north + MARGEN_GRADOS,
    )], crs="EPSG:4326")

    gdf = gpd.read_file(args.source, bbox=aoi.to_crs("EPSG:22181"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(args.out, driver="GPKG", layer="cobertura")
    print(f"{len(gdf):,} polígonos → {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")
    print("clases N3:", gdf["Ley_N3"].nunique(), "· CRS:", gdf.crs.name)


if __name__ == "__main__":
    main()
