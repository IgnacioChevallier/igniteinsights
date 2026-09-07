"""Scenario metrics must measure spread, not grid artefacts."""
import math

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from app.playground import metrics

CELL = 30.0
N = 41  # odd, so there is a true centre cell
CENTRE = (N - 1) // 2


def _toa(tmp_path, arr, nodata=0.0):
    p = tmp_path / "toa.tif"
    with rasterio.open(
        p, "w", driver="GTiff", height=N, width=N, count=1, dtype="float32",
        crs="EPSG:32719", nodata=nodata,
        transform=from_origin(500000.0, 5300000.0, CELL, CELL),
    ) as dst:
        dst.write(arr.astype("float32"), 1)
    return p


def _elliptical_burn(dy_bias=0.0, dx_bias=0.0, ry=8, rx=8):
    """Arrival times inside an ellipse offset from the centre; 0 (= nodata) outside."""
    rows, cols = np.mgrid[0:N, 0:N]
    r = ((rows - CENTRE - dy_bias) / ry) ** 2 + ((cols - CENTRE - dx_bias) / rx) ** 2
    arr = np.zeros((N, N))
    inside = r <= 1.0
    arr[inside] = 1.0 + 3000.0 * r[inside]
    return arr


def test_calm_fire_reports_no_direction(tmp_path):
    """A circle centred on the ignition has no head. Reporting a direction would be noise
    dressed as a measurement."""
    m = metrics.scenario_metrics(_toa(tmp_path, _elliptical_burn()), horizon_hours=1)
    assert m["final"]["head_direction_deg"] is None
    assert m["final"]["aspect_ratio"] == pytest.approx(1.0, abs=0.05)


def test_direction_is_south_when_the_burn_is_displaced_south(tmp_path):
    """Rows increase southward. Wind from the north (wd=0) must read ~180°."""
    m = metrics.scenario_metrics(
        _toa(tmp_path, _elliptical_burn(dy_bias=6)), horizon_hours=1
    )
    assert m["final"]["head_direction_deg"] == pytest.approx(180.0, abs=5.0)


def test_direction_is_east_when_the_burn_is_displaced_east(tmp_path):
    m = metrics.scenario_metrics(
        _toa(tmp_path, _elliptical_burn(dx_bias=6)), horizon_hours=1
    )
    assert m["final"]["head_direction_deg"] == pytest.approx(90.0, abs=5.0)


def test_direction_survives_a_jagged_boundary(tmp_path):
    """The reason this is a centroid and not the farthest cell: one stray cell in a corner
    must not swing the reported head direction."""
    arr = _elliptical_burn(dy_bias=6)
    arr[0, 0] = 500.0  # a lone far-away cell to the north-west
    m = metrics.scenario_metrics(_toa(tmp_path, arr), horizon_hours=1)
    assert m["final"]["head_direction_deg"] == pytest.approx(180.0, abs=8.0)


def test_aspect_ratio_is_orientation_independent(tmp_path):
    """A bounding box would report ~1 for a fire elongated at 45°, which is exactly what
    the wind-direction scenarios produce."""
    rows, cols = np.mgrid[0:N, 0:N]
    u = (rows - CENTRE + cols - CENTRE) / math.sqrt(2)
    v = (rows - CENTRE - cols + CENTRE) / math.sqrt(2)
    arr = np.zeros((N, N))
    inside = (u / 14.0) ** 2 + (v / 4.0) ** 2 <= 1.0
    arr[inside] = 100.0
    m = metrics.scenario_metrics(_toa(tmp_path, arr), horizon_hours=1)
    assert m["final"]["aspect_ratio"] == pytest.approx(3.5, rel=0.25)


def test_touching_the_boundary_is_flagged(tmp_path):
    """A clipped front under-reports area, elongation and direction. Returning the
    truncated numbers without saying so would corrupt a sensitivity comparison."""
    arr = np.zeros((N, N))
    arr[CENTRE - 2:CENTRE + 3, :] = 100.0  # spans the full width, touches both edges
    m = metrics.scenario_metrics(_toa(tmp_path, arr), horizon_hours=1)
    assert m["reached_domain_edge"] is True

    contained = metrics.scenario_metrics(_toa(tmp_path, _elliptical_burn()), horizon_hours=1)
    assert contained["reached_domain_edge"] is False


def test_hourly_growth_is_monotonic(tmp_path):
    m = metrics.scenario_metrics(_toa(tmp_path, _elliptical_burn()), horizon_hours=1)
    areas = [h["burned_ha"] for h in m["hourly"]]
    assert areas == sorted(areas)


def test_a_scenario_that_never_spreads_reports_zero_not_a_crash(tmp_path):
    m = metrics.scenario_metrics(_toa(tmp_path, np.zeros((N, N))), horizon_hours=3)
    assert m["burned_cells"] == 0
    assert m["final"]["burned_ha"] == 0.0
    assert m["final"]["head_direction_deg"] is None
    assert m["reached_domain_edge"] is False


def test_ros_adjective_matches_scott_and_burgan_table_5():
    """Table 5 is in chains/hour; 1 chain = 20.1168 m. The classes are the reference the
    playground checks our runs against."""
    assert metrics.ros_adjective(1.0 * metrics.M_PER_CHAIN) == "muy baja"
    assert metrics.ros_adjective(4.0 * metrics.M_PER_CHAIN) == "baja"
    assert metrics.ros_adjective(10.0 * metrics.M_PER_CHAIN) == "moderada"
    assert metrics.ros_adjective(30.0 * metrics.M_PER_CHAIN) == "alta"
    assert metrics.ros_adjective(100.0 * metrics.M_PER_CHAIN) == "muy alta"
    assert metrics.ros_adjective(200.0 * metrics.M_PER_CHAIN) == "extrema"
