"""The topography cache must not serve stale rasters after the derivation changes."""
import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.elmfire.builder import raster_aligner


def _raw_dem(path, value=100.0, size=8):
    with rasterio.open(
        path, "w", driver="GTiff", height=size, width=size, count=1,
        dtype="float32", crs="EPSG:4326",
        transform=from_origin(-72.0, -42.5, 0.001, 0.001),
    ) as dst:
        dst.write(np.full((1, size, size), value, dtype="float32"))
    return path


def test_second_call_hits_the_cache(tmp_path, caplog):
    raw = _raw_dem(tmp_path / "raw.tif")
    static = tmp_path / "static"
    raster_aligner.reproject_and_derive_topo(raw, static)
    mtime = (static / "dem.tif").stat().st_mtime_ns

    with caplog.at_level("INFO"):
        raster_aligner.reproject_and_derive_topo(raw, static)
    assert "cache hit" in caplog.text
    assert (static / "dem.tif").stat().st_mtime_ns == mtime


def test_bumping_the_derivation_version_invalidates_the_cache(tmp_path, monkeypatch):
    """The real failure: data/static held float32 rasters from an older revision while
    the code wrote int16, and every run silently used the stale copy."""
    raw = _raw_dem(tmp_path / "raw.tif")
    static = tmp_path / "static"
    raster_aligner.reproject_and_derive_topo(raw, static)
    before = (static / "dem.tif").read_bytes()

    # Simulate a change to the derivation code.
    monkeypatch.setattr(raster_aligner, "DERIVATION_VERSION", 999)
    monkeypatch.setattr(raster_aligner, "_derive_slope_aspect", _flat_slope_aspect)
    raster_aligner.reproject_and_derive_topo(raw, static)

    with rasterio.open(static / "slp.tif") as ds:
        assert ds.read(1).max() == 42, "stale cache served after a version bump"
    assert (static / "dem.tif").read_bytes() == before  # dem itself unchanged


def test_replacing_the_source_dem_invalidates_the_cache(tmp_path):
    raw = _raw_dem(tmp_path / "raw.tif", value=100.0)
    static = tmp_path / "static"
    raster_aligner.reproject_and_derive_topo(raw, static)
    with rasterio.open(static / "dem.tif") as ds:
        assert ds.read(1).max() == 100

    _raw_dem(raw, value=250.0)  # re-download replaces the raw DEM wholesale
    raster_aligner.reproject_and_derive_topo(raw, static)
    with rasterio.open(static / "dem.tif") as ds:
        assert ds.read(1).max() == 250, "cache ignored a replaced source DEM"


def test_unreadable_key_file_rebuilds_rather_than_crashing(tmp_path):
    raw = _raw_dem(tmp_path / "raw.tif")
    static = tmp_path / "static"
    raster_aligner.reproject_and_derive_topo(raw, static)
    (static / raster_aligner._CACHE_KEY_FILE).write_text("{ not json")
    raster_aligner.reproject_and_derive_topo(raw, static)
    assert (static / "dem.tif").exists()


def _flat_slope_aspect(dem_path, slp_path, asp_path, cell_size):
    with rasterio.open(dem_path) as ds:
        profile = ds.meta.copy()
    profile.update(dtype="int16", nodata=-9999, count=1)
    for path in (slp_path, asp_path):
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(np.full((1, profile["height"], profile["width"]), 42, dtype="int16"))
