import logging
import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query
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
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }


@router.post(
    "/firms/run",
    summary="Fetch and store recent NASA FIRMS fire detections",
    description=(
        "Starts a FIRMS ingestion run for the configured area of interest. The API "
        "downloads recent VIIRS active-fire detections from NASA FIRMS, normalizes "
        "the satellite rows into the internal schema, stores them in Postgres, and "
        "returns an ingestion `run_id`. By default it asks for the most recent day; "
        "provide `start_date` to request a historical FIRMS window starting on that "
        "date. After this succeeds, use `GET /api/v1/fires/active` to read the fire "
        "detections that were saved."
    ),
)
async def run_firms(
    day_range: int = Query(
        1,
        ge=1,
        le=5,
        description=(
            "Number of days to request from FIRMS. The current FIRMS area endpoint "
            "accepts values from 1 to 5 for this source."
        ),
    ),
    start_date: date | None = Query(
        None,
        description=(
            "Optional historical start date in `YYYY-MM-DD` format. When omitted, "
            "FIRMS returns the most recent data. When provided, FIRMS returns data "
            "from `start_date` through `start_date + day_range - 1`."
        ),
    ),
    session: AsyncSession = Depends(get_db),
):
    try:
        run_id = await run_firms_ingestion(
            session,
            day_range=day_range,
            start_date=start_date,
        )
        return _envelope(status="success", data={"run_id": str(run_id)})
    except FIRMSClientError as exc:
        logger.error("FIRMS ingestion failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@router.post(
    "/dem/run",
    summary="Download or register the terrain DEM for the area of interest",
    description=(
        "Ensures the system has a raw Copernicus GLO-30 DEM from OpenTopography for "
        "the configured area of interest. If a DEM raster asset is already registered "
        "and the file exists, the run is marked as skipped because terrain is static. "
        "If the canonical raw file already exists on disk, it is registered without "
        "downloading again. Otherwise, the API downloads the DEM and stores its raster "
        "metadata in Postgres."
    ),
)
async def run_dem(session: AsyncSession = Depends(get_db)):
    try:
        run_id = await run_dem_ingestion(session)
        return _envelope(status="success", data={"run_id": str(run_id)})
    except OpenTopographyError as exc:
        logger.error("DEM ingestion failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@router.get(
    "/runs/{run_id}",
    summary="Get the status and metadata for an ingestion run",
    description=(
        "Looks up a previous ingestion run by ID. Use this after starting FIRMS or "
        "DEM ingestion to confirm whether the run succeeded, failed, or was skipped. "
        "The response includes timestamps, any error message, and metadata such as "
        "downloaded file paths or the existing raster asset that caused a DEM run to "
        "skip."
    ),
)
async def get_run_status(
    run_id: uuid.UUID = Path(
        ...,
        description=(
            "The ingestion run ID returned by `POST /api/v1/ingestion/firms/run` "
            "or `POST /api/v1/ingestion/dem/run`."
        ),
    ),
    session: AsyncSession = Depends(get_db),
):
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
