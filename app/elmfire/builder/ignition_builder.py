"""
Builds the ignition layer (phi.tif) for ELMFIRE from FIRMS fire detection points.

phi.tif is ELMFIRE's initial level-set field, in ELMFIRE's own convention:
  phi = -1  inside the fire perimeter (burning cells)
  phi = +1  outside (unburned)

Delegates detection-points → burn polygon to perimeter_reconstruction (clustering +
concave hull) and rasterizes it.

**Not a signed distance.** ELMFIRE's tutorials and verification cases write phi = +1
everywhere and ignite cells at -1; its level set (superbee-limited upwinding on a
2-cell tagged band, elmfire_level_set.f90) advances the front at the Rothermel rate
only on that ±1 field. Until 2026-09-29 this builder wrote the signed distance in
metres (+30, +60, … outside): the front then moved at ~0.5× the rate ELMFIRE computed,
in every direction and at every wind speed (AUDITORIA-FISICA.md, hallazgo 2;
scripts/pruebas_fisicas.py).
"""
import logging
from pathlib import Path

import numpy as np
import rasterio
import rasterio.features
from shapely.geometry import mapping

from app.elmfire.builder import perimeter_reconstruction

logger = logging.getLogger(__name__)

# Buffer radius for detections in clusters too small for hull reconstruction
# (isolated spot fires). VIIRS nominal pixel width — the detection's footprint.
_DEFAULT_BUFFER_M = perimeter_reconstruction.VIIRS_PIXEL_M

# ELMFIRE's own raster loader resets any PHI0 value < -1.1 back to +1.0 (unburned) —
# a sanity clamp against nodata/garbage (elmfire_io.f90: WHERE(PHI0 < -1.1) PHI0 = 1.0).
# So the burning value must stay strictly above -1.1.
PHI_IGNITION_FLOOR = -1.0  # public: the playground writes phi too
PHI_UNBURNED = 1.0


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
        buffer_m: radius in metres for detections outside hullable clusters

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
        profile = ref.meta.copy()

    profile.update(dtype="float32", count=1, nodata=-9999.0, compress="deflate")

    if not fire_points:
        logger.warning("No fire detections — writing an all-unburned phi (no ignition)")
        _write_phi(np.zeros((height, width), dtype=bool), profile, phi_path)
        return phi_path, shp_path

    # Project fire points from EPSG:4326 to the reference CRS
    from pyproj import Transformer
    transformer = Transformer.from_crs("EPSG:4326", str(crs), always_xy=True)
    proj_points = [transformer.transform(lon, lat) for lon, lat in fire_points]

    # Cluster detections into fire events and reconstruct each event's perimeter
    burn_polygon = perimeter_reconstruction.reconstruct_burn_polygon(
        proj_points, point_buffer_m=buffer_m
    )

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
            "writing an all-unburned phi (no ignition)",
            len(fire_points),
        )
        # +1, not -9999: ELMFIRE would reset -9999 to +1 anyway, but every reader here
        # takes phi <= 0 as burning and would see the whole domain on fire.
        _write_phi(fire_mask, profile, phi_path)
        return phi_path, shp_path

    _write_phi(fire_mask, profile, phi_path)
    _write_shapefile(burn_polygon, str(crs), shp_path)
    logger.info(
        "Ignition layer: %d detections, %d burning cells → %s",
        len(fire_points),
        fire_mask.sum(),
        phi_path,
    )
    return phi_path, shp_path


def build_ignition_from_mask(
    fire_mask: np.ndarray,
    reference_raster: Path,
    output_dir: Path,
) -> Path:
    """Build phi.tif from an already-burned mask on the reference grid.

    What a chained validation window needs: the area a previous run predicted as burned
    becomes the next run's ignition, with no perimeter reconstruction in between —
    re-hulling it would burn cells the model never reached.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    phi_path = output_dir / "phi.tif"
    with rasterio.open(reference_raster) as ref:
        profile = ref.meta.copy()
        if fire_mask.shape != (ref.height, ref.width):
            raise ValueError(f"mask {fire_mask.shape} does not match the reference grid")
    profile.update(dtype="float32", count=1, nodata=-9999.0, compress="deflate")
    _write_phi(fire_mask.astype(bool), profile, phi_path)
    return phi_path


# ── internal helpers ───────────────────────────────────────────────────────────

def _write_phi(fire_mask: np.ndarray, profile: dict, phi_path: Path) -> None:
    """ELMFIRE's ±1 field (see the module docstring for why not a signed distance)."""
    phi = np.where(fire_mask, PHI_IGNITION_FLOOR, PHI_UNBURNED)
    with rasterio.open(phi_path, "w", **profile) as dst:
        dst.write(phi.astype(np.float32), 1)


def _write_shapefile(polygon, crs_wkt: str, path: Path) -> None:
    try:
        import geopandas as gpd

        gdf = gpd.GeoDataFrame({"geometry": [polygon], "id": [1]}, crs=crs_wkt)
        gdf.to_file(str(path))
    except Exception as exc:
        logger.warning("Could not write ignicion.shp: %s", exc)
