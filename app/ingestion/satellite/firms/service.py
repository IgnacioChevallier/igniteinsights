import asyncio
import logging
import uuid
from datetime import UTC, date, datetime

from geoalchemy2.shape import from_shape
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import resolve_data_path, settings
from app.db import repository

from .client import FIRMS_SOURCES, FIRMS_SOURCES_ARCHIVE, FIRMSClient
from .errors import FIRMSClientError
from .normalizer import normalize_firms_response

logger = logging.getLogger(__name__)

FIRMS_SOURCE_NAME = "firms_viirs"


async def run_firms_ingestion(
    session: AsyncSession,
    day_range: int = 1,
    start_date: date | None = None,
) -> uuid.UUID:
    ds = await repository.get_or_create_data_source(
        session,
        name=FIRMS_SOURCE_NAME,
        category="satellite",
        base_url="https://firms.modaps.eosdis.nasa.gov/api/area/csv",
    )
    aoi = await repository.get_or_create_default_aoi(session)
    run = await repository.create_ingestion_run(session, ds.id, aoi.id)
    await session.commit()

    try:
        await session.refresh(run)
        client = FIRMSClient()
        df = await asyncio.to_thread(
            client.fetch_active_fires,
            west=settings.aoi_west,
            south=settings.aoi_south,
            east=settings.aoi_east,
            north=settings.aoi_north,
            day_range=day_range,
            start_date=start_date,
            # SP and NRT cover disjoint dates (SP lags ~3 months): asking both serves a past
            # fire and a live one alike (docs/resultados/pronostico/areas-quemadas.md).
            sources=FIRMS_SOURCES + FIRMS_SOURCES_ARCHIVE,
        )

        # Persist raw CSV for auditing
        raw_dir = (resolve_data_path(settings.raw_data_dir) / "firms"
                   / datetime.now(UTC).strftime("%Y-%m-%d"))
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / "viirs_los_alerces.csv"
        if not df.empty:
            await asyncio.to_thread(df.to_csv, raw_path, index=False)

        detections = normalize_firms_response(df)

        db_records = [
            {
                "geom": from_shape(d.geom, srid=4326),
                "bright_ti4": d.bright_ti4,
                "frp": d.frp,
                "confidence": d.confidence,
                "acq_datetime": d.acq_datetime,
                "satellite": d.satellite,
                "daynight": d.daynight,
            }
            for d in detections
        ]

        count = await repository.bulk_insert_fire_detections(session, run.id, db_records)
        await repository.update_ingestion_run(
            session,
            run.id,
            status="success",
            metadata={
                "detection_count": count,
                "day_range": day_range,
                "start_date": start_date.isoformat() if start_date else None,
            },
        )
        await session.commit()
        logger.info("FIRMS ingestion complete: %d detections inserted (run_id=%s)", count, run.id)

    except FIRMSClientError as exc:
        await repository.update_ingestion_run(
            session, run.id, status="failed", error_message=str(exc)
        )
        await session.commit()
        raise

    return run.id
