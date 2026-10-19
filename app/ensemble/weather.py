"""Source-neutral weather transformations used by GEFS and SMN WRF.

Wind direction is meteorological (the direction *from* which it blows).  Temporal
interpolation is deliberately performed on U/V, never on circular direction angles.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import numpy as np


def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{name} must be timezone-aware UTC")
    return value


def gefs_time_axis(
    cycle: datetime, forecast_start: datetime, horizon_hours: int
) -> dict[str, object]:
    """Build an exact valid-time axis and the GEFS steps that bracket it."""
    cycle = _utc(cycle, "cycle")
    forecast_start = _utc(forecast_start, "forecast_start")
    if forecast_start < cycle:
        raise ValueError("forecast_start cannot precede the GEFS cycle")
    if horizon_hours < 1:
        raise ValueError("horizon_hours must be positive")
    offset_seconds = (forecast_start - cycle).total_seconds()
    step_seconds = 3 * 3600
    first_step = math.floor(offset_seconds / step_seconds) * 3
    last_seconds = offset_seconds + horizon_hours * 3600
    last_step = math.ceil(last_seconds / step_seconds) * 3
    source_hours = list(range(first_step, last_step + 1, 3))
    source_valid_at = [cycle + timedelta(hours=hour) for hour in source_hours]
    band_valid_at = [
        forecast_start + timedelta(hours=hour) for hour in range(horizon_hours + 1)
    ]
    return {
        "offset_seconds": offset_seconds,
        "offset_hours": offset_seconds / 3600,
        "source_hours": source_hours,
        "source_valid_at": source_valid_at,
        "band_valid_at": band_valid_at,
    }


def _epoch_seconds(values: list[datetime], name: str) -> list[float]:
    return [_utc(value, name).timestamp() for value in values]


def speed_direction_to_uv(
    speed: np.ndarray, direction_deg: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    theta = np.deg2rad(direction_deg)
    return -speed * np.sin(theta), -speed * np.cos(theta)


def uv_to_speed_direction(u: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    speed = np.hypot(u, v)
    direction = (np.rad2deg(np.arctan2(-u, -v)) + 360.0) % 360.0
    return speed, direction


def interpolate_cube(
    values: np.ndarray, source_hours: Sequence[float], target_hours: Sequence[float]
) -> np.ndarray:
    """Linearly interpolate a (time, y, x) cube, preserving chronological order."""
    source = np.asarray(source_hours, dtype=float)
    target = np.asarray(target_hours, dtype=float)
    cube = np.asarray(values, dtype=float)
    if cube.ndim != 3 or cube.shape[0] != source.size:
        raise ValueError("values must have shape (len(source_hours), y, x)")
    if source.size == 0 or np.any(np.diff(source) <= 0):
        raise ValueError("source_hours must be strictly increasing")
    if target.size == 0 or np.any(np.diff(target) <= 0):
        raise ValueError("target_hours must be strictly increasing")
    if target[0] < source[0] or target[-1] > source[-1]:
        raise ValueError("target_hours require extrapolation")
    hi = np.searchsorted(source, target, side="left")
    hi = np.clip(hi, 0, source.size - 1)
    lo = np.maximum(hi - 1, 0)
    exact = source[hi] == target
    lo[exact] = hi[exact]
    span = source[hi] - source[lo]
    weight = np.divide(target - source[lo], span, out=np.zeros_like(target), where=span != 0)
    return ((1.0 - weight)[:, None, None] * cube[lo] + weight[:, None, None] * cube[hi]).astype(
        "float32"
    )


def interpolate_weather(
    u: np.ndarray,
    v: np.ndarray,
    temperature_k: np.ndarray,
    rh_pct: np.ndarray,
    source_hours: Sequence[float],
    target_hours: Sequence[float],
) -> dict[str, np.ndarray]:
    """Interpolate the four physical fields to a common hourly time axis."""
    return {
        "u10": interpolate_cube(u, source_hours, target_hours),
        "v10": interpolate_cube(v, source_hours, target_hours),
        "t2m": interpolate_cube(temperature_k, source_hours, target_hours),
        "rh": np.clip(interpolate_cube(rh_pct, source_hours, target_hours), 0, 100),
    }


def interpolate_weather_at_valid_times(
    u: np.ndarray,
    v: np.ndarray,
    temperature_k: np.ndarray,
    rh_pct: np.ndarray,
    source_valid_at: list[datetime],
    band_valid_at: list[datetime],
) -> dict[str, np.ndarray]:
    """Interpolate on absolute UTC instants, including fractional-hour starts."""
    source_seconds = _epoch_seconds(source_valid_at, "source_valid_at")
    target_seconds = _epoch_seconds(band_valid_at, "band_valid_at")
    return interpolate_weather(
        u,
        v,
        temperature_k,
        rh_pct,
        source_seconds,
        target_seconds,
    )
