import logging
from io import StringIO

import httpx
import pandas as pd

from app.config import settings

from .errors import FIRMSAuthError, FIRMSClientError

logger = logging.getLogger(__name__)

FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


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
    ) -> pd.DataFrame:
        bbox = f"{west},{south},{east},{north}"
        url = f"{FIRMS_BASE_URL}/{settings.firms_map_key}/VIIRS_NOAA20_NRT/{bbox}/{day_range}"
        logger.info("Fetching FIRMS data bbox=%s day_range=%d", bbox, day_range)

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url)
                if response.status_code == 401:
                    raise FIRMSAuthError("MAP_KEY inválida o expirada")
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FIRMSClientError(f"Error HTTP al consultar FIRMS: {exc}") from exc

        if not response.text.strip() or "No data" in response.text:
            logger.info("FIRMS returned no detections for this bbox/period")
            return pd.DataFrame()

        df = pd.read_csv(StringIO(response.text))
        logger.info("FIRMS returned %d raw rows", len(df))
        return df
