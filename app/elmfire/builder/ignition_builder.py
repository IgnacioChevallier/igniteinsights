"""
Builds the ignition layer (phi.tif) for ELMFIRE from FIRMS fire detection points.

phi.tif is a signed distance function raster:
  phi < 0  inside the fire perimeter (igniting cells)
  phi > 0  outside the fire perimeter (unburned)
  phi = 0  at the fire front

Uses shapely to buffer points into a burn polygon, rasterio to rasterize,
then a 4-pass sweep to compute the L1 signed distance in metres.
"""
import logging
from pathlib import Path

import numpy as np
import rasterio
import rasterio.features
from shapely.geometry import Point, mapping

logger = logging.getLogger(__name__)

# Tunable app-side preprocessing heuristic (not an ELMFIRE-mandated value), set to
# VIIRS's own nominal pixel width so adjacent detections of one contiguous fire
# front overlap after buffering and merge into one ignition polygon, instead of
# fragmenting into many disjoint blobs that each spread/grow independently.
# Empirically (real DB data, 633 detections over a real 48h single-fire window):
# 90m -> 162 fragments, 200m -> 47, 300m -> 32, 400m -> 27, with diminishing
# returns beyond that. This buffer meaningfully reduces fragmentation but does not
# eliminate it — real, spread-out multi-day fire complexes and the twice-daily
# VIIRS revisit gap leave genuine spatial gaps no buffer size alone can close;
# that would need proper fire-front reconstruction (e.g. clustering + alpha
# shapes), which is out of scope here.
_DEFAULT_BUFFER_M = 375.0

# ELMFIRE's own raster loader resets any PHI0 value < -1.1 back to +1.0 (unburned) —
# a sanity clamp against nodata/garbage (elmfire_io.f90: WHERE(PHI0 < -1.1) PHI0 = 1.0).
# A signed-distance-in-meters field goes far more negative than that for any interior
# cell, so without this floor every ignition we write gets silently erased before the
# simulation starts. Must stay strictly above -1.1.
_PHI_IGNITION_FLOOR = -1.0


def build_ignition_layer(
    fire_points: list[tuple[float, float]],
    reference_raster: Path,
    output_dir: Path,
    buffer_m: float = _DEFAULT_BUFFER_M,
) -> tuple[Path, Path]:
    """
    Build phi.tif and ignicion.shp.

    Args:
        fire_points: list of (longitude, latitude) in EPSG:4326
        reference_raster: path to dem.tif (defines the output grid)
        output_dir: destination directory
        buffer_m: radius in metres to buffer each fire detection point

    Returns:
        (phi_path, shp_path)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    phi_path = output_dir / "phi.tif"
    shp_path = output_dir / "ignicion.shp"

    with rasterio.open(reference_raster) as ref:
        crs = ref.crs
        transform = ref.transform
        height, width = ref.height, ref.width
        cell_size = abs(transform.a)   # metres per pixel (UTM CRS)
        profile = ref.meta.copy()

    profile.update(dtype="float32", count=1, nodata=-9999.0)

    if not fire_points:
        logger.warning("No fire detections — writing uniform phi=-9999 (no ignition)")
        phi = np.full((height, width), -9999.0, dtype=np.float32)
        with rasterio.open(phi_path, "w", **profile) as dst:
            dst.write(phi, 1)
        return phi_path, shp_path

    # Project fire points from EPSG:4326 to the reference CRS
    from pyproj import Transformer
    transformer = Transformer.from_crs("EPSG:4326", str(crs), always_xy=True)
    proj_points = [transformer.transform(lon, lat) for lon, lat in fire_points]

    # Buffer each projected point and union them into a single polygon
    from shapely.ops import unary_union
    polygons = [Point(x, y).buffer(buffer_m) for x, y in proj_points]
    burn_polygon = unary_union(polygons)

    # Rasterize polygon into a binary mask (1 = fire, 0 = no fire)
    shapes = [(mapping(burn_polygon), 1)]
    fire_mask = rasterio.features.rasterize(
        shapes,
        out_shape=(height, width),
        transform=transform,
        fill=0,
        dtype=np.uint8,
    ).astype(bool)

    if not fire_mask.any():
        logger.warning(
            "Ignition layer: %d detections projected but none fall within raster bounds — "
            "writing nodata phi (no ignition)",
            len(fire_points),
        )
        phi_out = np.full((height, width), -9999.0, dtype=np.float32)
        with rasterio.open(phi_path, "w", **profile) as dst:
            dst.write(phi_out, 1)
        return phi_path, shp_path

    # Signed distance function via 4-pass L1 sweep
    phi_cells = _signed_distance(fire_mask)
    phi_m = phi_cells * cell_size
    phi_m = np.where(phi_m < 0, np.maximum(phi_m, _PHI_IGNITION_FLOOR), phi_m)
    phi_out = phi_m.astype(np.float32)

    with rasterio.open(phi_path, "w", **profile) as dst:
        dst.write(phi_out, 1)

    _write_shapefile(burn_polygon, str(crs), shp_path)
    logger.info(
        "Ignition layer: %d detections, %d burning cells → %s",
        len(fire_points),
        fire_mask.sum(),
        phi_path,
    )
    return phi_path, shp_path


# ── internal helpers ───────────────────────────────────────────────────────────

def _signed_distance(fire_mask: np.ndarray) -> np.ndarray:
    """
    L1 signed distance (in cells).
      phi < 0 inside fire (fire_mask == True)
      phi > 0 outside fire (fire_mask == False)
    """
    INF = float(fire_mask.size + 1)

    def _dt(source: np.ndarray) -> np.ndarray:
        """L1 distance transform: 0 at source, increasing elsewhere."""
        d = np.full(source.shape, INF)
        d[source] = 0.0
        rows, cols = d.shape
        for i in range(1, rows):
            d[i] = np.minimum(d[i], d[i - 1] + 1)
        for j in range(1, cols):
            d[:, j] = np.minimum(d[:, j], d[:, j - 1] + 1)
        for i in range(rows - 2, -1, -1):
            d[i] = np.minimum(d[i], d[i + 1] + 1)
        for j in range(cols - 2, -1, -1):
            d[:, j] = np.minimum(d[:, j], d[:, j + 1] + 1)
        return d

    dist_outside = _dt(fire_mask)         # dist from non-fire to nearest fire cell
    dist_inside = _dt(~fire_mask)         # dist from fire to nearest non-fire cell

    phi = np.where(fire_mask, -dist_inside, dist_outside)
    return phi


def _write_shapefile(polygon, crs_wkt: str, path: Path) -> None:
    try:
        import geopandas as gpd

        gdf = gpd.GeoDataFrame({"geometry": [polygon], "id": [1]}, crs=crs_wkt)
        gdf.to_file(str(path))
    except Exception as exc:
        logger.warning("Could not write ignicion.shp: %s", exc)
