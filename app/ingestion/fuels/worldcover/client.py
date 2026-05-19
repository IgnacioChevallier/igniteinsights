import logging
import math
import tempfile
from pathlib import Path

import httpx

from .errors import WorldCoverDownloadError, WorldCoverTileNotFoundError
from .schemas import WorldCoverMetadata, WorldCoverTile

logger = logging.getLogger(__name__)

VERSION = "v200"
YEAR = "2021"
BASE_URL = f"https://esa-worldcover.s3.amazonaws.com/{VERSION}/{YEAR}/map"

# Tiles are 3° × 3° GeoTIFFs (COG on S3, but read locally after download).
TILE_SIZE_DEG = 3

# Download timeout: tiles are 50–150 MB each.
_HTTP_TIMEOUT = httpx.Timeout(600.0)


def _tile_id(lat_ll: int, lon_ll: int) -> str:
    """Return tile identifier for the lower-left (SW) corner in whole degrees."""
    ns = "N" if lat_ll >= 0 else "S"
    ew = "E" if lon_ll >= 0 else "W"
    return f"{ns}{abs(lat_ll):02d}{ew}{abs(lon_ll):03d}"


class WorldCoverClient:
    def compute_tile_ids(
        self,
        west: float,
        south: float,
        east: float,
        north: float,
    ) -> list[WorldCoverTile]:
        lat_start = math.floor(south / TILE_SIZE_DEG) * TILE_SIZE_DEG
        lat_end = math.floor(north / TILE_SIZE_DEG) * TILE_SIZE_DEG
        lon_start = math.floor(west / TILE_SIZE_DEG) * TILE_SIZE_DEG
        lon_end = math.floor(east / TILE_SIZE_DEG) * TILE_SIZE_DEG

        tiles: list[WorldCoverTile] = []
        lat = lat_start
        while lat <= lat_end:
            lon = lon_start
            while lon <= lon_end:
                tile_id = _tile_id(lat, lon)
                url = f"{BASE_URL}/ESA_WorldCover_10m_{YEAR}_{VERSION}_{tile_id}_Map.tif"
                tiles.append(WorldCoverTile(tile_id=tile_id, url=url))
                lon += TILE_SIZE_DEG
            lat += TILE_SIZE_DEG

        return tiles

    def _download_tile(self, tile: WorldCoverTile, dest: Path) -> None:
        """Stream-download a tile via httpx to avoid GDAL remote-read issues."""
        logger.info("Downloading WorldCover tile %s (~50–150 MB)…", tile.tile_id)
        try:
            with httpx.stream("GET", tile.url, timeout=_HTTP_TIMEOUT, follow_redirects=True) as r:
                if r.status_code == 404:
                    raise WorldCoverTileNotFoundError(
                        f"Tile {tile.tile_id} not found at {tile.url}"
                    )
                r.raise_for_status()
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("wb") as f:
                    for chunk in r.iter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
        except (httpx.HTTPError, OSError) as exc:
            raise WorldCoverDownloadError(
                f"Failed to download tile {tile.tile_id}: {exc}"
            ) from exc

    def download_clipped(
        self,
        tiles: list[WorldCoverTile],
        west: float,
        south: float,
        east: float,
        north: float,
        output_path: Path,
    ) -> WorldCoverMetadata:
        try:
            import rasterio
            from rasterio.merge import merge
        except ImportError as exc:
            raise WorldCoverDownloadError(f"rasterio not installed: {exc}") from exc

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            # Download all tiles locally (avoids GDAL's VSICURL/curl dependency).
            local_paths: list[Path] = []
            for tile in tiles:
                dest = tmp_path / f"{tile.tile_id}.tif"
                self._download_tile(tile, dest)
                local_paths.append(dest)

            datasets = [rasterio.open(p) for p in local_paths]
            try:
                crs = datasets[0].crs
                dtype = datasets[0].dtypes[0]
                nodata = datasets[0].nodata

                # Pass bounds so merge only reads the bbox window from each tile
                # (avoids loading full ~1 GB tiles into memory).
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
                        source="ESA WorldCover",
                        version=VERSION,
                        acquisition_year=YEAR,
                        source_tiles=",".join(t.tile_id for t in tiles),
                    )
            finally:
                for ds in datasets:
                    ds.close()

        logger.info("WorldCover clipped raster saved to %s", output_path)
        return WorldCoverMetadata(
            file_path=str(output_path),
            crs=str(crs),
            version=VERSION,
            year=YEAR,
            tiles_used=[t.tile_id for t in tiles],
            band_count=1,
            dtype=str(dtype),
            file_size_bytes=output_path.stat().st_size,
            resolution_m=10.0,
        )
