"""
Simulation endpoints — wired to ELMFIRE runner microservice.

POST /simulations/run  — trigger a full ELMFIRE simulation (sprint siguiente)
GET  /simulations/{id} — poll simulation status
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repository
from app.dependencies import get_db

router = APIRouter(prefix="/simulations", tags=["simulations"])


def _envelope(status: str, data=None, error: dict | None = None) -> dict:
    return {
        "status": status,
        "data": data,
        "error": error,
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
    }


@router.post("/run")
async def run_simulation():
    raise HTTPException(
        status_code=501,
        detail="Simulation endpoint not yet implemented — sprint siguiente",
    )


@router.get("/{simulation_id}")
async def get_simulation(
    simulation_id: uuid.UUID,
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
            "ignition_datetime": run.ignition_datetime.isoformat() if run.ignition_datetime else None,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "error_message": run.error_message,
        },
    )
