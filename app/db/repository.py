import uuid
from datetime import UTC, datetime, timedelta

from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    AreaOfInterest,
    DataSource,
    FireDetection,
    IngestionRun,
    RasterAsset,
    SimulationOutput,
    SimulationRun,
)


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
    result = await session.execute(
        select(AreaOfInterest).where(AreaOfInterest.name == "Los Alerces")
    )
    aoi = result.scalar_one_or_none()
    if aoi is None:
        from geoalchemy2.shape import from_shape
        from shapely.geometry import box

        geom = from_shape(box(-72.0, -42.9, -71.5, -42.5), srid=4326)
        aoi = AreaOfInterest(
            name="Los Alerces",
            geom=geom,
            crs_processing="EPSG:32719",
        )
        session.add(aoi)
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
    if not detections:
        return 0
    objects = [FireDetection(ingestion_run_id=run_id, **d) for d in detections]
    session.add_all(objects)
    await session.flush()
    return len(objects)


async def get_active_fires(
    session: AsyncSession, hours: int = 24
) -> list[dict]:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    result = await session.execute(
        select(
            FireDetection,
            ST_AsGeoJSON(FireDetection.geom).label("geojson"),
        ).where(FireDetection.acq_datetime >= cutoff)
    )
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
) -> RasterAsset | None:
    result = await session.execute(
        select(RasterAsset)
        .join(IngestionRun, RasterAsset.ingestion_run_id == IngestionRun.id)
        .where(IngestionRun.aoi_id == aoi_id, RasterAsset.asset_type == asset_type)
        .order_by(RasterAsset.created_at.desc())
        .limit(1)
    )
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
) -> SimulationRun:
    run = SimulationRun(
        aoi_id=aoi_id,
        status="pending",
        horizon_hours=horizon_hours,
        ignition_datetime=ignition_datetime,
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
