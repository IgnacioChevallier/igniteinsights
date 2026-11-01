import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from app.elmfire.builder.weather_builder import MS_TO_MPH, wind_height_factor
from app.ensemble.agreement import aggregate_burn_agreement
from app.ensemble.sources import GEFS_MEMBERS, gefs_filter_url, selected_members
from app.ensemble.weather import (
    gefs_time_axis,
    interpolate_cube,
    interpolate_weather,
    interpolate_weather_at_valid_times,
    speed_direction_to_uv,
    uv_to_speed_direction,
)


def _toa(path: Path, burned: np.ndarray, *, transform=None, nodata=0.0) -> Path:
    transform = transform or from_origin(500000, 5400000, 30, 30)
    data = np.where(burned, 3600.0, nodata).astype("float32")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:32719",
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(data, 1)
    return path


def test_uv_speed_direction_round_trip_and_units():
    speed = np.array([0.0, 5.0, 10.0])
    direction = np.array([0.0, 90.0, 350.0])
    u, v = speed_direction_to_uv(speed, direction)
    got_speed, got_direction = uv_to_speed_direction(u, v)
    assert got_speed == pytest.approx(speed)
    assert got_direction[1:] == pytest.approx(direction[1:])
    assert 5.0 * wind_height_factor() * MS_TO_MPH == pytest.approx(9.73, abs=0.02)


def test_vector_interpolation_crosses_north_not_south():
    speed = np.full((2, 1, 1), 10.0)
    direction = np.array([[[350.0]], [[10.0]]])
    u, v = speed_direction_to_uv(speed, direction)
    weather = interpolate_weather(u, v, speed, speed, [0, 2], [0, 1, 2])
    mid_speed, mid_direction = uv_to_speed_direction(weather["u10"], weather["v10"])
    assert mid_direction[1, 0, 0] == pytest.approx(0.0, abs=1e-5)
    assert mid_speed[1, 0, 0] > 9.8


def test_interpolation_bands_are_chronological_and_reject_extrapolation():
    cube = np.array([[[0.0]], [[3.0]], [[6.0]]])
    result = interpolate_cube(cube, [0, 3, 6], list(range(7)))
    assert result[:, 0, 0].tolist() == pytest.approx(list(range(7)))
    with pytest.raises(ValueError, match="strictly increasing"):
        interpolate_cube(cube, [0, 3, 3], [0, 1])
    with pytest.raises(ValueError, match="extrapolation"):
        interpolate_cube(cube, [0, 3, 6], [0, 7])


def test_gefs_time_axis_preserves_fractional_hour_start_and_absolute_valid_times():
    cycle_at = datetime(2025, 1, 15, 12, tzinfo=UTC)
    forecast_start = datetime(2025, 1, 15, 18, 33, tzinfo=UTC)
    axis = gefs_time_axis(cycle_at, forecast_start, 24)
    assert axis["offset_seconds"] == 6 * 3600 + 33 * 60
    assert axis["offset_hours"] == pytest.approx(6.55)
    assert axis["source_hours"] == list(range(6, 34, 3))
    assert axis["source_valid_at"][0] == datetime(2025, 1, 15, 18, tzinfo=UTC)
    assert axis["source_valid_at"][-1] == datetime(2025, 1, 16, 21, tzinfo=UTC)
    assert axis["band_valid_at"][0] == forecast_start
    assert axis["band_valid_at"][-1] == forecast_start + timedelta(hours=24)

    cube = np.array([[[6.0]], [[9.0]]])
    result = interpolate_weather_at_valid_times(
        cube,
        cube,
        cube,
        cube,
        axis["source_valid_at"][:2],
        axis["band_valid_at"][:3],
    )
    assert result["u10"][:, 0, 0] == pytest.approx([6.55, 7.55, 8.55])


def test_gefs_selection_and_filtered_url_are_explicit():
    assert selected_members(3) == ["c00", "p01", "p02"]
    assert len(GEFS_MEMBERS) == 31 and GEFS_MEMBERS[-1] == "p30"
    url = gefs_filter_url(
        datetime(2026, 10, 12, 0, tzinfo=UTC),
        "p01",
        3,
        (-72.0, -44.0, -70.0, -42.0),
    )
    assert "gep01.t00z.pgrb2s.0p25.f003" in url
    assert all(token in url for token in ("var_UGRD=on", "var_VGRD=on", "var_TMP=on", "var_RH=on"))
    assert "leftlon=-72.0" in url and "bottomlat=-44.0" in url


