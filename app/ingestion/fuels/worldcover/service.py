import asyncio
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import repository
from app.ingestion.coverage import covers_aoi

from .client import WorldCoverClient
from .errors import WorldCoverError

logger = logging.getLogger(__name__)

WORLDCOVER_SOURCE_NAME = "esa_worldcover_v200"
ASSET_TYPE = "worldcover_raw"


async def run_worldcover_ingestion(session: AsyncSession) -> uuid.UUID:
    ds = await repository.get_or_create_data_source(
        session,
        name=WORLDCOVER_SOURCE_NAME,
        category="fuels",
        base_url="https://esa-worldcover.s3.amazonaws.com",
    )
    aoi = await repository.get_or_create_default_aoi(session)
    run = await repository.create_ingestion_run(session, ds.id, aoi.id)
    await session.commit()

    try:
        await session.refresh(run)

        output_path = (
            Path(settings.static_data_dir)
            / "worldcover"
            / datetime.now(UTC).strftime("%Y-%m-%d")
            / "esa_worldcover_v200_10m.tif"
        )

        # Idempotency: static data — reuse if already registered and file exists
        existing = await repository.find_raster_asset(session, aoi.id, ASSET_TYPE)
        if existing and Path(existing.file_path).exists() and covers_aoi(Path(existing.file_path)):
            logger.info("WorldCover already exists at %s — skipping download", existing.file_path)
            await repository.update_ingestion_run(
                session,
                run.id,
                status="success",
                metadata={"skipped": True, "existing_asset_id": str(existing.id)},
            )
            await session.commit()
            return run.id

        client = WorldCoverClient()
        tiles = client.compute_tile_ids(
            west=settings.aoi_west,
            south=settings.aoi_south,
            east=settings.aoi_east,
            north=settings.aoi_north,
        )
        logger.info("WorldCover tiles for AOI: %s", [t.tile_id for t in tiles])

        meta = await asyncio.to_thread(
            client.download_clipped,
            tiles,
            settings.aoi_west,
            settings.aoi_south,
            settings.aoi_east,
            settings.aoi_north,
            output_path,
        )

        await repository.create_raster_asset(
            session,
            ingestion_run_id=run.id,
            asset_type=ASSET_TYPE,
            file_path=meta.file_path,
            crs=meta.crs,
            resolution_m=meta.resolution_m,
            band_count=meta.band_count,
            dtype=meta.dtype,
            file_size_bytes=meta.file_size_bytes,
            metadata={
                "source": WORLDCOVER_SOURCE_NAME,
                "version": meta.version,
                "year": meta.year,
                "tiles": meta.tiles_used,
                "acquisition_date": meta.year,
                "crs": meta.crs,
            },
        )

        await repository.update_ingestion_run(
            session,
            run.id,
            status="success",
            metadata={
                "file_path": meta.file_path,
                "tiles": meta.tiles_used,
                "version": meta.version,
            },
        )
        await session.commit()
        logger.info("WorldCover ingestion complete (run_id=%s)", run.id)

    except WorldCoverError as exc:
        await repository.update_ingestion_run(
            session, run.id, status="failed", error_message=str(exc)
        )
        await session.commit()
        raise

    return run.id
