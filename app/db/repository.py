import logging
import uuid
from datetime import UTC, datetime
from typing import cast

from geoalchemy2.functions import ST_AsGeoJSON, ST_Intersects
from sqlalchemy import CursorResult, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.models import (
    AreaOfInterest,
    DataSource,
    FireDetection,
    IngestionRun,
    RasterAsset,
    SimulationOutput,
    SimulationRun,
)

logger = logging.getLogger(__name__)


async def get_or_create_data_source(
    session: AsyncSession, name: str, category: str, base_url: str | None = None
) -> DataSource:
    result = await session.execute(select(DataSource).where(DataSource.name == name))
    ds = result.scalar_one_or_none()
    if ds is None:
        ds = DataSource(name=name, category=category, base_url=base_url)
        session.add(ds)
        await session.flush()
    return ds


async def get_or_create_default_aoi(session: AsyncSession) -> AreaOfInterest:
    """The stored AOI follows the configured one.

    This used to create the geometry once and then only ever look it up by name, so editing
    `aoi_*` in config changed nothing: the row kept the original box forever while the
    ingestion clients computed tiles from the new one. Config is the single source of truth
    for the domain; the row tracks it. See ETAPA-A-BASELINE.md §A0.
    """
    from geoalchemy2.shape import from_shape, to_shape
    from shapely.geometry import box

    configured = box(
        settings.aoi_west, settings.aoi_south, settings.aoi_east, settings.aoi_north
    )
    by_name = select(AreaOfInterest).where(AreaOfInterest.name == "Los Alerces")
    aoi = (await session.execute(by_name)).scalar_one_or_none()

    if aoi is None:
        # /ingestion/run calls this from several sessions at once; ON CONFLICT lets the
        # losers pick up the winner's row instead of each inserting their own.
        await session.execute(
            pg_insert(AreaOfInterest)
            .values(
                id=uuid.uuid4(),
                name="Los Alerces",
                geom=from_shape(configured, srid=4326),
                crs_processing=settings.aoi_crs_processing,
            )
            .on_conflict_do_nothing(index_elements=["name"])
        )
        return (await session.execute(by_name)).scalar_one()

    stored = to_shape(aoi.geom)
    if not stored.equals_exact(configured, tolerance=1e-9):
        logger.warning(
            "AOI changed in config: %s → %s. Updating the stored geometry; static rasters "
            "that no longer cover it will be re-ingested on the next run.",
            [round(v, 4) for v in stored.bounds],
            [round(v, 4) for v in configured.bounds],
        )
        aoi.geom = from_shape(configured, srid=4326)
        aoi.crs_processing = settings.aoi_crs_processing
        await session.flush()
    return aoi


async def create_ingestion_run(
    session: AsyncSession,
    data_source_id: uuid.UUID,
    aoi_id: uuid.UUID,
) -> IngestionRun:
    run = IngestionRun(
        data_source_id=data_source_id,
        aoi_id=aoi_id,
        status="pending",
        started_at=datetime.now(UTC),
    )
    session.add(run)
    await session.flush()
    return run


