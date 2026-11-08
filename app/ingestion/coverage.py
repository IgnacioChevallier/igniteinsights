"""Does an already-downloaded static raster still cover the configured AOI?

The static ingestions (DEM, WorldCover, canopy) skip re-downloading when the asset row and
its file both exist. That guard is blind to the AOI: widening `aoi_*` in config left every
static raster cut to the old, smaller footprint while the config claimed a larger domain,
and nothing failed — every derived raster silently inherited the old extent. Same
stale-artefact failure as the topography and fbfm40 caches, one layer further upstream.

See docs/arquitectura.md §A0.
"""
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# Rasters are cut to whole source tiles, so they overshoot the AOI by far more than this.
# The tolerance only absorbs float noise in the CRS transform.
_EPS_DEG = 1e-6


def aoi_bounds() -> tuple[float, float, float, float]:
    """Configured AOI as (west, south, east, north) in EPSG:4326."""
    return (settings.aoi_west, settings.aoi_south, settings.aoi_east, settings.aoi_north)


def covers_aoi(raster_path: Path) -> bool:
    """True when the raster's footprint contains the configured AOI.

    Reads the extent off the file rather than trusting `RasterAsset.bbox`: the bbox column
    is populated by each ingestion separately, and this check exists precisely because
    bookkeeping and reality had drifted apart.
    """
    import rasterio
    from rasterio.errors import RasterioError
    from rasterio.warp import transform_bounds

    try:
        with rasterio.open(raster_path) as src:
            west, south, east, north = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
    except (OSError, RasterioError):
        logger.warning("Cannot read extent of %s — treating as not covering", raster_path)
        return False

    aoi_w, aoi_s, aoi_e, aoi_n = aoi_bounds()
    covered = (
        west <= aoi_w + _EPS_DEG
        and south <= aoi_s + _EPS_DEG
        and east >= aoi_e - _EPS_DEG
        and north >= aoi_n - _EPS_DEG
    )
    if not covered:
        logger.info(
            "%s covers (%.4f, %.4f, %.4f, %.4f) but the AOI is (%.4f, %.4f, %.4f, %.4f) "
            "— re-ingesting",
            raster_path.name, west, south, east, north, aoi_w, aoi_s, aoi_e, aoi_n,
        )
    return covered
