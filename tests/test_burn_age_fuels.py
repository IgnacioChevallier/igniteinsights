"""Fuel of burns the cover map never saw (docs/resultados/LO-YA-QUEMADO-PROPUESTA.md §4, §11)."""
import numpy as np

from app.elmfire.builder.fuels_builder import (
    last_burn_before,
    reassign_burns_by_age,
    valid_fuel_codes,
)

TU5, TL6, TL8, SH4, NB8 = 165, 186, 188, 144, 98
GR1, SH3 = 101, 143


def _year(y: int) -> np.ndarray:
    return np.array([[y - 2000 if y else 0]], dtype=np.uint8)


def _bits(*years: int) -> np.ndarray:
    return np.array([[sum(1 << (y - 2001) for y in years)]], dtype=np.uint32)


def _one(fuel: int, burn_year: int, simulation_year: int = 2026, map_year: int = 2017,
         other: tuple[int, ...] | None = None) -> int:
    out = reassign_burns_by_age(np.array([[fuel]], dtype=np.int16), _year(burn_year),
                                simulation_year, map_year,
                                None if other is None else _bits(*other))
    return int(out[0, 0])


def test_forest_by_age():
    assert _one(TU5, 2025) == GR1   # 1 year
    assert _one(TL6, 2021) == GR1   # 5 years
    assert _one(TL6, 2020) == SH3   # 6 years
    assert _one(TL6, 2018) == SH3


def test_shrub_keeps_its_class_after_five_years():
    # The loop M failure: slowing a resprouting shrubland (AUDITORIA-FISICA loop M §2).
    assert _one(SH4, 2022) == GR1
    assert _one(SH4, 2018) == SH4


def test_untouched():
    assert _one(TU5, 0) == TU5             # no burn
    assert _one(TU5, 2017) == TU5          # the map already saw it
    assert _one(TU5, 2015) == TU5
    assert _one(TU5, 2026) == TU5          # simulation year: maybe the fire itself
    assert _one(TU5, 2005, 2026, 2003) == TU5   # older than 15 years
    assert _one(NB8, 2025) == NB8          # water stays water


def test_forest_takes_other_sources_only_after_hansen():
    # LYQ-2: a pine plantation burnt in 2021 that Hansen never saw replaced stays a plantation.
    assert _one(TL8, 0, other=(2021,)) == TL8
    assert _one(TL8, 0, 2027, other=(2026,)) == GR1      # Hansen has not published 2026 yet
    assert _one(TL8, 2019, other=(2021,)) == SH3         # Hansen's year wins in forest
    assert _one(SH4, 0, other=(2024,)) == GR1            # shrubs take any source


def test_the_fire_itself_does_not_hide_earlier_burns():
    # Pre-LYQ-3: with only the last year per cell, Patriada 2026's own scar hid its 2021 burns.
    assert _one(SH4, 0, other=(2021, 2026)) == GR1
    assert _one(SH4, 0, other=(2026,)) == SH4
    assert _one(SH4, 2016, 2016, 2013, other=(2015,)) == GR1   # Hansen marks the fire's own year
    assert int(last_burn_before(_bits(2012, 2021, 2026), 2026)[0, 0]) == 21
    assert int(last_burn_before(_bits(2026), 2026)[0, 0]) == 0


def test_only_defined_codes():
    fuels = np.array([sorted(valid_fuel_codes())], dtype=np.int16)
    burn = np.full(fuels.shape, 2024 - 2000, dtype=np.uint8)
    out = reassign_burns_by_age(fuels, burn, 2026, 2017, np.full(fuels.shape, 1 << 23, np.uint32))
    assert set(np.unique(out)) <= valid_fuel_codes()
