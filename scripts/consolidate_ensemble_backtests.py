#!/usr/bin/env python3
"""Consolidate contemporary GEFS calibration backtests without tuning thresholds."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PRODUCTS = ("c00", "agreement_ge_10", "agreement_ge_50", "agreement_ge_80")
METRICS = ("iou", "dice", "recall", "precision", "sesgo_area")
EXPECTED_THRESHOLDS = [0.1, 0.5, 0.8]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _distribution(values: list[float]) -> dict[str, float | int | None]:
    return {
        "n": len(values),
        "median": statistics.median(values) if values else None,
        "q1": _quantile(values, 0.25),
        "q3": _quantile(values, 0.75),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def _delta(value: float | None, control: float | None) -> float | None:
    if value is None or control is None:
        return None
    return value - control


def _numeric(items: list[dict[str, Any]], field: str) -> list[float]:
    return [float(item[field]) for item in items if item.get(field) is not None]


def _fire_id(case: str) -> str:
    return case.split("/", 1)[0]


def _agreement_contract(case_root: Path, horizon: int) -> tuple[Path, dict[str, Any]]:
    path = case_root / "agreement" / f"h{horizon:02d}" / "ensemble_agreement.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def _directory_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _case_rows(metrics_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    case_root = metrics_path.parent
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    integrity_path = case_root / "integrity.json"
    if not integrity_path.exists():
        raise ValueError(f"missing integrity.json beside {metrics_path}")
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    if metrics.get("fixed_thresholds") != EXPECTED_THRESHOLDS:
        raise ValueError(f"thresholds changed in {metrics_path}")

    contracts: dict[str, dict[str, Any]] = {}
    contract_paths: dict[str, Path] = {}
    for horizon in (12, 24):
        contract_path, contract = _agreement_contract(case_root, horizon)
        contracts[str(horizon)] = contract
        contract_paths[str(horizon)] = contract_path

    metadata_24 = contracts["24"]["metadata"]
    run_metrics = [
        json.loads((case_root / "runs" / member / "run-metrics.json").read_text())
        for member in ("c00", *(f"p{index:02d}" for index in range(1, 31)))
    ]
    wall_seconds = [float(item["wall_seconds"]) for item in run_metrics]
    case_record = {
        "case_id": f"{_fire_id(metrics['case'])}-w{int(metrics['window_index']):02d}",
        "case": metrics["case"],
        "base_case": metrics["base_case"],
        "fire": _fire_id(metrics["case"]),
        "window_index": metrics["window_index"],
        "forecast_start": metrics["forecast_start"],
        "weather_cycle": metadata_24["weather_cycle"],
        "valid_members": metadata_24["valid_members"],
        "expected_members": metadata_24["expected_members"],
        "integrity_passed": integrity.get("integrity_passed", integrity.get("smoke_passed"))
        is True,
        "integrity_gates": integrity.get("gates", {}),
        "operational_observations": {
            "serial_client_wall_seconds": sum(wall_seconds),
            "member_wall_seconds_median": statistics.median(wall_seconds),
            "member_wall_seconds_min": min(wall_seconds),
            "member_wall_seconds_max": max(wall_seconds),
            "recorded_solver_output_bytes": sum(
                int(item.get("output_bytes") or 0) for item in run_metrics
            ),
            "retained_case_bytes": _directory_bytes(case_root),
            "retained_source_range_bytes": _directory_bytes(case_root / "sources"),
            "retained_toa_bytes": sum(
                path.stat().st_size for path in (case_root / "runs").glob("*/time_of_arrival_*.tif")
            ),
            "infrastructure_attempt_count": len(integrity.get("infrastructure_attempts", [])),
            "remote_solver_cpu_rss_available": False,
        },
        "artifacts": {
            "root": str(case_root),
            "backtest_metrics": str(metrics_path),
            "backtest_metrics_sha256": _sha256(metrics_path),
            "integrity": str(integrity_path),
            "integrity_sha256": _sha256(integrity_path),
            "agreement_h12": str(contract_paths["12"]),
            "agreement_h24": str(contract_paths["24"]),
        },
    }

    rows: list[dict[str, Any]] = []
    for horizon in (12, 24):
        horizon_data = metrics["horizons"][str(horizon)]
        products = horizon_data["products"]
        control = products["c00"]["cicatriz"]
        for product in PRODUCTS:
            scored = products[product]
            scar = scored["cicatriz"]
            firms = scored["firms"]
            row: dict[str, Any] = {
                "case_id": case_record["case_id"],
                "case": metrics["case"],
                "base_case": metrics["base_case"],
                "fire": case_record["fire"],
                "window_index": metrics["window_index"],
                "forecast_start": metrics["forecast_start"],
                "weather_cycle": metadata_24["weather_cycle"],
                "horizon_hours": horizon,
                "product": product,
                "threshold": None if product == "c00" else int(product[-2:]) / 100,
                "false_positive_ha": scar["fp_ha"],
                "false_negative_ha": scar["fn_ha"],
                "predicted_area_ha": scar["predicho_ha"],
                "observed_area_ha": scar["observado_ha"],
                "scar_coverage": scar["recall"],
                "new_firms_coverage": firms["recall"],
                "delta_new_firms_coverage": _delta(
                    firms["recall"], products["c00"]["firms"]["recall"]
                ),
                "delta_false_positive_ha": _delta(scar["fp_ha"], control["fp_ha"]),
                "delta_predicted_area_ha": _delta(scar["predicho_ha"], control["predicho_ha"]),
                "integrity_passed": case_record["integrity_passed"],
            }
            for metric in METRICS:
                row[metric] = scar[metric]
                row[f"delta_{metric}"] = _delta(scar[metric], control[metric])
            row["area_bias_improved"] = (
                abs(scar["sesgo_area"] - 1) < abs(control["sesgo_area"] - 1)
                if scar["sesgo_area"] is not None and control["sesgo_area"] is not None
                else None
            )
            rows.append(row)
    return case_record, rows


def _summaries(rows: list[dict[str, Any]], group_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[field] for field in group_fields)].append(row)
    summaries = []
    for key, items in sorted(grouped.items()):
        record = dict(zip(group_fields, key, strict=True))
        record["n_restarts"] = len(items)
        record["paired_differences"] = {
            metric: _distribution(_numeric(items, f"delta_{metric}")) for metric in METRICS
        }
        record["improvements_over_c00"] = {
            metric: {
                "count": sum(
                    item[f"delta_{metric}"] is not None and item[f"delta_{metric}"] > 0
                    for item in items
                ),
                "proportion": sum(
                    item[f"delta_{metric}"] is not None and item[f"delta_{metric}"] > 0
                    for item in items
                )
                / max(sum(item[f"delta_{metric}"] is not None for item in items), 1),
            }
            for metric in ("iou", "dice", "recall", "precision")
        }
        record["improvements_over_c00"]["area_bias"] = {
            "count": sum(item["area_bias_improved"] is True for item in items),
            "proportion": sum(item["area_bias_improved"] is True for item in items)
            / max(sum(item["area_bias_improved"] is not None for item in items), 1),
        }
        record["false_positive_ha"] = _distribution(_numeric(items, "false_positive_ha"))
        record["predicted_area_ha"] = _distribution(_numeric(items, "predicted_area_ha"))
        record["scar_coverage"] = _distribution(_numeric(items, "scar_coverage"))
        record["new_firms_coverage"] = _distribution(_numeric(items, "new_firms_coverage"))
        for field in (
            "delta_false_positive_ha",
            "delta_predicted_area_ha",
            "delta_new_firms_coverage",
        ):
            record[field] = _distribution(_numeric(items, field))
        summaries.append(record)
    return summaries


def _fire_consistency(by_fire: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Count fires (not restarts) whose median paired difference favours the band."""
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for item in by_fire:
        grouped[(item["horizon_hours"], item["product"])].append(item)
    records = []
    for (horizon, product), items in sorted(grouped.items()):
        if product == "c00":
            continue
        record: dict[str, Any] = {
            "horizon_hours": horizon,
            "product": product,
            "n_fires": len(items),
        }
        for metric in ("iou", "dice", "recall", "precision"):
            medians = [
                item["paired_differences"][metric]["median"]
                for item in items
                if item["paired_differences"][metric]["median"] is not None
            ]
            record[metric] = {
                "fires_with_positive_median": sum(value > 0 for value in medians),
                "median_of_fire_medians": statistics.median(medians) if medians else None,
                "fire_medians": {
                    item["fire"]: item["paired_differences"][metric]["median"] for item in items
                },
            }
        records.append(record)
    return records


