"""
Builds the ignition layer for ELMFIRE from FIRMS fire detections.

Produces:
  - phi.tif  — signed distance function raster (negative inside fire, positive outside)
  - ignicion.shp — ignition polygon shapefile

Uses FIRMS FireDetection points to define the initial fire perimeter.

TODO Sprint siguiente: implement phi.tif generation via shapely buffer + rasterio rasterize.
"""
from pathlib import Path


def build_ignition_layer(
    fire_points: list[tuple[float, float]],
    reference_raster: Path,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Return (phi.tif path, ignicion.shp path)."""
    raise NotImplementedError("ignition_builder: sprint siguiente")