async def update_ingestion_run(
    session: AsyncSession,
    run_id: uuid.UUID,
    status: str,
    error_message: str | None = None,
    metadata: dict | None = None,
) -> IngestionRun | None:
    result = await session.execute(select(IngestionRun).where(IngestionRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        return None
    run.status = status
    run.finished_at = datetime.now(UTC)
    if error_message is not None:
        run.error_message = error_message
    if metadata is not None:
        run.metadata_ = metadata
    await session.flush()
    return run


async def get_ingestion_run(
    session: AsyncSession, run_id: uuid.UUID
) -> IngestionRun | None:
    result = await session.execute(select(IngestionRun).where(IngestionRun.id == run_id))
    return result.scalar_one_or_none()


async def bulk_insert_fire_detections(
    session: AsyncSession,
    run_id: uuid.UUID,
    detections: list[dict],
) -> int:
    """Insert detections, skipping rows already stored (same geom/acq_datetime/
    satellite) by a previous overlapping ingestion. Returns rows actually inserted."""
    if not detections:
        return 0
    rows = [
        {"id": uuid.uuid4(), "ingestion_run_id": run_id, **d} for d in detections
    ]
    stmt = (
        pg_insert(FireDetection)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_fire_detection_natural_key")
    )
    result = cast(CursorResult, await session.execute(stmt))
    inserted = result.rowcount or 0
    if inserted < len(rows):
        logger.info(
            "bulk_insert_fire_detections: %d of %d detections already stored — skipped",
            len(rows) - inserted,
            len(rows),
        )
    return inserted


async def get_active_fires(
    session: AsyncSession,
    since: datetime,
    aoi_id: uuid.UUID | None = None,
    until: datetime | None = None,
) -> list[dict]:
    """Detections in [since, until). `until` is optional because the dashboard's
    "last N hours" view has no end; a run that asked for a specific FIRMS window must
    pass one, or stray detections from later ingestions land in the same result."""
    query = select(
        FireDetection,
        ST_AsGeoJSON(FireDetection.geom).label("geojson"),
    ).where(FireDetection.acq_datetime >= since)

    if until is not None:
        query = query.where(FireDetection.acq_datetime < until)

    if aoi_id is not None:
        query = query.join(
            AreaOfInterest, ST_Intersects(FireDetection.geom, AreaOfInterest.geom)
        ).where(AreaOfInterest.id == aoi_id)

    result = await session.execute(query)
    rows = result.all()
    features = []
    import json

    for row, geojson in rows:
        coords = json.loads(geojson)["coordinates"]
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(geojson),
                "properties": {
                    "id": str(row.id),
                    "bright_ti4": row.bright_ti4,
                    "frp": row.frp,
                    "confidence": row.confidence,
                    "acq_datetime": row.acq_datetime.isoformat(),
                    "satellite": row.satellite,
                    "daynight": row.daynight,
                    "longitude": coords[0],
                    "latitude": coords[1],
                },
            }
        )
    return features


async def find_raster_asset(
    session: AsyncSession,
    aoi_id: uuid.UUID,
    asset_type: str,
    at: datetime | None = None,
) -> RasterAsset | None:
    stmt = (
        select(RasterAsset)
        .join(IngestionRun, RasterAsset.ingestion_run_id == IngestionRun.id)
        .where(IngestionRun.aoi_id == aoi_id, RasterAsset.asset_type == asset_type)
    )
    if at is not None:
        stmt = stmt.where(
            RasterAsset.valid_time.is_not(None), RasterAsset.valid_time <= at
        ).order_by(RasterAsset.valid_time.desc())
    else:
        stmt = stmt.order_by(RasterAsset.created_at.desc())
    result = await session.execute(stmt.limit(1))
    return result.scalar_one_or_none()


async def create_raster_asset(
    session: AsyncSession,
    ingestion_run_id: uuid.UUID,
    asset_type: str,
    file_path: str,
    crs: str | None = None,
    resolution_m: float | None = None,
    band_count: int | None = None,
    dtype: str | None = None,
    file_size_bytes: int | None = None,
    valid_time: datetime | None = None,
    metadata: dict | None = None,
) -> RasterAsset:
    asset = RasterAsset(
        ingestion_run_id=ingestion_run_id,
        asset_type=asset_type,
        file_path=file_path,
        crs=crs,
        resolution_m=resolution_m,
        band_count=band_count,
        dtype=dtype,
        file_size_bytes=file_size_bytes,
        valid_time=valid_time,
        metadata_=metadata,
    )
    session.add(asset)
    await session.flush()
    return asset


async def create_simulation_run(
    session: AsyncSession,
    aoi_id: uuid.UUID,
    horizon_hours: int,
    ignition_datetime: datetime | None = None,
    elmfire_config: dict | None = None,
) -> SimulationRun:
    run = SimulationRun(
        aoi_id=aoi_id,
        status="pending",
        horizon_hours=horizon_hours,
        ignition_datetime=ignition_datetime,
        elmfire_config=elmfire_config,
        started_at=datetime.now(UTC),
    )
    session.add(run)
    await session.flush()
    return run


async def get_simulation_run(
    session: AsyncSession, run_id: uuid.UUID
) -> SimulationRun | None:
    result = await session.execute(select(SimulationRun).where(SimulationRun.id == run_id))
    return result.scalar_one_or_none()


