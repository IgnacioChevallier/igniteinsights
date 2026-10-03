"""
ELMFIRE canopy layer derivation.

  reproject_canopy  — reprojects Hansen CC or ETH CH raw raster to the reference
                      grid (EPSG:32719, 30 m) using bilinear resampling.
  derive_cbh_cbd    — derives canopy base height and bulk density from the
                      reprojected cc/ch rasters (see docs/historico/ETAPA-A-BASELINE.md §A4).
"""
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# ── Canopy structure derived from measured canopy rasters ───────────────────
# cbh/cbd used to be looked up from the FBFM40 code, which was both circular (a *surface*
# fuel model does not determine crown structure) and fragile: the table held 9 keys, so any
# new fuel code silently produced -9999. Derived from cc/ch instead, so the failure mode is
# gone rather than guarded. See docs/historico/ETAPA-A-BASELINE.md §A4.
#
# Method (deliberately simple; this is infrastructure, not the thesis contribution):
#   cbh = ch · f(cc)          self-pruning rises with stand density
#   cbd = cfl / (ch - cbh)    bulk density = canopy fuel load / canopy layer depth
#   cfl = cc · cfl_full       canopy cover as the available proxy for stocking
# Cruz, Alexander & Wakimoto (2003) model cbh/cbd from basal area and stand density, which
# we do not have for Los Alerces; cover and height are what Hansen GFC and ETH Canopy
# Height give us. Constants are named below so they can be revisited.
# ponytail: linear in cover, no species term. Revisit if a stand inventory ever exists.

# Below these, treat the pixel as having no crown fuel at all.
_MIN_CANOPY_COVER_FRAC = 0.10
_MIN_CANOPY_HEIGHT_M = 2.0

# Canopy base height as a fraction of canopy height, interpolated on canopy cover:
# open stands keep low branches, closed stands self-prune.
_CBH_FRACTION_OPEN = 0.20
_CBH_FRACTION_CLOSED = 0.50

# Canopy fuel load (kg/m²) at full cover. Typical conifer stands fall in 0.5-1.5 kg/m².
_CANOPY_FUEL_LOAD_FULL = 1.0

# Floor on canopy layer depth, so cbd cannot blow up when cbh approaches ch.
_MIN_CANOPY_DEPTH_M = 1.0

_NODATA = np.int16(-9999)


def reproject_canopy(
    raw_path: Path,
    reference_path: Path,
    output_path: Path,
    scale_factor: float = 1.0,
    resampling: str = "bilinear",
) -> Path:
    """
    Reproject a raw canopy raster (Hansen CC or ETH CH) to the reference grid.

    Output dtype is Int16 with nodata=-9999.
    scale_factor=10.0 converts ETH CH meters → 10×meters (ELMFIRE encoding).
    cc.tif: scale_factor=1.0 (Hansen percent 0–100 passes through as-is).
    resampling="nearest" for categorical layers (Hansen lossyear: bilinear would invent
    years between neighbours).
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
            resampling=Resampling[resampling],
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
    cc_path: Path,
    ch_path: Path,
    cbh_path: Path,
    cbd_path: Path,
) -> tuple[Path, Path]:
    """
    Derive canopy base height (10×meters, Int16) and canopy bulk density (100×kg/m³,
    Int16) from canopy cover and canopy height.

    cc.tif is percent 0-100; ch.tif is 10×meters. Both are already on the reference grid
    (written by reproject_canopy), so no reprojection happens here.

    Pixels with no meaningful canopy get cbh = cbd = 0. cbd = 0 is the control that
    matters: with no crown fuel there is no crown fire, whatever cbh says. Pixels where
    either input is nodata stay nodata, matching what cc.tif and ch.tif already do.

    cc.tif is rewritten with cover 0 where the canopy is shorter than _MIN_CANOPY_HEIGHT_M
    or its height is nodata.
    ELMFIRE takes the wind reduction under a canopy from (CC, CH): with CH ≈ 0 and CC ≥ 15 %
    it uses a sheltered factor of 0, and the cell gets no wind at all (AUDITORIA-FISICA.md,
    hallazgo 4: Hansen cover without ETH height, 0.1–2.6 % of the burnable cells).
    """
    import rasterio

    with rasterio.open(cc_path) as src:
        cc_raw = src.read(1)
        profile = src.meta.copy()
    with rasterio.open(ch_path) as src:
        ch_raw = src.read(1)

    known = (cc_raw != _NODATA) & (ch_raw != _NODATA)
    cc_frac = np.clip(cc_raw.astype(np.float32) / 100.0, 0.0, 1.0)
    ch_m = ch_raw.astype(np.float32) / 10.0  # ELMFIRE Int16 encoding → meters

    canopy = known & (cc_frac >= _MIN_CANOPY_COVER_FRAC) & (ch_m >= _MIN_CANOPY_HEIGHT_M)

    cbh_frac = _CBH_FRACTION_OPEN + (_CBH_FRACTION_CLOSED - _CBH_FRACTION_OPEN) * cc_frac
    cbh_m = ch_m * cbh_frac
    depth_m = np.maximum(ch_m - cbh_m, _MIN_CANOPY_DEPTH_M)
    cbd_kg_m3 = (cc_frac * _CANOPY_FUEL_LOAD_FULL) / depth_m

    cbh_out = np.zeros(cc_raw.shape, dtype=np.int16)
    cbd_out = np.zeros(cc_raw.shape, dtype=np.int16)
    cbh_out[canopy] = np.round(cbh_m[canopy] * 10.0).astype(np.int16)   # → 10×meters
    cbd_out[canopy] = np.round(cbd_kg_m3[canopy] * 100.0).astype(np.int16)  # → 100×kg/m³
    cbh_out[~known] = _NODATA
    cbd_out[~known] = _NODATA

    # ch nodata counts as no height: ELMFIRE clamps the height index to 0 (ICH =
    # MIN(MAX(NINT(CH),0),120), elmfire_init.f90:557), so a nodata height with CC >= 15 %
    # gives the same zero wind as CH = 0. In the benchmark preparations that is every
    # affected cell (Hansen cover where ETH has no height), not CH < 2 m.
    sin_altura = (ch_m < _MIN_CANOPY_HEIGHT_M) & (cc_raw > 0)
    cc_out = np.where(sin_altura, 0, cc_raw).astype(cc_raw.dtype)

    profile.update(dtype="int16", count=1, nodata=int(_NODATA))
    for out_path, data in [(cbh_path, cbh_out), (cbd_path, cbd_out), (cc_path, cc_out)]:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(data, 1)

    logger.info(
        "cbh/cbd derived from cc/ch — %.1f%% of the domain carries crown fuel",
        100.0 * canopy.sum() / max(canopy.size, 1),
    )
    return cbh_path, cbd_path

    return cbh_path, cbd_path
