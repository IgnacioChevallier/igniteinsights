"""
Reprojects a raw DEM (EPSG:4326) to the processing CRS (EPSG:32719, 30 m)
and derives slope and aspect rasters for ELMFIRE.

Outputs are cached in data/static/ and regenerated whenever the cache key changes —
see `_cache_key`. Bump `DERIVATION_VERSION` on ANY change to how dem/slp/asp are
produced, or the cache will keep serving the old rasters and the change will appear to
work while doing nothing.
"""
import json
import logging
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject

logger = logging.getLogger(__name__)

# Bump on any change to _reproject_dem / _derive_slope_aspect output (dtype, nodata,
# algorithm, units). Without this the `.exists()` check below serves stale rasters
# forever: the cache on disk was float32 from an earlier revision while the code had
# already moved to int16, and every simulation silently used the stale copy.
# 3: aspect was the upslope bearing; ELMFIRE read it as the facing direction and pushed
# every fire downslope (RESULTADOS-CSS-BAP, loop 2).
DERIVATION_VERSION = 3
_CACHE_KEY_FILE = ".topo_cache_key.json"


def reproject_and_derive_topo(
    dem_raw_path: Path,
    static_dir: Path,
    target_crs: str = "EPSG:32719",
    resolution_m: float = 30.0,
) -> tuple[Path, Path, Path]:
    """Reproject DEM and derive slope/aspect. Returns (dem, slp, asp) paths."""
    dem_out = static_dir / "dem.tif"
    slp_out = static_dir / "slp.tif"
    asp_out = static_dir / "asp.tif"

    static_dir.mkdir(parents=True, exist_ok=True)

    key = _cache_key(dem_raw_path, target_crs, resolution_m)
    key_path = static_dir / _CACHE_KEY_FILE
    outputs_present = dem_out.exists() and slp_out.exists() and asp_out.exists()
    cached_key = None
    if key_path.exists():
        try:
            cached_key = json.loads(key_path.read_text())
        except (OSError, ValueError):
            cached_key = None  # unreadable key → treat as a miss and rebuild

    if outputs_present and cached_key == key:
        logger.info("Topography cache hit at %s — skipping", static_dir)
        return dem_out, slp_out, asp_out

    if outputs_present:
        logger.info(
            "Topography cache stale (key %s → %s) — regenerating", cached_key, key
        )
    else:
        logger.info("Deriving topography from %s", dem_raw_path)

    _reproject_dem(dem_raw_path, dem_out, target_crs, resolution_m)
    _derive_slope_aspect(dem_out, slp_out, asp_out, resolution_m)
    key_path.write_text(json.dumps(key, sort_keys=True))
    logger.info("Topography written to %s", static_dir)

    return dem_out, slp_out, asp_out


def _cache_key(dem_raw_path: Path, target_crs: str, resolution_m: float) -> dict:
    """Identity of a cached topography set: the source DEM, the parameters it was
    derived with, and the version of the derivation code itself.

    Source identity uses size + mtime rather than a content hash — the raw DEM is
    hundreds of MB and is only ever replaced wholesale by a re-download.

    mtime is nanosecond, not whole seconds: a re-download that lands in the same second
    and produces the same file size would otherwise look identical and be served from
    cache. ponytail: hash the file if a filesystem with coarse timestamps ever matters.
    """
    stat = dem_raw_path.stat()
    return {
        "version": DERIVATION_VERSION,
        "src_name": dem_raw_path.name,
        "src_size": stat.st_size,
        "src_mtime_ns": stat.st_mtime_ns,
        "target_crs": target_crs,
        "resolution_m": resolution_m,
    }


def align_raster(
    src_path: Path,
    reference_path: Path,
    output_path: Path,
    resampling: Resampling = Resampling.bilinear,
) -> Path:
    """Reproject and snap src_path to match the grid of reference_path."""
    with rasterio.open(reference_path) as ref:
        dst_crs = ref.crs
        dst_transform = ref.transform
        dst_width = ref.width
        dst_height = ref.height
        dst_nodata = ref.nodata

    with rasterio.open(src_path) as src:
        profile = src.meta.copy()
        profile.update(
            crs=dst_crs,
            transform=dst_transform,
            width=dst_width,
            height=dst_height,
            nodata=dst_nodata if dst_nodata is not None else src.nodata,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(output_path, "w", **profile) as dst:
            for band_idx in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, band_idx),
                    destination=rasterio.band(dst, band_idx),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=resampling,
                )
    return output_path


# ── internal helpers ───────────────────────────────────────────────────────────

def _reproject_dem(src_path: Path, dst_path: Path, target_crs: str, res_m: float) -> None:
    with rasterio.open(src_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, target_crs, src.width, src.height, *src.bounds, resolution=(res_m, res_m)
        )
        profile = src.meta.copy()
        profile.update(
            crs=target_crs,
            transform=transform,
            width=width,
            height=height,
            dtype="int16",
            nodata=-9999,
        )
        with rasterio.open(dst_path, "w", **profile) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=target_crs,
                resampling=Resampling.bilinear,
                dst_nodata=-9999,
            )


def _derive_slope_aspect(
    dem_path: Path, slp_path: Path, asp_path: Path, cell_size: float
) -> None:
    with rasterio.open(dem_path) as ds:
        elev = ds.read(1).astype(np.float32)
        nodata = ds.nodata or -9999.0
        profile = ds.meta.copy()

    valid = elev != nodata
    elev_filled = np.where(valid, elev, np.nan)

    # Central-difference gradient (in metres per metre = dimensionless)
    dz_dy, dz_dx = np.gradient(elev_filled, cell_size)

    slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    slope_deg = np.degrees(slope_rad)

    # Aspect: compass bearing the slope FACES, i.e. the downslope direction (0=N, 90=E) —
    # the LANDFIRE convention ELMFIRE expects: it pushes spread toward ASP - 180
    # (elmfire_level_set.f90, SINASPM180), which is upslope only if ASP faces downslope.
    # Rows grow southward, so north is -dz_dy; downslope is minus the gradient.
    math_angle = np.degrees(np.arctan2(dz_dy, -dz_dx))
    aspect_compass = 90.0 - math_angle
    aspect_compass = np.where(aspect_compass < 0, aspect_compass + 360.0, aspect_compass)
    aspect_compass = np.where(aspect_compass >= 360.0, aspect_compass - 360.0, aspect_compass)

    nodata_mask = ~valid
    slope_out = np.round(slope_deg).astype(np.int16)
    aspect_out = np.round(aspect_compass).astype(np.int16)
    slope_out[nodata_mask] = -9999
    aspect_out[nodata_mask] = -9999

    profile.update(dtype="int16", nodata=-9999)
    with rasterio.open(slp_path, "w", **profile) as dst:
        dst.write(slope_out, 1)

    with rasterio.open(asp_path, "w", **profile) as dst:
        dst.write(aspect_out, 1)
