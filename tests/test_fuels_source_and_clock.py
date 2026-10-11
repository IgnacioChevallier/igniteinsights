"""Fuel-source selection (ETAPA-B §B3) and the two namelist values that were implicit.

Both failures these guard against are silent: an unknown source name would otherwise
fall through to whatever ran last, and a namelist that omits CROWN_FIRE_MODEL leaves
ELMFIRE deciding for us.
"""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from app.elmfire.builder import fuels_builder as fb
from app.elmfire.builder import namelist_writer


def _grid(path, value=1.0):
    with rasterio.open(
        path, "w", driver="GTiff", height=4, width=4, count=1, dtype="float32",
        crs="EPSG:32719", transform=from_origin(500000, 5300000, 30, 30),
    ) as dst:
        dst.write(np.full((4, 4), value, dtype="float32"), 1)
    return path


def test_unknown_source_raises_instead_of_silently_picking_one():
    with pytest.raises(ValueError, match="Unknown fuels source"):
        fb.build_fbfm40("landfire", "x", "y", "z")
    with pytest.raises(ValueError, match="Unknown fuels source"):
        fb.source_classes_by_fuel_model("landfire")


def test_every_source_declares_a_label_and_a_crosswalk():
    for source in ("worldcover", "mapbiomas", "ccsbap"):
        assert source in fb.SOURCE_LABELS
        assert fb.source_classes_by_fuel_model(source)


def test_crown_fire_model_is_written_explicitly(tmp_path):
    # ELMFIRE enables crown fire when the keyword is absent, so "not written" is not
    # the same as "off" — it is "on, by nobody's decision".
    inputs = tmp_path / "in"
    inputs.mkdir()
    _grid(inputs / "dem.tif")
    path, _, _ = namelist_writer.write_namelist(
        inputs, tmp_path / "out", simulation_hours=1, output_path=tmp_path / "elmfire.data",
    )
    text = path.read_text()
    simulator_block = text.split("&SIMULATOR")[1].split("/")[0]
    assert "CROWN_FIRE_MODEL" in simulator_block, "debe ir en &SIMULATOR, no en otro grupo"
    assert f"= {namelist_writer.DEFAULT_CROWN_FIRE_MODEL}" in simulator_block


def test_non_zero_tstart_shifts_the_whole_window(tmp_path):
    # Anchoring the run to the wall clock means TSTOP moves with TSTART: ELMFIRE reads
    # weather band n at absolute time n × DT_METEOROLOGY, so TSTOP = TSTART + duration.
    inputs = tmp_path / "in"
    inputs.mkdir()
    _grid(inputs / "dem.tif")
    path, _, _ = namelist_writer.write_namelist(
        inputs, tmp_path / "out", simulation_hours=2,
        output_path=tmp_path / "elmfire.data", simulation_tstart_s=7200.0,
    )
    text = path.read_text()
    assert "SIMULATION_TSTART               = 7200.0" in text
    assert "SIMULATION_TSTOP                = 14400.0" in text
