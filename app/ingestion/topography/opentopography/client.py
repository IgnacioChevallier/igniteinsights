import logging
from pathlib import Path

import httpx

from app.config import settings

from .errors import OpenTopographyAuthError, OpenTopographyDownloadError
from .schemas import BoundingBox, DEMMetadata

logger = logging.getLogger(__name__)

OPENTOPOGRAPHY_URL = "https://portal.opentopography.org/API/globaldem"


class OpenTopographyClient:
    def __init__(self) -> None:
        self._timeout = httpx.Timeout(120.0)

    def download_dem(self, bbox: BoundingBox, output_path: Path) -> DEMMetadata:
        params = {
            "demtype": "COP30",
            "south": bbox.south,
            "north": bbox.north,
            "west": bbox.west,
            "east": bbox.east,
            "outputFormat": "GTiff",
            "API_Key": settings.opentopography_api_key,
        }
        logger.info(
            "Downloading COP30 DEM bbox=(%s,%s,%s,%s)",
            bbox.west, bbox.south, bbox.east, bbox.north,
        )

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(OPENTOPOGRAPHY_URL, params=params)
                if response.status_code == 401:
                    raise OpenTopographyAuthError("API Key inválida o expirada")
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenTopographyDownloadError(f"Error descargando DEM: {exc}") from exc

        content_type = response.headers.get("content-type", "")
        if "json" in content_type or "html" in content_type:
            raise OpenTopographyDownloadError(
                f"Respuesta inesperada (no GeoTIFF): {response.text[:200]}"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)
        logger.info("DEM saved to %s (%d bytes)", output_path, len(response.content))

        return self._extract_metadata(output_path, bbox)

    def _extract_metadata(self, path: Path, bbox: BoundingBox) -> DEMMetadata:
        try:
            import rasterio

            with rasterio.open(path) as ds:
                return DEMMetadata(
                    file_path=str(path),
                    crs=str(ds.crs),
                    resolution_m=abs(ds.res[0]) * 111_320,  # degrees → approx meters
                    band_count=ds.count,
                    dtype=str(ds.dtypes[0]),
                    file_size_bytes=path.stat().st_size,
                    bbox=bbox,
                )
        except ImportError:
            return DEMMetadata(
                file_path=str(path),
                crs="EPSG:4326",
                resolution_m=30.0,
                band_count=1,
                dtype="float32",
                file_size_bytes=path.stat().st_size,
                bbox=bbox,
            )
