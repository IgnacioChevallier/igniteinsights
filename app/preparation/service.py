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

from app.config import resolve_data_path as _resolve
from app.config import settings
from app.db import repository
from app.elmfire.builder import (
    canopy_builder,
    fuels_builder,
    ignition_builder,
    namelist_writer,
    raster_aligner,
    rasters,
    weather_builder,
)

logger = logging.getLogger(__name__)

# Max tolerated gap between the fire's ignition time and the GFS cycle's valid_time
# before the preparation flags the pairing as incoherent. Live runs use a cycle at
# most a few hours old; anything beyond this means wrong-period weather.
_WEATHER_MISMATCH_MAX_S = 48 * 3600.0


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
      - warnings: list of coherence problems (e.g. fire/weather period mismatch)
    """
    prep_id = uuid.uuid4()
    aoi = await repository.get_or_create_default_aoi(session)
    await session.commit()

    static_dir = _resolve(settings.static_data_dir)
    inputs_dir = _resolve(settings.elmfire_inputs_dir) / str(prep_id)
    inputs_dir.mkdir(parents=True, exist_ok=True)

    generated: list[str] = []
    missing: list[str] = []
    warnings: list[str] = []

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
        await asyncio.to_thread(
            rasters.write_uniform_from_reference, reference, inputs_dir / "adj.tif", 1.0
        )
        generated.append("adj.tif")

    # ── 2. Fuel model (static, cached) ────────────────────────────────────────
    wc_asset = await repository.find_raster_asset(session, aoi.id, "worldcover_raw")
    fbfm_cached = static_dir / "fbfm40.tif"
    if wc_asset and Path(wc_asset.file_path).exists() and reference:
        wc_path = _resolve(wc_asset.file_path)
        # Caching (and its invalidation) lives in fuels_builder, not here — a bare
        # `.exists()` check made every crosswalk change a silent no-op.
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

    if (
        u10 is not None
        and v10 is not None
        and Path(u10.file_path).exists()
        and Path(v10.file_path).exists()
        and reference is not None
    ):
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

    if (
        t2m is not None
        and rh is not None
        and Path(t2m.file_path).exists()
        and Path(rh.file_path).exists()
        and reference is not None
    ):
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
    fire_features = await repository.get_active_fires(session, since=since, aoi_id=aoi.id)
    fire_points = [
        (f["properties"]["longitude"], f["properties"]["latitude"])
        for f in fire_features
    ]
    # Most recent detection actually used to build phi.tif — the closest thing we
    # have to a real-world "ignition time" for this simulation (see preparation
    # plan notes: SimulationRun.ignition_datetime has no other honest source today).
    ignition_datetime = (
        max(f["properties"]["acq_datetime"] for f in fire_features) if fire_features else None
    )

    # Coherence guard: simulating a fire with weather from a different period silently
    # produces zero spread (e.g. a February fire paired with a winter cycle whose fuel
    # moisture exceeds the extinction moisture of every fuel model). Surface it.
    if ignition_datetime is not None:
        ignition_dt = datetime.fromisoformat(ignition_datetime)
        weather_valid_times = [
            a.valid_time
            for a in (u10, v10, t2m, rh)
            if a is not None and a.valid_time is not None
        ]
        if weather_valid_times:
            mismatch = max(
                abs((ignition_dt - vt).total_seconds()) for vt in weather_valid_times
            )
            if mismatch > _WEATHER_MISMATCH_MAX_S:
                msg = (
                    f"Weather/fire mismatch: ignition {ignition_datetime} vs "
                    f"GFS valid_time {max(weather_valid_times).isoformat()} "
                    f"({mismatch / 86400:.1f} days apart) — the simulation will use "
                    "weather from a different period; pass gfs_date matching the fire "
                    "window (or re-run ingestion with include_gfs=true)"
                )
                logger.warning("Preparation %s: %s", prep_id, msg)
                warnings.append(msg)

    if fire_points and reference:
        phi, _ = await asyncio.to_thread(
            ignition_builder.build_ignition_layer, fire_points, reference, inputs_dir
        )
        generated.append("phi.tif")
    else:
        missing.append("phi.tif")
        if not fire_points:
            logger.warning(
                "No FIRMS detections since %s — phi.tif not generated", since.isoformat()
            )

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

    # cbh + cbd: derived from the measured canopy rasters, not from the fuel model code
    if "cc.tif" in generated and "ch.tif" in generated:
        await asyncio.to_thread(
            canopy_builder.derive_cbh_cbd,
            inputs_dir / "cc.tif",
            inputs_dir / "ch.tif",
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
        # ELMFIRE reads the fuel model table from MISCELLANEOUS_INPUTS_DIRECTORY, which
        # the namelist points at inputs_dir. Inputs reach the runner over a shared Docker
        # volume, so copying it here is all the transport there is.
        shutil.copy2(fuels_builder.FUEL_MODEL_TABLE, inputs_dir / namelist_writer.FUEL_MODEL_FILE)
        generated.append(namelist_writer.FUEL_MODEL_FILE)

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
        "warnings": warnings,
        "ignition_datetime": ignition_datetime,
    }




