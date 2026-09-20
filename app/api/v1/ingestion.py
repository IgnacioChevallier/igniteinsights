import asyncio
import logging
import uuid
from collections.abc import Awaitable
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repository
from app.db.session import async_session_factory
from app.dependencies import get_db
from app.ingestion.canopy.errors import CanopyError
from app.ingestion.canopy.service import run_canopy_ingestion
from app.ingestion.fuels.worldcover.errors import WorldCoverError
from app.ingestion.fuels.worldcover.service import run_worldcover_ingestion
from app.ingestion.meteorology.gfs.errors import GFSError
from app.ingestion.meteorology.gfs.service import run_gfs_ingestion
from app.ingestion.satellite.firms.errors import FIRMSClientError
from app.ingestion.satellite.firms.service import run_firms_ingestion
from app.ingestion.topography.opentopography.errors import OpenTopographyError
from app.ingestion.topography.opentopography.service import run_dem_ingestion
from app.preparation.service import run_preparation

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


@router.post(
    "/gfs/run",
    summary="Download a NOAA GFS forecast cycle for the area of interest",
    description=(
        "Resolves the most-recent available GFS 0.25° cycle from NOMADS/AWS/GCS and "
        "downloads four variables clipped to the configured AOI: U-wind at 10 m, V-wind "
        "at 10 m, temperature at 2 m, and relative humidity at 2 m. By default resolves "
        "the cycle closest to now (live weather). Provide `gfs_date` to fetch a historical "
        "cycle instead — AWS (noaa-gfs-bdp-pds) and Google Cloud (global-forecast-system) "
        "both retain full GFS archives back to 2021-01-01, so any date from then onward is "
        "fetchable with no extra credentials. Each variable is stored as a separate GeoTIFF "
        "and registered as a RasterAsset. Returns an ingestion run_id that can be polled "
        "via GET /runs/{run_id}."
    ),
)
async def run_gfs(
    gfs_date: date | None = Query(
        None,
        description=(
            "Optional historical date (YYYY-MM-DD). When omitted, resolves the most "
            "recent live cycle."
        ),
    ),
    session: AsyncSession = Depends(get_db),
):
    try:
        run_id = await run_gfs_ingestion(session, target_date=gfs_date)
        return _envelope(status="success", data={"run_id": str(run_id)})
    except GFSError as exc:
        logger.error("GFS ingestion failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@router.post(
    "/worldcover/run",
    summary="Download ESA WorldCover 10 m land cover for the area of interest",
    description=(
        "Downloads the ESA WorldCover v2.0 (2021) 10 m land cover tiles that intersect "
        "the configured AOI using COG windowed reads — only the bbox window is fetched. "
        "If multiple tiles are needed they are merged before clipping. The result is a "
        "single GeoTIFF registered as a 'worldcover_raw' RasterAsset. This endpoint is "
        "idempotent: if the asset is already registered and the file exists, the run is "
        "marked as skipped."
    ),
)
async def run_worldcover(session: AsyncSession = Depends(get_db)):
    try:
        run_id = await run_worldcover_ingestion(session)
        return _envelope(status="success", data={"run_id": str(run_id)})
    except WorldCoverError as exc:
        logger.error("WorldCover ingestion failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@router.post(
    "/canopy/run",
    summary="Download canopy cover (Hansen GFC) and height (ETH) for the area of interest",
    description=(
        "Downloads two public canopy datasets — Hansen Global Forest Change v1.11 "
        "treecover2000 (30 m, canopy cover %) and ETH Global Canopy Height 2020 "
        "(10 m, height in metres) — clipped to the configured AOI. Both are stored "
        "as static RasterAssets ('canopy_cc' and 'canopy_ch'). Canopy base height "
        "and bulk density (cbh.tif, cbd.tif) are derived from the fuel model during "
        "preparation and do not require a separate download. This endpoint is "
        "idempotent: if both assets are already registered and files exist, the run "
        "is marked as skipped."
    ),
)
async def run_canopy(session: AsyncSession = Depends(get_db)):
    try:
        run_id = await run_canopy_ingestion(session)
        return _envelope(status="success", data={"run_id": str(run_id)})
    except CanopyError as exc:
        logger.error("Canopy ingestion failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


class IngestionRunRequest(BaseModel):
    include_firms: bool = True
    include_dem: bool = False
    include_gfs: bool = True
    include_worldcover: bool = False
    include_canopy: bool = False
    fuels_source: Literal["ccsbap", "mapbiomas", "worldcover"] | None = Field(
        default=None,
        description="Cover product that feeds fbfm40.tif for this run. Defaults to "
                    "settings.fuels_source.",
    )
    firms_day_range: int = Field(default=1, ge=1, le=5)
    firms_start_date: date | None = None
    gfs_date: date | None = None
    gfs_forecast_hours: int | None = Field(
        default=None,
        ge=0,
        le=120,
        description=(
            "Last GFS forecast hour to fetch (inclusive) — one raster band each. "
            "Must cover the simulation horizon these rasters will be used for, or "
            "ELMFIRE freezes the weather at the last band. Defaults to "
            "settings.gfs_forecast_hours (24). GFS is hourly to f120."
        ),
    )


@router.post(
    "/run",
    summary="Run one or more ingestion sources simultaneously",
    description=(
        "Triggers any combination of FIRMS, DEM, GFS, WorldCover, and Canopy ingestions "
        "concurrently. DEM, WorldCover, and Canopy default to false (static, downloaded once). "
        "After all downloads complete, automatically runs the preparation step: derives "
        "ELMFIRE input rasters (dem, slp, asp, fbfm40, ws, wd, m1-100, phi) using the "
        "most recent data available in the DB and writes them to elmfire/inputs/{prep_id}/. "
        "Returns a map of source → run_id plus a 'preparation' summary with inputs_dir, "
        "generated files, and any missing files. When `firms_start_date` is provided "
        "without `gfs_date`, the GFS date defaults to the last day of the FIRMS window "
        "(`firms_start_date + firms_day_range - 1`) so historical fires are simulated "
        "with weather from the same period instead of the live cycle."
    ),
)
async def run_ingestion(body: IngestionRunRequest):
    async def _run(service_fn, **kwargs):
        async with async_session_factory() as s:
            return await service_fn(s, **kwargs)

    # Historical fires need weather from the same period: when a FIRMS start date is
    # given without an explicit GFS date, fetch the cycle for the *last* day of the
    # FIRMS window (the ignition day — preparation uses the newest detection as
    # ignition time). Otherwise a February fire gets paired with today's (e.g.
    # winter) weather and ELMFIRE produces zero spread.
    gfs_date = body.gfs_date
    if gfs_date is None and body.firms_start_date is not None:
        gfs_date = body.firms_start_date + timedelta(days=body.firms_day_range - 1)

    tasks: dict[str, Awaitable[object]] = {}
    if body.include_firms:
        tasks["firms"] = _run(
            run_firms_ingestion,
            day_range=body.firms_day_range,
            start_date=body.firms_start_date,
        )
    if body.include_dem:
        tasks["dem"] = _run(run_dem_ingestion)
    if body.include_gfs:
        tasks["gfs"] = _run(
            run_gfs_ingestion,
            target_date=gfs_date,
            forecast_hours=body.gfs_forecast_hours,
        )
    if body.include_worldcover:
        tasks["worldcover"] = _run(run_worldcover_ingestion)
    if body.include_canopy:
        tasks["canopy"] = _run(run_canopy_ingestion)

    if not tasks:
        return _envelope(status="success", data={}, error={"message": "No sources selected"})

    results = await asyncio.gather(
        *list(tasks.values()),
        return_exceptions=True,
    )

    data: dict = {}
    errors: dict = {}
    for label, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            errors[label] = str(result)
            logger.error("run: %s failed: %s", label, result)
        else:
            data[label] = str(result)

    # Compute the time window so preparation queries the same fires that were just ingested
    fires_since: datetime | None = None
    fires_until: datetime | None = None
    if body.include_firms:
        if body.firms_start_date:
            fires_since = datetime(
                body.firms_start_date.year,
                body.firms_start_date.month,
                body.firms_start_date.day,
                tzinfo=UTC,
            )
            # Close the window the run actually asked for. Without this the preparation
            # query is a bare lower bound, so detections ingested later — a different
            # fire, weeks after — are treated as part of this window and set the
            # ignition time.
            fires_until = fires_since + timedelta(days=body.firms_day_range)
        else:
            fires_since = datetime.now(UTC) - timedelta(days=body.firms_day_range)

    # Scope weather lookups to the historical GFS date (explicit or derived from the
    # FIRMS window), so a live ingestion elsewhere in the DB can't silently override
    # it (see valid_time on RasterAsset / find_raster_asset(at=...)).
    gfs_at: datetime | None = None
    if body.include_gfs and gfs_date:
        gfs_at = datetime(
            gfs_date.year, gfs_date.month, gfs_date.day,
            23, 59, 59, tzinfo=UTC,
        )

    # Prepare ELMFIRE inputs using the most recent data available in the DB
    try:
        async with async_session_factory() as s:
            prep = await run_preparation(
                s,
                fires_since=fires_since,
                fires_until=fires_until,
                gfs_at=gfs_at,
                fuels_source=body.fuels_source,
            )
        data["preparation"] = prep
    except Exception as exc:
        logger.error("Preparation failed after ingestion: %s", exc)
        errors["preparation"] = str(exc)

    status = "partial_failure" if errors else "success"
    return _envelope(status=status, data=data, error=errors or None)


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
