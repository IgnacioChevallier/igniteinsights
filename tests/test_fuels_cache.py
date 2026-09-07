"""The fbfm40 cache must not serve a stale raster after the crosswalk changes.

Before this, `preparation.service` guarded regeneration with a bare `.exists()`, so any
edit to WORLDCOVER_TO_FBFM40 was a no-op until someone deleted data/static/fbfm40.tif by
hand — the same failure raster_aligner already had for dem/slp/asp.
"""
import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.elmfire.builder import fuels_builder


def _worldcover(path, block=(10, 20), size=8):
    """Two land-cover classes, left half `block[0]`, right half `block[1]`, at 10 m."""
    data = np.full((size, size), block[0], dtype="uint8")
    data[:, size // 2:] = block[1]
    with rasterio.open(
        path, "w", driver="GTiff", height=size, width=size, count=1,
        dtype="uint8", crs="EPSG:32719", nodata=0,
        transform=from_origin(500000.0, 5300000.0, 10.0, 10.0),
    ) as dst:
        dst.write(data, 1)
    return path


def _reference(path, size=8):
    """Reference grid on the same footprint, so reprojection is a pure resample."""
    with rasterio.open(
        path, "w", driver="GTiff", height=size, width=size, count=1,
        dtype="float32", crs="EPSG:32719",
        transform=from_origin(500000.0, 5300000.0, 10.0, 10.0),
    ) as dst:
        dst.write(np.zeros((size, size), dtype="float32"), 1)
    return path


def test_second_call_hits_the_cache(tmp_path, caplog):
    wc = _worldcover(tmp_path / "wc.tif")
    ref = _reference(tmp_path / "ref.tif")
    out = tmp_path / "static" / "fbfm40.tif"

    fuels_builder.worldcover_to_fbfm40(wc, ref, out)
    mtime = out.stat().st_mtime_ns

    with caplog.at_level("INFO"):
        fuels_builder.worldcover_to_fbfm40(wc, ref, out)
    assert "cache hit" in caplog.text
    assert out.stat().st_mtime_ns == mtime


def test_editing_the_crosswalk_invalidates_the_cache(tmp_path, monkeypatch):
    """The real failure this guards: change the table, nothing happens."""
    wc = _worldcover(tmp_path / "wc.tif")
    ref = _reference(tmp_path / "ref.tif")
    out = tmp_path / "static" / "fbfm40.tif"

    fuels_builder.worldcover_to_fbfm40(wc, ref, out)
    with rasterio.open(out) as ds:
        assert 183 in ds.read(1), "tree cover should start out as TL3"

    edited = dict(fuels_builder.WORLDCOVER_TO_FBFM40)
    edited[10] = 165  # tree cover → TU5
    monkeypatch.setattr(fuels_builder, "WORLDCOVER_TO_FBFM40", edited)
    fuels_builder.worldcover_to_fbfm40(wc, ref, out)

    with rasterio.open(out) as ds:
        codes = set(np.unique(ds.read(1)).tolist())
    assert 165 in codes, "stale cache served after a crosswalk edit"
    assert 183 not in codes


def test_bumping_the_derivation_version_invalidates_the_cache(tmp_path, monkeypatch):
    wc = _worldcover(tmp_path / "wc.tif")
    ref = _reference(tmp_path / "ref.tif")
    out = tmp_path / "static" / "fbfm40.tif"

    fuels_builder.worldcover_to_fbfm40(wc, ref, out)
    monkeypatch.setattr(fuels_builder, "DERIVATION_VERSION", 999)

    key_before = (out.parent / fuels_builder._CACHE_KEY_FILE).read_text()
    fuels_builder.worldcover_to_fbfm40(wc, ref, out)
    assert (out.parent / fuels_builder._CACHE_KEY_FILE).read_text() != key_before


def test_aggregation_takes_the_majority_class(tmp_path):
    """Downsampling 10 m → 30 m: a pixel that is 8/9 shrubland must not become grassland
    because the class at its centre happened to differ. Resampling.nearest could."""
    size = 9
    data = np.full((size, size), 20, dtype="uint8")   # shrubland
    data[4, 4] = 30                                    # one grassland cell at the centre
    src = tmp_path / "wc.tif"
    with rasterio.open(
        src, "w", driver="GTiff", height=size, width=size, count=1,
        dtype="uint8", crs="EPSG:32719", nodata=0,
        transform=from_origin(500000.0, 5300000.0, 10.0, 10.0),
    ) as dst:
        dst.write(data, 1)

    ref = tmp_path / "ref.tif"
    with rasterio.open(
        ref, "w", driver="GTiff", height=3, width=3, count=1,
        dtype="float32", crs="EPSG:32719",
        transform=from_origin(500000.0, 5300000.0, 30.0, 30.0),
    ) as dst:
        dst.write(np.zeros((3, 3), dtype="float32"), 1)

    out = tmp_path / "static" / "fbfm40.tif"
    fuels_builder.worldcover_to_fbfm40(src, ref, out)
    with rasterio.open(out) as ds:
        centre = ds.read(1)[1, 1]
    assert centre == fuels_builder.WORLDCOVER_TO_FBFM40[20], (
        "centre pixel is 8/9 shrubland; majority aggregation must keep it shrubland"
    )


def test_an_undefined_fbfm_code_raises_instead_of_becoming_unburnable(tmp_path, monkeypatch):
    """ELMFIRE resolves a code missing from the fuel model table to 256 (NB, unburnable)
    with no error. A crosswalk edit that introduces such a code must not reach disk."""
    import pytest

    wc = _worldcover(tmp_path / "wc.tif")
    ref = _reference(tmp_path / "ref.tif")
    out = tmp_path / "static" / "fbfm40.tif"

    edited = dict(fuels_builder.WORLDCOVER_TO_FBFM40)
    edited[10] = 177  # a TU-block number reserved for custom models, not in the table
    monkeypatch.setattr(fuels_builder, "WORLDCOVER_TO_FBFM40", edited)

    with pytest.raises(ValueError, match="absent from the fuel model table"):
        fuels_builder.worldcover_to_fbfm40(wc, ref, out)
    assert not out.exists(), "a raster with an undefined code must not be written"


def test_every_code_the_crosswalk_can_emit_is_in_the_table():
    defined = fuels_builder.valid_fuel_codes()
    emitted = set(fuels_builder.WORLDCOVER_TO_FBFM40.values()) | {fuels_builder._NODATA_FBFM40}
    assert emitted <= defined, f"undefined: {sorted(emitted - defined)}"


def test_namelist_and_builder_agree_on_the_table_filename():
    """The namelist names the file; the builder owns the path. One test kills the drift."""
    from app.elmfire.builder import namelist_writer

    assert fuels_builder.FUEL_MODEL_TABLE.name == namelist_writer.FUEL_MODEL_FILE
    assert fuels_builder.FUEL_MODEL_TABLE.exists()


def test_the_table_has_no_header_or_comments():
    """ELMFIRE's reader is a list-directed READ in a `DO WHILE (IOS .EQ. 0)` loop: the
    first unparseable line silently truncates the table and drops every model after it."""
    for n, line in enumerate(
        fuels_builder.FUEL_MODEL_TABLE.read_text().splitlines(), start=1
    ):
        if not line.strip():
            continue
        fields = line.split(",")
        assert len(fields) == 14, f"line {n}: expected 14 fields, got {len(fields)}"
        int(fields[0])  # raises if the line is a header or a comment
        assert fields[2] in (".TRUE.", ".FALSE."), f"line {n}: bad dynamic flag"
