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

_DEFAULT_BUFFER_M = 90.0   # 3 × 30 m cells


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

    # Signed distance function via 4-pass L1 sweep
    phi_cells = _signed_distance(fire_mask)
    phi_m = phi_cells * cell_size

    # Replace zero-fire-point distance with nodata where mask is empty after rasterize
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
        from shapely.geometry import shape

        gdf = gpd.GeoDataFrame({"geometry": [polygon], "id": [1]}, crs=crs_wkt)
        gdf.to_file(str(path))
    except Exception as exc:
        logger.warning("Could not write ignicion.shp: %s", exc)
