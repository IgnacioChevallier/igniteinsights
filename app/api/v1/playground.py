"""
Playground endpoints — synthetic sensitivity scenarios.

POST /playground/run     — build a synthetic inputs dir and run ELMFIRE on it
POST /playground/preview — what a scenario looks like, without running it
GET  /playground/presets — the curated scenario sequence

The playground owns no simulation machinery. It writes a directory of uniform rasters and
hands it to the existing POST /simulations/run, which already writes the namelist, calls
the runner and registers the run. See docs/arquitectura.md.
"""
import json
import logging
import shutil
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.simulations import SimulationRunRequest, run_simulation
from app.config import resolve_data_path, settings
from app.db import repository
from app.dependencies import get_db
from app.elmfire.builder.fuels_builder import fuel_model_info
from app.playground.builder import build_scenario_inputs, scenario_map_layers
from app.playground.metrics import scenario_metrics
from app.playground.schemas import Scenario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playground", tags=["playground"])

_PRESETS_FILE = Path(__file__).resolve().parent.parent.parent / "playground" / "presets.json"

# Synthetic runs live under their own prefix so they are trivially separable from real
# simulations on disk, and can be swept without touching production outputs.
_PLAYGROUND_SUBDIR = "playground"

# Each run gets its own inputs directory — reusing one keyed by scenario hash would look
# tidier but races: run_simulation writes elmfire.data into it with that run's
# outputs_dir, so two concurrent runs of the same scenario (the A/B panel makes this one
# click away) could send their outputs to each other's folder. Unique directories instead,
# with a cap so an afternoon of clicking cannot fill the disk. ~8 MB per run at 12 km/30 m.
_MAX_KEPT_INPUT_DIRS = 50


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
    return {
        "status": "success",
        "data": {
            "presets": _load_presets(),
            "notes": {
                "wind_direction": (
                    "wind_direction_deg is the direction the wind blows FROM "
                    "(meteorological convention, verified against ELMFIRE "
                    "elmfire_subs.f90:473). 0° = wind from the north, so the fire "
                    "elongates SOUTH."
                ),
                "aspect": "aspect_deg is the downslope azimuth; fire runs upslope.",
                "terrain": (
                    "A preset carries no terrain, so it loads as a uniform slab. Vary "
                    "terrain between A and B like any other single factor; POST /preview "
                    "to see the result before running it."
                ),
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
    "/preview",
    summary="Draw a scenario without running it",
    description=(
        "The scenario's own geometry — the fuel slab, its lake if it has one, the "
        "ignition disc and the forcing vectors — plus the identity of its fuel model. "
        "Pure and cheap: no ELMFIRE call, nothing written to disk. The panel calls this "
        "the moment a scenario is picked so the map shows what is about to run instead "
        "of staying blank for the length of the run."
    ),
)
async def preview_scenario(scenario: Scenario):
    return {
        "status": "success",
        "data": {
            "map_layers": scenario_map_layers(scenario),
            "fuel_model": fuel_model_info(scenario.fbfm40_code),
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
    playground_root = resolve_data_path(settings.elmfire_inputs_dir) / _PLAYGROUND_SUBDIR
    _prune_old_inputs(playground_root)
    inputs_dir = playground_root / str(run_id)

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
        # What the scenario *is*, for the synthetic map: a uniform slab of one fuel model,
        # the ignition disc, and the forcing vectors. A satellite basemap under a run that
        # assumes flat ground and one fuel class shows terrain the scenario denies.
        data["map_layers"] = scenario_map_layers(scenario)
        data["fuel_model"] = fuel_model_info(scenario.fbfm40_code)
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


def _prune_old_inputs(root: Path) -> None:
    """Keep the most recent _MAX_KEPT_INPUT_DIRS scenario directories.

    Pruning by modification time and only beyond the cap means an in-flight run — always
    among the newest — is never touched.
    """
    if not root.exists():
        return
    dirs = sorted(
        (d for d in root.iterdir() if d.is_dir()),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    for stale in dirs[_MAX_KEPT_INPUT_DIRS:]:
        try:
            shutil.rmtree(stale)
        except OSError as exc:  # a run may still hold it; try again next time
            logger.warning("Could not prune %s: %s", stale, exc)


async def _build(scenario: Scenario, inputs_dir: Path) -> None:
    import asyncio

    await asyncio.to_thread(build_scenario_inputs, scenario, inputs_dir)
