import asyncio
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import repository
from app.ingestion.coverage import covers_aoi

from .client import OpenTopographyClient
from .errors import OpenTopographyError
from .schemas import BoundingBox

logger = logging.getLogger(__name__)

DEM_SOURCE_NAME = "opentopography_cop30"


async def run_dem_ingestion(session: AsyncSession) -> uuid.UUID:
    ds = await repository.get_or_create_data_source(
        session,
        name=DEM_SOURCE_NAME,
        category="topography",
        base_url="https://portal.opentopography.org/API/globaldem",
    )
    aoi = await repository.get_or_create_default_aoi(session)
    run = await repository.create_ingestion_run(session, ds.id, aoi.id)
    await session.commit()

    try:
        await session.refresh(run)

        bbox = BoundingBox(
            west=settings.aoi_west,
            south=settings.aoi_south,
            east=settings.aoi_east,
            north=settings.aoi_north,
        )
        raw_dir = (
            Path(settings.static_data_dir)
            / "opentopography"
            / datetime.now(UTC).strftime("%Y-%m-%d")
        )
        output_path = raw_dir / "dem_cop30_raw.tif"

        client = OpenTopographyClient()

        # Idempotency: reuse a DB-registered asset, or register the canonical file
        # when it was downloaded manually during local setup.
        existing = await repository.find_raster_asset(session, aoi.id, "dem_raw")
        if existing and Path(existing.file_path).exists() and covers_aoi(Path(existing.file_path)):
            logger.info("DEM already exists at %s — skipping download", existing.file_path)
            await repository.update_ingestion_run(
                session,
                run.id,
                status="success",
                metadata={"skipped": True, "existing_asset_id": str(existing.id)},
            )
            await session.commit()
            return run.id

        if output_path.exists():
            logger.info("Registering existing DEM at %s", output_path)
            metadata = await asyncio.to_thread(client.extract_metadata, output_path, bbox)
        else:
            metadata = await asyncio.to_thread(client.download_dem, bbox, output_path)

        await repository.create_raster_asset(
            session,
            ingestion_run_id=run.id,
            asset_type="dem_raw",
            file_path=metadata.file_path,
            crs=metadata.crs,
            resolution_m=metadata.resolution_m,
            band_count=metadata.band_count,
            dtype=metadata.dtype,
            file_size_bytes=metadata.file_size_bytes,
        )

        await repository.update_ingestion_run(
            session, run.id, status="success", metadata={"file_path": metadata.file_path}
        )
        await session.commit()
        logger.info("DEM ingestion complete (run_id=%s)", run.id)

    except OpenTopographyError as exc:
        await repository.update_ingestion_run(
            session, run.id, status="failed", error_message=str(exc)
        )
        await session.commit()
        raise

    return run.id
