"""Fuel of burns the cover map never saw (docs/resultados/LO-YA-QUEMADO-PROPUESTA.md §4)."""
import numpy as np

from app.elmfire.builder.fuels_builder import reassign_burns_by_age, valid_fuel_codes

TU5, TL6, SH4, NB8 = 165, 186, 144, 98
GR1, GS3, SH3 = 101, 123, 143


def _one(fuel: int, burn_year: int, simulation_year: int = 2026, map_year: int = 2017) -> int:
    out = reassign_burns_by_age(np.array([[fuel]], dtype=np.int16),
                                np.array([[burn_year - 2000 if burn_year else 0]], dtype=np.uint8),
                                simulation_year, map_year)
    return int(out[0, 0])


def test_forest_by_age():
    assert _one(TU5, 2025) == GR1   # 1 year
    assert _one(TU5, 2024) == GR1   # 2 years
    assert _one(TL6, 2022) == GS3   # 4 years
    assert _one(TL6, 2018) == SH3   # 8 years


def test_shrub_keeps_its_class_after_two_years():
    # The loop M failure: slowing a resprouting shrubland (AUDITORIA-FISICA loop M §2).
    assert _one(SH4, 2025) == GR1
    assert _one(SH4, 2022) == SH4
    assert _one(SH4, 2018) == SH4


def test_untouched():
    assert _one(TU5, 0) == TU5             # no burn
    assert _one(TU5, 2017) == TU5          # the map already saw it
    assert _one(TU5, 2015) == TU5
    assert _one(TU5, 2026) == TU5          # simulation year: maybe the fire itself
    assert _one(TU5, 2005, 2026, 2003) == TU5   # older than 15 years
    assert _one(NB8, 2025) == NB8          # water stays water


def test_only_defined_codes():
    fuels = np.array([sorted(valid_fuel_codes())], dtype=np.int16)
    burn = np.full(fuels.shape, 2024 - 2000, dtype=np.uint8)
    assert set(np.unique(reassign_burns_by_age(fuels, burn, 2026, 2017))) <= valid_fuel_codes()
