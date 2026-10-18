"""
Terrain tiles for the map's optional 3D view — Copernicus GLO-30, the DEM ELMFIRE runs on,
read from the public AWS Open Data COGs, warped onto a Web Mercator tile and encoded as
Mapzen Terrarium RGB, the encoding MapLibre's `raster-dem` source decodes.

They replace the public Terrarium tiles, whose SRTM voids over lakes and steep slopes decode
to kilometre-high spikes in 3D (Lago Futalaufquen at -71.764, -42.723 reads -1486 m there;
Copernicus says 517 m). Copernicus is void-free with its water bodies flattened, and global,
so the relief has no edge to pan past. Each tile is read from the COGs once, then served
from disk.
"""
import io
import math
import tempfile
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import httpx
import numpy as np
import rasterio
from fastapi import APIRouter, HTTPException, Response
from PIL import Image
from rasterio.errors import RasterioError
from rasterio.merge import merge
from rasterio.transform import Affine, from_bounds
from rasterio.warp import Resampling, reproject

from app.config import resolve_data_path, settings

router = APIRouter(prefix="/terrain", tags=["terrain"])

BUCKET = "https://copernicus-dem-30m.s3.amazonaws.com"
COG_URL = BUCKET + "/{name}/{name}.tif"
TILE_SIZE = 256
# Below MIN_ZOOM a tile spans dozens of 1° cells and a cold read gets slow; MapLibre draws
# flat ground under the source's minzoom, which at continental scale hardly shows. Above
# MAX_ZOOM it overzooms: z12 is ~28 m/px at this latitude, already the DEM's own 30 m.
MIN_ZOOM = 6
MAX_ZOOM = 12

_HALF_WORLD_M = math.pi * 6378137.0
_NATIVE_M = 30.0
_NATIVE_DEG = 1 / 3600  # GLO-30's 1″ latitude spacing
_OVERVIEW_FACTORS = (2, 4, 8)  # the GLO-30 COGs' internal overviews
_GDAL_ENV = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_HTTP_MAX_RETRY": "3",
    "GDAL_HTTP_RETRY_DELAY": "1",
}


def _cache_dir() -> Path:
    return resolve_data_path(settings.data_dir) / "cache" / "terrain"


@lru_cache(maxsize=1)
def _available_cells() -> frozenset[str]:
    """The bucket's own list of 1° cells. A cell missing from it is open sea, which is how
    sea level is told apart from a read that failed."""
    path = _cache_dir() / "tileList.txt"
    if not path.exists():
        try:
            response = httpx.get(f"{BUCKET}/tileList.txt", timeout=30)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(503, f"Copernicus tile list unavailable: {exc}") from exc
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(response.text)
    return frozenset(path.read_text().split())


def _lonlat(z: int, x: int, y: int) -> tuple[float, float]:
    """North-west corner of a Web Mercator tile."""
    n = 2**z
    return x / n * 360 - 180, math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))


def _cell_names(z: int, x: int, y: int) -> list[str]:
    """Copernicus cells under a tile, each named after its south-west corner."""
    west, north = _lonlat(z, x, y)
    east, south = _lonlat(z, x + 1, y + 1)
    return [
        f"Copernicus_DSM_COG_10_{'N' if lat >= 0 else 'S'}{abs(lat):02d}_00_"
        f"{'E' if lon >= 0 else 'W'}{abs(lon):03d}_00_DEM"
        for lat in range(math.floor(south), math.ceil(north))
        for lon in range(math.floor(west), math.ceil(east))
    ]


def _render(z: int, x: int, y: int) -> np.ndarray:
    """Elevation in metres on the tile's 256×256 Web Mercator grid; 0 over open sea."""
    west, north = _lonlat(z, x, y)
    east, south = _lonlat(z, x + 1, y + 1)
    size = 2 * _HALF_WORLD_M / 2**z
    left, top = -_HALF_WORLD_M + x * size, _HALF_WORLD_M - y * size
    out = np.full((TILE_SIZE, TILE_SIZE), np.nan, dtype=np.float32)

    names = [name for name in _cell_names(z, x, y) if name in _available_cells()]
    if names:
        ground_m = size / TILE_SIZE * math.cos(math.radians((north + south) / 2))
        level = sum(f <= ground_m / _NATIVE_M for f in _OVERVIEW_FACTORS) - 1
        options = {"overview_level": level} if level >= 0 else {}
        # Every cell lands on one shared lon/lat grid, which is then warped once: warping cell
        # by cell leaves a seam of empty pixels along each degree line, decoding as a trench
        # to 0 m. The pad gives bilinear resampling its neighbours at the tile edge.
        res = _NATIVE_DEG * (_OVERVIEW_FACTORS[level] if level >= 0 else 1)
        bounds = (west - 2 * res, south - 2 * res, east + 2 * res, north + 2 * res)

        def read(name: str) -> tuple[np.ndarray, Affine]:
            url = COG_URL.format(name=name)
            with rasterio.Env(**_GDAL_ENV), rasterio.open(url, **options) as src:
                return merge([src], bounds=bounds, res=res, nodata=np.nan)

        try:
            # Parallel: a cold low-zoom tile is ~30 cells, each mostly HTTP latency.
            with ThreadPoolExecutor(max_workers=8) as pool:
                parts = list(pool.map(read, names))
        except RasterioError as exc:
            raise HTTPException(503, f"Copernicus DEM read failed: {exc}") from exc
        mosaic, transform = parts[0][0][0], parts[0][1]
        for part, _ in parts[1:]:
            mosaic = np.where(np.isnan(mosaic), part[0], mosaic)
        reproject(
            mosaic, out,
            src_transform=transform, src_crs="EPSG:4326", src_nodata=np.nan,
            dst_transform=from_bounds(left, top - size, left + size, top, TILE_SIZE, TILE_SIZE),
            dst_crs="EPSG:3857", dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
    return np.nan_to_num(out, nan=0.0)


def _encode_terrarium(elevation: np.ndarray) -> bytes:
    """height = R·256 + G + B/256 − 32768, the encoding MapLibre's `terrarium` decodes."""
    v = np.clip(elevation.astype(np.float64) + 32768.0, 0.0, 65535.99)
    rgb = np.dstack([v // 256, np.floor(v % 256), np.floor(v % 1 * 256)]).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="PNG")
    return buf.getvalue()


def tile_png(z: int, x: int, y: int) -> bytes:
    if not (MIN_ZOOM <= z <= MAX_ZOOM and 0 <= x < 2**z and 0 <= y < 2**z):
        raise HTTPException(404, "No terrain tile at this address")
    path = _cache_dir() / f"{z}/{x}/{y}.png"
    if path.exists():
        return path.read_bytes()
    png = _encode_terrarium(_render(z, x, y))
    path.parent.mkdir(parents=True, exist_ok=True)
    # Written aside and renamed, so a concurrent request never reads half a PNG.
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        tmp.write(png)
    Path(tmp.name).replace(path)
    return png


@router.get("/{z}/{x}/{y}.png")
def terrain_tile(z: int, x: int, y: int) -> Response:
    return Response(
        tile_png(z, x, y),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
