import logging
from datetime import date
from io import StringIO

import httpx
import pandas as pd

from app.config import settings

from .errors import FIRMSAuthError, FIRMSClientError

logger = logging.getLogger(__name__)

FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# Querying only one satellite can silently miss real fires it never overflew —
# confirmed for the Los Alerces Jan/Feb 2026 event, detected exclusively by
# NOAA-21 (zero NOAA-20 detections in the same AOI/period).
FIRMS_SOURCES = ["VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT", "VIIRS_SNPP_NRT"]


class FIRMSClient:
    def __init__(self) -> None:
        self._timeout = httpx.Timeout(30.0)

    def fetch_active_fires(
        self,
        west: float,
        south: float,
        east: float,
        north: float,
        day_range: int = 1,
        start_date: date | None = None,
    ) -> pd.DataFrame:
        bbox = f"{west},{south},{east},{north}"
        frames = []
        for source in FIRMS_SOURCES:
            url = f"{FIRMS_BASE_URL}/{settings.firms_map_key}/{source}/{bbox}/{day_range}"
            if start_date is not None:
                url = f"{url}/{start_date.isoformat()}"

            logger.info(
                "Fetching FIRMS data source=%s bbox=%s day_range=%d start_date=%s",
                source,
                bbox,
                day_range,
                start_date,
            )

            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.get(url)
                    if response.status_code == 401:
                        raise FIRMSAuthError("MAP_KEY inválida o expirada")
                    response.raise_for_status()
            except httpx.HTTPError as exc:
                raise FIRMSClientError(f"Error HTTP al consultar FIRMS ({source}): {exc}") from exc

            if not response.text.strip() or "No data" in response.text:
                logger.info("FIRMS source=%s returned no detections for this bbox/period", source)
                continue

            frames.append(pd.read_csv(StringIO(response.text)))

        if not frames:
            return pd.DataFrame()

        df = pd.concat(frames, ignore_index=True)
        logger.info("FIRMS returned %d raw rows across %d source(s)", len(df), len(frames))
        return df
