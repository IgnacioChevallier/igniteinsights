import base64
import io

import numpy as np
import rasterio
from PIL import Image
from rasterio.transform import from_origin

from app.api.v1.fuels import _class_areas
from app.postprocessing.raster_overlay import render_categorical_overlay


def _write_fbfm40(path, array):
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=array.shape[0],
        width=array.shape[1],
        count=1,
        dtype="int16",
        crs="EPSG:32719",
        transform=from_origin(500000, 5300000, 30, 30),  # 30 m pixels
        nodata=99,
    ) as dst:
        dst.write(array, 1)


def test_categorical_overlay_paints_each_class(tmp_path):
    tif = tmp_path / "fbfm40.tif"
    _write_fbfm40(tif, np.array([[183, 98], [183, 102]], dtype=np.int16))

    overlay = render_categorical_overlay(tif, {183: "#1b5e20", 98: "#4a80c0"})
    png = np.array(
        Image.open(io.BytesIO(base64.b64decode(overlay["image_base64"].split(",", 1)[1])))
    )

    colors = {tuple(px) for px in png.reshape(-1, 4)}
    assert (0x1B, 0x5E, 0x20, 204) in colors
    assert (0x4A, 0x80, 0xC0, 204) in colors
    assert (0, 0, 0, 0) in colors  # 102 has no color → transparent
    assert len(overlay["coordinates"]) == 4


def test_class_areas_shares_and_crosswalk_sources(tmp_path):
    tif = tmp_path / "fbfm40.tif"
    _write_fbfm40(tif, np.array([[183, 183], [183, 102]], dtype=np.int16))

    rows, total_ha = _class_areas(tif, source="worldcover")

    assert [row["fbfm40"] for row in rows] == [183, 102]  # sorted by pixel count
    assert rows[0]["share"] == 0.75
    assert rows[0]["area_ha"] == 0.3  # 3 px × 900 m² = 0.27 ha, rounded to 0.1 ha
    assert "Cobertura arbórea" in rows[0]["source_classes"]
    assert total_ha == 0.4


def test_class_areas_reports_the_provenance_of_the_active_source(tmp_path):
    """The legend must name the classes of the source that actually built the raster.

    Claiming a WorldCover provenance for a map built from CCS-BAP would be a lie the
    dashboard tells silently — the codes exist in both crosswalks.
    """
    tif = tmp_path / "fbfm40.tif"
    _write_fbfm40(tif, np.array([[148, 148], [186, 99]], dtype=np.int16))

    rows, _ = _class_areas(tif, source="ccsbap")
    by_code = {row["fbfm40"]: row for row in rows}

    assert "Ñire bajo" in by_code[148]["source_classes"]
    assert "Bosque de lenga" in by_code[186]["source_classes"]
    # Same raster, different source: CCS-BAP classes must not appear under WorldCover.
    rows_wc, _ = _class_areas(tif, source="worldcover")
    assert all(not row["source_classes"] for row in rows_wc if row["fbfm40"] in (148, 186))


def test_fuels_map_serves_the_requested_source_and_lists_the_built_ones(tmp_path, monkeypatch):
    import asyncio

    import pytest
    from fastapi import HTTPException

    from app.api.v1 import fuels

    monkeypatch.setattr(fuels, "resolve_data_path", lambda _: tmp_path)
    _write_fbfm40(tmp_path / "fbfm40_worldcover.tif", np.array([[183, 102]], dtype=np.int16))
    _write_fbfm40(tmp_path / "fbfm40_ccsbap.tif", np.array([[186, 186]], dtype=np.int16))

    data = asyncio.run(fuels.get_fuels_map(source="worldcover"))["data"]
    assert data["source_id"] == "worldcover"
    assert data["source"].startswith("ESA WorldCover")
    assert sorted(data["available_sources"]) == ["ccsbap", "worldcover"]
    assert {row["fbfm40"] for row in data["classes"]} == {183, 102}

    # A source never run is a 404, not a silent fallback to another map.
    with pytest.raises(HTTPException) as exc:
        asyncio.run(fuels.get_fuels_map(source="mapbiomas"))
    assert exc.value.status_code == 404


def test_categorical_overlay_rows_land_where_maplibre_draws_them(tmp_path):
    """MapLibre stretches the PNG linearly in Web Mercator between its corners.

    A stripe in the middle of a ~1.2°-tall raster (Los Alerces' extent) must be drawn at
    its true latitude; an EPSG:4326 PNG put it ~300 m south.
    """
    import math

    from rasterio.warp import transform as warp_transform

    rows, cell = 1350, 100  # 135 km tall, 100 m cells
    array = np.full((rows, 4), 99, dtype=np.int16)
    array[rows // 2] = 183
    tif = tmp_path / "fbfm40.tif"
    with rasterio.open(
        tif, "w", driver="GTiff", height=rows, width=4, count=1, dtype="int16",
        crs="EPSG:32719", transform=from_origin(500000, 5300000, cell, cell), nodata=99,
    ) as dst:
        dst.write(array, 1)

    overlay = render_categorical_overlay(tif, {183: "#1b5e20"})
    png = np.array(
        Image.open(io.BytesIO(base64.b64decode(overlay["image_base64"].split(",", 1)[1])))
    )
    stripe = np.flatnonzero(png[:, :, 3].any(axis=1)).mean() + 0.5
    merc = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))  # noqa: E731
    inv = lambda y: math.degrees(2 * math.atan(math.exp(y)) - math.pi / 2)  # noqa: E731
    north, south = overlay["coordinates"][0][1], overlay["coordinates"][3][1]
    drawn = inv(merc(north) + (merc(south) - merc(north)) * stripe / png.shape[0])

    true_y = 5300000 - (rows // 2 + 0.5) * cell
    _, (true_lat,) = warp_transform("EPSG:32719", "EPSG:4326", [500200], [true_y])
    assert abs(drawn - true_lat) * 111_320 < cell