def _sensitivity_band(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per fire: width of the ≥0,10–≥0,80 band and observed growth left outside ≥0,10."""
    by_case: dict[tuple[str, int, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_case[(row["fire"], row["horizon_hours"], row["case_id"])][row["product"]] = row
    grouped: dict[tuple[str, int], list[dict[str, dict[str, Any]]]] = defaultdict(list)
    for (fire, horizon, _), products in by_case.items():
        grouped[(fire, horizon)].append(products)

    def values(cases: list[dict[str, dict[str, Any]]], product: str, field: str) -> list[float]:
        return _numeric([case[product] for case in cases], field)

    records = []
    for (fire, horizon), cases in sorted(grouped.items()):
        records.append(
            {
                "fire": fire,
                "horizon_hours": horizon,
                "n_restarts": len(cases),
                "observed_area_ha": _distribution(values(cases, "c00", "observed_area_ha")),
                "c00_scar_coverage": _distribution(values(cases, "c00", "scar_coverage")),
                "ge_10_scar_coverage": _distribution(
                    values(cases, "agreement_ge_10", "scar_coverage")
                ),
                "ge_10_missed_observed_ha": _distribution(
                    values(cases, "agreement_ge_10", "false_negative_ha")
                ),
                "band_width_over_c00_area": _distribution(
                    [
                        (
                            case["agreement_ge_10"]["predicted_area_ha"]
                            - case["agreement_ge_80"]["predicted_area_ha"]
                        )
                        / case["c00"]["predicted_area_ha"]
                        for case in cases
                        if case["c00"]["predicted_area_ha"]
                    ]
                ),
            }
        )
    return records


def _fmt(value: Any, digits: int = 4) -> str:
    return "—" if value is None else f"{float(value):.{digits}f}"


def _markdown(report: dict[str, Any]) -> str:
    operations = [case["operational_observations"] for case in report["cases"]]
    total_wall = sum(item["serial_client_wall_seconds"] for item in operations)
    retained_bytes = sum(item["retained_case_bytes"] for item in operations)
    attempts = sum(item["infrastructure_attempt_count"] for item in operations)
    lines = [
        "# Consolidado de backtests contemporáneos GEFS",
        "",
        f"> Generado: {report['generated_at']}. Casos: {report['case_count']}/"
        f"{report['expected_case_count']}. Integridad global: "
        f"**{'aprobada' if report['technical_gate_passed'] else 'no aprobada'}**.",
        "",
        "Los reinicios de un mismo incendio están correlacionados. Este informe es descriptivo: "
        "presenta primero medianas por incendio y no trata los reinicios como incendios "
        "independientes ni fabrica significancia estadística.",
        "",
        "## Gate técnico",
        "",
        f"- Casos con `integrity_passed=true`: {report['integrity_passed_count']}/"
        f"{report['case_count']}.",
        "- Umbrales congelados: `0,10`, `0,50`, `0,80`.",
        "- El acuerdo es fracción de miembros válidos; no es probabilidad calibrada.",
        "",
        "## Costo, latencia y almacenamiento observados",
        "",
        f"- Pared acumulada registrada por los clientes seriales: {total_wall / 3600:.2f} h.",
        f"- Almacenamiento lógico retenido en los casos: {retained_bytes / 2**30:.2f} GiB.",
        f"- Intentos de infraestructura documentados: {attempts}.",
        "- CPU/RSS remotos y costo monetario del solver: no expuestos por el runner; no se "
        "infiere costo facturable a partir de pared de cliente.",
        "",
        "## Resultados por reinicio",
        "",
        "| Reinicio | Horizonte | Producto | Δ IoU | Δ Dice | Δ recall | Δ precisión | "
        "Δ sesgo área | FP ha | Área predicha ha | Cobertura cicatriz | Cobertura FIRMS |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["rows"]:
        if row["product"] == "c00":
            continue
        lines.append(
            f"| {row['case_id']} | {row['horizon_hours']} h | {row['product']} | "
            f"{_fmt(row['delta_iou'])} | {_fmt(row['delta_dice'])} | "
            f"{_fmt(row['delta_recall'])} | {_fmt(row['delta_precision'])} | "
            f"{_fmt(row['delta_sesgo_area'])} | {_fmt(row['false_positive_ha'], 2)} | "
            f"{_fmt(row['predicted_area_ha'], 2)} | {_fmt(row['scar_coverage'])} | "
            f"{_fmt(row['new_firms_coverage'])} |"
        )
    lines.extend(
        [
            "",
            "## Medianas por incendio",
            "",
            "| Incendio | Horizonte | Producto | n | Δ IoU mediana | Δ Dice mediana | "
            "Δ recall mediana | Δ precisión mediana | Δ sesgo área mediana |",
            "|---|---:|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for item in report["summary_by_fire"]:
        if item["product"] == "c00":
            continue
        diff = item["paired_differences"]
        lines.append(
            f"| {item['fire']} | {item['horizon_hours']} h | {item['product']} | "
            f"{item['n_restarts']} | {_fmt(diff['iou']['median'])} | "
            f"{_fmt(diff['dice']['median'])} | {_fmt(diff['recall']['median'])} | "
            f"{_fmt(diff['precision']['median'])} | {_fmt(diff['sesgo_area']['median'])} |"
        )
    lines.extend(
        [
            "",
            "## Consistencia entre incendios",
            "",
            "Unidad de análisis: incendio. Se cuenta en cuántos incendios la mediana de sus "
            "reinicios favorece a la banda frente a c00.",
            "",
            "| Horizonte | Producto | Incendios | IoU: incendios con mediana > 0 | "
            "Mediana de medianas Δ IoU | Dice: incendios con mediana > 0 | "
            "Recall: incendios con mediana > 0 | Precisión: incendios con mediana > 0 |",
            "|---:|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for item in report["fire_consistency"]:
        lines.append(
            f"| {item['horizon_hours']} h | {item['product']} | {item['n_fires']} | "
            f"{item['iou']['fires_with_positive_median']}/{item['n_fires']} | "
            f"{_fmt(item['iou']['median_of_fire_medians'])} | "
            f"{item['dice']['fires_with_positive_median']}/{item['n_fires']} | "
            f"{item['recall']['fires_with_positive_median']}/{item['n_fires']} | "
            f"{item['precision']['fires_with_positive_median']}/{item['n_fires']} |"
        )
    lines.extend(
        [
            "",
            "## Envolvente ≥ 0,10 por incendio",
            "",
            "| Incendio | Horizonte | n | Δ cobertura cicatriz mediana | "
            "Δ cobertura FIRMS mediana | Δ FP ha mediana | Δ área predicha ha mediana |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for item in report["summary_by_fire"]:
        if item["product"] != "agreement_ge_10":
            continue
        lines.append(
            f"| {item['fire']} | {item['horizon_hours']} h | {item['n_restarts']} | "
            f"{_fmt(item['paired_differences']['recall']['median'])} | "
            f"{_fmt(item['delta_new_firms_coverage']['median'])} | "
            f"{_fmt(item['delta_false_positive_ha']['median'], 2)} | "
            f"{_fmt(item['delta_predicted_area_ha']['median'], 2)} |"
        )
    lines.extend(
        [
            "",
            "## Ancho de la banda frente al crecimiento observado",
            "",
            "Mide cuánta sensibilidad meteorológica muestra la capa y cuánto crecimiento "
            "observado queda fuera de la envolvente `≥ 0,10`. Medianas por incendio.",
            "",
            "| Incendio | Horizonte | n | Crecimiento observado ha | Cobertura c00 | "
            "Cobertura ≥ 0,10 | Observado fuera de ≥ 0,10 ha | (área ≥ 0,10 − área ≥ 0,80) / "
            "área c00 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for item in report["sensitivity_band"]:
        lines.append(
            f"| {item['fire']} | {item['horizon_hours']} h | {item['n_restarts']} | "
            f"{_fmt(item['observed_area_ha']['median'], 2)} | "
            f"{_fmt(item['c00_scar_coverage']['median'])} | "
            f"{_fmt(item['ge_10_scar_coverage']['median'])} | "
            f"{_fmt(item['ge_10_missed_observed_ha']['median'], 2)} | "
            f"{_fmt(item['band_width_over_c00_area']['median'])} |"
        )
    lines.extend(
        [
            "",
            "## Resumen global descriptivo",
            "",
            "Agrupa reinicios correlacionados dentro de cada incendio; se presenta después de las "
            "medianas por incendio y no constituye una muestra de incendios independientes.",
            "",
            "| Horizonte | Producto | n | Δ IoU mediana [IQR; rango] | Mejora IoU | "
            "Δ Dice mediana [IQR; rango] | Mejora Dice |",
            "|---:|---|---:|---|---:|---|---:|",
        ]
    )
    for item in report["summary_global"]:
        if item["product"] == "c00":
            continue
        iou = item["paired_differences"]["iou"]
        dice = item["paired_differences"]["dice"]
        iou_improvement = item["improvements_over_c00"]["iou"]
        dice_improvement = item["improvements_over_c00"]["dice"]
        lines.append(
            f"| {item['horizon_hours']} h | {item['product']} | {item['n_restarts']} | "
            f"{_fmt(iou['median'])} [{_fmt(iou['q1'])}, {_fmt(iou['q3'])}; "
            f"{_fmt(iou['min'])}, {_fmt(iou['max'])}] | {iou_improvement['count']}/"
            f"{item['n_restarts']} ({iou_improvement['proportion']:.1%}) | "
            f"{_fmt(dice['median'])} [{_fmt(dice['q1'])}, {_fmt(dice['q3'])}; "
            f"{_fmt(dice['min'])}, {_fmt(dice['max'])}] | {dice_improvement['count']}/"
            f"{item['n_restarts']} ({dice_improvement['proportion']:.1%}) |"
        )
    lines.extend(
        [
            "",
            "## Lectura de ≥ 0,10 como envolvente",
            "",
            "La banda `≥ 0,10` se evalúa por cobertura adicional, falsos positivos e inflación "
            "de área; no se descarta únicamente por IoU. Las columnas completas por reinicio "
            "están en el CSV y el JSON consolidados.",
            "",
            "## Veredicto",
            "",
            "El veredicto técnico, predictivo y comunicacional se registra por separado al "
            "cerrar los 23 casos. Un gate técnico aprobado no implica superioridad predictiva "
            "sobre c00; una capa puede seguir siendo útil para comunicar sensibilidad "
            "meteorológica si sus bandas son no degeneradas y sus limitaciones permanecen "
            "visibles.",
            "",
            "## Artefactos individuales",
            "",
        ]
    )
    for case in report["cases"]:
        lines.append(
            f"- `{case['case_id']}`: `{case['artifacts']['backtest_metrics']}`, "
            f"`{case['artifacts']['integrity']}`."
        )
    return "\n".join(lines) + "\n"


def consolidate(root: Path, expected_cases: int) -> dict[str, Any]:
    metrics_paths = sorted(root.rglob("backtest-metrics.json"))
    cases = []
    rows = []
    case_ids: set[str] = set()
    for path in metrics_paths:
        case, case_rows = _case_rows(path)
        if case["case_id"] in case_ids:
            raise ValueError(f"duplicate case id {case['case_id']}: {path}")
        case_ids.add(case["case_id"])
        cases.append(case)
        rows.extend(case_rows)
    cases.sort(key=lambda item: (item["fire"], item["window_index"]))
    summary_by_fire = _summaries(rows, ("fire", "horizon_hours", "product"))
    report = {
        "schema_version": 1,
        "classification": "contemporary calibration backtests; descriptive paired analysis",
        "scientific_constraints": {
            "model_snapshot": "modelo-v0",
            "recipe": "lw-100-001",
            "test_set_opened": False,
            "fixed_thresholds": EXPECTED_THRESHOLDS,
            "agreement_is_calibrated_probability": False,
            "suppression_modeled": False,
        },
        "expected_case_count": expected_cases,
        "case_count": len(cases),
        "integrity_passed_count": sum(case["integrity_passed"] for case in cases),
        "technical_gate_passed": len(cases) == expected_cases
        and all(case["integrity_passed"] for case in cases),
        "cases": cases,
        "rows": rows,
        "summary_by_fire": summary_by_fire,
        "fire_consistency": _fire_consistency(summary_by_fire),
        "sensitivity_band": _sensitivity_band(rows),
        "summary_global": _summaries(rows, ("horizon_hours", "product")),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data/ensemble-poc"))
    parser.add_argument("--expected-cases", type=int, default=23)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    report = consolidate(args.root, args.expected_cases)
    for path in (args.json, args.csv, args.markdown):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    fieldnames = list(report["rows"][0]) if report["rows"] else []
    with args.csv.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report["rows"])
    args.markdown.write_text(_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "case_count": report["case_count"],
                "expected_case_count": report["expected_case_count"],
                "technical_gate_passed": report["technical_gate_passed"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
