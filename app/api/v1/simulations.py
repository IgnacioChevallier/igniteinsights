"""
Simulation endpoints — wired to ELMFIRE runner microservice.

POST /simulations/run  — trigger a full ELMFIRE simulation
GET  /simulations/{id} — poll simulation status
"""
import asyncio
import functools
import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Path as FPath
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import resolve_data_path as _resolve
from app.config import settings
from app.db import repository
from app.dependencies import get_db
from app.elmfire.builder.namelist_writer import write_namelist
from app.elmfire.runner.client import ELMFIRERunnerClient
from app.elmfire.runner.errors import ELMFIRERunnerError
from app.elmfire.runner.schemas import SimulationRequest
from app.postprocessing.isochrone_converter import (
    isochrones_to_geojson,
    shapefile_to_geojson,
)
from app.postprocessing.raster_overlay import render_raster_overlay
from app.postprocessing.stats_reader import read_fire_size_stats
from app.postprocessing.wind_field import wind_bands

_RASTER_GLOBS: dict[str, str] = {
    "time_of_arrival": "time_of_arrival_*.tif",
    "fireline_intensity": "flin_*.tif",
}
_RASTER_UNITS: dict[str, tuple[float, str]] = {
    "time_of_arrival": (3600.0, "hours"),
    "fireline_intensity": (1.0, "kW/m"),
}

router = APIRouter(prefix="/simulations", tags=["simulations"])


def _envelope(status: str, data=None, error: dict | None = None) -> dict:
    return {
        "status": status,
        "data": data,
        "error": error,
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }


class SimulationRunRequest(BaseModel):
    inputs_dir: str
    horizon_hours: int = 12
    ignition_datetime: datetime | None = None
    # Optional overrides. None keeps the namelist writer's defaults, so existing callers
    # are unaffected; the playground uses them to control the synthetic scenario.
    dtdump_s: float | None = None
    lh_moisture_pct: float | None = None
    lw_moisture_pct: float | None = None


