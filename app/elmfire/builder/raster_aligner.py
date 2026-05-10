"""
Raster alignment for ELMFIRE inputs.

Reprojects and crops all input rasters to a common grid:
  - CRS: EPSG:32719 (UTM Zone 19S)
  - Resolution: 30 m
  - Extent: AOI bounding box

All inputs to ELMFIRE must share identical CRS, resolution, and extent.
Uses gdalwarp under the hood (via subprocess or rasterio).

TODO Sprint siguiente: implement full alignment pipeline.
"""
from pathlib import Path


def align_rasters(input_paths: list[Path], reference_path: Path, output_dir: Path) -> list[Path]:
    """Reproject and crop all rasters to match reference grid."""
    raise NotImplementedError("raster_aligner: sprint siguiente")