async def update_simulation_run(
    session: AsyncSession,
    run_id: uuid.UUID,
    status: str,
    output_dir: str | None = None,
    error_message: str | None = None,
    elmfire_config: dict | None = None,
) -> SimulationRun | None:
    result = await session.execute(select(SimulationRun).where(SimulationRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        return None
    run.status = status
    run.finished_at = datetime.now(UTC)
    if output_dir is not None:
        run.output_dir = output_dir
    if error_message is not None:
        run.error_message = error_message
    if elmfire_config is not None:
        run.elmfire_config = elmfire_config
    await session.flush()
    return run


async def create_simulation_output(
    session: AsyncSession,
    simulation_id: uuid.UUID,
    output_type: str,
    file_path: str | None = None,
    valid_at: datetime | None = None,
) -> SimulationOutput:
    """Insert a bookkeeping row for a simulation output file. `geom` is left NULL:
    simulation_outputs.geom is typed MULTIPOLYGON, but ELMFIRE's isochrone contours
    are LineStrings (see isochrone_converter.py), so it can't hold them. Isochrone
    geometry is served read-through from the shapefile instead of stored here."""
    output = SimulationOutput(
        simulation_id=simulation_id,
        output_type=output_type,
        file_path=file_path,
        valid_at=valid_at,
    )
    session.add(output)
    await session.flush()
    return output


async def list_recent_ingestion_runs(
    session: AsyncSession,
    limit: int = 25,
) -> list[dict]:
    result = await session.execute(
        select(IngestionRun, DataSource, AreaOfInterest)
        .join(DataSource, IngestionRun.data_source_id == DataSource.id)
        .join(AreaOfInterest, IngestionRun.aoi_id == AreaOfInterest.id)
        .order_by(IngestionRun.started_at.desc().nullslast())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "id": str(run.id),
            "kind": "ingestion",
            "source": data_source.name,
            "category": data_source.category,
            "aoi": aoi.name,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "error_message": run.error_message,
            "metadata": run.metadata_,
        }
        for run, data_source, aoi in rows
    ]


async def list_recent_simulation_runs(
    session: AsyncSession,
    limit: int = 25,
) -> list[dict]:
    result = await session.execute(
        select(SimulationRun, AreaOfInterest)
        .join(AreaOfInterest, SimulationRun.aoi_id == AreaOfInterest.id)
        .order_by(SimulationRun.started_at.desc().nullslast())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "id": str(run.id),
            "kind": "simulation",
            "source": "ELMFIRE",
            "aoi": aoi.name,
            "status": run.status,
            "horizon_hours": run.horizon_hours,
            "ignition_datetime": (
                run.ignition_datetime.isoformat() if run.ignition_datetime else None
            ),
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "output_dir": run.output_dir,
            "error_message": run.error_message,
            "warnings": (run.elmfire_config or {}).get("warnings", []),
        }
        for run, aoi in rows
    ]


async def list_recent_raster_assets(
    session: AsyncSession,
    limit: int = 50,
) -> list[dict]:
    result = await session.execute(
        select(RasterAsset, IngestionRun, DataSource, AreaOfInterest)
        .outerjoin(IngestionRun, RasterAsset.ingestion_run_id == IngestionRun.id)
        .outerjoin(DataSource, IngestionRun.data_source_id == DataSource.id)
        .outerjoin(AreaOfInterest, IngestionRun.aoi_id == AreaOfInterest.id)
        .order_by(RasterAsset.created_at.desc().nullslast())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "id": str(asset.id),
            "asset_type": asset.asset_type,
            "file_path": asset.file_path,
            "crs": asset.crs,
            "resolution_m": asset.resolution_m,
            "band_count": asset.band_count,
            "dtype": asset.dtype,
            "file_size_bytes": asset.file_size_bytes,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
            "ingestion_run_id": str(asset.ingestion_run_id) if asset.ingestion_run_id else None,
            "source": data_source.name if data_source else None,
            "aoi": aoi.name if aoi else None,
            "metadata": asset.metadata_,
        }
        for asset, _run, data_source, aoi in rows
    ]


async def list_recent_simulation_outputs(
    session: AsyncSession,
    limit: int = 50,
) -> list[dict]:
    result = await session.execute(
        select(SimulationOutput, SimulationRun)
        .join(SimulationRun, SimulationOutput.simulation_id == SimulationRun.id)
        .order_by(SimulationOutput.created_at.desc().nullslast())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "id": str(output.id),
            "simulation_id": str(output.simulation_id),
            "output_type": output.output_type,
            "file_path": output.file_path,
            "valid_at": output.valid_at.isoformat() if output.valid_at else None,
            "created_at": output.created_at.isoformat() if output.created_at else None,
            "simulation_status": run.status,
        }
        for output, run in rows
    ]
