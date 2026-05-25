"""
ELMFIRE canopy layer derivation.

  reproject_canopy  — reprojects Hansen CC or ETH CH raw raster to the reference
                      grid (EPSG:32719, 30 m) using bilinear resampling.
  derive_cbh_cbd    — derives canopy base height (m) and bulk density (kg/m³)
                      from the fbfm40 raster via Scott & Reinhardt (2005) tables.
"""
from pathlib import Path

import numpy as np

# ── Scott & Reinhardt (2005) FBFM40 lookup tables ───────────────────────────
# Keys match the FBFM40 codes produced by fuels_builder.worldcover_to_fbfm40().
# Values are pre-scaled to ELMFIRE's Int16 encoding:
#   cbh: 10×meters (e.g. 0.3 m → 3)
#   cbd: 100×kg/m³ (e.g. 0.08 kg/m³ → 8)

_FBFM40_CBH: dict[int, int] = {
    91: 0,    # NB1 Urban
    93: 0,    # NB3 Bare/sparse
    98: 0,    # NB8 Water
    99: 0,    # NB9 Nodata
    101: 3,   # GR1 Sparse grass  (0.3 m)
    102: 3,   # GR2 Low dry grass  (0.3 m)
    103: 3,   # GR3 Humid grass    (0.3 m)
    145: 15,  # SH5 High dry shrub (1.5 m)
    183: 15,  # TL3 Conifer litter (1.5 m)
}

_FBFM40_CBD: dict[int, int] = {
    91: 0,    # NB1
    93: 0,    # NB3
    98: 0,    # NB8
    99: 0,    # NB9
    101: 8,   # GR1 (0.08 kg/m³)
    102: 8,   # GR2
    103: 8,   # GR3
    145: 12,  # SH5 (0.12 kg/m³)
    183: 20,  # TL3 (0.20 kg/m³)
}

_NODATA = np.int16(-9999)


def reproject_canopy(
    raw_path: Path,
    reference_path: Path,
    output_path: Path,
    scale_factor: float = 1.0,
) -> Path:
    """
    Reproject a raw canopy raster (Hansen CC or ETH CH) to the reference grid.

    Output dtype is Int16 with nodata=-9999.
    scale_factor=10.0 converts ETH CH meters → 10×meters (ELMFIRE encoding).
    cc.tif: scale_factor=1.0 (Hansen percent 0–100 passes through as-is).
    """
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import reproject as warp_reproject

    with rasterio.open(reference_path) as ref:
        dst_transform = ref.transform
        dst_crs = ref.crs
        dst_shape = (ref.height, ref.width)

    with rasterio.open(raw_path) as src:
        src_nodata = src.nodata
        data_raw = np.empty(dst_shape, dtype=np.float32)
        data_raw[:] = float(_NODATA)

        warp_reproject(
            source=rasterio.band(src, 1),
            destination=data_raw,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.bilinear,
            src_nodata=src_nodata,
            dst_nodata=float(_NODATA),
        )

    valid = data_raw != float(_NODATA)
    if scale_factor != 1.0:
        data_raw[valid] = data_raw[valid] * scale_factor

    out = np.full(dst_shape, _NODATA, dtype=np.int16)
    out[valid] = np.round(data_raw[valid]).astype(np.int16)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(reference_path) as ref:
        profile = ref.meta.copy()
    profile.update(dtype="int16", count=1, nodata=int(_NODATA))

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(out, 1)

    return output_path


def derive_cbh_cbd(
    fbfm40_path: Path,
    reference_path: Path,
    cbh_path: Path,
    cbd_path: Path,
) -> tuple[Path, Path]:
    """
    Derive canopy base height (10×meters, Int16) and bulk density (100×kg/m³, Int16)
    from fbfm40 via Scott & Reinhardt (2005).

    fbfm40 is assumed to already be in the reference grid (produced by fuels_builder),
    so no reprojection is needed — values are read and lookup-mapped directly.
    """
    import rasterio

    with rasterio.open(fbfm40_path) as src:
        fbfm = src.read(1).astype(np.int16)

    with rasterio.open(reference_path) as ref:
        profile = ref.meta.copy()
    profile.update(dtype="int16", count=1, nodata=int(_NODATA))

    for out_path, table in [(cbh_path, _FBFM40_CBH), (cbd_path, _FBFM40_CBD)]:
        result = np.full(fbfm.shape, _NODATA, dtype=np.int16)
        for code, value in table.items():
            result[fbfm == code] = value

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(result, 1)

    return cbh_path, cbd_path
