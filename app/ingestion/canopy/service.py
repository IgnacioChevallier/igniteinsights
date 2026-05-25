import asyncio
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import repository

from .client import download_eth_ch, download_hansen_cc
from .errors import CanopyError

logger = logging.getLogger(__name__)

_SOURCE_NAME = "hansen_gfc_v1_11_eth_canopy_height_2020"
_CC_ASSET_TYPE = "canopy_cc"
_CH_ASSET_TYPE = "canopy_ch"


async def run_canopy_ingestion(session: AsyncSession) -> uuid.UUID:
    ds = await repository.get_or_create_data_source(
        session,
        name=_SOURCE_NAME,
        category="canopy",
        base_url="https://storage.googleapis.com/earthenginepartners-hansen",
    )
    aoi = await repository.get_or_create_default_aoi(session)
    run = await repository.create_ingestion_run(session, ds.id, aoi.id)
    await session.commit()

    try:
        await session.refresh(run)

        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        canopy_dir = Path(settings.static_data_dir) / "canopy" / date_str

        # Idempotency: skip if both assets already registered and files exist
        existing_cc = await repository.find_raster_asset(session, aoi.id, _CC_ASSET_TYPE)
        existing_ch = await repository.find_raster_asset(session, aoi.id, _CH_ASSET_TYPE)
        if (
            existing_cc and Path(existing_cc.file_path).exists()
            and existing_ch and Path(existing_ch.file_path).exists()
        ):
            logger.info("Canopy assets already present — skipping download")
            await repository.update_ingestion_run(
                session,
                run.id,
                status="success",
                metadata={
                    "skipped": True,
                    "existing_cc_id": str(existing_cc.id),
                    "existing_ch_id": str(existing_ch.id),
                },
            )
            await session.commit()
            return run.id

        cc_path = canopy_dir / "hansen_treecover2000.tif"
        ch_path = canopy_dir / "eth_canopy_height.tif"

        west = settings.aoi_west
        south = settings.aoi_south
        east = settings.aoi_east
        north = settings.aoi_north

        # Download both sources concurrently in thread pool
        cc_meta, ch_meta = await asyncio.gather(
            asyncio.to_thread(download_hansen_cc, west, south, east, north, cc_path),
            asyncio.to_thread(download_eth_ch, west, south, east, north, ch_path),
        )

        await repository.create_raster_asset(
            session,
            ingestion_run_id=run.id,
            asset_type=_CC_ASSET_TYPE,
            file_path=cc_meta.file_path,
            crs=cc_meta.crs,
            resolution_m=cc_meta.resolution_m,
            band_count=cc_meta.band_count,
            dtype=cc_meta.dtype,
            file_size_bytes=cc_meta.file_size_bytes,
            metadata={
                "source": cc_meta.source,
                "version": cc_meta.version,
                "tiles": cc_meta.tile_ids,
                "units": "percent_0_100",
            },
        )
        await repository.create_raster_asset(
            session,
            ingestion_run_id=run.id,
            asset_type=_CH_ASSET_TYPE,
            file_path=ch_meta.file_path,
            crs=ch_meta.crs,
            resolution_m=ch_meta.resolution_m,
            band_count=ch_meta.band_count,
            dtype=ch_meta.dtype,
            file_size_bytes=ch_meta.file_size_bytes,
            metadata={
                "source": ch_meta.source,
                "version": ch_meta.version,
                "tiles": ch_meta.tile_ids,
                "units": "meters",
            },
        )

        await repository.update_ingestion_run(
            session,
            run.id,
            status="success",
            metadata={
                "cc_file": cc_meta.file_path,
                "ch_file": ch_meta.file_path,
                "cc_tiles": cc_meta.tile_ids,
                "ch_tiles": ch_meta.tile_ids,
            },
        )
        await session.commit()
        logger.info("Canopy ingestion complete (run_id=%s)", run.id)

    except CanopyError as exc:
        await repository.update_ingestion_run(
            session, run.id, status="failed", error_message=str(exc)
        )
        await session.commit()
        raise

    return run.id
