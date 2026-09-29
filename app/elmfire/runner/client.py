"""
HTTP client to the elmfire-runner microservice.

The microservice is a separate Linux process that executes:
    mpirun -n 1 elmfire_2025.0212 elmfire.data
and returns paths to simulation outputs.

The namelist carries absolute paths, so both services must see inputs_dir and
outputs_dir at the same path. With a shared Docker volume that holds already; without
one (settings.elmfire_runner_transfer_files) the client copies inputs_dir to the runner
before the run, copies outputs_dir back after it, and deletes both on the runner.
"""
import asyncio
import logging
import tarfile
import tempfile
from collections.abc import AsyncIterator
from typing import IO

import httpx

from app.config import settings

from .errors import ELMFIRERunnerError, ELMFIRERunnerTimeoutError, ELMFIRERunnerUnavailableError
from .schemas import SimulationRequest, SimulationResult

logger = logging.getLogger(__name__)

# Mirrors elmfire-runner's own subprocess timeout buffer (job_timeout_buffer_seconds)
# so the HTTP client doesn't abandon a request that the runner is still legitimately
# working on.
JOB_TIMEOUT_BUFFER_SECONDS = 600


def pack_dir(path: str, dest: IO[bytes]) -> None:
    # compresslevel=1: the GeoTIFFs barely compress further and level 9 costs minutes.
    with tarfile.open(fileobj=dest, mode="w:gz", compresslevel=1) as tar:
        tar.add(path, arcname=".")
    dest.seek(0)


def unpack_dir(src: IO[bytes], path: str) -> None:
    with tarfile.open(fileobj=src, mode="r:gz") as tar:
        tar.extractall(path, filter="data")


async def _chunks(f: IO[bytes]) -> AsyncIterator[bytes]:
    while chunk := f.read(1 << 20):
        yield chunk


class ELMFIRERunnerClient:
    def __init__(self) -> None:
        self._base_url = settings.elmfire_runner_url

    async def _upload_dir(self, client: httpx.AsyncClient, path: str) -> None:
        with tempfile.TemporaryFile() as tmp:
            await asyncio.to_thread(pack_dir, path, tmp)
            response = await client.put(
                f"{self._base_url}/files", params={"path": path}, content=_chunks(tmp)
            )
            response.raise_for_status()

    async def _download_dir(self, client: httpx.AsyncClient, path: str) -> None:
        with tempfile.TemporaryFile() as tmp:
            async with client.stream("GET", f"{self._base_url}/files", params={"path": path}) as r:
                if r.is_error:
                    await r.aread()  # so the error handler can read the body
                r.raise_for_status()
                async for chunk in r.aiter_bytes():
                    tmp.write(chunk)
            tmp.seek(0)
            await asyncio.to_thread(unpack_dir, tmp, path)

    async def _cleanup(self, client: httpx.AsyncClient, request: SimulationRequest) -> None:
        for path in (request.inputs_dir, request.outputs_dir):
            try:
                await client.delete(f"{self._base_url}/files", params={"path": path})
            except httpx.HTTPError as exc:
                logger.warning("could not delete %s on elmfire-runner: %s", path, exc)

    async def run_simulation(self, request: SimulationRequest) -> SimulationResult:
        logger.info(
            "Sending simulation request to %s (inputs=%s)",
            self._base_url,
            request.inputs_dir,
        )
        timeout_s = max(
            settings.elmfire_runner_timeout,
            request.simulation_hours * 3600 + JOB_TIMEOUT_BUFFER_SECONDS,
        )
        transfer = settings.elmfire_runner_transfer_files
        async with httpx.AsyncClient(timeout=httpx.Timeout(float(timeout_s))) as client:
            try:
                if transfer:
                    await self._upload_dir(client, request.inputs_dir)
                response = await client.post(
                    f"{self._base_url}/simulate",
                    json=request.model_dump(),
                )
                response.raise_for_status()
                result = SimulationResult(**response.json())
                if transfer:
                    await self._download_dir(client, request.outputs_dir)
                return result
            except httpx.TimeoutException as exc:
                raise ELMFIRERunnerTimeoutError(
                    f"elmfire-runner timed out after {timeout_s}s"
                ) from exc
            except httpx.ConnectError as exc:
                raise ELMFIRERunnerUnavailableError(
                    f"elmfire-runner unreachable at {self._base_url}"
                ) from exc
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text
                try:
                    detail = exc.response.json().get("detail", detail)
                except ValueError:
                    pass
                raise ELMFIRERunnerError(
                    f"elmfire-runner HTTP {exc.response.status_code}: {detail}"
                ) from exc
            except httpx.HTTPError as exc:
                raise ELMFIRERunnerError(f"elmfire-runner HTTP error: {exc}") from exc
            finally:
                if transfer:
                    await self._cleanup(client, request)