def test_agreement_effective_denominator_thresholds_and_reproducibility(tmp_path):
    masks = {
        "c00": np.array([[1, 1], [0, 0]], dtype=bool),
        "p01": np.array([[1, 0], [1, 0]], dtype=bool),
        "p02": np.array([[1, 0], [0, 0]], dtype=bool),
    }
    paths = {name: _toa(tmp_path / f"{name}.tif", mask) for name, mask in masks.items()}
    out1, out2 = tmp_path / "out1", tmp_path / "out2"
    kwargs = dict(
        expected_members=["c00", "p01", "p02", "p03"],
        min_valid_members=3,
        cycle="2026101200",
        forecast_start="2026-10-12T06:33:00+00:00",
        horizon_hours=24,
        failed_members={"p03": "ELMFIRE failed"},
    )
    meta = aggregate_burn_agreement(paths, out1, **kwargs)
    aggregate_burn_agreement(paths, out2, **kwargs)
    assert meta["effective_denominator"] == 3
    assert meta["expected_member_count"] == 4
    with rasterio.open(out1 / "burn_agreement.tif") as src:
        assert src.dtypes[0] == "float32"
        assert src.read(1) == pytest.approx(np.array([[1, 1 / 3], [1 / 3, 0]]))
    for label in ("10", "50", "80"):
        assert (out1 / f"burn_agreement_ge_{label}.tif").exists()
        assert (out1 / f"burn_agreement_ge_{label}.geojson").exists()
    contract = json.loads((out1 / "ensemble_agreement.json").read_text())
    assert contract["schema_version"] == 1
    assert contract["layer"] == {
        "id": "ensemble_agreement",
        "name": "Acuerdo del ensamble",
        "legend_label": "acuerdo entre simulaciones",
        "default_visible": False,
        "geometry": "polygon",
    }
    assert contract["metadata"]["valid_members"] == 3
    assert contract["metadata"]["expected_members"] == 4
    assert contract["metadata"]["weather_cycle"] == "2026101200"
    assert contract["metadata"]["horizon_hours"] == 24
    assert contract["metadata"]["forecast_start"] == "2026-10-12T06:33:00+00:00"
    assert contract["metadata"]["forecast_valid_at"] == "2026-10-13T06:33:00+00:00"
    assert [band["value"] for band in contract["thresholds"]] == [0.1, 0.5, 0.8]
    assert [band["label"] for band in contract["thresholds"]] == [
        "≥ 0,10",
        "≥ 0,50",
        "≥ 0,80",
    ]
    for band in contract["thresholds"]:
        assert band["operator"] == ">="
        assert band["geojson"]["type"] == "FeatureCollection"
        assert all(
            feature["properties"]["agreement_threshold"] == band["value"]
            for feature in band["geojson"]["features"]
        )
    assert (out1 / "burn_agreement.tif").read_bytes() == (out2 / "burn_agreement.tif").read_bytes()


def test_agreement_rejects_too_few_members_and_grid_mismatch(tmp_path):
    first = _toa(tmp_path / "first.tif", np.ones((2, 2), dtype=bool))
    with pytest.raises(ValueError, match="minimum"):
        aggregate_burn_agreement(
            {"c00": first},
            tmp_path / "few",
            expected_members=["c00", "p01"],
            min_valid_members=2,
            cycle="x",
            forecast_start="2025-01-15T18:33:00+00:00",
            horizon_hours=12,
        )
    shifted = _toa(
        tmp_path / "shifted.tif",
        np.ones((2, 2), dtype=bool),
        transform=from_origin(500030, 5400000, 30, 30),
    )
    with pytest.raises(ValueError, match="grid/CRS/transform/nodata"):
        aggregate_burn_agreement(
            {"c00": first, "p01": shifted},
            tmp_path / "bad-grid",
            expected_members=["c00", "p01"],
            min_valid_members=2,
            cycle="x",
            forecast_start="2025-01-15T18:33:00+00:00",
            horizon_hours=12,
        )


def test_agreement_uses_horizon_cutoff_and_forecast_start(tmp_path):
    toa = _toa(tmp_path / "toa.tif", np.ones((1, 2), dtype=bool))
    with rasterio.open(toa, "r+") as dst:
        dst.write(np.array([[12 * 3600, 13 * 3600]], dtype="float32"), 1)
    output = tmp_path / "agreement"
    metadata = aggregate_burn_agreement(
        {"c00": toa},
        output,
        expected_members=["c00"],
        min_valid_members=1,
        cycle="2025011512",
        forecast_start="2025-01-15T18:33:00+00:00",
        horizon_hours=12,
    )
    with rasterio.open(output / "burn_agreement.tif") as src:
        assert src.read(1).tolist() == [[1.0, 0.0]]
    assert metadata["forecast_valid_at"] == "2025-01-16T06:33:00+00:00"


def test_gefs_download_retries_s3_slow_down_then_gives_up(monkeypatch):
    """09-01 lost 6 members to S3 '503 Slow Down' (ENSAMBLE-DEMO-DIAGNOSTICO.md)."""
    import httpx

    from app.ensemble import sources

    monkeypatch.setattr(sources.time, "sleep", lambda _: None)

    def failing(status: int, times: int):
        calls = []

        def download() -> str:
            calls.append(1)
            if len(calls) <= times:
                request = httpx.Request("GET", "https://noaa-gefs-pds.s3.amazonaws.com/x")
                raise httpx.HTTPStatusError("x", request=request,
                                            response=httpx.Response(status, request=request))
            return "ok"

        return download, calls

    download, calls = failing(503, 2)
    assert sources._retrying(download) == "ok" and len(calls) == 3
    download, calls = failing(503, 99)
    with pytest.raises(httpx.HTTPStatusError):
        sources._retrying(download)
    assert len(calls) == 1 + len(sources.RETRY_DELAYS_S)
    download, calls = failing(404, 99)
    with pytest.raises(httpx.HTTPStatusError):
        sources._retrying(download)
    assert len(calls) == 1
