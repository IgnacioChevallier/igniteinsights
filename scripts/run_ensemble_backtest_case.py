#!/usr/bin/env python3
"""Run one restart end-to-end with a global serial ELMFIRE lock and safe retries."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MEMBERS = ["c00", *(f"p{index:02d}" for index in range(1, 31))]
STANDARDIZED_WEATHER = ("u10.tif", "v10.tif", "t2m.tif", "rh.tif")
DERIVED_OUTPUTS = ("flin_*.tif", "vs_*.tif", "hourly_isochrones.*", "fire_size_stats.csv")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True, env=env)


def _record_attempt(root: Path, event: dict[str, Any]) -> None:
    path = root / "infrastructure-attempts.json"
    attempts: list[dict[str, Any]] = (
        json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    )
    attempts.append({"at": datetime.now(UTC).isoformat(), **event})
    path.write_text(json.dumps(attempts, indent=2, ensure_ascii=False), encoding="utf-8")


def _safe_remove(path: Path, root: Path) -> None:
    resolved = path.resolve()
    resolved.relative_to(root.resolve())
    if resolved.is_dir():
        shutil.rmtree(resolved)
    else:
        resolved.unlink(missing_ok=True)


def _is_successful_run(root: Path, member: str) -> bool:
    run = root / "runs" / member
    metrics_path = run / "run-metrics.json"
    if not metrics_path.exists():
        return False
    metrics = _read(metrics_path)
    return metrics.get("status") == "success" and len(list(run.glob("time_of_arrival_*.tif"))) == 1


def _isolate_failed_attempt(root: Path, member: str, attempt: int) -> None:
    run_dir = root / "runs" / member
    if run_dir.exists() and not _is_successful_run(root, member):
        failures = root / "failures"
        failures.mkdir(exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        destination = failures / f"{member}-attempt-{attempt}-{timestamp}"
        shutil.move(str(run_dir), destination)
    input_dir = root / "inputs" / member
    if input_dir.exists():
        _safe_remove(input_dir, root)


def _validate_inventory(root: Path, cycle: str, forecast_start: str) -> dict[str, Any]:
    inventory = _read(root / "archive-inventory.json")
    available_at = datetime.fromisoformat(inventory["cycle_available_at"])
    start_at = datetime.fromisoformat(inventory["forecast_start"])
    if inventory.get("complete") is not True or len(inventory.get("entries", [])) != 310:
        raise RuntimeError("archive inventory is not complete for 31 members × 10 hours")
    if available_at > start_at:
        raise RuntimeError("GEFS cycle was not completely available before forecast_start")
    if start_at != datetime.fromisoformat(forecast_start):
        raise RuntimeError("inventory forecast_start differs from the frozen restart")
    inventory_cycle = datetime.fromisoformat(inventory["cycle"]).strftime("%Y%m%d%H")
    if inventory_cycle != cycle:
        raise RuntimeError("inventory cycle differs from the preselected cycle")
    return inventory


def _download_sources(args: argparse.Namespace, python: str, cli: str) -> None:
    root: Path = args.output
    manifests = list((root / "sources").glob("*/manifest.json"))
    if len(manifests) == 31:
        return
    delays = [0, *args.retry_backoff]
    for attempt, delay in enumerate(delays, start=1):
        if delay:
            print(f"transient download retry in {delay}s", flush=True)
            time.sleep(delay)
        try:
            _run(
                [
                    python,
                    cli,
                    "download-gefs",
                    "--cycle",
                    args.cycle,
                    "--forecast-start",
                    args.forecast_start,
                    "--bbox",
                    *(str(value) for value in args.bbox),
                    "--horizon",
                    "24",
                    "--member-limit",
                    "31",
                    "--workers",
                    str(args.download_workers),
                    "--keep-going",
                    "--inventory",
                    str(root / "archive-inventory.json"),
                    "--output",
                    str(root / "sources"),
                ]
            )
        except subprocess.CalledProcessError as exc:
            _record_attempt(
                root,
                {
                    "stage": "download-gefs",
                    "attempt": attempt,
                    "classification": "transient infrastructure failure",
                    "returncode": exc.returncode,
                    "cycle_preserved": args.cycle,
                },
            )
        manifests = list((root / "sources").glob("*/manifest.json"))
        if len(manifests) == 31:
            return
    raise RuntimeError(f"only {len(manifests)}/31 source manifests after safe retries")


def _inventory_with_retries(args: argparse.Namespace, python: str, cli: str) -> None:
    root: Path = args.output
    inventory = root / "archive-inventory.json"
    if inventory.exists():
        return
    delays = [0, *args.retry_backoff]
    for attempt, delay in enumerate(delays, start=1):
        if delay:
            print(f"transient inventory retry in {delay}s", flush=True)
            time.sleep(delay)
        try:
            _run(
                [
                    python,
                    cli,
                    "inventory-gefs",
                    "--cycle",
                    args.cycle,
                    "--forecast-start",
                    args.forecast_start,
                    "--horizon",
                    "24",
                    "--member-limit",
                    "31",
                    "--output",
                    str(inventory),
                ]
            )
        except subprocess.CalledProcessError as exc:
            _record_attempt(
                root,
                {
                    "stage": "inventory-gefs",
                    "attempt": attempt,
                    "classification": "transient infrastructure failure",
                    "returncode": exc.returncode,
                    "cycle_preserved": args.cycle,
                },
            )
        if inventory.exists():
            return
    raise RuntimeError("could not complete the 31-member archive inventory after safe retries")


def _validate_source_hashes(root: Path) -> None:
    for member in MEMBERS:
        manifest = _read(root / "sources" / member / "manifest.json")
        if manifest["member"] != member:
            raise RuntimeError(f"source manifest member mismatch for {member}")
        for item in manifest["files"]:
            path = Path(item["file"])
            if not path.is_absolute():
                path = Path.cwd() / path
            if not path.exists() or _sha256(path) != item["sha256"]:
                raise RuntimeError(f"source hash mismatch: {path}")


def _run_member(
    args: argparse.Namespace, python: str, cli: str, member: str, runner_env: dict[str, str]
) -> None:
    root: Path = args.output
    if _is_successful_run(root, member):
        input_dir = root / "inputs" / member
        if input_dir.exists():
            _safe_remove(input_dir, root)
        for name in STANDARDIZED_WEATHER:
            _safe_remove(root / "sources" / member / name, root)
        run_dir = root / "runs" / member
        for pattern in DERIVED_OUTPUTS:
            for path in run_dir.glob(pattern):
                _safe_remove(path, root)
        print(f"{member}: already successful", flush=True)
        return
    for attempt in range(1, args.member_attempts + 1):
        _isolate_failed_attempt(root, member, attempt)
        input_dir = root / "inputs" / member
        run_dir = root / "runs" / member
        try:
            _run(
                [
                    python,
                    cli,
                    "materialize",
                    "--source",
                    str(root / "sources" / member),
                    "--frozen-inputs",
                    str(root / "base-p24-modelo-v0-inputs"),
                    "--output",
                    str(input_dir),
                ]
            )
            shutil.copy2(
                input_dir / "ensemble-member.json",
                root / "member-manifests" / f"{member}.json",
            )
            _run(
                [
                    python,
                    cli,
                    "run",
                    "--inputs",
                    str(input_dir),
                    "--outputs",
                    str(run_dir),
                    "--horizon",
                    "24",
                ],
                env=runner_env,
            )
            if not _is_successful_run(root, member):
                raise RuntimeError("run returned without one valid TOA and success metrics")
            _safe_remove(input_dir, root)
            for name in STANDARDIZED_WEATHER:
                _safe_remove(root / "sources" / member / name, root)
            for pattern in DERIVED_OUTPUTS:
                for path in run_dir.glob(pattern):
                    _safe_remove(path, root)
            print(f"{member}: retained and cleaned", flush=True)
            return
        except Exception as exc:
            _record_attempt(
                root,
                {
                    "stage": "member",
                    "member": member,
                    "attempt": attempt,
                    "classification": "infrastructure attempt; excluded from scientific count",
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
            _isolate_failed_attempt(root, member, attempt)
            if attempt == args.member_attempts:
                raise
            time.sleep(args.member_retry_seconds)


def run_case(args: argparse.Namespace) -> None:
    repo = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.relative_to((repo / "data/ensemble-poc").resolve())
    args.output = output
    python = sys.executable
    cli = str(repo / "scripts/weather_ensemble_poc.py")
    validator = str(repo / "scripts/validate_retained_ensemble.py")
    output.mkdir(parents=True, exist_ok=True)

    base = output / "base-p24-modelo-v0-inputs"
    if not base.exists():
        _run(
            [
                python,
                cli,
                "build-base",
                "--case",
                args.case,
                "--window",
                str(args.window),
                "--purpose",
                "contemporary GEFS calibration backtest; scoreable",
                "--output",
                str(base),
            ]
        )
    _inventory_with_retries(args, python, cli)
    _validate_inventory(output, args.cycle, args.forecast_start)
    _download_sources(args, python, cli)
    _validate_source_hashes(output)

    (output / "inputs").mkdir(exist_ok=True)
    (output / "runs").mkdir(exist_ok=True)
    (output / "member-manifests").mkdir(exist_ok=True)
    runner_env = os.environ.copy()
    runner_env["ELMFIRE_RUNNER_URL"] = args.runner_url
    runner_env["ELMFIRE_RUNNER_TRANSFER_FILES"] = "false"
    for member in MEMBERS:
        _run_member(args, python, cli, member, runner_env)

    for horizon in (12, 24):
        agreement = output / "agreement" / f"h{horizon:02d}"
        if not (agreement / "ensemble_agreement.json").exists():
            _run(
                [
                    python,
                    cli,
                    "aggregate",
                    "--runs",
                    str(output / "runs"),
                    "--expected-members",
                    "31",
                    "--min-valid-members",
                    "31",
                    "--cycle-label",
                    args.cycle,
                    "--forecast-start",
                    args.forecast_start,
                    "--horizon",
                    str(horizon),
                    "--output",
                    str(agreement),
                ]
            )
    _run(
        [
            python,
            cli,
            "evaluate-backtest",
            "--base-inputs",
            str(base),
            "--runs",
            str(output / "runs"),
            "--agreement-root",
            str(output / "agreement"),
            "--output",
            str(output / "backtest-metrics.json"),
        ]
    )
    _run([python, validator, str(output)])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--window", type=int, required=True)
    parser.add_argument("--cycle", required=True)
    parser.add_argument("--forecast-start", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bbox", type=float, nargs=4, default=(-72.0, -44.0, -70.0, -41.8))
    parser.add_argument("--download-workers", type=int, default=4)
    parser.add_argument("--retry-backoff", type=int, nargs="*", default=[15, 30, 60, 120])
    parser.add_argument("--member-attempts", type=int, default=3)
    parser.add_argument("--member-retry-seconds", type=int, default=15)
    parser.add_argument("--runner-url", default="http://localhost:8001")
    args = parser.parse_args()
    lock_path = Path("data/ensemble-poc/.elmfire-serial.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SystemExit("another managed ELMFIRE ensemble case holds the serial lock") from exc
        run_case(args)


if __name__ == "__main__":
    main()
