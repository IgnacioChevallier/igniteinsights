"""ELMFIRERunnerClient with and without directory transfer (Railway vs docker-compose)."""
import asyncio
import io
from pathlib import Path

import httpx

from app.config import settings
from app.elmfire.runner import client as runner_client
from app.elmfire.runner.schemas import SimulationRequest


def _run(monkeypatch, tmp_path: Path, transfer: bool) -> tuple[list[str], Path]:
    inputs, outputs = tmp_path / "inputs", tmp_path / "outputs"
    inputs.mkdir()
    (inputs / "dem.tif").write_text("dem")
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.url.path == "/simulate":
            return httpx.Response(200, json={
                "status": "success", "run_id": "r1",
                "outputs": {"time_of_arrival_tif": f"{outputs}/time_of_arrival_001.tif"},
            })
        if request.method == "GET":  # what the runner would send back from outputs_dir
            src = tmp_path / "runner_out"
            src.mkdir()
            (src / "time_of_arrival_001.tif").write_text("toa")
            buf = io.BytesIO()
            runner_client.pack_dir(str(src), buf)
            return httpx.Response(200, content=buf.read())
        return httpx.Response(200, json={})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        runner_client.httpx, "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    monkeypatch.setattr(settings, "elmfire_runner_transfer_files", transfer)
    outputs.mkdir()
    asyncio.run(runner_client.ELMFIRERunnerClient().run_simulation(SimulationRequest(
        elmfire_data_path=str(inputs / "elmfire.data"),
        inputs_dir=str(inputs), outputs_dir=str(outputs),
    )))
    return calls, outputs


def test_shared_volume_only_calls_simulate(monkeypatch, tmp_path):
    calls, _ = _run(monkeypatch, tmp_path, transfer=False)
    assert calls == ["POST /simulate"]


def test_transfer_uploads_simulates_downloads_and_cleans(monkeypatch, tmp_path):
    calls, outputs = _run(monkeypatch, tmp_path, transfer=True)
    assert calls == ["PUT /files", "POST /simulate", "GET /files", "DELETE /files", "DELETE /files"]
    assert (outputs / "time_of_arrival_001.tif").read_text() == "toa"
