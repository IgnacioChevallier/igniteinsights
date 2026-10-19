#!/usr/bin/env python3
"""Resume every archived calibration restart, one complete case at a time."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _existing_roots(ensemble_root: Path) -> dict[tuple[str, int], Path]:
    roots: dict[tuple[str, int], Path] = {}
    for manifest_path in ensemble_root.rglob("base-p24-modelo-v0-inputs/base-package.json"):
        manifest = _read(manifest_path)
        key = (manifest["case"], int(manifest["window_index"]))
        root = manifest_path.parent.parent
        if root.resolve() == ensemble_root.resolve():
            continue
        if key in roots and roots[key] != root:
            complete = [
                candidate
                for candidate in (roots[key], root)
                if (candidate / "backtest-metrics.json").exists()
            ]
            if len(complete) == 1:
                roots[key] = complete[0]
                continue
            raise RuntimeError(f"ambiguous roots for {key}: {roots[key]} and {root}")
        roots[key] = root
    return roots


def _new_root(ensemble_root: Path, row: dict[str, Any]) -> Path:
    fire = row["case"].split("/", 1)[0]
    cycle = datetime.fromisoformat(row["selected_cycle"]).strftime("%Y%m%d%H")
    return (
        ensemble_root
        / "backtest-calibration"
        / f"{fire}-w{int(row['window_index']):02d}-gefs-{cycle}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path(
            "data/ensemble-poc/backtest-epuyen-20250115T1833Z-gefs-2025011512/"
            "calibration-restart-archive-inventory.json"
        ),
    )
    parser.add_argument("--ensemble-root", type=Path, default=Path("data/ensemble-poc"))
    parser.add_argument("--stop-on-failure", action="store_true")
    args = parser.parse_args()

    inventory = _read(args.inventory)
    rows = [row for row in inventory["rows"] if row["archived"]]
    if len(rows) != 23:
        raise SystemExit(f"expected 23 archived calibration restarts, found {len(rows)}")
    roots = _existing_roots(args.ensemble_root)
    runner = Path(__file__).with_name("run_ensemble_backtest_case.py")
    status_path = args.ensemble_root / "calibration-backtest-queue-status.json"
    status: dict[str, Any] = {
        "expected": 23,
        "completed": [],
        "failed": [],
        "pending": [],
    }

    for index, row in enumerate(rows, start=1):
        key = (row["case"], int(row["window_index"]))
        root = roots.get(key, _new_root(args.ensemble_root, row))
        case_id = f"{row['case']}:w{int(row['window_index']):02d}"
        if (root / "backtest-metrics.json").exists() and (root / "integrity.json").exists():
            print(f"[{index}/23] {case_id}: already complete", flush=True)
            status["completed"].append({"case_id": case_id, "root": str(root)})
            continue
        cycle = datetime.fromisoformat(row["selected_cycle"]).strftime("%Y%m%d%H")
        command = [
            sys.executable,
            str(runner),
            "--case",
            row["case"],
            "--window",
            str(row["window_index"]),
            "--cycle",
            cycle,
            "--forecast-start",
            row["forecast_start"],
            "--output",
            str(root),
        ]
        print(f"[{index}/23] {case_id}: starting", flush=True)
        try:
            subprocess.run(command, check=True)
            status["completed"].append({"case_id": case_id, "root": str(root)})
        except subprocess.CalledProcessError as exc:
            failure = {"case_id": case_id, "root": str(root), "returncode": exc.returncode}
            status["failed"].append(failure)
            print(f"[{index}/23] {case_id}: failed, continuing", flush=True)
            if args.stop_on_failure:
                status["pending"] = [
                    f"{item['case']}:w{int(item['window_index']):02d}"
                    for item in rows[index:]
                ]
                status_path.write_text(
                    json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                raise
        status["pending"] = [
            f"{item['case']}:w{int(item['window_index']):02d}" for item in rows[index:]
        ]
        status_path.write_text(
            json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    status["pending"] = []
    status_path.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "completed": len(status["completed"]),
                "failed": len(status["failed"]),
                "pending": 0,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
