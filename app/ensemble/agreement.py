"""Aggregate independent ELMFIRE member outputs into ensemble agreement products."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.warp import transform_geom

THRESHOLDS = (0.10, 0.50, 0.80)
THRESHOLD_PRESENTATION = {
    0.10: {"label": "≥ 0,10", "fill_color": "#fed976", "line_color": "#b45309"},
    0.50: {"label": "≥ 0,50", "fill_color": "#fd8d3c", "line_color": "#c2410c"},
    0.80: {"label": "≥ 0,80", "fill_color": "#bd0026", "line_color": "#881337"},
}


def _same_grid(reference: rasterio.DatasetReader, candidate: rasterio.DatasetReader) -> bool:
    return (
        reference.shape == candidate.shape
        and reference.crs == candidate.crs
        and reference.transform.almost_equals(candidate.transform)
        and reference.nodata == candidate.nodata
    )


def _geojson(mask: np.ndarray, transform, crs, threshold: float) -> dict:
    label = THRESHOLD_PRESENTATION[threshold]["label"]
    features = []
    for geometry, value in shapes(mask.astype("uint8"), mask=mask, transform=transform):
        if value != 1:
            continue
        if crs and crs.to_epsg() != 4326:
            geometry = transform_geom(crs, "EPSG:4326", geometry, precision=6)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "agreement_threshold": threshold,
                    "agreement_label": label,
                },
                "geometry": geometry,
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _forecast_valid_at(forecast_start: str, horizon_hours: int) -> str | None:
    """Return the end-of-horizon timestamp from the simulation start."""
    try:
        start_at = datetime.fromisoformat(forecast_start)
    except ValueError:
        return None
    if start_at.tzinfo is None:
        return None
    return (start_at.astimezone(UTC) + timedelta(hours=horizon_hours)).isoformat()


def aggregate_burn_agreement(
    member_toa: dict[str, Path],
    output_dir: Path,
    *,
    expected_members: list[str],
    min_valid_members: int,
    cycle: str,
    forecast_start: str,
    horizon_hours: int,
    failed_members: dict[str, str] | None = None,
) -> dict:
    """Write agreement GeoTIFF, threshold masks/GeoJSON and an auditable manifest.

    A cell counts when 0 < TOA <= the requested horizon. The denominator is the
    number of successful, grid-compatible members, never the nominal ensemble size.
    """
    successful = sorted(member_toa)
    failed = dict(failed_members or {})
    missing = sorted(set(expected_members) - set(successful) - set(failed))
    failed.update({name: "missing output" for name in missing})
    if len(successful) < min_valid_members:
        raise ValueError(
            f"only {len(successful)} valid member(s); minimum is {min_valid_members}; "
            f"failed={sorted(failed)}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    reference_path = member_toa[successful[0]]
    threshold_geojson: dict[float, dict] = {}
    with rasterio.open(reference_path) as reference:
        profile = reference.profile.copy()
        total = np.zeros(reference.shape, dtype="uint16")
        for member in successful:
            with rasterio.open(member_toa[member]) as src:
                if not _same_grid(reference, src):
                    raise ValueError(f"member {member} does not share grid/CRS/transform/nodata")
                toa = src.read(1)
                total += (toa > 0) & (toa <= horizon_hours * 3600)
        agreement = total.astype("float32") / len(successful)
        profile.update(dtype="float32", count=1, nodata=-9999.0, compress="deflate", predictor=3)
        with rasterio.open(output_dir / "burn_agreement.tif", "w", **profile) as dst:
            dst.write(agreement, 1)
        for threshold in THRESHOLDS:
            label = f"{int(threshold * 100):02d}"
            mask = agreement >= threshold
            mask_profile = profile | {"dtype": "uint8", "nodata": 0, "predictor": 2}
            with rasterio.open(
                output_dir / f"burn_agreement_ge_{label}.tif", "w", **mask_profile
            ) as dst:
                dst.write(mask.astype("uint8"), 1)
            payload = _geojson(mask, reference.transform, reference.crs, threshold)
            threshold_geojson[threshold] = payload
            (output_dir / f"burn_agreement_ge_{label}.geojson").write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
    generated_at = datetime.now(UTC).isoformat()
    metadata = {
        "product": "fraccion de miembros GEFS que quemaron cada pixel",
        "not_calibrated_probability": True,
        "expected_member_count": len(expected_members),
        "effective_denominator": len(successful),
        "successful_members": successful,
        "failed_members": failed,
        "cycle": cycle,
        "forecast_start": forecast_start,
        "horizon_hours": horizon_hours,
        "generated_at": generated_at,
        "forecast_valid_at": _forecast_valid_at(forecast_start, horizon_hours),
        "thresholds": list(THRESHOLDS),
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    frontend_contract = {
        "schema_version": 1,
        "layer": {
            "id": "ensemble_agreement",
            "name": "Acuerdo del ensamble",
            "legend_label": "acuerdo entre simulaciones",
            "default_visible": False,
            "geometry": "polygon",
        },
        "metadata": {
            "valid_members": len(successful),
            "expected_members": len(expected_members),
            "valid_member_ids": successful,
            "failed_members": failed,
            "weather_cycle": cycle,
            "forecast_start": forecast_start,
            "horizon_hours": horizon_hours,
            "generated_at": generated_at,
            "forecast_valid_at": metadata["forecast_valid_at"],
        },
        "thresholds": [
            {
                "value": threshold,
                "operator": ">=",
                **THRESHOLD_PRESENTATION[threshold],
                "geojson": threshold_geojson[threshold],
            }
            for threshold in THRESHOLDS
        ],
    }
    (output_dir / "ensemble_agreement.json").write_text(
        json.dumps(frontend_contract, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return metadata
