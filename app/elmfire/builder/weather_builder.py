"""
Derives ELMFIRE-ready weather rasters from raw GFS outputs.

Inputs (EPSG:4326, 0.25°, one band per forecast hour):
  gfs_u10  — eastward wind component at 10 m (m/s)
  gfs_v10  — northward wind component at 10 m (m/s)
  gfs_t2m  — temperature at 2 m (Kelvin)
  gfs_rh   — relative humidity at 2 m (%)

Outputs (matched to reference grid, Float32, one band per forecast hour):
  ws.tif   — wind speed at 20 ft (mph)
  wd.tif   — wind direction, meteorological from-direction (degrees, 0=N)
  m1.tif   — 1-hour fuel moisture (%)
  m10.tif  — 10-hour fuel moisture (%)
  m100.tif — 100-hour fuel moisture (%)

**Band count is the time series.** ELMFIRE reads band *n* as the weather at
`SIMULATION_TSTART + n × DT_METEOROLOGY` and linearly interpolates between bands, so
the band count must cover the simulation horizon. A single-band raster paired with
`DT_METEOROLOGY = 3600` silently freezes weather for the whole run — no diurnal wind
peak, no afternoon RH minimum. See `namelist_writer.validate_weather_coverage()`.

Float32 (not Int16): the vendor tutorials declare `ws`/`wd` via `FLOAT_RASTER[n]=`.
Int16 mph also quantized wind to ±0.45 m/s for no benefit.
"""
import logging
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

logger = logging.getLogger(__name__)

# ── 10 m → 20 ft wind conversion ──────────────────────────────────────────────
# ELMFIRE follows the LANDFIRE/US fire-weather convention: WS is the 20-ft wind, not
# the 10 m wind meteorological models publish. Converted with the log wind profile
#     U(z) = U_ref · ln(z/z0) / ln(z_ref/z0)
# z0 is the surface roughness length and is the calibration knob here: 0.22 m
# reproduces the ~0.87 factor standard in fire weather (stations sited over
# vegetation). Open grassland (z0 = 0.03 m) would give ~0.91 instead — if the AOI's
# effective roughness is ever characterised, tune this rather than the factor.
GFS_WIND_HEIGHT_M = 10.0
ELMFIRE_WIND_HEIGHT_M = 6.096  # 20 ft
WIND_ROUGHNESS_LENGTH_M = 0.22

MS_TO_MPH = 2.23694
_NODATA = -9999.0


def wind_height_factor(
    z_from: float = GFS_WIND_HEIGHT_M,
    z_to: float = ELMFIRE_WIND_HEIGHT_M,
    z0: float = WIND_ROUGHNESS_LENGTH_M,
) -> float:
    """Log-profile scaling factor to move a wind speed from `z_from` to `z_to`."""
    if not (z_from > z0 and z_to > z0 and z0 > 0):
        raise ValueError("heights must exceed a positive roughness length z0")
    return math.log(z_to / z0) / math.log(z_from / z0)


