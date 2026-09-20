"""A static raster from a smaller AOI must not be reused after the AOI is widened.

Widening `aoi_*` used to be a no-op: the ingestion guard skipped on "asset row and file
exist", so DEM/WorldCover/canopy stayed cut to the old footprint and every derived raster
silently inherited it.
"""
import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.ingestion import coverage


def _raster(path, west, north, size_deg, n=4):
    res = size_deg / n
    with rasterio.open(
        path, "w", driver="GTiff", height=n, width=n, count=1, dtype="uint8",
        crs="EPSG:4326", transform=from_origin(west, north, res, res),
    ) as dst:
        dst.write(np.ones((n, n), dtype="uint8"), 1)
    return path


def _set_aoi(monkeypatch, west, south, east, north):
    for name, value in [
        ("aoi_west", west), ("aoi_south", south), ("aoi_east", east), ("aoi_north", north)
    ]:
        monkeypatch.setattr(coverage.settings, name, value, raising=False)


def test_raster_covering_the_aoi_is_reused(tmp_path, monkeypatch):
    _set_aoi(monkeypatch, -72.0, -42.9, -71.5, -42.5)
    r = _raster(tmp_path / "wide.tif", west=-72.5, north=-42.0, size_deg=1.5)
    assert coverage.covers_aoi(r)


def test_raster_from_the_old_smaller_aoi_is_rejected(tmp_path, monkeypatch):
    """The real case: AOI widened north to -42.05, the raster stops at -42.5."""
    r = _raster(tmp_path / "old.tif", west=-72.05, north=-42.5, size_deg=0.4)
    _set_aoi(monkeypatch, -72.05, -42.90, -71.15, -42.05)
    assert not coverage.covers_aoi(r), "stale raster reused after the AOI was widened"


def test_partial_overlap_is_not_coverage(tmp_path, monkeypatch):
    _set_aoi(monkeypatch, -72.0, -42.9, -71.5, -42.5)
    r = _raster(tmp_path / "shifted.tif", west=-71.8, north=-42.4, size_deg=0.5)
    assert not coverage.covers_aoi(r)


def test_unreadable_file_forces_reingestion(tmp_path, monkeypatch):
    _set_aoi(monkeypatch, -72.0, -42.9, -71.5, -42.5)
    bad = tmp_path / "truncated.tif"
    bad.write_bytes(b"not a geotiff")
    assert not coverage.covers_aoi(bad)
