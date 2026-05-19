import asyncio
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import repository

from .client import VARIABLES, GFSClient
from .errors import GFSError

logger = logging.getLogger(__name__)

GFS_SOURCE_NAME = "noaa_gfs_0p25"


async def run_gfs_ingestion(session: AsyncSession) -> uuid.UUID:
    ds = await repository.get_or_create_data_source(
        session,
        name=GFS_SOURCE_NAME,
        category="meteorology",
        base_url="https://nomads.ncep.noaa.gov",
    )
    aoi = await repository.get_or_create_default_aoi(session)
    run = await repository.create_ingestion_run(session, ds.id, aoi.id)
    await session.commit()

    try:
        await session.refresh(run)

        client = GFSClient()
        cycle = await asyncio.to_thread(client.resolve_latest_cycle)
        cycle_str = f"{cycle.date.replace('-', '')}{cycle.cycle_hour:02d}"

        raw_dir = (
            Path(settings.raw_data_dir)
            / "gfs"
            / datetime.now(UTC).strftime("%Y-%m-%d")
        )

        downloaded: list[dict] = []
        for var_key in VARIABLES:
            output_path = raw_dir / f"{cycle_str}_{var_key}.tif"
            meta = await asyncio.to_thread(
                client.download_variable,
                cycle,
                var_key,
                settings.aoi_west,
                settings.aoi_south,
                settings.aoi_east,
                settings.aoi_north,
                output_path,
            )
            await repository.create_raster_asset(
                session,
                ingestion_run_id=run.id,
                asset_type=meta.asset_type,
                file_path=meta.file_path,
                crs=meta.crs,
                resolution_m=meta.resolution_deg * 111_320,
                band_count=meta.band_count,
                dtype=meta.dtype,
                file_size_bytes=meta.file_size_bytes,
                metadata={
                    "source": GFS_SOURCE_NAME,
                    "cycle": meta.cycle,
                    "variable": meta.variable,
                    "search_string": meta.search_string,
                },
            )
            downloaded.append({"variable": var_key, "file_path": meta.file_path})

        await repository.update_ingestion_run(
            session,
            run.id,
            status="success",
            metadata={
                "cycle": cycle_str,
                "fxx": cycle.fxx,
                "variables": list(VARIABLES.keys()),
                "files": downloaded,
            },
        )
        await session.commit()
        logger.info("GFS ingestion complete (run_id=%s, cycle=%s)", run.id, cycle_str)

    except GFSError as exc:
        await repository.update_ingestion_run(
            session, run.id, status="failed", error_message=str(exc)
        )
        await session.commit()
        raise

    return run.id
