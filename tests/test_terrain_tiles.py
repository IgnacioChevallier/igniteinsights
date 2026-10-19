import io

import numpy as np
import pytest
import rasterio
from fastapi import HTTPException
from PIL import Image
from rasterio.transform import from_origin

from app.api.v1 import terrain

# Web Mercator tile over Los Alerces (≈ -71.75, -42.75), inside Copernicus cell S43_W072.
Z, X, Y = 12, 1231, 2587


def _decode(png: bytes) -> np.ndarray:
    rgb = np.asarray(Image.open(io.BytesIO(png)).convert("RGB")).astype(float)
    return rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768


def _write_cog(path, elevation: float):
    # One 1° Copernicus cell at a coarse 0.01° grid: a flat plateau is enough to check the
    # warp lands in the right place and the encoding round-trips.
    with rasterio.open(
        path, "w", driver="GTiff", height=100, width=100, count=1, dtype="float32",
        crs="EPSG:4326", transform=from_origin(-72, -42, 0.01, 0.01),
    ) as dst:
        dst.write(np.full((100, 100), elevation, dtype=np.float32), 1)


@pytest.fixture
def local_copernicus(tmp_path, monkeypatch):
    monkeypatch.setattr(terrain, "COG_URL", str(tmp_path / "{name}.tif"))
    monkeypatch.setattr(terrain, "_cache_dir", lambda: tmp_path / "cache")
    return tmp_path


def test_cell_names_follow_copernicus_south_west_corner():
    assert terrain._cell_names(Z, X, Y) == ["Copernicus_DSM_COG_10_S43_00_W072_00_DEM"]


def test_terrarium_round_trip():
    h = np.array([[-12.5, 0.0], [518.25, 2484.0]])
    assert np.allclose(_decode(terrain._encode_terrarium(h)), h, atol=1 / 256)


def test_tile_reads_copernicus_and_caches(local_copernicus, monkeypatch):
    name = "Copernicus_DSM_COG_10_S43_00_W072_00_DEM"
    _write_cog(local_copernicus / f"{name}.tif", 1234.0)
    monkeypatch.setattr(terrain, "_available_cells", lambda: frozenset({name}))

    h = _decode(terrain.tile_png(Z, X, Y))
    assert np.allclose(h, 1234.0, atol=1)
    assert (local_copernicus / "cache" / f"{Z}/{X}/{Y}.png").exists()


def test_cell_absent_from_the_list_is_sea_level(local_copernicus, monkeypatch):
    monkeypatch.setattr(terrain, "_available_cells", lambda: frozenset())
    assert np.allclose(_decode(terrain.tile_png(Z, X, Y)), 0.0)


def test_listed_cell_that_fails_to_read_is_not_cached_as_flat(local_copernicus, monkeypatch):
    # Listed but missing on disk: stands in for a network error. Caching it as 0 m would
    # bake a flat hole into the map for good.
    name = "Copernicus_DSM_COG_10_S43_00_W072_00_DEM"
    monkeypatch.setattr(terrain, "_available_cells", lambda: frozenset({name}))
    with pytest.raises(HTTPException) as exc:
        terrain.tile_png(Z, X, Y)
    assert exc.value.status_code == 503
    assert not (local_copernicus / "cache" / f"{Z}/{X}/{Y}.png").exists()


@pytest.mark.parametrize("z, x, y", [(5, 0, 0), (13, 0, 0), (12, 4096, 0)])
def test_out_of_range_tiles_are_rejected(z, x, y):
    with pytest.raises(HTTPException) as exc:
        terrain.tile_png(z, x, y)
    assert exc.value.status_code == 404
