"""B6 — Build the three fuel maps on one grid so they can be compared.

Baseline (ESA WorldCover 2021), MapBiomas Argentina Col. 2 (2024) and CCS-BAP
(CIEFAP/MAyDS 2017) all reclassified to FBFM40 on the same reference grid, with the same
majority-class aggregation (ETAPA-A §A5) and the same gap-fill rule (IGN-20 §7.5): the two
Argentine products stop at the border, and that gap is filled from WorldCover so the west
edge of the domain is not artificially unburnable.

    uv run python scripts/build_fuel_maps.py [--reference data/static/dem.tif]
"""
import argparse
import logging
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

from app.elmfire.builder import fuels_builder as fb
from app.ingestion.coverage import covers_aoi

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("build_fuel_maps")

MAPBIOMAS_COG = (
    "https://storage.googleapis.com/mapbiomas-public/initiatives/argentina"
    "/collection-2/coverage/argentina_coverage_{year}.tif"
)
CCSBAP_SHP = Path("datasets/CH_2017_Ver20190521_Subido202000316/cob_2017_N3_aok_CH.shp")


def fetch_mapbiomas_window(reference: Path, out: Path, year: int = 2024) -> Path:
    """Cut the AOI window out of the public COG instead of downloading 650 MB."""
    if out.exists() and covers_aoi(out):
        log.info("MapBiomas window already local at %s", out)
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(reference) as ref:
        west, south, east, north = transform_bounds(ref.crs, "EPSG:4326", *ref.bounds)
    pad = 0.02  # margin so the reprojection has data past the edges
    with rasterio.open(MAPBIOMAS_COG.format(year=year)) as src:
        window = from_bounds(west - pad, south - pad, east + pad, north + pad, src.transform)
        data = src.read(1, window=window)
        profile = src.profile | {
            "height": data.shape[0], "width": data.shape[1], "count": 1,
            "transform": src.window_transform(window), "driver": "GTiff", "compress": "deflate",
        }
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(data, 1)
    log.info("MapBiomas window %s written to %s", data.shape, out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", type=Path, default=Path("data/static/dem.tif"))
    ap.add_argument("--out-dir", type=Path, default=Path("data/static/fuel_maps"))
    ap.add_argument("--mapbiomas-years", type=int, nargs="+", default=[2024])
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    baseline = fb.raster_to_fbfm40(
        Path("data/raw/worldcover/esa_worldcover_v200_10m.tif"), args.reference,
        args.out_dir / "fbfm40_worldcover.tif", fb.WORLDCOVER_TO_FBFM40, fb.WORLDCOVER_SOURCE_ID,
    )
    # 2024 es el mapa que sirve la app (fbfm40_mapbiomas.tif). Otros años, para validar
    # incendios anteriores sin fuga temporal (IGN-26 §Benchmark), llevan el año en el nombre.
    for year in args.mapbiomas_years:
        salida = args.out_dir / ("fbfm40_mapbiomas.tif" if year == 2024
                                 else f"fbfm40_mapbiomas{year}.tif")
        mapbiomas = fb.raster_to_fbfm40(
            fetch_mapbiomas_window(args.reference,
                                   Path(f"data/raw/mapbiomas/mapbiomas_{year}_aoi.tif"), year),
            args.reference, salida,
            fb.MAPBIOMAS_TO_FBFM40, fb.MAPBIOMAS_SOURCE_ID, fill_path=baseline,
        )
    ccsbap = fb.ccsbap_to_fbfm40(
        CCSBAP_SHP, args.reference, args.out_dir / "fbfm40_ccsbap.tif", fill_path=baseline,
    )

    maps = {"WorldCover": baseline, "MapBiomas": mapbiomas, "CCS-BAP": ccsbap}
    report(maps)


def report(maps: dict[str, Path]) -> None:
    """Distribution by fuel type and the three numbers the thesis argues about."""
    rows = {}
    for name, path in maps.items():
        with rasterio.open(path) as src:
            a = src.read(1)
        total = a.size
        by_type: dict[str, float] = {}
        for code in np.unique(a):
            info = fb.fuel_model_info(int(code))
            share = 100 * float((a == code).sum()) / total
            by_type[info["fuel_type"]] = by_type.get(info["fuel_type"], 0.0) + share
        rows[name] = by_type

    types = ["NB", "GR", "GS", "SH", "TU", "TL", "SB"]
    print("\n=== Superficie por tipo de combustible (% de la grilla) ===")
    print(f"{'Tipo':6s}" + "".join(f"{n:>13s}" for n in maps))
    for t in types:
        if any(rows[n].get(t, 0) > 0 for n in maps):
            print(f"{t:6s}" + "".join(f"{rows[n].get(t, 0):12.2f}%" for n in maps))

    print("\n=== Detalle por modelo ===")
    for name, path in maps.items():
        with rasterio.open(path) as src:
            a = src.read(1)
        codes, counts = np.unique(a, return_counts=True)
        top = sorted(zip(codes, counts), key=lambda p: -p[1])
        print(f"\n{name}:")
        for code, n in top:
            info = fb.fuel_model_info(int(code))
            print(f"   {info['name']:6s} ({int(code):3d})  "
                  f"{100 * n / a.size:6.2f}%  {info['fuel_type_label']}")


if __name__ == "__main__":
    main()
