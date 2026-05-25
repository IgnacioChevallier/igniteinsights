"""
Derives ELMFIRE-ready weather rasters from raw GFS outputs.

Inputs (EPSG:4326, 0.25°):
  gfs_u10  — eastward wind component at 10 m (m/s)
  gfs_v10  — northward wind component at 10 m (m/s)
  gfs_t2m  — temperature at 2 m (Kelvin)
  gfs_rh   — relative humidity at 2 m (%)

Outputs (matched to reference grid):
  ws.tif   — wind speed (mph), Int16
  wd.tif   — wind direction, meteorological from-direction (degrees, 0=N), Int16
  m1.tif   — 1-hour fuel moisture (%)
  m10.tif  — 10-hour fuel moisture (%)
  m100.tif — 100-hour fuel moisture (%)
"""
import logging
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

logger = logging.getLogger(__name__)


def derive_wind(
    u10_path: Path,
    v10_path: Path,
    reference_path: Path,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Produce ws.tif (mph, Int16) and wd.tif (degrees from N, Int16) on the reference grid."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ws_path = output_dir / "ws.tif"
    wd_path = output_dir / "wd.tif"

    u10 = _read_aligned(u10_path, reference_path)
    v10 = _read_aligned(v10_path, reference_path)

    ws_ms = np.sqrt(u10**2 + v10**2)
    ws_mph = ws_ms * 2.23694

    # Meteorological convention: direction FROM which wind blows, CW from north
    wd_deg = np.degrees(np.arctan2(-u10, -v10))
    wd_deg = (wd_deg + 360.0) % 360.0

    _write_like_reference(reference_path, ws_path, ws_mph.astype(np.float32), dtype="int16")
    _write_like_reference(reference_path, wd_path, wd_deg.astype(np.float32), dtype="int16")
    logger.info("Wind rasters written to %s", output_dir)
    return ws_path, wd_path


def derive_moisture(
    t2m_path: Path,
    rh_path: Path,
    reference_path: Path,
    output_dir: Path,
) -> tuple[Path, Path, Path]:
    """Produce m1/m10/m100.tif (%) using Nelson (1984) EMC equilibrium model."""
    output_dir.mkdir(parents=True, exist_ok=True)
    m1_path = output_dir / "m1.tif"
    m10_path = output_dir / "m10.tif"
    m100_path = output_dir / "m100.tif"

    t_kelvin = _read_aligned(t2m_path, reference_path)
    rh = _read_aligned(rh_path, reference_path)

    t_f = (t_kelvin - 273.15) * 9.0 / 5.0 + 32.0  # Kelvin → Fahrenheit
    rh = np.clip(rh, 0.0, 100.0)

    emc = _nelson_emc(t_f, rh)
    m1 = np.clip(emc, 1.0, 40.0)
    m10 = np.clip(emc + 2.0, 1.0, 40.0)
    m100 = np.clip(emc + 5.0, 1.0, 40.0)

    _write_like_reference(reference_path, m1_path, m1.astype(np.float32))
    _write_like_reference(reference_path, m10_path, m10.astype(np.float32))
    _write_like_reference(reference_path, m100_path, m100.astype(np.float32))
    logger.info("Moisture rasters written to %s", output_dir)
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
    """Read src raster reprojected to match reference grid, returned as 2-D float32 array."""
    with rasterio.open(reference_path) as ref:
        dst_transform = ref.transform
        dst_crs = ref.crs
        dst_shape = (ref.height, ref.width)

    with rasterio.open(src_path) as src:
        data = np.empty(dst_shape, dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=data,
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
    dtype: str = "float32",
) -> None:
    with rasterio.open(reference_path) as ref:
        profile = ref.meta.copy()
    nodata = -9999 if dtype == "int16" else -9999.0
    profile.update(dtype=dtype, count=1, nodata=nodata)
    out = np.round(data).astype(dtype) if dtype == "int16" else data
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(out, 1)
