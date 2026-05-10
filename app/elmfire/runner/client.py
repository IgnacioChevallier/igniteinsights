"""
HTTP client to the elmfire-runner microservice.

The microservice is a separate Linux process that executes:
    elmfire_2025.0212 < elmfire.data
and returns paths to simulation outputs.

Paths must be accessible to both services via a shared Docker volume.
"""
import logging

import httpx

from app.config import settings

from .errors import ELMFIRERunnerError, ELMFIRERunnerTimeoutError, ELMFIRERunnerUnavailableError
from .schemas import SimulationRequest, SimulationResult

logger = logging.getLogger(__name__)


class ELMFIRERunnerClient:
    def __init__(self) -> None:
        self._base_url = settings.elmfire_runner_url
        self._timeout = httpx.Timeout(float(settings.elmfire_runner_timeout))

    async def run_simulation(self, request: SimulationRequest) -> SimulationResult:
        logger.info(
            "Sending simulation request to %s (inputs=%s)",
            self._base_url,
            request.inputs_dir,
        )
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/simulate",
                    json=request.model_dump(),
                )
                response.raise_for_status()
                return SimulationResult(**response.json())
            except httpx.TimeoutException as exc:
                raise ELMFIRERunnerTimeoutError(
                    f"elmfire-runner timed out after {settings.elmfire_runner_timeout}s"
                ) from exc
            except httpx.ConnectError as exc:
                raise ELMFIRERunnerUnavailableError(
                    f"elmfire-runner unreachable at {self._base_url}"
                ) from exc
            except httpx.HTTPError as exc:
                raise ELMFIRERunnerError(f"elmfire-runner HTTP error: {exc}") from exc
