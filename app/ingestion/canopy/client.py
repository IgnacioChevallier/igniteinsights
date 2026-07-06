"""
Canopy cover and height downloads from two public COG sources (no auth):
  - Hansen Global Forest Change v1.11 treecover2000 (Google Cloud Storage, 30 m)
  - ETH Global Canopy Height 2020 — Lang et al. (libdrive.ethz.ch, 10 m)
"""
import logging
import math
import tempfile
from pathlib import Path

import httpx

from .errors import CanopyDownloadError, CanopyTileNotFoundError
from .schemas import CanopyLayerMetadata, CanopyTile

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = httpx.Timeout(600.0)

# ── Hansen GFC v1.11 ─────────────────────────────────────────────────────────
_HANSEN_BASE = (
    "https://storage.googleapis.com/earthenginepartners-hansen"
    "/GFC-2023-v1.11"
)
_HANSEN_VERSION = "GFC-2023-v1.11"
_HANSEN_TILE_DEG = 10  # 10°×10° tiles, named by NW (upper-left) corner


def _hansen_tile_id(lat_nw: int, lon_nw: int) -> str:
    """Tile ID for the upper-left (NW) corner, e.g. '40S_080W'."""
    ns = "S" if lat_nw < 0 else "N"
    ew = "W" if lon_nw < 0 else "E"
    return f"{abs(lat_nw):02d}{ns}_{abs(lon_nw):03d}{ew}"


def _hansen_tiles(west: float, south: float, east: float, north: float) -> list[CanopyTile]:
    """Return all Hansen 10°×10° tiles that cover the bbox."""
    # NW corner for the tile containing `south`: ceil to nearest 10° multiple above south
    lat_nw_start = math.ceil(south / _HANSEN_TILE_DEG) * _HANSEN_TILE_DEG
    lat_nw_end = math.ceil(north / _HANSEN_TILE_DEG) * _HANSEN_TILE_DEG
    lon_nw_start = math.floor(west / _HANSEN_TILE_DEG) * _HANSEN_TILE_DEG
    lon_nw_end = math.floor(east / _HANSEN_TILE_DEG) * _HANSEN_TILE_DEG

    tiles: list[CanopyTile] = []
    lat = lat_nw_start
    while lat <= lat_nw_end:
        lon = lon_nw_start
        while lon <= lon_nw_end:
            tile_id = _hansen_tile_id(lat, lon)
            url = f"{_HANSEN_BASE}/Hansen_{_HANSEN_VERSION}_treecover2000_{tile_id}.tif"
            tiles.append(CanopyTile(tile_id=tile_id, url=url))
            lon += _HANSEN_TILE_DEG
        lat += _HANSEN_TILE_DEG

    return tiles


# ── ETH Global Canopy Height 2020 ────────────────────────────────────────────
_ETH_BASE = "https://libdrive.ethz.ch/index.php/s/cO8or7iOe5dT2Rt/download"
_ETH_VERSION = "ETH-GlobalCanopyHeight-2020"
_ETH_TILE_DEG = 3  # 3°×3° tiles, named by SW (lower-left) corner


def _eth_tile_id(lat_ll: int, lon_ll: int) -> str:
    """Tile ID for the lower-left (SW) corner, e.g. 'S45W072'."""
    ns = "S" if lat_ll < 0 else "N"
    ew = "W" if lon_ll < 0 else "E"
    return f"{ns}{abs(lat_ll):02d}{ew}{abs(lon_ll):03d}"


def _eth_tiles(west: float, south: float, east: float, north: float) -> list[CanopyTile]:
    """Return all ETH 3°×3° tiles that cover the bbox."""
    lat_start = math.floor(south / _ETH_TILE_DEG) * _ETH_TILE_DEG
    lat_end = math.floor(north / _ETH_TILE_DEG) * _ETH_TILE_DEG
    lon_start = math.floor(west / _ETH_TILE_DEG) * _ETH_TILE_DEG
    lon_end = math.floor(east / _ETH_TILE_DEG) * _ETH_TILE_DEG

    tiles: list[CanopyTile] = []
    lat = lat_start
    while lat <= lat_end:
        lon = lon_start
        while lon <= lon_end:
            tile_id = _eth_tile_id(lat, lon)
            url = (
                f"{_ETH_BASE}?path=%2F3deg_cogs%2FETH_GlobalCanopyHeight_10m_2020_{tile_id}_Map.tif"
            )
            tiles.append(CanopyTile(tile_id=tile_id, url=url))
            lon += _ETH_TILE_DEG
        lat += _ETH_TILE_DEG

    return tiles


