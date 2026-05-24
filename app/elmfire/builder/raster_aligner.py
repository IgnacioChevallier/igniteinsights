"""
Reprojects a raw DEM (EPSG:4326) to the processing CRS (EPSG:32719, 30 m)
and derives slope and aspect rasters for ELMFIRE.

Outputs written to data/static/ and cached — only regenerated if missing.
"""
import logging
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject

logger = logging.getLogger(__name__)


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

    if not (dem_out.exists() and slp_out.exists() and asp_out.exists()):
        logger.info("Deriving topography from %s", dem_raw_path)
        _reproject_dem(dem_raw_path, dem_out, target_crs, resolution_m)
        _derive_slope_aspect(dem_out, slp_out, asp_out, resolution_m)
        logger.info("Topography written to %s", static_dir)
    else:
        logger.info("Topography already cached at %s — skipping", static_dir)

    return dem_out, slp_out, asp_out


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
            dtype="float32",
            nodata=-9999.0,
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
                dst_nodata=-9999.0,
            )


def _derive_slope_aspect(
    dem_path: Path, slp_path: Path, asp_path: Path, cell_size: float
) -> None:
    with rasterio.open(dem_path) as ds:
        elev = ds.read(1).astype(np.float32)
        nodata = ds.nodata or -9999.0
        profile = ds.meta.copy()
        profile.update(dtype="float32", nodata=-9999.0)

    valid = elev != nodata
    elev_filled = np.where(valid, elev, np.nan)

    # Central-difference gradient (in metres per metre = dimensionless)
    dz_dy, dz_dx = np.gradient(elev_filled, cell_size)

    slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    slope_deg = np.degrees(slope_rad)

    # Aspect: compass bearing from which slope descends (0=N, 90=E)
    math_angle = np.degrees(np.arctan2(-dz_dy, dz_dx))
    aspect_compass = 90.0 - math_angle
    aspect_compass = np.where(aspect_compass < 0, aspect_compass + 360.0, aspect_compass)
    aspect_compass = np.where(aspect_compass >= 360.0, aspect_compass - 360.0, aspect_compass)

    nodata_mask = ~valid
    slope_deg[nodata_mask] = -9999.0
    aspect_compass[nodata_mask] = -9999.0

    with rasterio.open(slp_path, "w", **profile) as dst:
        dst.write(slope_deg.astype(np.float32), 1)

    with rasterio.open(asp_path, "w", **profile) as dst:
        dst.write(aspect_compass.astype(np.float32), 1)
