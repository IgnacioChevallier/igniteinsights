import logging
from datetime import UTC, datetime

import pandas as pd
from shapely.geometry import Point

from .schemas import FireDetectionNormalized

logger = logging.getLogger(__name__)

ACCEPTED_CONFIDENCE = {"n", "h"}


def normalize_firms_response(df: pd.DataFrame) -> list[FireDetectionNormalized]:
    if df.empty:
        return []

    filtered = df[df["confidence"].isin(ACCEPTED_CONFIDENCE)].copy()
    discarded = len(df) - len(filtered)
    if discarded:
        logger.info("Discarded %d low-confidence detections", discarded)

    detections: list[FireDetectionNormalized] = []
    for _, row in filtered.iterrows():
        acq_dt = datetime.strptime(
            f"{row['acq_date']} {str(int(row['acq_time'])).zfill(4)}",
            "%Y-%m-%d %H%M",
        ).replace(tzinfo=UTC)

        detections.append(
            FireDetectionNormalized(
                geom=Point(float(row["longitude"]), float(row["latitude"])),
                bright_ti4=float(row["bright_ti4"]),
                frp=float(row["frp"]),
                confidence=str(row["confidence"]),
                acq_datetime=acq_dt,
                satellite=str(row["satellite"]),
                daynight=str(row["daynight"]),
            )
        )

    logger.info("Normalized %d fire detections", len(detections))
    return detections
