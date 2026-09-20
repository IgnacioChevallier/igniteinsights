"""Comparable metrics for a synthetic scenario, read off the time-of-arrival raster.

`GET /simulations/{id}/stats` returns ELMFIRE's fire_size_stats.csv, which is a
final-state summary and says nothing about growth over time, direction or shape. Comparing
two base cases needs exactly those, so they are derived here from `time_of_arrival`, where
every cell carries the second at which the front reached it.

Only meaningful for a point ignition at a known location, which is why this lives in the
playground rather than being generalised to real runs. See PLAYGROUND-SENSIBILIDAD.md §P6.
"""
import logging
import math
from pathlib import Path

import numpy as np
import rasterio

logger = logging.getLogger(__name__)

# 1 chain = 66 ft = 20.1168 m. Scott & Burgan publish spread rate in chains/hour, so the
# adjective classes of their Table 5 are only comparable after this conversion.
M_PER_CHAIN = 20.1168

# Scott & Burgan (2005) Table 5, chains/hour. The upper bound of each class.
_ROS_CLASSES = [
    (2.0, "muy baja"), (5.0, "baja"), (20.0, "moderada"),
    (50.0, "alta"), (150.0, "muy alta"), (math.inf, "extrema"),
]


def ros_adjective(ros_m_per_h: float) -> str:
    """Scott & Burgan adjective class for a spread rate, for comparison against the
    behaviour they publish per fuel model."""
    ch_h = ros_m_per_h / M_PER_CHAIN
    return next(name for upper, name in _ROS_CLASSES if ch_h < upper)


def scenario_metrics(toa_path: Path, horizon_hours: int) -> dict:
    """Growth, shape and direction from the time-of-arrival raster."""
    with rasterio.open(toa_path) as src:
        toa = src.read(1).astype(np.float64)
        nodata = src.nodata
        cell_m = abs(src.transform.a)

    # ELMFIRE writes nodata = 0 on this raster, and the ignition cells also arrive at
    # t = 0, so a cell holding 0 is ambiguous. Both are excluded, which makes every metric
    # here a measure of *spread beyond the ignition disc* — the quantity a sensitivity
    # comparison actually wants. The ignition disc is a few tens of cells against
    # thousands, and it is identical across scenarios, so the comparison is unaffected.
    horizon_s = horizon_hours * 3600.0
    burned = np.isfinite(toa) & (toa > 0) & (toa <= horizon_s)
    if nodata is not None and nodata != 0:
        burned &= toa != nodata

    if not burned.any():
        logger.warning("No burned cells in %s — the scenario did not spread", toa_path)
        return {
            "cell_size_m": cell_m, "burned_cells": 0, "hourly": [],
            "reached_domain_edge": False,
            "final": {"burned_ha": 0.0, "max_distance_m": 0.0, "head_ros_m_per_h": 0.0,
                      "head_ros_class": ros_adjective(0.0), "head_direction_deg": None,
                      "aspect_ratio": None},
        }

    rows, cols = np.mgrid[0:toa.shape[0], 0:toa.shape[1]]
    cy, cx = (toa.shape[0] - 1) / 2.0, (toa.shape[1] - 1) / 2.0
    dist_m = np.hypot(rows - cy, cols - cx) * cell_m
    cell_ha = (cell_m * cell_m) / 10_000.0

    hourly = []
    for hour in range(1, horizon_hours + 1):
        reached = burned & (toa <= hour * 3600.0)
        n = int(reached.sum())
        max_d = float(dist_m[reached].max()) if n else 0.0
        hourly.append({
            "hour": hour,
            "burned_ha": round(n * cell_ha, 2),
            "max_distance_m": round(max_d, 1),
            "mean_ros_m_per_h": round(max_d / hour, 1),
        })

    max_d = float(dist_m[burned].max())
    head_ros = max_d / horizon_hours

    return {
        "cell_size_m": cell_m,
        "burned_cells": int(burned.sum()),
        "hourly": hourly,
        # A front that touches the domain boundary is clipped: area, elongation and
        # direction all under-report, and the run is not comparable with one that fits.
        # Silently returning the truncated numbers would corrupt any sensitivity result.
        "reached_domain_edge": bool(
            burned[0, :].any() or burned[-1, :].any()
            or burned[:, 0].any() or burned[:, -1].any()
        ),
        "final": {
            "burned_ha": round(int(burned.sum()) * cell_ha, 2),
            "max_distance_m": round(max_d, 1),
            "head_ros_m_per_h": round(head_ros, 1),
            "head_ros_class": ros_adjective(head_ros),
            "head_direction_deg": _head_direction(burned, rows, cols, cy, cx, cell_m),
            "aspect_ratio": _aspect_ratio(burned, rows, cols),
        },
    }


# Below this the burned area is effectively centred on the ignition and no direction can
# be claimed — reporting one would be noise dressed as a measurement.
_MIN_CENTROID_OFFSET_M = 30.0


def _head_direction(burned, rows, cols, cy, cx, cell_m) -> float | None:
    """Azimuth from the ignition point to the centroid of the burned area, from north.

    Deliberately not the azimuth to the farthest burned cell: on a discrete grid the
    isochrone boundary is jagged and `argmax` picks one arbitrary cell among near-ties,
    which read 204.7° for a fire measured to run due south (375 m of backing against
    2055 m of heading, flanks symmetric at 975 m). The centroid uses every burned cell and
    reports 180° for that same run.

    This is the metric that verifies the wind convention end to end: with wind from the
    north (wd = 0) ELMFIRE spreads south, so this must read ~180°.
    """
    dy = (cy - rows[burned].mean()) * cell_m  # north is decreasing row
    dx = (cols[burned].mean() - cx) * cell_m
    if math.hypot(dx, dy) < _MIN_CENTROID_OFFSET_M:
        return None
    return round((math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0, 1)


def _aspect_ratio(burned, rows, cols) -> float | None:
    """Elongation of the burned area, from the principal axes of the burned cells.

    A bounding box would report ~1 for a fire elongated at 45°, which is exactly the case
    the wind-direction scenarios produce. The covariance eigenvalues are orientation
    independent, so they measure elongation rather than alignment with the grid.
    """
    r = rows[burned].astype(np.float64)
    c = cols[burned].astype(np.float64)
    if r.size < 3:
        return None
    cov = np.cov(np.vstack([c, r]))
    eig = np.linalg.eigvalsh(cov)
    minor, major = float(eig[0]), float(eig[1])
    if minor <= 1e-9:
        return None
    return round(math.sqrt(major / minor), 2)
