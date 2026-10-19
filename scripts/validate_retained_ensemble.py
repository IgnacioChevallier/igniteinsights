#!/usr/bin/env python3
"""Validate scientific integrity after reproducible ensemble inputs are removed."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

MEMBERS = ["c00", *(f"p{index:02d}" for index in range(1, 31))]
THRESHOLDS = [0.1, 0.5, 0.8]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _cycle_key(value: str) -> str:
    if len(value) == 10 and value.isdigit():
        return value
    return datetime.fromisoformat(value).strftime("%Y%m%d%H")


def validate(root: Path) -> dict[str, Any]:
    inventory_path = root / "archive-inventory.json"
    backtest_path = root / "backtest-metrics.json"
    inventory = _read(inventory_path)
    backtest = _read(backtest_path)
    manifests = {
        member: _read(root / "member-manifests" / f"{member}.json")
        for member in MEMBERS
    }
    weather_distinct = {
        key: len(
            {manifest["weather_sha256"][f"{key}.tif"] for manifest in manifests.values()}
        )
        == len(MEMBERS)
        for key in ("ws", "wd", "m1")
    }

    reference_grid = None
    geometries: set[str] = set()
    toa_rows = []
    for member in MEMBERS:
        metrics_path = root / "runs" / member / "run-metrics.json"
        metrics = _read(metrics_path)
        matches = sorted((root / "runs" / member).glob("time_of_arrival_*.tif"))
        row: dict[str, Any] = {
            "member": member,
            "status": metrics["status"],
            "toa_count": len(matches),
            "wall_seconds": metrics["wall_seconds"],
        }
        if len(matches) == 1:
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
            row |= {
                "same_grid": grid == reference_grid,
                "toa_sha256": _sha256(matches[0]),
                "geometry_sha256": geometry,
                "burned_cells": int(mask.sum()),
            }
        toa_rows.append(row)

    agreement_checks = {}
    for horizon in (12, 24):
        agreement_dir = root / "agreement" / f"h{horizon:02d}"
        contract = _read(agreement_dir / "ensemble_agreement.json")
        metadata = contract["metadata"]
        with rasterio.open(agreement_dir / "burn_agreement.tif") as src:
            values = np.unique(src.read(1))
        start = datetime.fromisoformat(metadata["forecast_start"])
        valid_at = datetime.fromisoformat(metadata["forecast_valid_at"])
        agreement_checks[str(horizon)] = {
            "valid_members": metadata["valid_members"],
            "expected_members": metadata["expected_members"],
            "failed_members": metadata["failed_members"],
            "weather_cycle": metadata["weather_cycle"],
            "forecast_start": metadata["forecast_start"],
            "forecast_valid_at": metadata["forecast_valid_at"],
            "horizon_hours": metadata["horizon_hours"],
            "timestamps_valid": valid_at == start + timedelta(hours=horizon),
            "thresholds": [band["value"] for band in contract["thresholds"]],
            "nonempty": bool(np.any(values > 0)),
            "nonuniform": len(values) > 1,
            "threshold_files_present": all(
                (agreement_dir / f"burn_agreement_ge_{threshold:02d}.tif").exists()
                and (agreement_dir / f"burn_agreement_ge_{threshold:02d}.geojson").exists()
                for threshold in (10, 50, 80)
            ),
        }

    source_manifests = sorted((root / "sources").glob("*/manifest.json"))
    source_gribs = sorted((root / "sources").glob("*/source/*.grib2"))
    source_tifs = [
        path
        for name in ("u10.tif", "v10.tif", "t2m.tif", "rh.tif")
        for path in (root / "sources").glob(f"*/{name}")
    ]
    input_entries = list((root / "inputs").glob("*"))
    attempts_path = root / "infrastructure-attempts.json"
    infrastructure_attempts = _read(attempts_path) if attempts_path.exists() else []
    cycle_available = datetime.fromisoformat(inventory["cycle_available_at"])
    forecast_start = datetime.fromisoformat(inventory["forecast_start"])
    all_runs_valid = len(toa_rows) == 31 and all(
        row["status"] == "success"
        and row["toa_count"] == 1
        and row.get("burned_cells", 0) > 0
        for row in toa_rows
    )
    agreements_valid = all(
        item["valid_members"] == 31
        and item["expected_members"] == 31
        and not item["failed_members"]
        and item["horizon_hours"] == horizon
        and _cycle_key(item["weather_cycle"]) == _cycle_key(inventory["cycle"])
        and item["forecast_start"] == inventory["forecast_start"]
        and item["timestamps_valid"]
        and item["thresholds"] == THRESHOLDS
        and item["nonempty"]
        and item["nonuniform"]
        and item["threshold_files_present"]
        for horizon, item in ((12, agreement_checks["12"]), (24, agreement_checks["24"]))
    )
    gates = {
        "archive_complete_31": inventory["complete"] is True
        and len(inventory["entries"]) == 310,
        "cycle_available_before_forecast": cycle_available <= forecast_start,
        "source_manifests_31": len(source_manifests) == 31,
        "source_ranges_retained": len(source_gribs) == 310,
        "all_members_successful": all_runs_valid,
        "all_toa_same_grid": all(row.get("same_grid") for row in toa_rows),
        "distinct_ws_wd_m1": all(weather_distinct.values()),
        "different_geometries_31": len(geometries) == 31,
        "agreement_valid_h12_h24": agreements_valid,
        "backtest_metrics_present": backtest_path.exists(),
        "thresholds_frozen": backtest["fixed_thresholds"] == THRESHOLDS,
        "reference_hashes_present": set(backtest["reference_hashes"])
        == {
            "ref_firms_horas.tif",
            "vistas_horas.tif",
            "cicatriz.tif",
            "excluido.tif",
        },
        "base_manifest_present": (root / "base-p24-modelo-v0-inputs/base-package.json").exists(),
        "reproducible_materializations_removed": not input_entries and not source_tifs,
    }
    return {
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
            "retained_source_manifests": len(source_manifests),
            "retained_source_ranges": len(source_gribs),
        },
        "infrastructure_attempts": infrastructure_attempts,
        "gates": gates,
        "integrity_passed": all(gates.values()),
        "generated_at": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_root", type=Path)
    args = parser.parse_args()
    report = validate(args.case_root)
    (args.case_root / "integrity.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        json.dumps(
            {"integrity_passed": report["integrity_passed"], "gates": report["gates"]},
            indent=2,
        )
    )
    if not report["integrity_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
