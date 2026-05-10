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
