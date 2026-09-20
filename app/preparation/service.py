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


def _as_utc(dt: datetime) -> datetime:
    """Naive datetimes coming from storage are UTC; comparing them to aware ones raises."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)

# Max tolerated gap between the fire's ignition time and the GFS cycle's valid_time
# before the preparation flags the pairing as incoherent. Live runs use a cycle at
# most a few hours old; anything beyond this means wrong-period weather.
_WEATHER_MISMATCH_MAX_S = 48 * 3600.0


async def run_preparation(
    session: AsyncSession,
    fires_since: datetime | None = None,
    fires_until: datetime | None = None,
    gfs_at: datetime | None = None,
    fuels_source: str | None = None,
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
    # Which cover product feeds fbfm40.tif is configuration, not code (ETAPA-B §B3): the
    # thesis has to be able to regenerate any of the three maps to compare them. The
    # source id is part of the cache key, so switching sources rebuilds the raster.
    # A run can override the configured source, so the three maps can be compared without
    # editing .env between runs.
    source = fuels_source or settings.fuels_source
    fbfm_cached = static_dir / f"fbfm40_{source}.tif"
    wc_asset = await repository.find_raster_asset(session, aoi.id, "worldcover_raw")
    wc_path = _resolve(wc_asset.file_path) if wc_asset else None
    if wc_path is not None and not wc_path.exists():
        wc_path = None

    configured: str | None = None
    fill_path = None
    if source == "worldcover":
        source_path = wc_path
    else:
        configured = (
            settings.ccsbap_vector_path if source == "ccsbap" else settings.mapbiomas_raster_path
        )
        resolved = _resolve(configured)
        source_path = resolved if resolved.exists() else None
        # Both Argentine products stop at the international border, and that gap sits on
        # the west edge of the domain: an artificially unburnable border stops the front
        # by construction (IGN-20 §7.5). Fill it from the global product.
        if wc_path is not None and reference is not None:
            fill_path = await asyncio.to_thread(
                fuels_builder.build_fbfm40, "worldcover", wc_path, reference,
                static_dir / "fbfm40_worldcover.tif",
            )
        elif reference is not None:
            msg = (
                f"Fuente de combustible '{source}' sin relleno: no hay asset de WorldCover, "
                "así que el hueco fronterizo queda como NB9 y frena el frente por construcción"
            )
            logger.warning("Preparation %s: %s", prep_id, msg)
            warnings.append(msg)

    if source_path is not None and reference:
        # Caching (and its invalidation) lives in fuels_builder, not here — a bare
        # `.exists()` check made every crosswalk change a silent no-op.
        await asyncio.to_thread(
            fuels_builder.build_fbfm40, source, source_path, reference, fbfm_cached, fill_path
        )
        shutil.copy2(fbfm_cached, inputs_dir / "fbfm40.tif")
        # El caché es por fuente (fbfm40_<fuente>.tif) para que alternar entre mapas no
        # obligue a reconstruir; este segundo destino es "el mapa vigente", que es lo que
        # sirve el dashboard.
        shutil.copy2(fbfm_cached, static_dir / "fbfm40.tif")
        generated.append("fbfm40.tif")
    else:
        missing.append("fbfm40.tif")
        logger.warning(
            "Sin insumo de cobertura para la fuente %r — se esperaba %s",
            source,
            "un asset worldcover_raw (ingesta con include_worldcover=true)"
            if source == "worldcover" else configured,
        )

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
    # Bounded on both ends: `since` alone let detections from *later* ingestions into a
    # run that asked for a specific FIRMS window. A single stray detection weeks after
    # the window became `ignition_datetime`, which anchors TSTART — the run then asked
    # for hundreds of weather bands it did not have and preparation died before writing
    # the namelist.
    fire_features = await repository.get_active_fires(
        session, since=since, aoi_id=aoi.id, until=fires_until
    )
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
    simulation_tstart_s = 0.0
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

            # Anchor the run to the wall clock. ELMFIRE reads weather band n at
            # TSTART + n × DT_METEOROLOGY, so with TSTART = 0 a fire igniting at 16:00
            # was simulated with the first forecast hour's weather — the wrong point of
            # the diurnal cycle, and with hourly bands that is a real error, not a
            # cosmetic one (PENDING_PARAMETERS §3).
            weather_start = min(_as_utc(vt) for vt in weather_valid_times)
            offset_s = (_as_utc(ignition_dt) - weather_start).total_seconds()
            if offset_s < 0:
                msg = (
                    f"Ignición {ignition_datetime} anterior al primer paso de "
                    f"meteorología {weather_start.isoformat()}: la corrida arranca en la "
                    "banda 0 en vez de la hora real"
                )
                logger.warning("Preparation %s: %s", prep_id, msg)
                warnings.append(msg)
            else:
                simulation_tstart_s = offset_s
                logger.info(
                    "Preparation %s: corrida anclada a t=%.0f s (%.1f h tras la banda 0)",
                    prep_id, offset_s, offset_s / 3600.0,
                )

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
            simulation_tstart_s=simulation_tstart_s,
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
        "fuels_source": source,
    }




