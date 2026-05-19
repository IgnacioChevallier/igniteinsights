from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import repository
from app.dependencies import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

EXPECTED_ELMFIRE_INPUTS = [
    "dem.tif",
    "slp.tif",
    "asp.tif",
    "fbfm40.tif",
    "cc.tif",
    "ch.tif",
    "cbh.tif",
    "cbd.tif",
    "ws.tif",
    "wd.tif",
    "m1.tif",
    "m10.tif",
    "m100.tif",
    "phi.tif",
    "elmfire.data",
]


def _envelope(status: str, data: Any = None, error: dict | None = None) -> dict:
    return {
        "status": status,
        "data": data,
        "error": error,
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }


def _resolve_data_path(configured_path: str) -> Path:
    path = Path(configured_path)
    if path.exists():
        return path

    parts = path.parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "app" and parts[2] == "data":
        local_path = Path.cwd() / "data" / Path(*parts[3:])
        if local_path.exists():
            return local_path

    return path


def _file_info(path: Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
    }


def _scan_elmfire_inputs() -> list[dict]:
    root = _resolve_data_path(settings.elmfire_inputs_dir)
    if not root.exists():
        return []

    folders = [path for path in root.iterdir() if path.is_dir()]
    folders.sort(key=lambda path: path.stat().st_mtime, reverse=True)

    scanned = []
    for folder in folders:
        present = sorted(
            expected for expected in EXPECTED_ELMFIRE_INPUTS if (folder / expected).exists()
        )
        missing = sorted(set(EXPECTED_ELMFIRE_INPUTS) - set(present))
        files = sorted(
            [_file_info(path) for path in folder.iterdir() if path.is_file()],
            key=lambda item: item["name"],
        )
        modified_at = datetime.fromtimestamp(folder.stat().st_mtime, tz=UTC).isoformat()
        scanned.append(
            {
                "name": folder.name,
                "path": str(folder),
                "modified_at": modified_at,
                "present_count": len(present),
                "expected_count": len(EXPECTED_ELMFIRE_INPUTS),
                "missing_count": len(missing),
                "present_files": present,
                "missing_files": missing,
                "files": files,
                "ready": len(missing) == 0,
            }
        )
    return scanned


def _scan_elmfire_outputs() -> list[dict]:
    root = _resolve_data_path(settings.elmfire_outputs_dir)
    if not root.exists():
        return []

    folders = [path for path in root.iterdir() if path.is_dir()]
    folders.sort(key=lambda path: path.stat().st_mtime, reverse=True)

    scanned = []
    for folder in folders:
        files = sorted(
            [_file_info(path) for path in folder.rglob("*") if path.is_file()],
            key=lambda item: item["path"],
        )
        modified_at = datetime.fromtimestamp(folder.stat().st_mtime, tz=UTC).isoformat()
        scanned.append(
            {
                "name": folder.name,
                "path": str(folder),
                "modified_at": modified_at,
                "file_count": len(files),
                "files": files,
            }
        )
    return scanned


def _asset_exists(file_path: str) -> bool:
    return _resolve_data_path(file_path).exists()


@router.get(
    "/summary",
    summary="Read dashboard summary for previous runs and ELMFIRE files",
    description=(
        "Returns recent ingestion/simulation runs, raster assets, registered outputs, "
        "and scanned ELMFIRE input/output directories for the read-only dashboard."
    ),
)
async def get_dashboard_summary(session: AsyncSession = Depends(get_db)):
    ingestion_runs = await repository.list_recent_ingestion_runs(session)
    simulation_runs = await repository.list_recent_simulation_runs(session)
    raster_assets = await repository.list_recent_raster_assets(session)
    simulation_outputs = await repository.list_recent_simulation_outputs(session)

    for asset in raster_assets:
        asset["file_exists"] = _asset_exists(asset["file_path"])

    input_folders = _scan_elmfire_inputs()
    output_folders = _scan_elmfire_outputs()
    combined_runs = sorted(
        [*ingestion_runs, *simulation_runs],
        key=lambda item: item.get("started_at") or "",
        reverse=True,
    )

    data = {
        "generated_at": datetime.now(UTC).isoformat(),
        "expected_elmfire_inputs": EXPECTED_ELMFIRE_INPUTS,
        "summary": {
            "latest_ingestion_status": (
                ingestion_runs[0]["status"] if ingestion_runs else "none"
            ),
            "latest_simulation_status": (
                simulation_runs[0]["status"] if simulation_runs else "none"
            ),
            "raster_asset_count": len(raster_assets),
            "ready_input_folder_count": sum(1 for folder in input_folders if folder["ready"]),
            "input_folder_count": len(input_folders),
            "output_folder_count": len(output_folders),
        },
        "runs": combined_runs,
        "ingestion_runs": ingestion_runs,
        "simulation_runs": simulation_runs,
        "raster_assets": raster_assets,
        "simulation_outputs": simulation_outputs,
        "elmfire_inputs": input_folders,
        "elmfire_outputs": output_folders,
    }
    return _envelope(status="success", data=data)
