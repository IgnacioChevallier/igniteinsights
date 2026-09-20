"""B0 — Does MapBiomas separate Patagonian shrubland better than ESA WorldCover?

One-shot probe, not an ingestion module. Reads the AOI window straight out of the
MapBiomas Argentina Collection 2 COG over HTTP (no 650 MB download), tabulates the class
distribution, and prints it next to the WorldCover-derived FBFM40 distribution.

The decision criterion is fixed BEFORE looking at the output (ETAPA-B-INSUMO-PATAGONICO.md
§B0): if shrubland stays in the same order as WorldCover (~0%), MapBiomas adds nothing here
and is dropped, with the negative result recorded. If it approaches the ~15% Godoy et al.
(2022) report for the adjacent Esquel-Trevelin area, it is promoted to a third comparison
point for the thesis.

    uv run python scripts/probe_mapbiomas.py [--year 2024]
"""
import argparse
import os

import numpy as np
import rasterio
from rasterio.windows import from_bounds

from app.config import settings

COG_URL = (
    "https://storage.googleapis.com/mapbiomas-public/initiatives/argentina"
    "/collection-2/coverage/argentina_coverage_{year}.tif"
)

# MapBiomas Argentina Collection 2 legend
# https://argentina.mapbiomas.org/wp-content/uploads/sites/12/2025/09/Leyenda_Code.pdf
LEGEND: dict[int, str] = {
    3: "Bosques cerrados",
    4: "Bosques abiertos",
    6: "Bosques inundables",
    66: "Arbustales cerrados",
    77: "Arbustales abiertos",
    63: "Mosaicos de arbustos y herbáceas",
    12: "Herbáceas",
    11: "Herbáceas inundables",
    73: "Turberas",
    18: "Agricultura",
    19: "Cultivos temporarios",
    36: "Cultivos perennes",
    15: "Pasturas",
    9: "Silvicultura",
    21: "Mosaico de usos",
    24: "Áreas urbanas",
    25: "Otras áreas no vegetadas",
    34: "Hielo y nieve permanente",
    33: "Ríos, lagunas, lagos y océano",
    27: "No observado",
    0: "SIN DATO — fuera de Argentina (lado chileno de la frontera)",
}

# No usable fuel class. 0 is the COG nodata: MapBiomas Argentina stops at the international
# border, and the western edge of the AOI crosses into Chile. 27 is the product's own
# "not observed".
NO_CLASS = {0, 27}

# Classes whose fire-carrying stratum is shrub-dominated. This is the number B0 exists to
# measure: WorldCover puts 0.04% of the AOI in shrubland, which Mermoz et al. (2005) and
# Godoy et al. (2022) both make implausible for this landscape.
SHRUB_CLASSES = {66, 77, 63}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2024, help="Collection 2 covers 1985-2024")
    args = ap.parse_args()

    # Only fetch the tiles the window touches.
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")

    url = COG_URL.format(year=args.year)
    bounds = (settings.aoi_west, settings.aoi_south, settings.aoi_east, settings.aoi_north)
    print(f"MapBiomas Argentina Collection 2, {args.year}")
    print(f"AOI  {bounds}\n")

    with rasterio.open(f"/vsicurl/{url}") as src:
        window = from_bounds(*bounds, transform=src.transform)
        data = src.read(1, window=window)

    codes, counts = np.unique(data, return_counts=True)
    total = int(counts.sum())
    px_ha = 0.09  # 30 m pixel

    print(f"{data.shape[1]} x {data.shape[0]} px = {total:,} px = {total * px_ha:,.0f} ha\n")
    print(f"{'code':>5}  {'share':>7}  {'ha':>12}  class")
    print("-" * 72)
    share = {}
    for code, n in sorted(zip(codes, counts), key=lambda p: -p[1]):
        code = int(code)
        share[code] = n / total
        name = LEGEND.get(code, "UNKNOWN — check the legend PDF")
        print(f"{code:>5}  {n / total:>6.2%}  {n * px_ha:>12,.0f}  {name}")

    shrub = sum(share.get(c, 0.0) for c in SHRUB_CLASSES)
    unburnable = sum(share.get(c, 0.0) for c in (24, 25, 33, 34))
    print("\n" + "=" * 72)
    print(f"{'shrub-dominated (66+77+63)':<44} {shrub:>7.2%}   WorldCover: 0.04%")
    print(f"{'unburnable (24+25+33+34)':<44} {unburnable:>7.2%}   WorldCover: 23.0%")
    print(f"{'peatland (73) — outside Rothermel scope':<44} {share.get(73, 0.0):>7.2%}")
    print(f"{'NO CLASS (0 nodata + 27 not observed)':<44} "
          f"{sum(share.get(c, 0.0) for c in NO_CLASS):>7.2%}   WorldCover: 0% (global)")
    print("=" * 72)
    print(
        "\nCriterion (ETAPA-B §B0): drop MapBiomas if shrubland stays ~0%; promote it to a\n"
        "third comparison point if it approaches the ~15% Godoy et al. (2022) report for\n"
        "the adjacent Esquel-Trevelin area."
    )


if __name__ == "__main__":
    main()
