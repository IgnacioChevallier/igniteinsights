"""
HTTP client to the elmfire-runner microservice.

The microservice is a separate Linux process that executes:
    mpirun -n 1 elmfire_2025.0212 elmfire.data
and returns paths to simulation outputs.

Paths must be accessible to both services via a shared Docker volume.
"""
import logging

import httpx

from app.config import settings

from .errors import ELMFIRERunnerError, ELMFIRERunnerTimeoutError, ELMFIRERunnerUnavailableError
from .schemas import SimulationRequest, SimulationResult

logger = logging.getLogger(__name__)

# Mirrors elmfire-runner's own subprocess timeout buffer (job_timeout_buffer_seconds)
# so the HTTP client doesn't abandon a request that the runner is still legitimately
# working on.
JOB_TIMEOUT_BUFFER_SECONDS = 600


class ELMFIRERunnerClient:
    def __init__(self) -> None:
        self._base_url = settings.elmfire_runner_url

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
        async with httpx.AsyncClient(timeout=httpx.Timeout(float(timeout_s))) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/simulate",
                    json=request.model_dump(),
                )
                response.raise_for_status()
                return SimulationResult(**response.json())
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
