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
