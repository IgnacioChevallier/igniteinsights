"""`wind_bands` reads one band at a time; this pins the arithmetic that refactor moved.

It used to read both cubes whole and promote them to float64 — ~1.6 GB each, plus four
more arrays that size for the u/v components. On a real 25-band domain that is ~13 GB of
peak for a result of two floats per hour, and it killed the API process rather than
raising: the isochrone and ignition requests in flight died with it, so the panel had
nothing to draw. Going band by band is only correct if the numbers do not move, which is
what the equivalence check below is for.
"""
import math

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from app.postprocessing.wind_field import (
    compass_point,
    read_wind_field,
    wind_bands,
    wind_components,
    wind_field,
    write_wind_field,
)


def _raster(path, bands: list[np.ndarray], *, crs="EPSG:32719", nodata=None):
    with rasterio.open(
        path, "w", driver="GTiff", height=bands[0].shape[0], width=bands[0].shape[1],
        count=len(bands), dtype="float32", crs=crs, nodata=nodata,
        transform=from_origin(500000, 5300000, 30, 30),
    ) as dst:
        for i, band in enumerate(bands, start=1):
            dst.write(band.astype("float32"), i)
    return path


def _whole_cube_reference(ws_path, wd_path) -> list[dict]:
    """The pre-refactor formula, vectorised over the whole cube."""
    with rasterio.open(ws_path) as ws_src, rasterio.open(wd_path) as wd_src:
        ws = ws_src.read(masked=True).astype("float64")
        wd = wd_src.read(masked=True).astype("float64")
    theta = np.radians(wd)
    u, v = ws * -np.sin(theta), ws * -np.cos(theta)
    out = []
    for i in range(ws.shape[0]):
        speed = float(np.ma.mean(ws[i]))
        mean_u, mean_v = float(np.ma.mean(u[i])), float(np.ma.mean(v[i]))
        out.append({
            "speed_mph": round(speed, 2),
            "blows_to_deg": round(math.degrees(math.atan2(mean_u, mean_v)) % 360.0, 1),
            "direction_consistency": round(math.hypot(mean_u, mean_v) / speed, 3)
            if speed > 0 else 1.0,
        })
    return out


def test_uniform_band_blows_opposite_to_the_direction_it_comes_from(tmp_path):
    # wd is the meteorological convention: 0° means the wind comes FROM the north, so the
    # map has to draw it going south.
    ws = _raster(tmp_path / "ws.tif", [np.full((4, 4), 10.0)])
    wd = _raster(tmp_path / "wd.tif", [np.zeros((4, 4))])

    band = wind_bands(ws, wd)["bands"][0]
    assert band["speed_mph"] == 10.0
    assert band["blows_to_deg"] == 180.0
    assert band["direction_consistency"] == 1.0
    assert compass_point(band["blows_to_deg"]) == "S"


def test_band_by_band_matches_the_whole_cube_formula(tmp_path):
    rng = np.random.default_rng(0)
    speeds = [rng.uniform(0, 30, (8, 8)) for _ in range(4)]
    # One band deliberately incoherent, so direction_consistency is exercised below 1.
    dirs = [rng.uniform(0, 360, (8, 8)) for _ in range(4)]
    dirs[1] = np.full((8, 8), 270.0)

    ws = _raster(tmp_path / "ws.tif", speeds)
    wd = _raster(tmp_path / "wd.tif", dirs)

    got = wind_bands(ws, wd)["bands"]
    expected = _whole_cube_reference(ws, wd)

    assert len(got) == len(expected) == 4
    for band, ref in zip(got, expected):
        assert band["speed_mph"] == ref["speed_mph"]
        assert band["blows_to_deg"] == ref["blows_to_deg"]
        assert band["direction_consistency"] == ref["direction_consistency"]

    # The uniform band is coherent; the random ones are not, which is the signal the map
    # uses to decide an arrow would be a lie.
    assert got[1]["direction_consistency"] == 1.0
    assert got[0]["direction_consistency"] < 0.5


def test_the_domain_ring_closes_and_is_lonlat(tmp_path):
    ws = _raster(tmp_path / "ws.tif", [np.full((4, 4), 5.0)])
    wd = _raster(tmp_path / "wd.tif", [np.full((4, 4), 90.0)])

    ring = wind_bands(ws, wd)["ring"]
    assert len(ring) == 5 and ring[0] == ring[-1]
    assert all(-180 <= lon <= 180 and -90 <= lat <= 90 for lon, lat in ring)


