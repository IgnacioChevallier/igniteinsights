"""
Preparation service: derives ELMFIRE input rasters from the most recent
ingested data and writes them to data/elmfire/inputs/{prep_id}/.

Called automatically at the end of every POST /ingestion/run.
"""
import asyncio
import logging
import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import repository
from app.elmfire.builder import (
    canopy_builder,
    fuels_builder,
    ignition_builder,
    namelist_writer,
    raster_aligner,
    weather_builder,
)

logger = logging.getLogger(__name__)


async def run_preparation(
    session: AsyncSession,
    fires_since: datetime | None = None,
    gfs_at: datetime | None = None,
) -> dict:
    """
    Derive all available ELMFIRE input rasters using the most recent DB assets.

    Returns a summary dict with:
      - prep_id: UUID (also the name of the inputs folder)
      - inputs_dir: absolute path to the written inputs folder
      - generated: list of filenames successfully written
      - missing: list of filenames that could not be generated (missing source data)
    """
    prep_id = uuid.uuid4()
    aoi = await repository.get_or_create_default_aoi(session)
    await session.commit()

    static_dir = _resolve(settings.static_data_dir)
    inputs_dir = _resolve(settings.elmfire_inputs_dir) / str(prep_id)
    inputs_dir.mkdir(parents=True, exist_ok=True)

    generated: list[str] = []
    missing: list[str] = []

    # ── 1. Topography (static, cached) ────────────────────────────────────────
    dem_asset = await repository.find_raster_asset(session, aoi.id, "dem_raw")
    if dem_asset and Path(dem_asset.file_path).exists():
        dem_raw = _resolve(dem_asset.file_path)
        dem_tif, slp_tif, asp_tif = await asyncio.to_thread(
            raster_aligner.reproject_and_derive_topo, dem_raw, static_dir
        )
        for name, src in [("dem.tif", dem_tif), ("slp.tif", slp_tif), ("asp.tif", asp_tif)]:
            dst = inputs_dir / name
            shutil.copy2(src, dst)
            generated.append(name)
    else:
        missing.extend(["dem.tif", "slp.tif", "asp.tif"])
        logger.warning("No DEM asset — run ingestion with include_dem=true")

    # Reference grid for all subsequent rasters (dem.tif in inputs_dir if available)
    reference = inputs_dir / "dem.tif" if "dem.tif" in generated else None

    # Wind adjustment factor — uniform 1.0 (no adjustment), required by ELMFIRE
    if reference:
        await asyncio.to_thread(_write_uniform_raster, reference, inputs_dir / "adj.tif", 1.0)
        generated.append("adj.tif")

    # ── 2. Fuel model (static, cached) ────────────────────────────────────────
    wc_asset = await repository.find_raster_asset(session, aoi.id, "worldcover_raw")
    fbfm_cached = static_dir / "fbfm40.tif"
    if wc_asset and Path(wc_asset.file_path).exists() and reference:
        wc_path = _resolve(wc_asset.file_path)
        if not fbfm_cached.exists():
            await asyncio.to_thread(
                fuels_builder.worldcover_to_fbfm40, wc_path, reference, fbfm_cached
            )
        shutil.copy2(fbfm_cached, inputs_dir / "fbfm40.tif")
        generated.append("fbfm40.tif")
    else:
        missing.append("fbfm40.tif")
        if not wc_asset:
            logger.warning("No WorldCover asset — run ingestion with include_worldcover=true")

    # ── 3. Weather (dynamic, derived per run) ─────────────────────────────────
    u10 = await repository.find_raster_asset(session, aoi.id, "gfs_u10", at=gfs_at)
    v10 = await repository.find_raster_asset(session, aoi.id, "gfs_v10", at=gfs_at)
    t2m = await repository.find_raster_asset(session, aoi.id, "gfs_t2m", at=gfs_at)
    rh = await repository.find_raster_asset(session, aoi.id, "gfs_rh", at=gfs_at)

    if all(a and Path(a.file_path).exists() for a in [u10, v10]) and reference:
        ws, wd = await asyncio.to_thread(
            weather_builder.derive_wind,
            _resolve(u10.file_path),
            _resolve(v10.file_path),
            reference,
            inputs_dir,
        )
        generated.extend(["ws.tif", "wd.tif"])
    else:
        missing.extend(["ws.tif", "wd.tif"])
        if not (u10 and v10):
            logger.warning("No GFS wind assets — run ingestion with include_gfs=true")

    if all(a and Path(a.file_path).exists() for a in [t2m, rh]) and reference:
        m1, m10, m100 = await asyncio.to_thread(
            weather_builder.derive_moisture,
            _resolve(t2m.file_path),
            _resolve(rh.file_path),
            reference,
            inputs_dir,
        )
        generated.extend(["m1.tif", "m10.tif", "m100.tif"])
    else:
        missing.extend(["m1.tif", "m10.tif", "m100.tif"])
        if not (t2m and rh):
            logger.warning("No GFS moisture assets — run ingestion with include_gfs=true")

    # ── 4. Ignition (from FIRMS detections in DB) ─────────────────────────────
    since = fires_since or datetime.now(UTC) - timedelta(hours=48)
    fire_features = await repository.get_active_fires(session, since=since)
    fire_points = [
        (f["properties"]["longitude"], f["properties"]["latitude"])
        for f in fire_features
    ]
    if fire_points and reference:
        phi, _ = await asyncio.to_thread(
            ignition_builder.build_ignition_layer, fire_points, reference, inputs_dir
        )
        generated.append("phi.tif")
    else:
        missing.append("phi.tif")
        if not fire_points:
            logger.warning("No FIRMS detections since %s — phi.tif not generated", since.isoformat())

    # ── 5. Canopy ─────────────────────────────────────────────────────────────
    cc_asset = await repository.find_raster_asset(session, aoi.id, "canopy_cc")
    ch_asset = await repository.find_raster_asset(session, aoi.id, "canopy_ch")

    if cc_asset and Path(cc_asset.file_path).exists() and reference:
        await asyncio.to_thread(
            canopy_builder.reproject_canopy,
            _resolve(cc_asset.file_path),
            reference,
            inputs_dir / "cc.tif",
        )
        generated.append("cc.tif")
    else:
        missing.append("cc.tif")
        if not cc_asset:
            logger.warning("No canopy_cc asset — run ingestion with include_canopy=true")

    if ch_asset and Path(ch_asset.file_path).exists() and reference:
        await asyncio.to_thread(
            canopy_builder.reproject_canopy,
            _resolve(ch_asset.file_path),
            reference,
            inputs_dir / "ch.tif",
            10.0,  # meters → 10×meters (ELMFIRE Int16 encoding)
        )
        generated.append("ch.tif")
    else:
        missing.append("ch.tif")
        if not ch_asset:
            logger.warning("No canopy_ch asset — run ingestion with include_canopy=true")

    # cbh + cbd: derived from fbfm40 (no extra download needed)
    if "fbfm40.tif" in generated and reference:
        await asyncio.to_thread(
            canopy_builder.derive_cbh_cbd,
            inputs_dir / "fbfm40.tif",
            reference,
            inputs_dir / "cbh.tif",
            inputs_dir / "cbd.tif",
        )
        generated.extend(["cbh.tif", "cbd.tif"])
    else:
        missing.extend(["cbh.tif", "cbd.tif"])

    # ── 6. Namelist (only when DEM is present for domain info) ────────────────
    if "dem.tif" in generated:
        outputs_dir = _resolve(settings.elmfire_outputs_dir) / str(prep_id)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        elmfire_data = inputs_dir / "elmfire.data"
        await asyncio.to_thread(
            namelist_writer.write_namelist,
            inputs_dir,
            outputs_dir,
            simulation_hours=12,
            output_path=elmfire_data,
        )
        generated.append("elmfire.data")
    else:
        missing.append("elmfire.data")

    logger.info(
        "Preparation %s complete: %d generated, %d missing",
        prep_id,
        len(generated),
        len(missing),
    )
    return {
        "prep_id": str(prep_id),
        "inputs_dir": str(inputs_dir),
        "generated": generated,
        "missing": missing,
    }


def _write_uniform_raster(reference: Path, output: Path, value: float) -> None:
    import numpy as np
    import rasterio
    with rasterio.open(reference) as src:
        profile = src.meta.copy()
    profile.update(dtype="float32", count=1, nodata=None)
    with rasterio.open(output, "w", **profile) as dst:
        dst.write(
            np.full((1, profile["height"], profile["width"]), value, dtype="float32")
        )


def _resolve(path_str: str) -> Path:
    """Resolve configured path, falling back to local ./data/ when running outside Docker."""
    p = Path(path_str)
    if p.exists():
        return p
    parts = p.parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "app" and parts[2] == "data":
        local = Path.cwd() / "data" / Path(*parts[3:])
        if local.exists() or not p.exists():
            return local
    return p
