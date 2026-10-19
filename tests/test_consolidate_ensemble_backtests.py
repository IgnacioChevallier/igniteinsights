from __future__ import annotations

import json
from pathlib import Path

from scripts.consolidate_ensemble_backtests import consolidate


def _write_case(root: Path, *, window: int, fire: str = "incendio") -> None:
    case_root = root / f"case-{window}"
    for horizon in (12, 24):
        agreement = case_root / "agreement" / f"h{horizon:02d}"
        agreement.mkdir(parents=True)
        (agreement / "ensemble_agreement.json").write_text(
            json.dumps(
                {
                    "metadata": {
                        "weather_cycle": "2025-01-01T00:00:00+00:00",
                        "valid_members": 31,
                        "expected_members": 31,
                    }
                }
            ),
            encoding="utf-8",
        )

    def product(offset: float, firms: float | None) -> dict:
        return {
            "cicatriz": {
                "iou": 0.4 + offset,
                "dice": 0.5 + offset,
                "recall": 0.6 + offset,
                "precision": 0.3 + offset,
                "sesgo_area": 2.0 + offset,
                "fp_ha": 100 + offset,
                "fn_ha": 30 - offset,
                "predicho_ha": 150 + offset,
                "observado_ha": 75,
            },
            "firms": {"recall": firms},
        }

    products = {
        "c00": product(0, None),
        "agreement_ge_10": product(0.02, None),
        "agreement_ge_50": product(0.01, 0.7),
        "agreement_ge_80": product(-0.01, 0.6),
    }
    metrics = {
        "case": f"{fire}/pronostico-v6",
        "base_case": f"{fire}/calibracion-v6",
        "window_index": window,
        "forecast_start": "2025-01-01T06:00:00+00:00",
        "fixed_thresholds": [0.1, 0.5, 0.8],
        "horizons": {
            "12": {"products": products},
            "24": {"products": products},
        },
    }
    (case_root / "backtest-metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    (case_root / "integrity.json").write_text(
        json.dumps({"integrity_passed": True, "gates": {"members": True}}),
        encoding="utf-8",
    )
    for member in ("c00", *(f"p{index:02d}" for index in range(1, 31))):
        run = case_root / "runs" / member
        run.mkdir(parents=True)
        (run / "run-metrics.json").write_text(
            json.dumps({"wall_seconds": 2.0, "output_bytes": 1000}), encoding="utf-8"
        )


def test_consolidate_preserves_pairs_and_groups_by_fire(tmp_path: Path) -> None:
    _write_case(tmp_path, window=1)
    _write_case(tmp_path, window=2)

    report = consolidate(tmp_path, expected_cases=2)

    assert report["technical_gate_passed"] is True
    assert report["case_count"] == 2
    assert len(report["rows"]) == 16
    ge_50 = next(
        row
        for row in report["rows"]
        if row["case_id"] == "incendio-w01"
        and row["horizon_hours"] == 12
        and row["product"] == "agreement_ge_50"
    )
    assert ge_50["delta_iou"] == 0.010000000000000009
    assert ge_50["delta_new_firms_coverage"] is None
    summary = next(
        item
        for item in report["summary_by_fire"]
        if item["horizon_hours"] == 12 and item["product"] == "agreement_ge_50"
    )
    assert summary["n_restarts"] == 2
    assert summary["improvements_over_c00"]["iou"]["count"] == 2
    band = next(item for item in report["sensitivity_band"] if item["horizon_hours"] == 24)
    assert band["n_restarts"] == 2
    assert band["ge_10_missed_observed_ha"]["median"] == 29.98
    # (150.02 - 149.99) / 150: the band is paired within each restart.
    assert round(band["band_width_over_c00_area"]["median"], 6) == 0.0002


def test_legacy_smoke_integrity_is_accepted(tmp_path: Path) -> None:
    _write_case(tmp_path, window=1)
    integrity = tmp_path / "case-1" / "integrity.json"
    integrity.write_text(
        json.dumps({"smoke_passed": True, "gates": {"members": True}}),
        encoding="utf-8",
    )

    report = consolidate(tmp_path, expected_cases=1)

    assert report["technical_gate_passed"] is True


def test_consistency_counts_fires_not_restarts(tmp_path: Path) -> None:
    # Three restarts of one fire must count as one fire, not three wins.
    for window in (1, 2, 3):
        _write_case(tmp_path, window=window, fire="a")
    _write_case(tmp_path, window=4, fire="b")

    report = consolidate(tmp_path, expected_cases=4)

    ge_80 = next(
        item
        for item in report["fire_consistency"]
        if item["horizon_hours"] == 24 and item["product"] == "agreement_ge_80"
    )
    assert ge_80["n_fires"] == 2
    assert ge_80["iou"]["fires_with_positive_median"] == 0
    ge_10 = next(
        item
        for item in report["fire_consistency"]
        if item["horizon_hours"] == 24 and item["product"] == "agreement_ge_10"
    )
    assert ge_10["iou"]["fires_with_positive_median"] == 2
    row = next(row for row in report["rows"] if row["product"] == "agreement_ge_10")
    assert round(row["delta_false_positive_ha"], 6) == 0.02
