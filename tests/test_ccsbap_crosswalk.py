"""The CCS-BAP legend → FBFM40 resolution (IGN-20B-CROSSWALK-CCSBAP.md §3).

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
