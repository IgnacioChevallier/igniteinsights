"""Parses ELMFIRE's fire_size_stats.csv into JSON-serializable rows.

Every observed run produces exactly one row (a single icase / Meteorology band) —
this is the run's final-state summary at `tstop (h)`, not a time series. Sentinel
values from ELMFIRE: `-1.0` in population_affected / real_estate_value / land_value
means "no assets-at-risk layer configured" (not a real zero); `-9999.0` in
containfrac is a nodata sentinel. Callers should render these as "N/A", not as 0.
"""
import csv
from pathlib import Path

_COLUMN_MAP = {
    "icase": "icase",
    "Meteorology band": "meteorology_band",
    "x": "x",
    "y": "y",
    "tstop (h)": "tstop_h",
    "Wall clock time (s)": "wall_clock_time_s",
    "Total fire area (ac)": "total_fire_area_ac",
    "Crown fire area (ac)": "crown_fire_area_ac",
    "Fire volume (ac-ft)": "fire_volume_ac_ft",
    "Population affected": "population_affected",
    "Real estate value": "real_estate_value",
    "Land value": "land_value",
    "Nembers": "nembers",
    "Pyrome": "pyrome",
    "Containfrac": "containfrac",
    "PM 2.5 release (ug)": "pm25_release_ug",
    "HRR peak (MW)": "hrr_peak_mw",
    "Start timestamp": "start_timestamp",
    "Fire id": "fire_id",
    "Astop (ac)": "astop_ac",
}


def read_fire_size_stats(csv_path: Path) -> list[dict]:
    """Return each data row of fire_size_stats.csv as a dict keyed by normalized
    snake_case names, with numeric values coerced to int/float. Returns [] if the
    file doesn't exist — a valid state for a run with no size-stats output."""
    if not csv_path.exists():
        return []

    rows = []
    with csv_path.open(newline="") as f:
        for raw_row in csv.DictReader(f):
            row = {}
            for key, value in raw_row.items():
                mapped_key = _COLUMN_MAP.get(key.strip(), key.strip())
                row[mapped_key] = _coerce(value.strip() if isinstance(value, str) else value)
            rows.append(row)
    return rows


def _coerce(value):
    if value in (None, ""):
        return None
    for cast in (int, float):
        try:
            return cast(value)
        except (TypeError, ValueError):
            continue
    return value
