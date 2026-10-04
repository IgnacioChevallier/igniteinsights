"""The CCS-BAP legend → FBFM40 resolution (docs/crosswalk/IGN-20B-FINAL-CROSSWALK-CCSBAP.md §3).

The failure this guards against is silent: a legend class with no fuel model would either
raise deep inside a raster build or, worse, land on a code ELMFIRE resolves to unburnable.
"""
from pathlib import Path

import pytest

from app.elmfire.builder.fuels_builder import (
    CCSBAP_TO_FBFM40,
    ccsbap_fuel_code,
    valid_fuel_codes,
)

CCSBAP_SHP = Path("datasets/CH_2017_Ver20190521_Subido202000316/cob_2017_N3_aok_CH.shp")


def test_level3_override_beats_level2():
    # Turbera lives under OT/Humedales, whose level-2 model is GR5 (mallín). Rothermel does
    # not model smouldering combustion, so the peatland must not inherit the marsh's model.
    assert ccsbap_fuel_code("OT", "Humedales", "Mallin") == 105
    assert ccsbap_fuel_code("OT", "Humedales", "Turbera") == 99


def test_species_mixtures_inherit_their_level2():
    # "Le-Co" is lenga with coihue: it takes lenga's model, the dominant species naming it.
    assert ccsbap_fuel_code("TF", "Le", "Le-Co") == ccsbap_fuel_code("TF", "Le", "Le")


def test_level1_disambiguates_repeated_level2_codes():
    # "Le" is both closed lenga forest (TF) and stunted lenga shrubland (OFL). Keying on
    # level 2 alone would give a litter model to a shrubland.
    assert ccsbap_fuel_code("TF", "Le", "Le") != ccsbap_fuel_code("OFL", "Le", "Le Ach")


def test_unknown_class_raises_instead_of_defaulting():
    with pytest.raises(ValueError, match="no fuel model"):
        ccsbap_fuel_code("TF", "Inexistente", "Inexistente")


def test_every_model_exists_in_the_table_elmfire_loads():
    defined = valid_fuel_codes()
    assert set(CCSBAP_TO_FBFM40.values()) <= defined


@pytest.mark.skipif(not CCSBAP_SHP.exists(), reason="CCS-BAP dataset not present")
def test_every_legend_class_in_the_real_layer_resolves():
    import pyogrio

    df = pyogrio.read_dataframe(CCSBAP_SHP, read_geometry=False)
    unresolved = {
        (a, b, c)
        for a, b, c in zip(df["Ley_N1"], df["Ley_N2"], df["Ley_N3"])
        if _fails(a, b, c)
    }
    assert not unresolved


def _fails(a: str, b: str, c: str) -> bool:
    try:
        ccsbap_fuel_code(a, b, c)
        return False
    except ValueError:
        return True


def test_estepa_sobre_el_limite_del_bosque_es_no_quemable(tmp_path):
    """La 'Estepa' de CCS-BAP sobre 1.300 m es vegetación altoandina: NB9; abajo, GR2. Un
    polígono de otra clase a la misma altura no cambia."""
    import geopandas as gpd
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from shapely.geometry import box

    from app.elmfire.builder.fuels_builder import ccsbap_to_fbfm40

    t = from_origin(500000, 5300000, 30, 30)
    dem = tmp_path / "dem.tif"
    with rasterio.open(dem, "w", driver="GTiff", height=1, width=3, count=1, dtype="float32",
                       crs="EPSG:32719", transform=t) as dst:
        dst.write(np.array([[1400.0, 900.0, 1400.0]], dtype="float32"), 1)
    gdf = gpd.GeoDataFrame(
        {"Ley_N1": ["OT", "OT", "TF"], "Ley_N2": ["Herb-Subarb", "Herb-Subarb", "Le"],
         "Ley_N3": ["Estepa", "Estepa", "Le"]},
        geometry=[box(500000, 5299970, 500030, 5300000), box(500030, 5299970, 500060, 5300000),
                  box(500060, 5299970, 500090, 5300000)], crs="EPSG:32719")
    shp = tmp_path / "ccsbap.shp"
    gdf.to_file(shp)
    salida = ccsbap_to_fbfm40(shp, dem, tmp_path / "fbfm40.tif")
    with rasterio.open(salida) as src:
        assert src.read(1).tolist() == [[99, 102, 186]]
