"""Background jobs: what the dashboard reads while polling GET /jobs/{id}."""
import asyncio

import pytest
from fastapi import HTTPException

from app.api.v1 import jobs


async def _finish(coro):
    job_id = jobs.start(coro)
    assert (await jobs.get_job(job_id))["status"] == "running"
    await asyncio.gather(*jobs._tasks)
    return await jobs.get_job(job_id)


def test_done_job_carries_the_endpoint_envelope():
    async def ok():
        return {"status": "success", "data": {"simulation_id": "s1"}}

    job = asyncio.run(_finish(ok()))
    assert job["status"] == "done" and job["error"] is None
    assert job["result"] == {"status": "success", "data": {"simulation_id": "s1"}}


def test_http_exception_becomes_its_detail():
    async def boom():
        raise HTTPException(status_code=502, detail="elmfire-runner unreachable")

    job = asyncio.run(_finish(boom()))
    assert job["status"] == "failed" and job["error"] == "elmfire-runner unreachable"


def test_unknown_job_is_404():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(jobs.get_job("nope"))
    assert exc.value.status_code == 404