def test_spatial_grid_contains_to_components_and_preserves_aspect_ratio(tmp_path):
    ws = _raster(tmp_path / "ws.tif", [np.full((4, 8), 10.0)])
    wd = _raster(tmp_path / "wd.tif", [np.zeros((4, 8))])

    payload = wind_field(ws, wd, maximum_grid_dimension=12)
    band = payload["bands"][0]

    assert payload["schema_version"] == 2
    assert (payload["width"], payload["height"]) == (12, 6)
    assert len(band["u_mph"]) == len(band["v_mph"]) == 72
    assert max(abs(value) for value in band["u_mph"]) == pytest.approx(0, abs=1e-3)
    assert min(band["v_mph"]) == pytest.approx(-10, abs=1e-3)
    assert band["speed_min_mph"] == pytest.approx(10)
    assert band["speed_max_mph"] == pytest.approx(10)


def test_component_conversion_is_safe_across_north(tmp_path):
    speed = np.array([10.0, 10.0], dtype="float32")
    direction = np.array([350.0, 10.0], dtype="float32")
    u, v = wind_components(speed, direction)

    # Winds arriving either side of north both travel mostly south. Averaging their
    # angles directly would incorrectly point them north through 180 degrees.
    assert float(np.mean(v)) < -9.8
    assert float(np.mean(u)) == pytest.approx(0, abs=1e-5)


def test_sidecar_round_trip_keeps_provenance_and_all_bands(tmp_path):
    ws = _raster(
        tmp_path / "ws.tif",
        [np.full((4, 4), 5.0), np.full((4, 4), 15.0)],
    )
    wd = _raster(
        tmp_path / "wd.tif",
        [np.full((4, 4), 90.0), np.full((4, 4), 270.0)],
    )
    sidecar = tmp_path / "wind-field.json"

    expected = write_wind_field(
        ws,
        wd,
        sidecar,
        forecast_start="2026-09-20T00:00:00+00:00",
        forecast_cycle="2026092000",
    )
    actual = read_wind_field(sidecar)

    assert actual == expected
    assert actual["forecast_cycle"] == "2026092000"
    assert actual["forecast_start"] == "2026-09-20T00:00:00+00:00"
    assert [band["hour"] for band in actual["bands"]] == [0, 1]


def test_mismatched_band_counts_are_rejected(tmp_path):
    ws = _raster(tmp_path / "ws.tif", [np.full((4, 4), 5.0)])
    wd = _raster(
        tmp_path / "wd.tif",
        [np.full((4, 4), 90.0), np.full((4, 4), 90.0)],
    )

    with pytest.raises(ValueError, match="same band count"):
        wind_field(ws, wd)


def test_missing_crs_and_nodata_only_fields_are_rejected(tmp_path):
    without_crs = _raster(tmp_path / "without-crs.tif", [np.ones((4, 4))], crs=None)
    valid_direction = _raster(tmp_path / "direction.tif", [np.zeros((4, 4))])
    with pytest.raises(ValueError, match="declare a CRS"):
        wind_field(without_crs, valid_direction)

    nodata_speed = _raster(
        tmp_path / "nodata-speed.tif",
        [np.full((4, 4), -9999.0)],
        nodata=-9999.0,
    )
    nodata_direction = _raster(
        tmp_path / "nodata-direction.tif",
        [np.full((4, 4), -9999.0)],
        nodata=-9999.0,
    )
    with pytest.raises(ValueError, match="contains no valid cells"):
        wind_field(nodata_speed, nodata_direction)


def test_wind_endpoint_serves_the_sidecar_without_the_rasters(tmp_path, monkeypatch):
    """`servicio.podar` deletes ws.tif/wd.tif and keeps wind-field.json: the map's wind must
    still come back for a pruned operational forecast."""
    import asyncio
    import uuid
    from types import SimpleNamespace

    from app.api.v1 import simulations

    ws = _raster(tmp_path / "ws.tif", [np.full((4, 4), 5.0)])
    wd = _raster(tmp_path / "wd.tif", [np.full((4, 4), 90.0)])
    expected = write_wind_field(ws, wd, tmp_path / "wind-field.json",
                                forecast_start=None, forecast_cycle=None)
    ws.unlink()
    wd.unlink()

    async def run(_session, _id):
        return SimpleNamespace(elmfire_config={"inputs_dir": str(tmp_path)})

    monkeypatch.setattr(simulations.repository, "get_simulation_run", run)
    body = asyncio.run(simulations.get_simulation_wind(uuid.uuid4(), None))
    assert body["data"] == expected
