#!/usr/bin/env python3
"""Validate a retained GEFS ensemble after reproducible materializations were removed."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio


MEMBERS = ["c00", *(f"p{index:02d}" for index in range(1, 31))]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_root", type=Path)
    args = parser.parse_args()
    root = args.case_root

    inventory = json.loads((root / "archive-inventory.json").read_text())
    backtest = json.loads((root / "backtest-metrics.json").read_text())
    manifests = {
        member: json.loads((root / "member-manifests" / f"{member}.json").read_text())
        for member in MEMBERS
    }
    weather_distinct = {
        key: len({manifest["weather_sha256"][f"{key}.tif"] for manifest in manifests.values()})
        == len(MEMBERS)
        for key in ("ws", "wd", "m1")
    }

    reference_grid = None
    geometries: set[str] = set()
    toa_rows = []
    for member in MEMBERS:
        metrics = json.loads((root / "runs" / member / "run-metrics.json").read_text())
        matches = sorted((root / "runs" / member).glob("time_of_arrival_*.tif"))
        if len(matches) != 1:
            toa_rows.append({"member": member, "status": metrics["status"], "toa_count": len(matches)})
            continue
        with rasterio.open(matches[0]) as src:
            data = src.read(1)
            mask = np.isfinite(data) & (data > 0)
            grid = {
                "shape": list(src.shape),
                "crs": str(src.crs),
                "transform": list(src.transform)[:6],
                "nodata": src.nodata,
            }
        reference_grid = reference_grid or grid
        geometry = hashlib.sha256(np.packbits(mask).tobytes()).hexdigest()
        geometries.add(geometry)
        toa_rows.append(
            {
                "member": member,
                "status": metrics["status"],
                "same_grid": grid == reference_grid,
                "toa_sha256": sha256(matches[0]),
                "geometry_sha256": geometry,
                "burned_cells": int(mask.sum()),
                "wall_seconds": metrics["wall_seconds"],
            }
        )

    agreement_checks = {}
    for horizon in (12, 24):
        agreement_dir = root / "agreement" / f"h{horizon:02d}"
        metadata = json.loads((agreement_dir / "ensemble_agreement.json").read_text())
        contract = metadata["metadata"]
        with rasterio.open(agreement_dir / "burn_agreement.tif") as src:
            values = np.unique(src.read(1))
        agreement_checks[str(horizon)] = {
            "effective_denominator": contract["valid_members"],
            "failed_members": contract["failed_members"],
            "forecast_start": contract["forecast_start"],
            "forecast_valid_at": contract["forecast_valid_at"],
            "nonempty": bool(np.any(values > 0)),
            "nonuniform_positive": int((values > 0).sum()) > 1,
            "threshold_files_present": all(
                (agreement_dir / f"burn_agreement_ge_{threshold:02d}.tif").exists()
                for threshold in (10, 50, 80)
            ),
        }

    source_tifs = [
        str(path.relative_to(root))
        for name in ("u10.tif", "v10.tif", "t2m.tif", "rh.tif")
        for path in (root / "sources").glob(f"*/{name}")
    ]
    input_entries = list((root / "inputs").glob("*"))
    attempts_path = root / "infrastructure-attempts.json"
    infrastructure_attempts = (
        json.loads(attempts_path.read_text()) if attempts_path.exists() else []
    )
    gates = {
        "archive_complete_31": inventory["complete"] is True,
        "cycle_available_before_forecast": datetime.fromisoformat(inventory["cycle_available_at"])
        <= datetime.fromisoformat(inventory["forecast_start"]),
        "all_members_successful": len(toa_rows) == 31
        and all(row.get("status") == "success" and row.get("burned_cells", 0) > 0 for row in toa_rows),
        "all_toa_same_grid": all(row.get("same_grid") for row in toa_rows),
        "distinct_ws_wd_m1": all(weather_distinct.values()),
        "different_geometries": len(geometries) > 1,
        "agreement_valid_h12_h24": all(
            item["effective_denominator"] == 31
            and not item["failed_members"]
            and item["nonempty"]
            and item["nonuniform_positive"]
            and item["threshold_files_present"]
            for item in agreement_checks.values()
        ),
        "thresholds_frozen": backtest["fixed_thresholds"] == [0.1, 0.5, 0.8],
        "reproducible_materializations_removed": not input_entries and not source_tifs,
    }
    report = {
        "schema_version": 1,
        "case": backtest["case"],
        "window_index": backtest["window_index"],
        "forecast_start": backtest["forecast_start"],
        "weather_distinct": weather_distinct,
        "reference_grid": reference_grid,
        "distinct_geometry_count": len(geometries),
        "toa": toa_rows,
        "agreement": agreement_checks,
        "retention": {
            "removed_inputs": not input_entries,
            "removed_standardized_source_tifs": not source_tifs,
            "retained_member_manifests": len(manifests),
        },
        "infrastructure_attempts": infrastructure_attempts,
        "gates": gates,
        "integrity_passed": all(gates.values()),
    }
    (root / "integrity.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"integrity_passed": report["integrity_passed"], "gates": gates}, indent=2))


if __name__ == "__main__":
    main()
