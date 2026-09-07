"""
Fuels endpoint — exposes the fbfm40.tif fuel-model map (WorldCover → Scott & Burgan
crosswalk) as a colorized map overlay plus the per-class area breakdown, so the
crosswalk currently in use can be inspected instead of taken on faith.
"""
import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import rasterio
from fastapi import APIRouter, HTTPException

from app.config import resolve_data_path, settings
from app.elmfire.builder.fuels_builder import (
    FBFM40_DISPLAY,
    WORLDCOVER_LABELS,
    WORLDCOVER_TO_FBFM40,
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


def _class_areas(tif_path: Path) -> tuple[list[dict], float]:
    """Per-class pixel counts and area, computed on the native (30 m) grid."""
    with rasterio.open(tif_path) as src:
        band = src.read(1)
        pixel_area_ha = abs(src.transform.a * src.transform.e) / 10_000.0

    sources: dict[int, list[str]] = defaultdict(list)
    for wc_class, fuel_model in WORLDCOVER_TO_FBFM40.items():
        sources[fuel_model].append(WORLDCOVER_LABELS.get(wc_class, str(wc_class)))

    values, counts = np.unique(band, return_counts=True)
    total = int(counts.sum())
    rows = [
        {
            "fbfm40": int(value),
            "label": FBFM40_DISPLAY.get(int(value), (f"FBFM {value}", "#e6e6e6"))[0],
            "color": _FBFM40_COLORS.get(int(value), "#e6e6e6"),
            "worldcover_classes": sources.get(int(value), []),
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
        "Renders the cached fbfm40.tif — the ESA WorldCover → Scott & Burgan FBFM40 "
        "crosswalk this system runs today — as a base64 PNG overlay in EPSG:4326, "
        "with the per-class area breakdown and the WorldCover classes each fuel "
        "model came from. NB9 (99) is the raster's nodata value: it is counted in "
        "the breakdown but drawn transparent. 404 until preparation has built "
        "fbfm40.tif (POST /api/v1/ingestion/run with include_worldcover=true)."
    ),
)
async def get_fuels_map():
    tif_path = resolve_data_path(settings.static_data_dir) / "fbfm40.tif"
    if not tif_path.exists():
        raise HTTPException(
            status_code=404,
            detail="fbfm40.tif not built yet — run POST /api/v1/ingestion/run first.",
        )

    overlay, (classes, total_area_ha) = await asyncio.gather(
        asyncio.to_thread(render_categorical_overlay, tif_path, _FBFM40_COLORS),
        asyncio.to_thread(_class_areas, tif_path),
    )
    return _envelope(
        "success",
        {
            "source": "ESA WorldCover v200 (2021) → Scott & Burgan FBFM40",
            "classes": classes,
            "total_area_ha": total_area_ha,
            **overlay,
        },
    )