def derive_wind(
    u10_path: Path,
    v10_path: Path,
    reference_path: Path,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Produce ws.tif (20-ft wind, mph) and wd.tif (degrees from N), Float32,
    one band per forecast hour, on the reference grid."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ws_path = output_dir / "ws.tif"
    wd_path = output_dir / "wd.tif"

    u10 = _read_aligned(u10_path, reference_path)
    v10 = _read_aligned(v10_path, reference_path)
    if u10.shape[0] != v10.shape[0]:
        raise ValueError(
            f"u10 has {u10.shape[0]} band(s) but v10 has {v10.shape[0]} — "
            "wind components must share a forecast time series"
        )

    ws_ms = np.sqrt(u10**2 + v10**2) * wind_height_factor()
    ws_mph = ws_ms * MS_TO_MPH

    # Meteorological convention: direction FROM which wind blows, CW from north.
    # Height conversion scales magnitude only, so direction is taken from raw u/v.
    wd_deg = (np.degrees(np.arctan2(-u10, -v10)) + 360.0) % 360.0

    _write_like_reference(reference_path, ws_path, ws_mph)
    _write_like_reference(reference_path, wd_path, wd_deg)
    logger.info(
        "Wind rasters written to %s (%d band(s), 20-ft factor %.3f)",
        output_dir,
        ws_mph.shape[0],
        wind_height_factor(),
    )
    return ws_path, wd_path


def derive_moisture(
    t2m_path: Path,
    rh_path: Path,
    reference_path: Path,
    output_dir: Path,
) -> tuple[Path, Path, Path]:
    """Produce m1/m10/m100.tif (%) using Nelson (1984) EMC, Float32, one band per
    forecast hour."""
    output_dir.mkdir(parents=True, exist_ok=True)
    m1_path = output_dir / "m1.tif"
    m10_path = output_dir / "m10.tif"
    m100_path = output_dir / "m100.tif"

    t_kelvin = _read_aligned(t2m_path, reference_path)
    rh = _read_aligned(rh_path, reference_path)
    if t_kelvin.shape[0] != rh.shape[0]:
        raise ValueError(
            f"t2m has {t_kelvin.shape[0]} band(s) but rh has {rh.shape[0]} — "
            "moisture inputs must share a forecast time series"
        )

    t_f = (t_kelvin - 273.15) * 9.0 / 5.0 + 32.0  # Kelvin → Fahrenheit
    rh = np.clip(rh, 0.0, 100.0)

    # ponytail: m10/m100 are the instantaneous EMC offset by +2/+5 %, which has no
    # physical basis — time-lag classes damp toward a running mean, they are not a
    # fixed offset from the current equilibrium. Correct fix needs a drying history
    # (several days of prior GFS), which the ingestion does not keep today.
    emc = _nelson_emc(t_f, rh)
    m1 = np.clip(emc, 1.0, 40.0)
    m10 = np.clip(emc + 2.0, 1.0, 40.0)
    m100 = np.clip(emc + 5.0, 1.0, 40.0)

    for path, data in [(m1_path, m1), (m10_path, m10), (m100_path, m100)]:
        _write_like_reference(reference_path, path, data)
    logger.info("Moisture rasters written to %s (%d band(s))", output_dir, m1.shape[0])
    return m1_path, m10_path, m100_path


# ── internal helpers ───────────────────────────────────────────────────────────

def _nelson_emc(t_f: np.ndarray, rh: np.ndarray) -> np.ndarray:
    """Nelson (1984) equilibrium moisture content (%)."""
    emc = np.zeros_like(t_f)
    lo = rh <= 10
    mid = (rh > 10) & (rh <= 50)
    hi = rh > 50
    emc[lo] = 0.03229 + 0.281073 * rh[lo] - 0.000578 * t_f[lo] * rh[lo]
    emc[mid] = 2.22749 + 0.160107 * rh[mid] - 0.014784 * t_f[mid]
    emc[hi] = 21.0606 + 0.005565 * rh[hi] ** 2 - 0.00035 * t_f[hi] * rh[hi] - 0.483199 * rh[hi]
    return emc


def _read_aligned(src_path: Path, reference_path: Path) -> np.ndarray:
    """Read every band of `src_path` reprojected onto the reference grid.

    Returns a 3-D (bands, height, width) float32 array — band order is preserved, so
    band *n* stays the n-th forecast hour.
    """
    with rasterio.open(reference_path) as ref:
        dst_transform = ref.transform
        dst_crs = ref.crs
        dst_shape = (ref.height, ref.width)

    with rasterio.open(src_path) as src:
        data = np.empty((src.count, *dst_shape), dtype=np.float32)
        for idx in range(src.count):
            reproject(
                source=rasterio.band(src, idx + 1),
                destination=data[idx],
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear,
            )
    return data


def _write_like_reference(
    reference_path: Path,
    output_path: Path,
    data: np.ndarray,
) -> None:
    """Write a (bands, height, width) Float32 stack onto the reference grid."""
    if data.ndim != 3:
        raise ValueError(f"expected a (bands, height, width) array, got shape {data.shape}")
    with rasterio.open(reference_path) as ref:
        profile = ref.meta.copy()
    profile.update(dtype="float32", count=data.shape[0], nodata=_NODATA)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(data.astype(np.float32))
