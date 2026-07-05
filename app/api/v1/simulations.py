"""
Simulation endpoints — wired to ELMFIRE runner microservice.

POST /simulations/run  — trigger a full ELMFIRE simulation
GET  /simulations/{id} — poll simulation status
"""
import uuid
from datetime import UTC, datetime
from pathlib import Path

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
        session, aoi.id, horizon_hours=body.horizon_hours
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
