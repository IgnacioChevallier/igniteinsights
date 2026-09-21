"""Compact spatial wind fields for the map.

The authoritative inputs are ``ws.tif`` and ``wd.tif``: the 20-ft wind rasters ELMFIRE
actually consumed. The files are on the fine simulation grid even though the underlying
GFS product is 0.25 degrees, so the dashboard receives a deliberately small WGS84 grid.
It is dense enough for smooth visual interpolation without pretending to add forecast
resolution.
"""

import json
import logging
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.warp import reproject, transform_bounds
from rasterio.warp import transform as warp_transform

logger = logging.getLogger(__name__)

_COMPASS = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
_NODATA = -9999.0
_MAX_GRID_DIMENSION = 48
WIND_FIELD_FILENAME = "wind-field.json"


def compass_point(azimuth_deg: float) -> str:
    return _COMPASS[int((azimuth_deg % 360.0) / 45.0 + 0.5) % 8]


def wind_components(
    speed_mph: np.ndarray, direction_from_deg: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Convert meteorological from-direction into eastward/northward to-components."""
    theta = np.radians(direction_from_deg)
    return speed_mph * -np.sin(theta), speed_mph * -np.cos(theta)


def _grid_shape(source_width: int, source_height: int, maximum: int) -> tuple[int, int]:
    if source_width <= 0 or source_height <= 0:
        raise ValueError("wind rasters must have positive dimensions")
    if source_width >= source_height:
        return maximum, max(2, round(maximum * source_height / source_width))
    return max(2, round(maximum * source_width / source_height)), maximum


def _provenance_value(value: datetime | str | None) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _rounded_flat(values: np.ndarray) -> list[float]:
    """Return JSON-friendly values whose textual representation stays compact."""
    return [round(float(value), 3) for value in values.ravel()]


def wind_field(
    ws_path: Path,
    wd_path: Path,
    *,
    forecast_start: datetime | str | None = None,
    forecast_cycle: str | None = None,
    maximum_grid_dimension: int = _MAX_GRID_DIMENSION,
) -> dict:
    """Return summaries and a compact WGS84 u/v grid for every weather band.

    Processing stays band-by-band. A real run contains hundreds of millions of source
    pixels across its time series; reading the whole cube and promoting it to float64 can
    exhaust the API process. Only two source bands and two small destinations exist at
    any point here.
    """
    if maximum_grid_dimension < 2:
        raise ValueError("maximum_grid_dimension must be at least 2")

    with rasterio.open(ws_path) as ws_src, rasterio.open(wd_path) as wd_src:
        if ws_src.crs is None or wd_src.crs is None:
            raise ValueError("wind rasters must both declare a CRS")
        if (
            ws_src.count != wd_src.count
            or ws_src.shape != wd_src.shape
            or ws_src.transform != wd_src.transform
            or ws_src.crs != wd_src.crs
        ):
            raise ValueError(
                "ws and wd must have the same band count, shape, transform, and CRS"
            )

        width, height = _grid_shape(ws_src.width, ws_src.height, maximum_grid_dimension)
        west, south, east, north = transform_bounds(
            ws_src.crs, "EPSG:4326", *ws_src.bounds, densify_pts=21
        )
        destination_transform = from_bounds(west, south, east, north, width, height)

        bounds = ws_src.bounds
        xs = [bounds.left, bounds.right, bounds.right, bounds.left, bounds.left]
        ys = [bounds.top, bounds.top, bounds.bottom, bounds.bottom, bounds.top]
        lons, lats = warp_transform(ws_src.crs, "EPSG:4326", xs, ys)

        bands: list[dict] = []
        for index in range(1, ws_src.count + 1):
            speed = ws_src.read(index, masked=True).astype("float32")
            direction = wd_src.read(index, masked=True).astype("float32")
            combined_mask = np.ma.getmaskarray(speed) | np.ma.getmaskarray(direction)
            speed = np.ma.array(speed, mask=combined_mask)
            direction = np.ma.array(direction, mask=combined_mask)
            if speed.count() == 0:
                raise ValueError(f"wind band {index} contains no valid cells")

            u, v = wind_components(speed, direction)
            scalar_mean = float(np.ma.mean(speed))
            mean_u = float(np.ma.mean(u))
            mean_v = float(np.ma.mean(v))
            if not all(math.isfinite(value) for value in (scalar_mean, mean_u, mean_v)):
                raise ValueError(f"wind band {index} contains non-finite values")

            destination_u = np.full((height, width), _NODATA, dtype=np.float32)
            destination_v = np.full((height, width), _NODATA, dtype=np.float32)
            for source_component, destination in ((u, destination_u), (v, destination_v)):
                reproject(
                    source=np.ma.filled(source_component, _NODATA).astype("float32"),
                    destination=destination,
                    src_transform=ws_src.transform,
                    src_crs=ws_src.crs,
                    src_nodata=_NODATA,
                    dst_transform=destination_transform,
                    dst_crs="EPSG:4326",
                    dst_nodata=_NODATA,
                    resampling=Resampling.bilinear,
                )

            valid = (
                np.isfinite(destination_u)
                & np.isfinite(destination_v)
                & (destination_u != _NODATA)
                & (destination_v != _NODATA)
            )
            if not np.any(valid):
                raise ValueError(f"wind band {index} has no valid cells after reprojection")

            grid_speed = np.hypot(destination_u[valid], destination_v[valid])
            # Invalid edge pixels behave as calm in the browser. The field covers a
            # rectangular ELMFIRE grid, so they only occur at reprojection boundaries.
            destination_u[~valid] = 0
            destination_v[~valid] = 0
            blows_to = math.degrees(math.atan2(mean_u, mean_v)) % 360.0

            bands.append(
                {
                    "hour": index - 1,
                    "u_mph": _rounded_flat(destination_u),
                    "v_mph": _rounded_flat(destination_v),
                    "speed_min_mph": round(float(np.min(grid_speed)), 2),
                    "speed_max_mph": round(float(np.max(grid_speed)), 2),
                    "speed_mph": round(scalar_mean, 2),
                    "blows_to_deg": round(blows_to, 1),
                    "label": (
                        f"viento {scalar_mean:.1f}".replace(".", ",")
                        + f" mph hacia el {compass_point(blows_to)}"
                    ),
                    "direction_consistency": (
                        round(math.hypot(mean_u, mean_v) / scalar_mean, 3)
                        if scalar_mean > 0
                        else 1.0
                    ),
                }
            )

    logger.info(
        "Wind field: %d bands, %dx%d display grid from %s",
        len(bands),
        width,
        height,
        ws_path.name,
    )
    return {
        "schema_version": 2,
        "bounds": [west, south, east, north],
        "ring": [[lon, lat] for lon, lat in zip(lons, lats)],
        "width": width,
        "height": height,
        "unit": "mph",
        "basis": "elmfire_20ft",
        "height_m": 6.096,
        "source_model": "GFS 0.25°",
        "forecast_start": _provenance_value(forecast_start),
        "forecast_cycle": forecast_cycle,
        "step_hours": 1,
        "bands": bands,
    }


def write_wind_field(
    ws_path: Path,
    wd_path: Path,
    output_path: Path,
    *,
    forecast_start: datetime | str | None = None,
    forecast_cycle: str | None = None,
) -> dict:
    """Build and persist the compact field used by new runs."""
    payload = wind_field(
        ws_path,
        wd_path,
        forecast_start=forecast_start,
        forecast_cycle=forecast_cycle,
    )
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return payload


def read_wind_field(output_path: Path) -> dict:
    """Read a prepared sidecar and reject stale or malformed schemas."""
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 2:
        raise ValueError(f"unsupported wind field schema in {output_path}")
    if not payload.get("bands") or payload.get("width", 0) < 2 or payload.get("height", 0) < 2:
        raise ValueError(f"invalid wind field payload in {output_path}")
    expected = payload["width"] * payload["height"]
    for band in payload["bands"]:
        if len(band.get("u_mph", [])) != expected or len(band.get("v_mph", [])) != expected:
            raise ValueError(f"invalid wind component lengths in {output_path}")
    return payload


def wind_bands(ws_path: Path, wd_path: Path) -> dict:
    """Backward-compatible name for callers that previously requested only summaries."""
    return wind_field(ws_path, wd_path)
