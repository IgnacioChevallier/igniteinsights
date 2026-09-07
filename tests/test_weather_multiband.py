"""Weather rasters carry the forecast time series in their bands, and wind is
converted from GFS 10 m to ELMFIRE's 20-ft convention."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from app.elmfire.builder.namelist_writer import validate_weather_coverage, write_namelist
from app.elmfire.builder.weather_builder import (
    ELMFIRE_WIND_HEIGHT_M,
    GFS_WIND_HEIGHT_M,
    MS_TO_MPH,
    derive_moisture,
    derive_wind,
    wind_height_factor,
)

_CRS = "EPSG:32719"


def _raster(path, data, crs=_CRS, res=30.0):
    """Write a (bands, h, w) stack; `data` may be 2-D for a single band."""
    arr = np.atleast_3d(np.asarray(data, dtype="float32"))
    if arr.shape[-1] in (1,) and arr.ndim == 3 and np.asarray(data).ndim == 2:
        arr = np.asarray(data, dtype="float32")[None, :, :]
    with rasterio.open(
        path, "w", driver="GTiff", height=arr.shape[1], width=arr.shape[2],
        count=arr.shape[0], dtype="float32", crs=crs,
        transform=from_origin(253479.65, 5291693.28, res, res),
    ) as dst:
        dst.write(arr)
    return path


def _reference(tmp_path):
    return _raster(tmp_path / "dem.tif", np.zeros((4, 4), dtype="float32"))


# ── 10 m → 20 ft conversion ───────────────────────────────────────────────────

def test_wind_height_factor_matches_fire_weather_standard():
    """Log profile at z0=0.22 m reproduces the ~0.87 factor used in fire weather."""
    assert wind_height_factor() == pytest.approx(0.87, abs=0.005)


def test_wind_height_factor_reduces_speed():
    """20 ft is below 10 m, so the factor must be < 1 — the old code used 1.0."""
    assert 0 < wind_height_factor() < 1
    assert ELMFIRE_WIND_HEIGHT_M < GFS_WIND_HEIGHT_M


def test_wind_height_factor_is_identity_when_heights_match():
    assert wind_height_factor(z_from=10.0, z_to=10.0) == pytest.approx(1.0)


def test_wind_height_factor_rejects_height_below_roughness():
    with pytest.raises(ValueError, match="roughness"):
        wind_height_factor(z_from=10.0, z_to=0.1, z0=0.22)


def test_derive_wind_applies_the_height_conversion(tmp_path):
    ref = _reference(tmp_path)
    _raster(tmp_path / "u.tif", np.full((4, 4), 3.0, dtype="float32"))
    _raster(tmp_path / "v.tif", np.full((4, 4), 4.0, dtype="float32"))
    ws_path, _ = derive_wind(tmp_path / "u.tif", tmp_path / "v.tif", ref, tmp_path / "out")

    with rasterio.open(ws_path) as ds:
        ws = ds.read(1)
    # |(3,4)| = 5 m/s at 10 m → 20 ft → mph
    assert ws.mean() == pytest.approx(5.0 * wind_height_factor() * MS_TO_MPH, rel=1e-4)


# ── multiband time series ─────────────────────────────────────────────────────

def test_wind_preserves_one_band_per_forecast_hour(tmp_path):
    ref = _reference(tmp_path)
    hours = 6
    u = np.stack([np.full((4, 4), float(h)) for h in range(hours)]).astype("float32")
    v = np.zeros_like(u)
    _raster(tmp_path / "u.tif", u)
    _raster(tmp_path / "v.tif", v)

    ws_path, wd_path = derive_wind(tmp_path / "u.tif", tmp_path / "v.tif", ref, tmp_path / "out")
    for path in (ws_path, wd_path):
        with rasterio.open(path) as ds:
            assert ds.count == hours, f"{path.name} collapsed the time series"
            assert ds.dtypes[0] == "float32"

    # Band n must still be forecast hour n, ascending with the input.
    with rasterio.open(ws_path) as ds:
        per_band = [ds.read(b + 1).mean() for b in range(hours)]
    assert per_band == sorted(per_band)
    assert per_band[0] == pytest.approx(0.0, abs=1e-6)


def test_moisture_preserves_one_band_per_forecast_hour(tmp_path):
    ref = _reference(tmp_path)
    hours = 4
    t2m = np.stack([np.full((4, 4), 293.15) for _ in range(hours)]).astype("float32")
    rh = np.stack([np.full((4, 4), 20.0 + 10 * h) for h in range(hours)]).astype("float32")
    _raster(tmp_path / "t.tif", t2m)
    _raster(tmp_path / "rh.tif", rh)

    paths = derive_moisture(tmp_path / "t.tif", tmp_path / "rh.tif", ref, tmp_path / "out")
    for path in paths:
        with rasterio.open(path) as ds:
            assert ds.count == hours
    # Rising RH must raise fuel moisture band over band.
    with rasterio.open(paths[0]) as ds:
        per_band = [ds.read(b + 1).mean() for b in range(hours)]
    assert per_band == sorted(per_band)


def test_mismatched_band_counts_are_rejected(tmp_path):
    ref = _reference(tmp_path)
    _raster(tmp_path / "u.tif", np.zeros((3, 4, 4), dtype="float32"))
    _raster(tmp_path / "v.tif", np.zeros((5, 4, 4), dtype="float32"))
    with pytest.raises(ValueError, match="band"):
        derive_wind(tmp_path / "u.tif", tmp_path / "v.tif", ref, tmp_path / "out")


# ── coverage guard ────────────────────────────────────────────────────────────

def test_horizon_exceeding_available_bands_is_rejected(tmp_path):
    """ELMFIRE holds the last band rather than erroring, freezing weather mid-run."""
    for name in ("ws", "wd", "m1", "m10", "m100"):
        _raster(tmp_path / f"{name}.tif", np.zeros((6, 4, 4), dtype="float32"))
    with pytest.raises(ValueError, match="band"):
        validate_weather_coverage(tmp_path, tstop_s=12 * 3600, dt_meteorology_s=3600.0)


def test_sufficient_bands_pass(tmp_path):
    for name in ("ws", "wd", "m1", "m10", "m100"):
        _raster(tmp_path / f"{name}.tif", np.zeros((13, 4, 4), dtype="float32"))
    validate_weather_coverage(tmp_path, tstop_s=12 * 3600, dt_meteorology_s=3600.0)


def test_single_band_is_allowed_but_returns_a_warning(tmp_path):
    """Legacy single-band runs must still work — they are just constant weather. The
    warning is returned (not only logged) so the dashboard can show it: a frozen-weather
    run looks identical to a good one on the map."""
    for name in ("ws", "wd", "m1", "m10", "m100"):
        _raster(tmp_path / f"{name}.tif", np.zeros((4, 4), dtype="float32"))
    warnings = validate_weather_coverage(tmp_path, tstop_s=12 * 3600, dt_meteorology_s=3600.0)
    assert len(warnings) == 5
    assert all("ws.tif" in w or ".tif" in w for w in warnings)


def test_multiband_run_produces_no_warnings(tmp_path):
    for name in ("ws", "wd", "m1", "m10", "m100"):
        _raster(tmp_path / f"{name}.tif", np.zeros((13, 4, 4), dtype="float32"))
    assert validate_weather_coverage(tmp_path, tstop_s=12 * 3600, dt_meteorology_s=3600.0) == []


def test_write_namelist_rejects_insufficient_weather(tmp_path):
    _raster(tmp_path / "dem.tif", np.zeros((4, 4), dtype="float32"))
    for name in ("ws", "wd", "m1", "m10", "m100"):
        _raster(tmp_path / f"{name}.tif", np.zeros((3, 4, 4), dtype="float32"))
    with pytest.raises(ValueError, match="band"):
        write_namelist(tmp_path, tmp_path / "out", 12, tmp_path / "elmfire.data")
