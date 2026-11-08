"""The synthetic scenario builder must produce a directory ELMFIRE can actually run."""
import json
import math

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


def test_phi_is_elmfires_plus_minus_one_field(tmp_path):
    """-1 inside the disc, +1 outside, nothing else. A signed distance in metres made
    ELMFIRE's front advance at ~0.5x the computed rate (scripts/pruebas_fisicas.py,
    docs/resultados/modelo/auditoria.md hallazgo 2)."""
    radius, cell = 90.0, 30.0
    d = _build(tmp_path, domain_size_m=1200, cellsize_m=cell, ignition_radius_m=radius)
    with rasterio.open(d / "phi.tif") as ds:
        phi = ds.read(1)

    n = phi.shape[0]
    centre = (n - 1) / 2.0
    rows, cols = np.mgrid[0:n, 0:n]
    distance = np.hypot(rows - centre, cols - centre) * cell
    assert (phi[distance < radius] == -1.0).all()
    assert (phi[distance > radius] == 1.0).all()
    assert set(np.unique(phi)) == {-1.0, 1.0}


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


def test_old_scenario_directories_are_pruned(tmp_path, monkeypatch):
    """An afternoon of clicking through the A/B panel must not fill the disk: each run
    writes ~5 MB of uniform rasters and every click is a new directory."""
    from app.api.v1 import playground as pg

    monkeypatch.setattr(pg, "_MAX_KEPT_INPUT_DIRS", 3)
    root = tmp_path / "playground"
    root.mkdir()
    made = []
    for i in range(6):
        d = root / f"run-{i}"
        d.mkdir()
        (d / "dem.tif").write_bytes(b"x")
        # Oldest first, so run-0 is the stalest.
        import os
        os.utime(d, (1000 + i, 1000 + i))
        made.append(d)

    pg._prune_old_inputs(root)

    survivors = sorted(p.name for p in root.iterdir())
    assert survivors == ["run-3", "run-4", "run-5"], survivors


def test_pruning_an_empty_or_missing_root_is_a_no_op(tmp_path):
    from app.api.v1 import playground as pg

    pg._prune_old_inputs(tmp_path / "does-not-exist")  # must not raise
    empty = tmp_path / "empty"
    empty.mkdir()
    pg._prune_old_inputs(empty)
    assert list(empty.iterdir()) == []


# ── Terrain: the one deliberate departure from a uniform domain ────────────────────────


def _fbfm(inputs_dir):
    with rasterio.open(inputs_dir / "fbfm40.tif") as ds:
        return ds.read(1)


def test_uniform_terrain_is_still_one_code_everywhere(tmp_path):
    """The lake must be opt-in: the default scenario is the controlled base case."""
    fbfm = _fbfm(_build(tmp_path, domain_size_m=1200, cellsize_m=30, fbfm40_code=165))
    assert np.unique(fbfm).tolist() == [165]


def test_lake_cuts_a_non_burnable_patch_out_of_the_slab(tmp_path):
    fbfm = _fbfm(_build(tmp_path, domain_size_m=1200, cellsize_m=30,
                        fbfm40_code=165, terrain="lake"))
    assert set(np.unique(fbfm).tolist()) == {165, 98}
    # A disc of r = 0.16·span inside a span² domain.
    expected = math.pi * builder._LAKE_RADIUS_FRAC**2
    assert abs((fbfm == 98).mean() - expected) < 0.01


def test_lake_never_swallows_the_ignition(tmp_path):
    """A lake over the ignition disc produces a run that does nothing, silently."""
    for wind, slope in [(15.0, 0), (0.0, 30), (0.0, 0)]:
        fbfm = _fbfm(_build(tmp_path / f"w{wind}s{slope}", domain_size_m=1200, cellsize_m=30,
                            terrain="lake", wind_speed_mph=wind, slope_deg=slope))
        n = fbfm.shape[0]
        assert fbfm[n // 2, n // 2] != 98, f"lake covers the ignition at wind={wind} slope={slope}"


def test_lake_sits_in_the_path_of_the_fire(tmp_path):
    """Placed downwind, otherwise the front never reaches the barrier and the terrain
    looks like it does nothing. wd=0 is wind FROM the north, so the fire runs south —
    which is the larger row index."""
    fbfm = _fbfm(_build(tmp_path, domain_size_m=1200, cellsize_m=30,
                        terrain="lake", wind_speed_mph=15.0, wind_direction_deg=0.0))
    rows = np.nonzero(fbfm == 98)[0]
    assert rows.mean() > fbfm.shape[0] / 2


def test_lake_runs_upslope_when_there_is_no_wind(tmp_path):
    """aspect_deg is the DOWNslope azimuth and fire runs upslope, so aspect 0 — terrain
    falling to the north — means the fire climbs SOUTH, the larger row index. Getting this
    backwards would park the lake behind the ignition, where nothing ever reaches it."""
    fbfm = _fbfm(_build(tmp_path, domain_size_m=1200, cellsize_m=30,
                        terrain="lake", wind_speed_mph=0.0, slope_deg=30, aspect_deg=0))
    rows = np.nonzero(fbfm == 98)[0]
    assert rows.mean() > fbfm.shape[0] / 2


def test_map_layers_draw_the_lake_only_when_the_raster_has_one(tmp_path):
    """The picture and the fuel grid come from the same geometry; a map showing a lake the
    simulation never had would be worse than no map at all."""
    def kinds(**kwargs):
        layers = builder.scenario_map_layers(Scenario(domain_size_m=1200, **kwargs))
        return [f["properties"]["kind"] for f in layers["features"]]

    assert "water" not in kinds(wind_speed_mph=15.0)
    assert "water" in kinds(wind_speed_mph=15.0, terrain="lake")
