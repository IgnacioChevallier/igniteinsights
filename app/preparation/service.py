"""
Preparation service: derives ELMFIRE input rasters from the most recent
ingested data and writes them to data/elmfire/inputs/{prep_id}/.

Called automatically at the end of every POST /ingestion/run.
"""
import asyncio
import logging
import shutil
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import repository
from app.elmfire.builder import (
    fuels_builder,
    ignition_builder,
    namelist_writer,
    raster_aligner,
    weather_builder,
)

logger = logging.getLogger(__name__)


async def run_preparation(session: AsyncSession) -> dict:
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
    u10 = await repository.find_raster_asset(session, aoi.id, "gfs_u10")
    v10 = await repository.find_raster_asset(session, aoi.id, "gfs_v10")
    t2m = await repository.find_raster_asset(session, aoi.id, "gfs_t2m")
    rh = await repository.find_raster_asset(session, aoi.id, "gfs_rh")

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

    # ── 4. Ignition (from latest FIRMS detections in DB) ──────────────────────
    fire_features = await repository.get_active_fires(session, hours=48)
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
            logger.warning("No FIRMS detections in last 48 h — phi.tif not generated")

    # ── 5. Canopy (pending GEDI — Hito 4) ─────────────────────────────────────
    missing.extend(["cc.tif", "ch.tif", "cbh.tif", "cbd.tif"])

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
