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
# The NRT products only reach back a few months. Past fires (validation cases) need the
# standard-processing archive; NOAA-21 has no SP product for 2023.
FIRMS_SOURCES_ARCHIVE = ["VIIRS_SNPP_SP", "VIIRS_NOAA20_SP"]


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
        sources: list[str] | None = None,
    ) -> pd.DataFrame:
        if not settings.firms_map_key:
            raise FIRMSAuthError("FIRMS_MAP_KEY no está configurada")
        bbox = f"{west},{south},{east},{north}"
        frames = []
        for source in sources or FIRMS_SOURCES:
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

            frame = pd.read_csv(StringIO(response.text))
            frame["source"] = source
            frames.append(frame)

        if not frames:
            return pd.DataFrame()

        df = drop_nrt_covered_by_sp(pd.concat(frames, ignore_index=True))
        logger.info("FIRMS returned %d raw rows across %d source(s)", len(df), len(frames))
        return df


def drop_nrt_covered_by_sp(df: pd.DataFrame) -> pd.DataFrame:
    """Drop NRT rows on dates the same satellite already has in SP.

    FIRMS serves SP up to its last processed day and NRT from the next one, so a request that
    asks both normally gets disjoint dates. While a new SP month is being published they can
    overlap; SP is the reprocessed product and wins. Matched by date, not coordinates: the
    reprocessing moves the points.
    """
    if df.empty or "source" not in df:
        return df
    is_sp = df["source"].str.endswith("_SP")
    satellite = df["source"].str.rsplit("_", n=1).str[0]   # VIIRS_SNPP_SP → VIIRS_SNPP
    last_sp = df[is_sp].groupby(satellite[is_sp])["acq_date"].max()
    if last_sp.empty:
        return df
    cutoff = satellite.map(last_sp)
    covered = ~is_sp & cutoff.notna() & (df["acq_date"] <= cutoff)
    if covered.any():
        logger.info("Dropped %d NRT rows already covered by SP", int(covered.sum()))
    return df[~covered].reset_index(drop=True)
