"""
Simulation endpoints — wired to ELMFIRE runner microservice.

POST /simulations/run  — trigger a full ELMFIRE simulation
GET  /simulations/{id} — poll simulation status
"""
import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path as FPath
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import repository
from app.db.session import async_session_factory
from app.dependencies import get_db
from app.elmfire.builder.ignition_builder import build_ignition_layer
from app.elmfire.builder.namelist_writer import write_namelist
from app.elmfire.runner.client import ELMFIRERunnerClient
from app.elmfire.runner.errors import ELMFIRERunnerError
from app.elmfire.runner.schemas import SimulationRequest
from app.postprocessing.isochrone_converter import (
    enrich_with_arrival_time,
    shapefile_to_geojson,
)
from app.postprocessing.raster_overlay import render_raster_overlay
from app.postprocessing.stats_reader import read_fire_size_stats

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


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    if p.exists():
        return p
    parts = p.parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "app" and parts[2] == "data":
        local = Path.cwd() / "data" / Path(*parts[3:])
        return local
    return p


class SimulationRunRequest(BaseModel):
    inputs_dir: str
    horizon_hours: int = 12
    ignition_datetime: datetime | None = None


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
        session, aoi.id, horizon_hours=body.horizon_hours, ignition_datetime=body.ignition_datetime
    )
    await session.commit()
    await session.refresh(sim_run)

    outputs_dir = _resolve(settings.elmfire_outputs_dir) / str(sim_run.id)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    try:
        # (Re)write namelist with the requested horizon
        elmfire_data = inputs_dir / "elmfire.data"
        import asyncio
        _, resolved_dtdump_s = await asyncio.to_thread(
            write_namelist,
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
        },
    )


@router.get(
    "/{simulation_id}/isochrones",
    summary="Get predicted fire isochrones for a simulation run as GeoJSON",
    description=(
        "Converts the run's hourly_isochrones.shp (fire-front contour lines, "
        "generated by the elmfire-runner from the time-of-arrival raster) to a "
        "GeoJSON FeatureCollection in EPSG:4326, enriched with arrival_s/"
        "arrival_hours per feature where the time-of-arrival raster is available. "
        "Returns an empty FeatureCollection (not an error) if the run produced no "
        "isochrones."
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

    output_dir = _resolve(run.output_dir)
    shp_path = output_dir / "hourly_isochrones.shp"
    geojson = await asyncio.to_thread(shapefile_to_geojson, shp_path)

    tifs = sorted(output_dir.glob("time_of_arrival_*.tif"))
    if tifs and geojson["features"]:
        geojson = await asyncio.to_thread(enrich_with_arrival_time, geojson, tifs[-1])

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
