"""
Playground endpoints — synthetic sensitivity scenarios.

POST /playground/run     — build a synthetic inputs dir and run ELMFIRE on it
GET  /playground/presets — the curated scenario sequence

The playground owns no simulation machinery. It writes a directory of uniform rasters and
hands it to the existing POST /simulations/run, which already writes the namelist, calls
the runner and registers the run. See PLAYGROUND-SENSIBILIDAD.md.
"""
import json
import logging
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.simulations import SimulationRunRequest, run_simulation
from app.config import resolve_data_path, settings
from app.db import repository
from app.dependencies import get_db
from app.playground.builder import build_scenario_inputs
from app.playground.metrics import scenario_metrics
from app.playground.schemas import Scenario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playground", tags=["playground"])

_PRESETS_FILE = Path(__file__).resolve().parent.parent.parent / "playground" / "presets.json"

# Synthetic runs live under their own prefix so they are trivially separable from real
# simulations on disk, and can be swept without touching production outputs.
_PLAYGROUND_SUBDIR = "playground"


@lru_cache(maxsize=1)
def _load_presets() -> list[dict]:
    """Presets are versioned data, not code. Validated at load so a broken file fails
    loudly here rather than producing an unburnable domain at run time."""
    presets = json.loads(_PRESETS_FILE.read_text(encoding="utf-8"))
    for preset in presets:
        Scenario(**preset["scenario"])
    return presets


@router.get(
    "/presets",
    summary="Curated sensitivity scenarios",
    description=(
        "An ordered sequence of synthetic base cases. Each one changes exactly one factor "
        "with respect to the scenario named in 'changes_from', so the difference between "
        "two runs is attributable to that factor. 'expectation' states what to look for."
    ),
)
async def get_presets():
    presets = _load_presets()
    return {
        "status": "success",
        "data": {
            "presets": presets,
            "notes": {
                "wind_direction": (
                    "wind_direction_deg is the direction the wind blows FROM "
                    "(meteorological convention, verified against ELMFIRE "
                    "elmfire_subs.f90:473). 0° = wind from the north, so the fire "
                    "elongates SOUTH."
                ),
                "aspect": "aspect_deg is the downslope azimuth; fire runs upslope.",
                "synthetic": (
                    "These domains are synthetic. They are centred on the AOI only so the "
                    "map shows them somewhere plausible — they are not a prediction for "
                    "that location."
                ),
            },
        },
        "error": None,
    }


@router.post(
    "/run",
    summary="Run a synthetic scenario",
    description=(
        "Builds a square domain of uniform rasters from the scenario and runs ELMFIRE on "
        "it. Returns the same simulation_id as a real run, so GET /simulations/{id}/"
        "isochrones and the rest work unchanged."
    ),
)
async def run_playground_scenario(
    scenario: Scenario,
    session: AsyncSession = Depends(get_db),
):
    run_id = uuid.uuid4()
    inputs_dir = resolve_data_path(settings.elmfire_inputs_dir) / _PLAYGROUND_SUBDIR / str(run_id)

    try:
        await _build(scenario, inputs_dir)
    except ValueError as exc:
        # Invalid scenario (fuel code absent from the table, ignition smaller than a cell).
        # Caller-fixable, so 422 rather than 500.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    response = await run_simulation(
        SimulationRunRequest(
            inputs_dir=str(inputs_dir),
            horizon_hours=scenario.horizon_hours,
            dtdump_s=scenario.dtdump_s,
            lh_moisture_pct=scenario.lh_moisture_pct,
            lw_moisture_pct=scenario.lw_moisture_pct,
        ),
        session,
    )
    # Persist the scenario alongside the run so /metrics and the comparison view can
    # recover what produced it. run_simulation owns elmfire_config, so merge rather than
    # overwrite — dropping inputs_dir would break GET /simulations/{id}/ignition.
    data = response.get("data") if isinstance(response, dict) else None
    if data and data.get("simulation_id"):
        sim_id = uuid.UUID(data["simulation_id"])
        run = await repository.get_simulation_run(session, sim_id)
        if run is not None:
            merged = dict(run.elmfire_config or {})
            merged["scenario"] = scenario.model_dump()
            await repository.update_simulation_run(
                session, sim_id, status=run.status, elmfire_config=merged
            )
            await session.commit()
        data["scenario"] = scenario.model_dump()
    return response


@router.get(
    "/{simulation_id}/metrics",
    summary="Comparable growth, shape and direction metrics for a scenario",
    description=(
        "Derived from the run's time-of-arrival raster: burned area and maximum spread "
        "distance per hour, plus head spread rate, its Scott & Burgan adjective class, "
        "spread azimuth and elongation. Only meaningful for the playground's point "
        "ignition at the domain centre."
    ),
)
async def get_scenario_metrics(
    simulation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    import asyncio

    run = await repository.get_simulation_run(session, simulation_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if not run.output_dir:
        raise HTTPException(status_code=409, detail="Simulation has produced no output yet")

    outputs = resolve_data_path(run.output_dir)
    candidates = sorted(outputs.glob("time_of_arrival*.tif"))
    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"No time_of_arrival raster in {run.output_dir}",
        )

    metrics = await asyncio.to_thread(
        scenario_metrics, candidates[0], run.horizon_hours or 1
    )
    metrics["scenario"] = (run.elmfire_config or {}).get("scenario")
    return {"status": "success", "data": metrics, "error": None}


async def _build(scenario: Scenario, inputs_dir: Path) -> None:
    import asyncio

    await asyncio.to_thread(build_scenario_inputs, scenario, inputs_dir)
