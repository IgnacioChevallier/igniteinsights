"""
Background jobs for the endpoints that outlive an HTTP request.

On Railway, ingestion + preparation take ~11 min and a simulation adds ELMFIRE on top,
but the browser-to-Railway connection is cut at 300 s. The `/run/async` variants start
the same coroutine the synchronous endpoint awaits and answer at once with a job id;
the dashboard polls GET /jobs/{id} for the envelope the synchronous call would have
returned.

ponytail: jobs live in this process's memory — a restart or redeploy loses the ones in
flight (polling then gets 404), and a second replica would not see them. Move them to
the database if the api ever runs more than one instance.
"""
import asyncio
import logging
import uuid
from collections.abc import Coroutine
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

_jobs: dict[str, dict[str, Any]] = {}
_tasks: set[asyncio.Task] = set()  # the event loop only holds weak references


async def _run(job_id: str, coro: Coroutine[Any, Any, Any]) -> None:
    try:
        _jobs[job_id].update(status="done", result=await coro)
    except HTTPException as exc:
        _jobs[job_id].update(status="failed", error=str(exc.detail))
    except Exception as exc:
        logger.exception("job %s failed", job_id)
        _jobs[job_id].update(status="failed", error=str(exc))


def start(coro: Coroutine[Any, Any, Any]) -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "result": None, "error": None}
    task = asyncio.create_task(_run(job_id, coro))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return job_id


@router.get(
    "/{job_id}",
    summary="Poll a background job",
    description=(
        "status is 'running', 'done' (result holds the envelope the synchronous endpoint "
        "returns) or 'failed' (error holds the message). 404 means the job is unknown to "
        "this process — typically because the api restarted while it ran."
    ),
)
async def get_job(job_id: str) -> dict[str, Any]:
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found (did the api restart?)")
    return job
