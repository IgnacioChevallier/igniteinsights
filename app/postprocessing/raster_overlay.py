"""
Renders an ELMFIRE output GeoTIFF (time_of_arrival_*.tif, flin_*.tif) as a
colorized, web-mercator-ready PNG overlay for the map.

Reprojects to EPSG:4326, maps values through a fixed sequential color ramp
(ColorBrewer YlOrRd, 5 stops), and returns the corner coordinates MapLibre's
`image` source expects: [top-left, top-right, bottom-right, bottom-left].
"""
import base64
import io
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.warp import Resampling, calculate_default_transform, reproject

# ColorBrewer YlOrRd (5-class) — a standard sequential "heat" ramp for hazard data.
_RAMP_STOPS = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
_RAMP_COLORS = np.array(
    [
        [255, 255, 178],
        [254, 204, 92],
        [253, 141, 60],
        [240, 59, 32],
        [189, 0, 38],
    ],
    dtype=np.float64,
)


def render_raster_overlay(
    tif_path: Path, unit_divisor: float = 1.0, unit_label: str = ""
) -> dict | None:
    """Return {image_base64, coordinates, value_range, unit} for `tif_path`,
    reprojected to EPSG:4326 and colorized. Returns None if the file doesn't exist."""
    if not tif_path.exists():
        return None

    with rasterio.open(tif_path) as src:
        dst_crs = "EPSG:4326"
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )
        nodata = src.nodata
        dst = np.full((height, width), np.nan, dtype=np.float64)
        reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=nodata,
            dst_transform=transform,
            dst_crs=dst_crs,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )

    valid_mask = ~np.isnan(dst)
    scaled = dst / unit_divisor
    values = scaled[valid_mask]
    value_min = float(values.min()) if values.size else 0.0
    value_max = float(values.max()) if values.size else 0.0

    normalized = np.zeros_like(dst)
    if value_max > value_min:
        normalized[valid_mask] = (values - value_min) / (value_max - value_min)

    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    for channel in range(3):
        rgba[:, :, channel] = np.interp(
            normalized, _RAMP_STOPS, _RAMP_COLORS[:, channel]
        ).astype(np.uint8)
    rgba[:, :, 3] = np.where(valid_mask, 178, 0).astype(np.uint8)  # ~70% opacity

    buffer = io.BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(buffer, format="PNG")
    image_base64 = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

    west, south, east, north = rasterio.transform.array_bounds(height, width, transform)
    coordinates = [
        [west, north],  # top-left
        [east, north],  # top-right
        [east, south],  # bottom-right
        [west, south],  # bottom-left
    ]

    return {
        "image_base64": image_base64,
        "coordinates": coordinates,
        "value_range": [value_min, value_max],
        "unit": unit_label,
    }