@router.post(
    "/run",
    summary="Start an ELMFIRE wildfire spread simulation",
    description=(
        "Runs an ELMFIRE simulation from a prepared inputs directory. "
        "Provide 'inputs_dir' (returned by POST /ingestion/run in the "
        "'preparation.inputs_dir' field) and 'horizon_hours'. "
        "The endpoint writes the elmfire.data namelist, calls the elmfire-runner "
        "microservice, registers the simulation in the database, and returns a "
        "simulation_id. Use GET /simulations/{id} to poll for completion."
    ),
)
async def run_simulation(
    body: SimulationRunRequest,
    session: AsyncSession = Depends(get_db),
):
    inputs_dir = _resolve(body.inputs_dir)
    if not inputs_dir.exists():
        raise HTTPException(
            status_code=422,
            detail=f"inputs_dir not found: {body.inputs_dir}. Run POST /ingestion/run first.",
        )

    # Require at least a DEM to define the simulation domain
    if not (inputs_dir / "dem.tif").exists():
        raise HTTPException(
            status_code=422,
            detail="dem.tif missing from inputs_dir. Run ingestion with include_dem=true first.",
        )

    aoi = await repository.get_or_create_default_aoi(session)
    sim_run = await repository.create_simulation_run(
        session,
        aoi.id,
        horizon_hours=body.horizon_hours,
        ignition_datetime=body.ignition_datetime,
        # Recorded so GET /{id}/ignition can find ignicion.shp, which lives in the
        # inputs folder — SimulationRun otherwise only tracks output_dir.
        elmfire_config={"inputs_dir": str(inputs_dir)},
    )
    await session.commit()
    await session.refresh(sim_run)

    outputs_dir = _resolve(settings.elmfire_outputs_dir) / str(sim_run.id)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    try:
        # (Re)write namelist with the requested horizon
        elmfire_data = inputs_dir / "elmfire.data"
        import asyncio
        namelist_kwargs: dict = {}
        if body.dtdump_s is not None:
            namelist_kwargs["dtdump_s"] = body.dtdump_s
        if body.lh_moisture_pct is not None:
            namelist_kwargs["lh_moisture_pct"] = body.lh_moisture_pct
        if body.lw_moisture_pct is not None:
            namelist_kwargs["lw_moisture_pct"] = body.lw_moisture_pct

        _, resolved_dtdump_s, weather_warnings = await asyncio.to_thread(
            functools.partial(write_namelist, **namelist_kwargs),
            inputs_dir,
            outputs_dir,
            body.horizon_hours,
            elmfire_data,
        )

        client = ELMFIRERunnerClient()
        result = await client.run_simulation(
            SimulationRequest(
                elmfire_data_path=str(elmfire_data),
                inputs_dir=str(inputs_dir),
                outputs_dir=str(outputs_dir),
                simulation_hours=body.horizon_hours,
                dtdump_s=resolved_dtdump_s,
            )
        )

        await repository.update_simulation_run(
            session,
            sim_run.id,
            status="success",
            output_dir=str(outputs_dir),
            # Surfaced on the dashboard: a run with frozen weather looks identical to a
            # good one on the map, so the caveat has to travel with the result.
            elmfire_config={"inputs_dir": str(inputs_dir), "warnings": weather_warnings},
        )

        if result.outputs.isochrones_shp:
            await repository.create_simulation_output(
                session, sim_run.id, "isochrones", file_path=result.outputs.isochrones_shp
            )
        if result.outputs.time_of_arrival_tif:
            await repository.create_simulation_output(
                session, sim_run.id, "time_of_arrival", file_path=result.outputs.time_of_arrival_tif
            )
        for p in result.outputs.flame_length_tifs:
            await repository.create_simulation_output(
                session, sim_run.id, "flame_length", file_path=p
            )
        for p in result.outputs.spread_rate_tifs:
            await repository.create_simulation_output(
                session, sim_run.id, "spread_rate", file_path=p
            )

        await session.commit()

        return _envelope(
            status="success",
            data={
                "simulation_id": str(sim_run.id),
                "inputs_dir": str(inputs_dir),
                "outputs_dir": str(outputs_dir),
                "runner_run_id": result.run_id,
                "outputs": result.outputs.model_dump(),
            },
        )

    except ELMFIRERunnerError as exc:
        await repository.update_simulation_run(
            session, sim_run.id, status="failed", error_message=str(exc)
        )
        await session.commit()
        raise HTTPException(status_code=502, detail=str(exc))

    except ValueError as exc:
        # Namelist/input validation — e.g. horizon_hours exceeds the forecast hours the
        # weather rasters actually carry. A caller-fixable request, not a server fault.
        await repository.update_simulation_run(
            session, sim_run.id, status="failed", error_message=str(exc)
        )
        await session.commit()
        raise HTTPException(status_code=422, detail=str(exc))

    except Exception as exc:
        await repository.update_simulation_run(
            session, sim_run.id, status="failed", error_message=str(exc)
        )
        await session.commit()
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/{simulation_id}",
    summary="Get the status of an ELMFIRE simulation run",
    description=(
        "Looks up a simulation run by ID and returns its status, time horizon, "
        "ignition time, timestamps, and error message if one exists."
    ),
)
async def get_simulation(
    simulation_id: uuid.UUID = FPath(
        ...,
        description="The simulation run ID returned by POST /api/v1/simulations/run.",
    ),
    session: AsyncSession = Depends(get_db),
):
    run = await repository.get_simulation_run(session, simulation_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return _envelope(
        status="success",
        data={
            "id": str(run.id),
            "status": run.status,
            "horizon_hours": run.horizon_hours,
            "ignition_datetime": (
                run.ignition_datetime.isoformat() if run.ignition_datetime else None
            ),
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "output_dir": run.output_dir,
            "error_message": run.error_message,
            "warnings": (run.elmfire_config or {}).get("warnings", []),
        },
    )


@router.get(
    "/{simulation_id}/isochrones",
    summary="Get predicted fire isochrones for a simulation run as GeoJSON",
    description=(
        "Cumulative burned area per contour level as GeoJSON Polygons in EPSG:4326, "
        "with arrival_s/arrival_hours per feature. The levels come from the run's "
        "hourly_isochrones.shp; the geometry is polygonised from its time-of-arrival "
        "raster, so unburned ground enclosed by the front (a lake, a rock outcrop) is a "
        "hole rather than area painted as burned. Runs with no raster, or made before "
        "gdal_contour stored the level, fall back to the raw contour LineStrings. "
        "These are the PREDICTION: for the observed fire perimeter the prediction "
        "started from, see GET /{id}/ignition. Returns an empty FeatureCollection "
        "(not an error) if the run produced no isochrones."
    ),
)
async def get_simulation_isochrones(
    simulation_id: uuid.UUID = FPath(
        ...,
        description="The simulation run ID returned by POST /api/v1/simulations/run.",
    ),
    session: AsyncSession = Depends(get_db),
):
    run = await repository.get_simulation_run(session, simulation_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if not run.output_dir:
        return _envelope("success", {"type": "FeatureCollection", "features": []})

    outputs = _resolve(run.output_dir)
    shp_path = outputs / "hourly_isochrones.shp"
    # The contour lines give the levels; the raster gives which cells actually burned.
    # Without it the map has to close open contours itself and paints across lakes.
    toa = sorted(outputs.glob(_RASTER_GLOBS["time_of_arrival"]))
    geojson = await asyncio.to_thread(
        isochrones_to_geojson, shp_path, toa[0] if toa else None
    )
    return _envelope("success", geojson)


@router.get(
    "/{simulation_id}/wind",
    summary="The real wind the run was driven by, per hourly band",
    description=(
        "Domain-mean wind speed and blowing-to azimuth for each band of the run's own "
        "ws.tif/wd.tif, plus the domain outline in EPSG:4326. Read from the ELMFIRE "
        "inputs rather than the raw GFS assets, so it cannot disagree with the wind the "
        "simulation actually used. `blows_to_deg` is where the wind goes — the rasters "
        "store the direction it comes FROM. Each band carries a `direction_consistency` "
        "(1.0 = uniform across the domain); it collapses in calm hours, where the "
        "direction of a sub-1 mph wind carries no information. Returns an empty payload "
        "for runs with no tracked inputs directory or no weather rasters."
    ),
)
async def get_simulation_wind(
    simulation_id: uuid.UUID = FPath(
        ..., description="The simulation run ID returned by POST /api/v1/simulations/run."
    ),
    session: AsyncSession = Depends(get_db),
):
    run = await repository.get_simulation_run(session, simulation_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    inputs_dir = (run.elmfire_config or {}).get("inputs_dir")
    if not inputs_dir:
        return _envelope("success", None)
    inputs = _resolve(inputs_dir)
    ws, wd = inputs / "ws.tif", inputs / "wd.tif"
    if not (ws.exists() and wd.exists()):
        return _envelope("success", None)

    return _envelope("success", await asyncio.to_thread(wind_bands, ws, wd))


@router.get(
    "/{simulation_id}/ignition",
    summary="Get the observed fire perimeter the simulation started from, as GeoJSON",
    description=(
        "Returns ignicion.shp — the burn perimeter reconstructed from FIRMS "
        "detections (clustering + concave hull) that seeded phi.tif for this run. "
        "This is OBSERVED INPUT, not prediction: it is typically the large majority "
        "of the burned area a run reports, so it must be shown distinctly from the "
        "isochrones rather than blended with them. Returns an empty FeatureCollection "
        "for runs recorded before inputs_dir was tracked, or if the file is missing."
    ),
)
async def get_simulation_ignition(
    simulation_id: uuid.UUID = FPath(
        ...,
        description="The simulation run ID returned by POST /api/v1/simulations/run.",
    ),
    session: AsyncSession = Depends(get_db),
):
    run = await repository.get_simulation_run(session, simulation_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    inputs_dir = (run.elmfire_config or {}).get("inputs_dir")
    if not inputs_dir:
        return _envelope("success", {"type": "FeatureCollection", "features": []})

    shp_path = _resolve(inputs_dir) / "ignicion.shp"
    geojson = await asyncio.to_thread(shapefile_to_geojson, shp_path)
    return _envelope("success", geojson)


@router.get(
    "/{simulation_id}/stats",
    summary="Get fire growth summary stats for a simulation run",
    description=(
        "Parses the run's fire_size_stats.csv (ELMFIRE's final-state summary: "
        "total/crown fire area, fire volume, population and asset exposure, PM2.5 "
        "release) and returns it as a list of rows. Population/real estate/land "
        "value of -1 means no assets-at-risk layer was configured, not zero."
    ),
)
async def get_simulation_stats(
    simulation_id: uuid.UUID = FPath(
        ...,
        description="The simulation run ID returned by POST /api/v1/simulations/run.",
    ),
    session: AsyncSession = Depends(get_db),
):
    run = await repository.get_simulation_run(session, simulation_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if not run.output_dir:
        return _envelope("success", {"simulation_id": str(simulation_id), "rows": []})

    csv_path = _resolve(run.output_dir) / "fire_size_stats.csv"
    rows = await asyncio.to_thread(read_fire_size_stats, csv_path)
    return _envelope("success", {"simulation_id": str(simulation_id), "rows": rows})


@router.get(
    "/{simulation_id}/rasters/{raster_type}",
    summary="Get a colorized raster overlay (time-of-arrival or fireline intensity)",
    description=(
        "Reprojects and colorizes the run's time_of_arrival or flin GeoTIFF for "
        "display as a map image overlay. Returns a base64 PNG, its corner "
        "coordinates in EPSG:4326, and the data's value range/unit. Returns a "
        "degenerate [0, 0] value_range (not an error) for runs with no fire spread."
    ),
)
async def get_simulation_raster(
    simulation_id: uuid.UUID = FPath(
        ...,
        description="The simulation run ID returned by POST /api/v1/simulations/run.",
    ),
    raster_type: Literal["time_of_arrival", "fireline_intensity"] = FPath(...),
    session: AsyncSession = Depends(get_db),
):
    run = await repository.get_simulation_run(session, simulation_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if not run.output_dir:
        raise HTTPException(status_code=404, detail="Simulation has no output directory")

    output_dir = _resolve(run.output_dir)
    matches = sorted(output_dir.glob(_RASTER_GLOBS[raster_type]))
    if not matches:
        raise HTTPException(
            status_code=404, detail=f"No {raster_type} raster found for this simulation"
        )

    unit_divisor, unit_label = _RASTER_UNITS[raster_type]
    overlay = await asyncio.to_thread(
        render_raster_overlay, matches[-1], unit_divisor, unit_label
    )
    return _envelope("success", overlay)
