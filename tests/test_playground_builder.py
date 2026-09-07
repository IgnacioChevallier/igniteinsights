"""The synthetic scenario builder must produce a directory ELMFIRE can actually run."""
import json

import numpy as np
import pytest
import rasterio

from app.playground import builder
from app.playground.schemas import Scenario

_FLOAT = ["ws", "wd", "m1", "m10", "m100", "adj"]
_INT = ["dem", "slp", "asp", "fbfm40", "cc", "ch", "cbh", "cbd"]


def _build(tmp_path, **kwargs):
    d = tmp_path / "inputs"
    builder.build_scenario_inputs(Scenario(**kwargs), d)
    return d


def test_writes_every_raster_the_namelist_references(tmp_path):
    d = _build(tmp_path, domain_size_m=600, cellsize_m=30)
    for name in _FLOAT + _INT + ["phi"]:
        assert (d / f"{name}.tif").exists(), f"{name}.tif missing"
    assert (d / "fuel_models.csv").exists(), "ELMFIRE reads the table from this directory"


def test_domain_is_square_and_the_requested_size(tmp_path):
    d = _build(tmp_path, domain_size_m=1200, cellsize_m=30)
    with rasterio.open(d / "dem.tif") as ds:
        assert ds.width == ds.height == 40
        assert abs(ds.res[0] - 30.0) < 1e-6
        assert ds.crs.to_string() == "EPSG:32719"


def test_canopy_uses_elmfire_on_disk_encoding(tmp_path):
    """ch/cbh are 10x metres and cbd is 100x kg/m3. Feeding raw units silently corrupts
    crown fire behaviour: the values look plausible, just off by 10x/100x."""
    d = _build(tmp_path, domain_size_m=300, cellsize_m=30,
               cc_pct=89, ch_m=20.0, cbh_m=9.3, cbd_kg_m3=0.08)
    def val(name):
        with rasterio.open(d / f"{name}.tif") as ds:
            return int(ds.read(1)[0, 0])
    assert val("cc") == 89          # percent, unscaled
    assert val("ch") == 200         # 20.0 m
    assert val("cbh") == 93         # 9.3 m
    assert val("cbd") == 8          # 0.08 kg/m3


def test_scalars_reach_the_rasters_unchanged(tmp_path):
    d = _build(tmp_path, domain_size_m=300, cellsize_m=30,
               wind_speed_mph=15.0, wind_direction_deg=45.0, m1_pct=12.0, adj=1.0)
    def val(name):
        with rasterio.open(d / f"{name}.tif") as ds:
            return float(ds.read(1)[0, 0])
    assert val("ws") == 15.0
    assert val("wd") == 45.0
    assert val("m1") == 12.0


def test_phi_ignites_the_centre_and_respects_elmfires_floor(tmp_path):
    """ELMFIRE resets any PHI0 < -1.1 back to +1.0 (unburned) as a nodata guard
    (elmfire_io.f90). A raw signed-distance field would be erased before the run starts."""
    d = _build(tmp_path, domain_size_m=1200, cellsize_m=30, ignition_radius_m=90)
    with rasterio.open(d / "phi.tif") as ds:
        phi = ds.read(1)
    n = phi.shape[0]
    assert phi[n // 2, n // 2] < 0, "centre must be burning"
    assert phi[0, 0] > 0, "corner must be unburned"
    assert phi.min() >= -1.1, f"phi min {phi.min()} would be reset to unburned by ELMFIRE"
    assert (phi < 0).sum() > 1


def test_ignition_smaller_than_a_cell_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="no cell would ignite"):
        _build(tmp_path, domain_size_m=1200, cellsize_m=30, ignition_radius_m=1.0)


def test_a_fuel_code_absent_from_the_table_is_rejected(tmp_path):
    """Otherwise ELMFIRE resolves it to model 256 (NB) and the whole domain is unburnable,
    silently — the run 'succeeds' and shows no spread."""
    with pytest.raises(ValueError, match="absent from the fuel model table"):
        _build(tmp_path, domain_size_m=300, cellsize_m=30, fbfm40_code=177)


def test_uniform_means_uniform(tmp_path):
    d = _build(tmp_path, domain_size_m=600, cellsize_m=30, fbfm40_code=165)
    with rasterio.open(d / "fbfm40.tif") as ds:
        assert set(np.unique(ds.read(1)).tolist()) == {165}


class TestPresets:
    def test_every_preset_is_a_valid_scenario(self):
        for preset in json.loads(_presets_text()):
            Scenario(**preset["scenario"])

    def test_changes_from_resolves(self):
        presets = json.loads(_presets_text())
        ids = {p["id"] for p in presets}
        for p in presets:
            assert p["changes_from"] is None or p["changes_from"] in ids, p["id"]

    def test_every_preset_fuel_code_is_in_the_table(self):
        from app.elmfire.builder.fuels_builder import valid_fuel_codes

        defined = valid_fuel_codes()
        for p in json.loads(_presets_text()):
            code = p["scenario"].get("fbfm40_code", 102)
            assert code in defined, f"{p['id']} uses undefined fuel code {code}"

    def test_the_sequence_isolates_one_factor_at_a_time(self):
        """A preset that declares a parent must differ from it. If it does not, the
        comparison shows nothing and the preset is a copy."""
        presets = {p["id"]: p for p in json.loads(_presets_text())}
        for p in presets.values():
            parent = p["changes_from"]
            if parent is None:
                continue
            a = Scenario(**presets[parent]["scenario"]).model_dump()
            b = Scenario(**p["scenario"]).model_dump()
            differing = {
                k for k in a
                if a[k] != b[k] and k not in ("name", "description")
            }
            assert differing, f"{p['id']} is identical to {parent}"


def _presets_text() -> str:
    from app.api.v1.playground import _PRESETS_FILE

    return _PRESETS_FILE.read_text(encoding="utf-8")
