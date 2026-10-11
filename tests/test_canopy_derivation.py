"""cbh/cbd come from the measured canopy rasters, not from the fuel model code.

The old lookup was keyed by FBFM40 and held 9 entries, so any new fuel code produced
-9999 silently. Deriving from cc/ch removes the coupling rather than guarding it.
"""
import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.elmfire.builder import canopy_builder

_NODATA = -9999


def _raster(path, values):
    arr = np.asarray(values, dtype="int16")
    with rasterio.open(
        path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1,
        dtype="int16", crs="EPSG:32719", nodata=_NODATA,
        transform=from_origin(500000.0, 5300000.0, 30.0, 30.0),
    ) as dst:
        dst.write(arr, 1)
    return path


def _derive(tmp_path, cc, ch):
    cc_p = _raster(tmp_path / "cc.tif", cc)
    ch_p = _raster(tmp_path / "ch.tif", ch)
    cbh_p, cbd_p = canopy_builder.derive_cbh_cbd(
        cc_p, ch_p, tmp_path / "cbh.tif", tmp_path / "cbd.tif"
    )
    with rasterio.open(cbh_p) as a, rasterio.open(cbd_p) as b:
        return a.read(1), b.read(1)


def test_bare_ground_carries_no_crown_fuel(tmp_path):
    """cbd = 0 is the control that matters: no crown fuel, no crown fire."""
    cbh, cbd = _derive(tmp_path, [[0, 5]], [[0, 150]])
    assert (cbh == 0).all()
    assert (cbd == 0).all(), "5% cover must not produce canopy bulk density"


def test_short_vegetation_carries_no_crown_fuel(tmp_path):
    """Dense but 1 m tall: shrubland, not a canopy that can sustain crown fire."""
    cbh, cbd = _derive(tmp_path, [[90]], [[10]])  # 90% cover, 1.0 m
    assert cbd[0, 0] == 0


def test_closed_forest_gives_plausible_values_in_elmfire_encoding(tmp_path):
    """Los Alerces is ~89% cover. cbh is 10x metres, cbd is 100x kg/m3."""
    cbh, cbd = _derive(tmp_path, [[89]], [[200]])  # 89% cover, 20.0 m
    cbh_m = cbh[0, 0] / 10.0
    cbd_kg_m3 = cbd[0, 0] / 100.0
    assert 5.0 < cbh_m < 15.0, f"cbh {cbh_m} m implausible for a 20 m stand"
    assert 0.02 < cbd_kg_m3 < 0.30, f"cbd {cbd_kg_m3} kg/m3 outside the typical range"
    assert cbh_m < 20.0, "canopy base cannot sit above the canopy top"


def test_denser_stands_self_prune_higher(tmp_path):
    """Canopy base height rises with cover: closed stands shed low branches."""
    cbh, _ = _derive(tmp_path, [[20, 95]], [[200, 200]])
    assert cbh[0, 1] > cbh[0, 0]


def test_nodata_propagates(tmp_path):
    cbh, cbd = _derive(tmp_path, [[_NODATA, 89]], [[200, _NODATA]])
    assert cbh[0, 0] == _NODATA and cbd[0, 0] == _NODATA
    assert cbh[0, 1] == _NODATA and cbd[0, 1] == _NODATA


def test_forest_type_sets_cbh_and_an_unknown_code_keeps_the_derived_value(tmp_path):
    """Regression: an FBFM lookup used to blank out cbh/cbd for codes missing from it. The
    forest-type table only overrides where there is canopy; anything else stays derived."""
    cc_p = _raster(tmp_path / "cc.tif", [[80, 80, 80, 80, 0]])
    ch_p = _raster(tmp_path / "ch.tif", [[200, 200, 200, 200, 200]])
    fuel_p = _raster(tmp_path / "fbfm40.tif", [[165, 188, 186, 147, 165]])
    canopy_builder.derive_cbh_cbd(cc_p, ch_p, tmp_path / "cbh.tif", tmp_path / "cbd.tif",
                                  fuel_path=fuel_p)
    with rasterio.open(tmp_path / "cbh.tif") as a, rasterio.open(tmp_path / "cbd.tif") as b:
        cbh, cbd = a.read(1).tolist()[0], b.read(1).tolist()[0]
    assert cbh[:3] == [15, 15, 60]          # TU5 1,5 m, TL8 1,5 m, TL6 6 m
    assert cbh[3] == round(20 * (0.2 + 0.3 * 0.8) * 10)   # SH7: derivado
    assert cbh[4] == 0 and cbd[4] == 0      # sin copa, sin tabla
    assert cbd[1] == 16                     # pino 0,16 kg/m³


def test_hansen_loss_before_the_fire_year_removes_the_canopy(tmp_path):
    cc_p = _raster(tmp_path / "cc.tif", [[80, 80, 80, 80]])
    ch_p = _raster(tmp_path / "ch.tif", [[150, 150, 150, 150]])
    ly_p = _raster(tmp_path / "ly.tif", [[0, 15, 24, 25]])
    canopy_builder.derive_cbh_cbd(cc_p, ch_p, tmp_path / "cbh.tif", tmp_path / "cbd.tif",
                                  lossyear_path=ly_p, fire_year=2025)
    with rasterio.open(cc_p) as a, rasterio.open(ch_p) as b, \
            rasterio.open(tmp_path / "cbd.tif") as c:
        assert a.read(1).tolist() == [[80, 0, 0, 80]]   # 2025: el propio incendio, no
        assert b.read(1).tolist() == [[150, 0, 0, 150]]
        assert [v > 0 for v in c.read(1).tolist()[0]] == [True, False, False, True]


def test_cover_without_height_is_not_canopy(tmp_path):
    """Hansen cover over ETH height ~0 gave ELMFIRE a sheltered wind factor of 0: the cell had
    no wind at all (docs/resultados/AUDITORIA-FISICA.md, hallazgo 4). No height, no canopy,
    no cover."""
    _derive(tmp_path, [[60, 60, 0, 60]], [[0, 150, 150, -9999]])
    with rasterio.open(tmp_path / "cc.tif") as src:
        # ch nodata too: ELMFIRE clamps its height index to 0 (elmfire_init.f90:557)
        assert src.read(1).tolist() == [[0, 60, 0, 0]]
