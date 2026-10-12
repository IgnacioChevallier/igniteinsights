"""The app asks FIRMS for SP and NRT together; SP wins where they overlap."""
import pandas as pd

from app.ingestion.satellite.firms.client import drop_nrt_covered_by_sp


def test_nrt_dropped_where_sp_covers_the_satellite():
    df = pd.DataFrame({
        "source": ["VIIRS_SNPP_SP", "VIIRS_SNPP_NRT", "VIIRS_SNPP_NRT", "VIIRS_NOAA21_NRT"],
        "acq_date": ["2026-06-30", "2026-06-30", "2026-07-01", "2026-06-30"],
    })
    kept = drop_nrt_covered_by_sp(df)
    assert list(zip(kept["source"], kept["acq_date"])) == [
        ("VIIRS_SNPP_SP", "2026-06-30"),
        ("VIIRS_SNPP_NRT", "2026-07-01"),
        ("VIIRS_NOAA21_NRT", "2026-06-30"),   # no SP product for NOAA-21
    ]


def test_nrt_only_is_untouched():
    df = pd.DataFrame({"source": ["VIIRS_NOAA20_NRT"], "acq_date": ["2026-10-01"]})
    assert drop_nrt_covered_by_sp(df).equals(df)
