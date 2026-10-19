#!/usr/bin/env python3
"""Reproducible CLI for the GEFS + SMN WRF meteorological ensemble POC."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import resource
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform_bounds

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.elmfire.builder.namelist_writer import write_namelist  # noqa: E402
from app.elmfire.builder.weather_builder import derive_moisture, derive_wind  # noqa: E402
from app.elmfire.runner.client import ELMFIRERunnerClient  # noqa: E402
from app.elmfire.runner.schemas import SimulationRequest  # noqa: E402
from app.ensemble.agreement import aggregate_burn_agreement  # noqa: E402
from app.ensemble.sources import (  # noqa: E402
    GEFS_MEMBERS,
    download_gefs_member,
    download_smn_wrf,
    inspect_gefs_archive,
    selected_members,
    sha256,
)
from app.validation import pronostico  # noqa: E402
from app.validation.almacen import abrir as open_benchmark_object  # noqa: E402

BASE_STATIC_SOURCES = {
    "dem.tif": "dem.tif",
    "slp.tif": "slp.tif",
    "asp.tif": "asp.tif",
    "fbfm40.tif": "fbfm40_ccsbap2017.tif",
    "cc.tif": "cc.tif",
    "ch.tif": "ch.tif",
    "cbh.tif": "cbh.tif",
    "cbd.tif": "cbd.tif",
    "adj.tif": "adj.tif",
    "fuel_models.csv": "fuel_models.csv",
}


def cycle(value: str) -> datetime:
    try:
        result = datetime.strptime(value, "%Y%m%d%H").replace(tzinfo=UTC)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("cycle must be YYYYMMDDHH") from exc
    if result.hour not in (0, 6, 12, 18):
        raise argparse.ArgumentTypeError("cycle hour must be 00, 06, 12 or 18 UTC")
    return result


def timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timestamp must be ISO-8601") from exc
    if result.tzinfo is None or result.utcoffset() != UTC.utcoffset(result):
        raise argparse.ArgumentTypeError("timestamp must be timezone-aware UTC")
    return result


def bbox(values: list[str]) -> tuple[float, float, float, float]:
    west, south, east, north = map(float, values)
    if not (west < east and south < north):
        raise SystemExit("bbox must be WEST SOUTH EAST NORTH")
    return west, south, east, north


def cmd_gefs(args) -> None:
    members = selected_members(args.member_limit)
    inventory = (
        json.loads(args.inventory.read_text(encoding="utf-8")) if args.inventory else None
    )
    failures = {}
    def fetch(member: str) -> None:
        manifest_path = args.output / member / "manifest.json"
        if manifest_path.exists():
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                existing.get("cycle") == args.cycle.isoformat()
                and existing.get("forecast_start") == args.forecast_start.isoformat()
                and existing.get("source_hours") == (inventory or existing).get("source_hours")
            ):
                return
        download_gefs_member(
            args.cycle,
            member,
            bbox(args.bbox),
            args.horizon,
            args.output / member,
            forecast_start=args.forecast_start,
            inventory=inventory,
        )

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch, member): member for member in members}
        for future in as_completed(futures):
            member = futures[future]
            try:
                future.result()
            except Exception as exc:
                failures[member] = str(exc)
                if not args.keep_going:
                    for pending in futures:
                        pending.cancel()
                    raise
    summary = {
        "expected_members": members,
        "cycle": args.cycle.isoformat(),
        "cycle_available_at": (inventory or {}).get("cycle_available_at"),
        "forecast_start": args.forecast_start.isoformat(),
        "failures": failures,
    }
    (args.output / "download-summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    if failures:
        raise SystemExit(f"missing GEFS members; no substitution: {sorted(failures)}")


def cmd_inventory_gefs(args) -> None:
    inventory = inspect_gefs_archive(
        args.cycle,
        args.forecast_start,
        args.horizon,
        selected_members(args.member_limit),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    print(json.dumps({key: inventory[key] for key in (
        "cycle", "cycle_available_at", "forecast_start", "offset_hours",
        "source_hours", "complete",
    )}, indent=2))


def cmd_inventory_restarts(args) -> None:
    """Probe archived GEFS coverage for every non-test P-24 calibration restart."""
    partition = json.loads(Path("benchmarks/particion.json").read_text(encoding="utf-8"))
    calibration = {case_id for cases in partition["calibracion"].values() for case_id in cases}
    rows = []
    for case_path in sorted(Path("benchmarks/casos").glob("*/pronostico-v6.json")):
        case = json.loads(case_path.read_text(encoding="utf-8"))
        package_path = case_path.with_suffix(".paquete.json")
        package = json.loads(package_path.read_text(encoding="utf-8"))
        base_case = package["origen"]["base"]
        if base_case not in calibration:
            continue
        for window_index, window in enumerate(case["ventanas"][1:], start=1):
            start = datetime.fromisoformat(window["t0"]) + timedelta(
                seconds=float(window.get("tstart_s", 0))
            )
            candidate = start.replace(
                hour=start.hour // 6 * 6, minute=0, second=0, microsecond=0
            )
            attempts = []
            selected = None
            for _ in range(2):
                try:
                    probe = inspect_gefs_archive(
                        candidate, start, args.horizon, ["c00", "p30"]
                    )
                    available_at = datetime.fromisoformat(probe["cycle_available_at"])
                    attempts.append(
                        {
                            "cycle": candidate.isoformat(),
                            "cycle_available_at": available_at.isoformat(),
                            "status": "available" if available_at <= start else "late",
                        }
                    )
                    if available_at <= start:
                        selected = probe
                        break
                except Exception as exc:
                    attempts.append(
                        {"cycle": candidate.isoformat(), "status": "missing", "error": str(exc)}
                    )
                candidate -= timedelta(hours=6)
            rows.append(
                {
                    "case": f"{case_path.parent.name}/pronostico-v6",
                    "base_case": base_case,
                    "window_index": window_index,
                    "forecast_start": start.isoformat(),
                    "archived": selected is not None,
                    "selected_cycle": selected["cycle"] if selected else None,
                    "cycle_available_at": (
                        selected["cycle_available_at"] if selected else None
                    ),
                    "source_hours": selected["source_hours"] if selected else None,
                    "attempts": attempts,
                }
            )
    report = {
        "schema_version": 1,
        "probe_scope": (
            "c00 and p30, every required source hour and all four required fields; "
            "a future run must still gate all 31 members"
        ),
        "horizon_hours": args.horizon,
        "rows": rows,
        "available_count": sum(row["archived"] for row in rows),
        "total_count": len(rows),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "available_count": report["available_count"],
        "total_count": report["total_count"],
    }, indent=2))


def cmd_prepare(args) -> None:
    required = [args.source / f"{name}.tif" for name in ("u10", "v10", "t2m", "rh")]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"missing standardized weather inputs: {missing}")
    with rasterio.open(required[0]) as weather, rasterio.open(args.reference) as reference:
        reference_bounds = transform_bounds(reference.crs, weather.crs, *reference.bounds)
        wb = weather.bounds
        if not (
            wb.left <= reference_bounds[0]
            and wb.bottom <= reference_bounds[1]
            and wb.right >= reference_bounds[2]
            and wb.top >= reference_bounds[3]
        ):
            raise SystemExit(
                "weather AOI does not cover the frozen reference grid; re-download with "
                f"a margin. weather={tuple(weather.bounds)}, reference={reference_bounds}"
            )
    args.output.mkdir(parents=True, exist_ok=True)
    derive_wind(required[0], required[1], args.reference, args.output)
    derive_moisture(required[2], required[3], args.reference, args.output)


def cmd_build_base(args) -> None:
    """Materialize one observed P-24 restart from the immutable v6 benchmark store."""
    if args.window < 1:
        raise SystemExit("window must be >= 1: window 0 is ignition, not an observed P-24 restart")
    case_parts = args.case.split("/", 1)
    if len(case_parts) != 2:
        raise SystemExit("case must be INCENDIO/PROTOCOLO")
    cases_root = Path("benchmarks/casos")
    case_path = cases_root / case_parts[0] / f"{case_parts[1]}.json"
    package_path = cases_root / case_parts[0] / f"{case_parts[1]}.paquete.json"
    partition_path = Path("benchmarks/particion.json")
    case = json.loads(case_path.read_text(encoding="utf-8"))
    package = json.loads(package_path.read_text(encoding="utf-8"))
    partition = json.loads(partition_path.read_text(encoding="utf-8"))
    calibration = {case_id for cases in partition["calibracion"].values() for case_id in cases}
    test = {case_id for cases in partition["prueba"].values() for case_id in cases}
    base_case = package["origen"]["base"]
    if base_case in test or base_case not in calibration:
        raise SystemExit(
            f"refusing decision case {base_case}: it must be in calibration and outside test"
        )
    if case.get("empaquetado", {}).get("tipo") != "pronostico":
        raise SystemExit(f"{args.case} is not a P-24 forecast package")
    if args.window >= len(case["ventanas"]):
        raise SystemExit(f"window {args.window} does not exist in {args.case}")
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing base package {args.output}")

    files = {target: package["comunes"][source] for target, source in BASE_STATIC_SOURCES.items()}
    files["phi.tif"] = package["ventanas"][args.window]["phi.tif"]
    args.output.mkdir(parents=True)
    for target, object_hash in files.items():
        (args.output / target).hardlink_to(open_benchmark_object(object_hash))

    window = case["ventanas"][args.window]
    window_anchor = datetime.fromisoformat(window["t0"])
    perimeter_at = window_anchor + timedelta(seconds=float(window.get("tstart_s", 0)))
    with rasterio.open(args.output / "dem.tif") as dem:
        grid = {
            "crs": str(dem.crs),
            "shape": list(dem.shape),
            "transform": list(dem.transform)[:6],
            "bounds": list(dem.bounds),
            "resolution_m": abs(dem.transform.a),
        }
    manifest = {
        "schema_version": 1,
        "purpose": args.purpose,
        "model_snapshot": "modelo-v0",
        "recipe": "lw-100-001",
        "preparation_version": "v6",
        "case": args.case,
        "base_case": base_case,
        "benchmark_split": "calibration",
        "window_index": args.window,
        "window_anchor": window_anchor.isoformat(),
        "perimeter_at": perimeter_at.isoformat(),
        "perimeter_source": case["referencias"]["firms"],
        "source_preparation": package["origen"]["preparacion"],
        "source_package": str(package_path),
        "source_package_sha256": sha256(package_path),
        "partition_sha256": sha256(partition_path),
        "grid": grid,
        "files": {
            target: {
                "sha256": object_hash,
                "source_name": BASE_STATIC_SOURCES.get(target, "phi.tif"),
            }
            for target, object_hash in files.items()
        },
        "evaluation_references": {
            name: object_hash
            for name, object_hash in (
                {
                    key: package["ventanas"][args.window][key]
                    for key in ("ref_firms_horas.tif", "vistas_horas.tif")
                }
                | {
                    key: package["comunes"][key]
                    for key in ("cicatriz.tif", "excluido.tif")
                }
            ).items()
        },
        "created_at": datetime.now(UTC).isoformat(),
    }
    (args.output / "base-package.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


def cmd_materialize(args) -> None:
    """Clone frozen inputs by hardlink, then replace meteorology copy-on-write."""
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing inputs directory {args.output}")
    static_names = (
        "dem.tif",
        "slp.tif",
        "asp.tif",
        "fbfm40.tif",
        "cc.tif",
        "ch.tif",
        "cbh.tif",
        "cbd.tif",
        "adj.tif",
        "phi.tif",
        "fuel_models.csv",
    )
    missing = [name for name in static_names if not (args.frozen_inputs / name).exists()]
    if missing:
        raise SystemExit(
            f"frozen inputs must be a complete P-24 ELMFIRE input set; missing {missing}"
        )
    shutil.copytree(args.frozen_inputs, args.output, copy_function=os.link)
    for name in ("ws", "wd", "m1", "m10", "m100"):
        (args.output / f"{name}.tif").unlink(missing_ok=True)
    args.source, args.reference = args.source, args.output / "dem.tif"
    cmd_prepare(args)
    manifest = {
        "model_snapshot": "modelo-v0",
        "recipe": "lw-100-001",
        "elmfire_version": "2025.0212",
        "changed_input": "meteorology only",
        "frozen_inputs": str(args.frozen_inputs),
        "static_sha256": {name: sha256(args.output / name) for name in static_names},
        "weather_sha256": {
            f"{name}.tif": sha256(args.output / f"{name}.tif")
            for name in ("ws", "wd", "m1", "m10", "m100")
        },
    }
    (args.output / "ensemble-member.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def cmd_run(args) -> None:
    args.outputs.mkdir(parents=True, exist_ok=True)
    namelist = args.outputs / "elmfire.data"
    write_namelist(args.inputs.resolve(), args.outputs.resolve(), args.horizon, namelist)
    local_data = Path("data").resolve()
    try:
        runner_inputs = args.runner_data_root / args.inputs.resolve().relative_to(local_data)
        runner_outputs = args.runner_data_root / args.outputs.resolve().relative_to(local_data)
    except ValueError as exc:
        raise SystemExit("inputs and outputs must live below ./data for the shared runner") from exc
    namelist.write_text(
        namelist.read_text(encoding="utf-8")
        .replace(str(args.inputs.resolve()), str(runner_inputs))
        .replace(str(args.outputs.resolve()), str(runner_outputs)),
        encoding="utf-8",
    )
    request = SimulationRequest(
        elmfire_data_path=str(runner_outputs / namelist.name),
        inputs_dir=str(runner_inputs),
        outputs_dir=str(runner_outputs),
        simulation_hours=args.horizon,
    )
    started = time.perf_counter()
    before = resource.getrusage(resource.RUSAGE_SELF)
    error = None
    result = None
    try:
        result = asyncio.run(
            ELMFIRERunnerClient().run_simulation(
                request,
                local_inputs_dir=str(args.inputs.resolve()),
                local_outputs_dir=str(args.outputs.resolve()),
            )
        )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        after = resource.getrusage(resource.RUSAGE_SELF)
        metrics = {
            "model_snapshot": "modelo-v0",
            "recipe": "lw-100-001",
            "elmfire_version": "2025.0212",
            "status": "success" if result is not None else "failed",
            "wall_seconds": time.perf_counter() - started,
            "client_cpu_user_seconds": after.ru_utime - before.ru_utime,
            "client_cpu_system_seconds": after.ru_stime - before.ru_stime,
            "client_max_rss": after.ru_maxrss,
            "output_bytes": sum(
                path.stat().st_size for path in args.outputs.rglob("*") if path.is_file()
            ),
            "runner_result": result.model_dump() if result is not None else None,
            "error": error,
            "note": "CPU/RSS are client-side; remote runner resource metrics are not exposed.",
        }
        (args.outputs / "run-metrics.json").write_text(
            json.dumps(metrics, indent=2), encoding="utf-8"
        )
    if error is not None:
        raise RuntimeError(error)


def cmd_aggregate(args) -> None:
    expected = selected_members(args.expected_members)
    paths = {}
    failures = {}
    for member in expected:
        matches = sorted((args.runs / member).glob(args.toa_pattern))
        if matches:
            paths[member] = matches[-1]
        else:
            failures[member] = f"no {args.toa_pattern} in {args.runs / member}"
    metadata = aggregate_burn_agreement(
        paths,
        args.output,
        expected_members=expected,
        min_valid_members=args.min_valid_members,
        cycle=args.cycle_label,
        forecast_start=args.forecast_start.isoformat(),
        horizon_hours=args.horizon,
        failed_members=failures,
    )
    print(json.dumps(metadata, indent=2, ensure_ascii=False))


def _directory_bytes(path: Path, names: set[str] | None = None) -> int:
    return sum(
        item.stat().st_size
        for item in path.rglob("*")
        if item.is_file() and (names is None or item.name in names)
    )


def cmd_evaluate_smoke(args) -> None:
    members = selected_members(args.expected_members)
    weather_names = {"ws.tif", "wd.tif", "m1.tif", "m10.tif", "m100.tif"}
    weather_hashes = {
        member: {
            name.removesuffix(".tif"): sha256(args.inputs / member / name)
            for name in sorted(weather_names)
        }
        for member in members
    }
    distinct_weather = {
        name: len({weather_hashes[member][name] for member in members}) == len(members)
        for name in ("ws", "wd", "m1")
    }

    reference_grid = None
    masks: dict[str, np.ndarray] = {}
    toa_rows = []
    for member in members:
        matches = sorted((args.runs / member).glob(args.toa_pattern))
        metrics_path = args.runs / member / "run-metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        if not matches:
            toa_rows.append({"member": member, "status": metrics["status"], "toa": None})
            continue
        toa_path = matches[-1]
        with rasterio.open(toa_path) as src:
            grid = {
                "shape": list(src.shape),
                "crs": str(src.crs),
                "transform": list(src.transform)[:6],
                "nodata": src.nodata,
            }
            reference_grid = reference_grid or grid
            same_grid = grid == reference_grid
            data = src.read(1)
            mask = np.isfinite(data) & (data > 0)
            masks[member] = mask
            cell_area_ha = abs(src.transform.a * src.transform.e) / 10_000
            toa_rows.append(
                {
                    "member": member,
                    "status": metrics["status"],
                    "same_grid": same_grid,
                    "toa_path": str(toa_path),
                    "toa_sha256": sha256(toa_path),
                    "geometry_sha256": hashlib.sha256(np.packbits(mask).tobytes()).hexdigest(),
                    "burned_cells": int(mask.sum()),
                    "burned_area_ha": float(mask.sum() * cell_area_ha),
                    "toa_min_seconds": float(data[mask].min()) if mask.any() else None,
                    "toa_max_seconds": float(data[mask].max()) if mask.any() else None,
                    "wall_seconds": metrics["wall_seconds"],
                    "output_bytes": _directory_bytes(args.runs / member),
                    "error": metrics["error"],
                }
            )

    pairwise = []
    for index, left in enumerate(members):
        for right in members[index + 1 :]:
            if left not in masks or right not in masks:
                continue
            intersection = int((masks[left] & masks[right]).sum())
            union = int((masks[left] | masks[right]).sum())
            pairwise.append(
                {
                    "members": [left, right],
                    "xor_cells": int((masks[left] ^ masks[right]).sum()),
                    "iou": intersection / union if union else None,
                }
            )

    with rasterio.open(args.agreement / "burn_agreement.tif") as src:
        agreement = src.read(1)
        agreement_cell_area_ha = abs(src.transform.a * src.transform.e) / 10_000
    agreement_values, agreement_counts = np.unique(agreement, return_counts=True)
    positive_values = agreement_values[agreement_values > 0]
    agreement_summary = {
        "values": [float(value) for value in agreement_values],
        "cell_counts": [int(count) for count in agreement_counts],
        "nonempty": bool(np.any(agreement > 0)),
        "nonuniform_positive": len(positive_values) > 1,
    }

    control = masks.get("c00")
    threshold_rows = []
    for threshold in (10, 50, 80):
        with rasterio.open(args.agreement / f"burn_agreement_ge_{threshold:02d}.tif") as src:
            threshold_mask = src.read(1).astype(bool)
        intersection = int((control & threshold_mask).sum()) if control is not None else 0
        union = int((control | threshold_mask).sum()) if control is not None else 0
        threshold_rows.append(
            {
                "threshold": threshold / 100,
                "area_ha": float(threshold_mask.sum() * agreement_cell_area_ha),
                "control_intersection_ha": float(intersection * agreement_cell_area_ha),
                "control_iou": intersection / union if union else None,
                "control_only_ha": float((control & ~threshold_mask).sum() * agreement_cell_area_ha)
                if control is not None
                else None,
                "threshold_only_ha": float(
                    (~control & threshold_mask).sum() * agreement_cell_area_ha
                )
                if control is not None
                else None,
            }
        )

    successful = [row for row in toa_rows if row.get("status") == "success" and row.get("toa_path")]
    wall_total = sum(row["wall_seconds"] for row in successful)
    member_weather_bytes = [
        _directory_bytes(args.inputs / member, weather_names) for member in members
    ]
    source_bytes = [_directory_bytes(args.sources / member) for member in members]
    output_bytes = [row["output_bytes"] for row in successful]
    scale_count = args.scale_members
    estimate = {
        "members": scale_count,
        "serial_solver_wall_seconds": wall_total / len(successful) * scale_count,
        "standardized_source_bytes": sum(source_bytes) / len(source_bytes) * scale_count,
        "elmfire_weather_input_bytes": sum(member_weather_bytes)
        / len(member_weather_bytes)
        * scale_count,
        "solver_output_bytes": sum(output_bytes) / len(output_bytes) * scale_count,
        "method": (
            f"observed totals for {scale_count} completed members"
            if scale_count == len(successful) == len(members)
            else f"linear extrapolation from {len(successful)} completed members; excludes "
            "download and preparation wall time"
        ),
    }
    gates = {
        "all_members_successful": len(successful) == len(members),
        "distinct_ws_wd_m1": all(distinct_weather.values()),
        "all_toa_nonempty_same_grid": len(masks) == len(members)
        and all(row.get("same_grid") and row.get("burned_cells", 0) > 0 for row in toa_rows),
        "different_geometries": len({row.get("geometry_sha256") for row in toa_rows}) > 1,
        "agreement_nonempty_nonuniform": agreement_summary["nonempty"]
        and agreement_summary["nonuniform_positive"],
    }
    report = {
        "schema_version": 1,
        "classification": args.classification,
        "members": members,
        "weather_hashes": weather_hashes,
        "distinct_weather": distinct_weather,
        "reference_grid": reference_grid,
        "toa": toa_rows,
        "pairwise_geometry": pairwise,
        "agreement": agreement_summary,
        "control_comparison": threshold_rows,
        "failures": {
            row["member"]: row.get("error")
            for row in toa_rows
            if row.get("status") != "success" or not row.get("toa_path")
        },
        "scale_estimate": estimate,
        "gates": gates,
        "smoke_passed": all(gates.values()),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


def cmd_evaluate_backtest(args) -> None:
    """Score fixed ensemble products as new growth under the existing P-24 protocol."""
    base = json.loads((args.base_inputs / "base-package.json").read_text(encoding="utf-8"))
    package = json.loads(Path(base["source_package"]).read_text(encoding="utf-8"))
    window = package["ventanas"][base["window_index"]]
    phi = rasterio.open(args.base_inputs / "phi.tif").read(1)
    seed = phi < 0
    cicatriz = (
        rasterio.open(open_benchmark_object(package["comunes"]["cicatriz.tif"]))
        .read(1)
        .astype(bool)
    )
    excluido = (
        rasterio.open(open_benchmark_object(package["comunes"]["excluido.tif"]))
        .read(1)
        .astype(bool)
    )
    vistas = rasterio.open(open_benchmark_object(window["vistas_horas.tif"])).read(1)
    detecciones = rasterio.open(open_benchmark_object(window["ref_firms_horas.tif"])).read(1)
    with rasterio.open(args.base_inputs / "dem.tif") as grid:
        cell_area_ha = abs(grid.transform.a * grid.transform.e) / 10_000

    control_matches = sorted((args.runs / "c00").glob(args.toa_pattern))
    if not control_matches:
        raise SystemExit("control c00 has no TOA output")
    with rasterio.open(control_matches[-1]) as src:
        control_toa = src.read(1)

    horizons = {}
    for horizon in (12, 24):
        agreement_dir = args.agreement_root / f"h{horizon:02d}"
        predictions = {"c00": (control_toa > 0) & (control_toa <= horizon * 3600)}
        for threshold in (10, 50, 80):
            with rasterio.open(agreement_dir / f"burn_agreement_ge_{threshold:02d}.tif") as src:
                predictions[f"agreement_ge_{threshold:02d}"] = src.read(1).astype(bool)
        scored = {
            name: pronostico.puntuar(
                prediction,
                seed,
                cicatriz,
                excluido,
                vistas,
                detecciones,
                horizon,
                cell_area_ha,
            )
            for name, prediction in predictions.items()
        }
        low = scored["agreement_ge_10"]
        horizons[str(horizon)] = {
            "products": scored,
            "observation_coverage_by_ge_10": low["cicatriz"]["recall"],
            "new_detection_coverage_by_ge_10": low["firms"]["recall"],
            "ge_10_additional_area_ha": low["cicatriz"]["fp_ha"],
            "ge_10_predicted_new_growth_ha": low["cicatriz"]["predicho_ha"],
            "ge_80_interpretation": "zona de alto acuerdo; no probabilidad calibrada",
        }
    report = {
        "schema_version": 1,
        "classification": "contemporary calibration backtest; scoreable",
        "case": base["case"],
        "base_case": base["base_case"],
        "window_index": base["window_index"],
        "forecast_start": base["perimeter_at"],
        "fixed_thresholds": [0.10, 0.50, 0.80],
        "threshold_selection": "declared before scoring; no post-result selection",
        "reference_hashes": base["evaluation_references"],
        "horizons": horizons,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--cycle", required=True, type=cycle)
    common.add_argument(
        "--bbox", nargs=4, required=True, metavar=("WEST", "SOUTH", "EAST", "NORTH")
    )
    common.add_argument("--horizon", type=int, default=24)
    common.add_argument("--output", type=Path, required=True)

    gefs = sub.add_parser("download-gefs", parents=[common])
    gefs.add_argument("--forecast-start", required=True, type=timestamp)
    gefs.add_argument("--inventory", type=Path)
    gefs.add_argument("--workers", type=int, default=4)
    gefs.add_argument("--member-limit", type=int, default=len(GEFS_MEMBERS))
    gefs.add_argument("--keep-going", action="store_true")
    gefs.set_defaults(func=cmd_gefs)

    inventory = sub.add_parser("inventory-gefs")
    inventory.add_argument("--cycle", required=True, type=cycle)
    inventory.add_argument("--forecast-start", required=True, type=timestamp)
    inventory.add_argument("--horizon", type=int, default=24)
    inventory.add_argument("--member-limit", type=int, default=len(GEFS_MEMBERS))
    inventory.add_argument("--output", type=Path, required=True)
    inventory.set_defaults(func=cmd_inventory_gefs)

    restart_inventory = sub.add_parser("inventory-restarts")
    restart_inventory.add_argument("--horizon", type=int, default=24)
    restart_inventory.add_argument("--output", type=Path, required=True)
    restart_inventory.set_defaults(func=cmd_inventory_restarts)

    smn = sub.add_parser("download-smn", parents=[common])
    smn.set_defaults(func=lambda a: download_smn_wrf(a.cycle, bbox(a.bbox), a.horizon, a.output))

    build_base = sub.add_parser("build-base")
    build_base.add_argument("--case", required=True)
    build_base.add_argument("--window", type=int, required=True)
    build_base.add_argument("--output", type=Path, required=True)
    build_base.add_argument(
        "--purpose", default="ensemble infrastructure smoke; not scoreable"
    )
    build_base.set_defaults(func=cmd_build_base)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--source", type=Path, required=True)
    prepare.add_argument("--reference", type=Path, required=True, help="frozen preparation dem.tif")
    prepare.add_argument("--output", type=Path, required=True)
    prepare.set_defaults(func=cmd_prepare)

    materialize = sub.add_parser("materialize")
    materialize.add_argument("--source", type=Path, required=True)
    materialize.add_argument("--frozen-inputs", type=Path, required=True)
    materialize.add_argument("--output", type=Path, required=True)
    materialize.set_defaults(func=cmd_materialize)

    run = sub.add_parser("run")
    run.add_argument("--inputs", type=Path, required=True)
    run.add_argument("--outputs", type=Path, required=True)
    run.add_argument("--horizon", type=int, default=24)
    run.add_argument("--runner-data-root", type=Path, default=Path("/app/data"))
    run.set_defaults(func=cmd_run)

    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("--runs", type=Path, required=True)
    aggregate.add_argument("--toa-pattern", default="time_of_arrival_*.tif")
    aggregate.add_argument("--expected-members", type=int, default=31)
    aggregate.add_argument("--min-valid-members", type=int, default=24)
    aggregate.add_argument("--cycle-label", required=True)
    aggregate.add_argument("--forecast-start", required=True, type=timestamp)
    aggregate.add_argument("--horizon", type=int, default=24)
    aggregate.add_argument("--output", type=Path, required=True)
    aggregate.set_defaults(func=cmd_aggregate)

    evaluate = sub.add_parser("evaluate-smoke")
    evaluate.add_argument("--sources", type=Path, required=True)
    evaluate.add_argument("--inputs", type=Path, required=True)
    evaluate.add_argument("--runs", type=Path, required=True)
    evaluate.add_argument("--agreement", type=Path, required=True)
    evaluate.add_argument("--toa-pattern", default="time_of_arrival_*.tif")
    evaluate.add_argument("--expected-members", type=int, default=5)
    evaluate.add_argument("--scale-members", type=int, default=31)
    evaluate.add_argument("--classification", default="infrastructure smoke; not scoreable")
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.set_defaults(func=cmd_evaluate_smoke)

    backtest = sub.add_parser("evaluate-backtest")
    backtest.add_argument("--base-inputs", type=Path, required=True)
    backtest.add_argument("--runs", type=Path, required=True)
    backtest.add_argument("--agreement-root", type=Path, required=True)
    backtest.add_argument("--toa-pattern", default="time_of_arrival_*.tif")
    backtest.add_argument("--output", type=Path, required=True)
    backtest.set_defaults(func=cmd_evaluate_backtest)
    return root


if __name__ == "__main__":
    args = parser().parse_args()
    args.func(args)
