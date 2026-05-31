import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repository
from app.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fires", tags=["fires"])


def _envelope(status: str, data=None, error: dict | None = None) -> dict:
    return {
        "status": status,
        "data": data,
        "error": error,
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }


@router.get(
    "/active",
    summary="List active fire detections stored in the database",
    description=(
        "Returns recent satellite fire detections as a GeoJSON FeatureCollection. "
        "This endpoint does not contact NASA FIRMS directly; it only reads detections "
        "that were already imported by `POST /api/v1/ingestion/firms/run`. Use it "
        "after running FIRMS ingestion to inspect the fire points currently available "
        "for the configured area of interest."
    ),
)
async def get_active_fires(
    hours: int = Query(
        24,
        ge=1,
        le=168,
        description=(
            "Look-back window, in hours, used to filter stored fire detections. "
            "For example, `24` returns detections acquired during the last day; "
            "`168` returns up to the last seven days."
        ),
    ),
    session: AsyncSession = Depends(get_db),
):
    if hours < 1 or hours > 168:
        raise HTTPException(status_code=400, detail="hours must be between 1 and 168")

    features = await repository.get_active_fires(session, since=datetime.now(UTC) - timedelta(hours=hours))
    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }
    return _envelope(status="success", data=geojson)
