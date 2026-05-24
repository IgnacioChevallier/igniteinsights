"""
Derives fbfm40.tif (Scott & Burgan 40 fuel models) from ESA WorldCover land cover.

WorldCover v2.0 classes (2021) → FBFM40 crosswalk for Patagonian forest (Los Alerces).
Output is matched to the reference grid (EPSG:32719, 30 m).
"""
import logging
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

logger = logging.getLogger(__name__)

# WorldCover class → Scott & Burgan FBFM40 model number
# Reference: Scott & Burgan (2005), Gen. Tech. Rep. RMRS-GTR-153
_WORLDCOVER_TO_FBFM40: dict[int, int] = {
    10: 183,   # Tree cover         → TL3 Tall pine needles/cones
    20: 145,   # Shrubland          → SH5 High load dry shrub
    30: 102,   # Grassland          → GR2 Low load dry grass
    40: 101,   # Cropland           → GR1 Short sparse dry grass
    50: 91,    # Built-up           → NB1 Urban/suburban
    60: 93,    # Bare/sparse veg    → NB3 Agricultural/bare
    70: 93,    # Snow and ice       → NB3
    80: 98,    # Permanent water    → NB8 Open water
    90: 103,   # Herbaceous wetland → GR3 Low load very coarse humid
    95: 183,   # Mangroves          → TL3
    100: 101,  # Moss and lichen    → GR1
}
_NODATA_FBFM40 = 99   # NB9 Barrens (unburnable placeholder)


def worldcover_to_fbfm40(
    worldcover_path: Path,
    reference_path: Path,
    output_path: Path,
) -> Path:
    """Reclassify WorldCover to FBFM40 and reproject to the reference grid."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(reference_path) as ref:
        dst_transform = ref.transform
        dst_crs = ref.crs
        dst_shape = (ref.height, ref.width)

    with rasterio.open(worldcover_path) as src:
        wc_raw = np.empty(dst_shape, dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=wc_raw,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,  # land-cover: nearest-neighbor
        )

    wc_int = np.round(wc_raw).astype(np.int16)
    fbfm40 = np.full_like(wc_int, _NODATA_FBFM40, dtype=np.int16)
    for wc_class, fuel_model in _WORLDCOVER_TO_FBFM40.items():
        fbfm40[wc_int == wc_class] = fuel_model

    with rasterio.open(reference_path) as ref:
        profile = ref.meta.copy()
    profile.update(dtype="int16", count=1, nodata=_NODATA_FBFM40)

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(fbfm40, 1)

    logger.info("FBFM40 raster written to %s", output_path)
    return output_path
