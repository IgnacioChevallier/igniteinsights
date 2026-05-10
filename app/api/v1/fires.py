import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
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
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
    }


@router.get("/active")
async def get_active_fires(
    hours: int = 24,
    session: AsyncSession = Depends(get_db),
):
    if hours < 1 or hours > 168:
        raise HTTPException(status_code=400, detail="hours must be between 1 and 168")

    features = await repository.get_active_fires(session, hours=hours)
    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }
    return _envelope(status="success", data=geojson)
