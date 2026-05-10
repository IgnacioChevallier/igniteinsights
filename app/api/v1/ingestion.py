import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repository
from app.dependencies import get_db
from app.ingestion.satellite.firms.errors import FIRMSClientError
from app.ingestion.satellite.firms.service import run_firms_ingestion
from app.ingestion.topography.opentopography.errors import OpenTopographyError
from app.ingestion.topography.opentopography.service import run_dem_ingestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def _envelope(status: str, data=None, error: dict | None = None) -> dict:
    return {
        "status": status,
        "data": data,
        "error": error,
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
    }


@router.post("/firms/run")
async def run_firms(session: AsyncSession = Depends(get_db)):
    try:
        run_id = await run_firms_ingestion(session)
        return _envelope(status="success", data={"run_id": str(run_id)})
    except FIRMSClientError as exc:
        logger.error("FIRMS ingestion failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/dem/run")
async def run_dem(session: AsyncSession = Depends(get_db)):
    try:
        run_id = await run_dem_ingestion(session)
        return _envelope(status="success", data={"run_id": str(run_id)})
    except OpenTopographyError as exc:
        logger.error("DEM ingestion failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/runs/{run_id}")
async def get_run_status(run_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    run = await repository.get_ingestion_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Ingestion run not found")
    return _envelope(
        status="success",
        data={
            "id": str(run.id),
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "error_message": run.error_message,
            "metadata": run.metadata_,
        },
    )
