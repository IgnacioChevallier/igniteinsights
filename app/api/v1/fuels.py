"""
Fuels endpoint — exposes the fbfm40.tif fuel-model map as a colorized overlay plus the
per-class area breakdown, so the crosswalk currently in use can be inspected instead of
taken on faith. Which cover product feeds it is configuration (`settings.fuels_source`),
so the legend reports the active source rather than assuming WorldCover.
"""
import asyncio
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import rasterio
from fastapi import APIRouter, HTTPException

from app.config import resolve_data_path, settings
from app.elmfire.builder.fuels_builder import (
    FBFM40_DISPLAY,
    SOURCE_LABELS,
    fuel_model_info,
    source_classes_by_fuel_model,
)
from app.postprocessing.raster_overlay import render_categorical_overlay

router = APIRouter(prefix="/fuels", tags=["fuels"])

_FBFM40_COLORS = {code: color for code, (_, color) in FBFM40_DISPLAY.items()}


def _envelope(status: str, data=None, error: dict | None = None) -> dict:
    return {
        "status": status,
        "data": data,
        "error": error,
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }


def _class_areas(tif_path: Path, source: str | None = None) -> tuple[list[dict], float]:
    """Per-class pixel counts and area, computed on the native (30 m) grid."""
    with rasterio.open(tif_path) as src:
        band = src.read(1)
        pixel_area_ha = abs(src.transform.a * src.transform.e) / 10_000.0

    sources = source_classes_by_fuel_model(source or settings.fuels_source)

    values, counts = np.unique(band, return_counts=True)
    total = int(counts.sum())
    rows = [
        {
            "fbfm40": int(value),
            "label": FBFM40_DISPLAY.get(int(value), (fuel_model_info(int(value))["label"], ""))[0],
            "color": _FBFM40_COLORS.get(int(value), fuel_model_info(int(value))["color"]),
            "source_classes": sources.get(int(value), []),
            "pixel_count": int(count),
            "area_ha": round(int(count) * pixel_area_ha, 1),
            "share": round(int(count) / total, 4) if total else 0.0,
        }
        for value, count in zip(values.tolist(), counts.tolist(), strict=True)
    ]
    rows.sort(key=lambda row: row["pixel_count"], reverse=True)
    return rows, round(total * pixel_area_ha, 1)


@router.get(
    "/map",
    summary="Get the current fuel-model (FBFM40) map as a colorized overlay",
    description=(
        "Renders the cached fbfm40.tif — built from the cover source configured in "
        "`fuels_source` — as a base64 PNG overlay in EPSG:4326, with the per-class area "
        "breakdown and the cover classes each fuel model came from. NB9 (99) is the "
        "raster's nodata value: it is counted in the breakdown but drawn transparent. "
        "404 until preparation has built fbfm40.tif (POST /api/v1/ingestion/run)."
    ),
)
async def get_fuels_map():
    tif_path = resolve_data_path(settings.static_data_dir) / "fbfm40.tif"
    if not tif_path.exists():
        raise HTTPException(
            status_code=404,
            detail="fbfm40.tif not built yet — run POST /api/v1/ingestion/run first.",
        )

    colors = dict(_FBFM40_COLORS)
    with rasterio.open(tif_path) as src:
        for code in np.unique(src.read(1)).tolist():
            colors.setdefault(int(code), fuel_model_info(int(code))["color"])

    overlay, (classes, total_area_ha) = await asyncio.gather(
        asyncio.to_thread(render_categorical_overlay, tif_path, colors),
        asyncio.to_thread(_class_areas, tif_path),
    )
    return _envelope(
        "success",
        {
            "source": f"{SOURCE_LABELS.get(settings.fuels_source, settings.fuels_source)}"
                      " → Scott & Burgan FBFM40",
            "classes": classes,
            "total_area_ha": total_area_ha,
            **overlay,
        },
    )