# ── Shared download + clip ────────────────────────────────────────────────────

def _stream_download(url: str, dest: Path, label: str) -> None:
    """Stream-download url → dest via httpx (same pattern as WorldCover)."""
    logger.info("Downloading %s (~50–500 MB)…", label)
    try:
        with httpx.stream("GET", url, timeout=_HTTP_TIMEOUT, follow_redirects=True) as r:
            if r.status_code == 404:
                raise CanopyTileNotFoundError(f"{label} not found at {url}")
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("wb") as f:
                for chunk in r.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
    except (httpx.HTTPError, OSError) as exc:
        raise CanopyDownloadError(f"Failed to download {label}: {exc}") from exc


def _clip_and_write(
    local_paths: list[Path],
    west: float,
    south: float,
    east: float,
    north: float,
    output_path: Path,
    source_label: str,
    version: str,
    tile_ids: list[str],
    resolution_m: float,
) -> CanopyLayerMetadata:
    """Merge (if >1 tile), clip to bbox, and write a single GeoTIFF."""
    try:
        import rasterio
        from rasterio.merge import merge
    except ImportError as exc:
        raise CanopyDownloadError(f"rasterio not installed: {exc}") from exc

    datasets = [rasterio.open(p) for p in local_paths]
    try:
        crs = datasets[0].crs
        dtype = datasets[0].dtypes[0]
        nodata = datasets[0].nodata

        merged_data, merged_transform = merge(
            datasets,
            bounds=(west, south, east, north),
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(
            output_path,
            "w",
            driver="GTiff",
            height=merged_data.shape[1],
            width=merged_data.shape[2],
            count=1,
            dtype=dtype,
            crs=crs,
            transform=merged_transform,
            nodata=nodata,
            compress="deflate",
        ) as dst:
            dst.write(merged_data[0], 1)
            dst.update_tags(
                source=source_label,
                version=version,
                source_tiles=",".join(tile_ids),
            )
    finally:
        for ds in datasets:
            ds.close()

    logger.info("%s clipped raster saved to %s", source_label, output_path)
    return CanopyLayerMetadata(
        file_path=str(output_path),
        crs=str(crs),
        band_count=1,
        dtype=str(dtype),
        file_size_bytes=output_path.stat().st_size,
        resolution_m=resolution_m,
        source=source_label,
        version=version,
        tile_ids=tile_ids,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def download_hansen_cc(
    west: float,
    south: float,
    east: float,
    north: float,
    output_path: Path,
) -> CanopyLayerMetadata:
    """Download Hansen GFC treecover2000 (percent 0–100) clipped to bbox."""
    tiles = _hansen_tiles(west, south, east, north)
    if not tiles:
        raise CanopyDownloadError("No Hansen tiles computed for the given bbox")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        local_paths: list[Path] = []
        for tile in tiles:
            dest = tmp_path / f"{tile.tile_id}.tif"
            _stream_download(tile.url, dest, f"Hansen {tile.tile_id}")
            local_paths.append(dest)

        return _clip_and_write(
            local_paths, west, south, east, north, output_path,
            source_label="Hansen GFC v1.11 treecover2000",
            version=_HANSEN_VERSION,
            tile_ids=[t.tile_id for t in tiles],
            resolution_m=30.0,
        )


def download_eth_ch(
    west: float,
    south: float,
    east: float,
    north: float,
    output_path: Path,
) -> CanopyLayerMetadata:
    """Download ETH Global Canopy Height 2020 (meters) clipped to bbox."""
    tiles = _eth_tiles(west, south, east, north)
    if not tiles:
        raise CanopyDownloadError("No ETH canopy height tiles computed for the given bbox")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        local_paths: list[Path] = []
        for tile in tiles:
            dest = tmp_path / f"{tile.tile_id}.tif"
            _stream_download(tile.url, dest, f"ETH {tile.tile_id}")
            local_paths.append(dest)

        return _clip_and_write(
            local_paths, west, south, east, north, output_path,
            source_label="ETH Global Canopy Height 2020",
            version=_ETH_VERSION,
            tile_ids=[t.tile_id for t in tiles],
            resolution_m=10.0,
        )
