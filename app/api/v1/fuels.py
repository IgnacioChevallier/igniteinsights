"""
Fuels endpoint — exposes the fbfm40.tif fuel-model map as a colorized overlay plus the
per-class area breakdown, so the crosswalk currently in use can be inspected instead of
taken on faith. Each cover product has its own cached raster (fbfm40_<source>.tif, written by
preparation), so the three maps can be viewed side by side; `settings.fuels_source` is only
the default.
"""
import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import numpy as np
import rasterio
from fastapi import APIRouter, HTTPException, Query

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

FuelsSource = Literal["ccsbap", "mapbiomas", "worldcover"]


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
    summary="Get a fuel-model (FBFM40) map as a colorized overlay",
    description=(
        "Renders the cached fbfm40_<source>.tif — the raster preparation built from that "
        "cover product, i.e. exactly what ELMFIRE receives — as a base64 PNG overlay in "
        "EPSG:4326, with the per-class area breakdown and the cover classes each fuel model "
        "came from. `source` defaults to settings.fuels_source. NB9 (99) is the raster's "
        "nodata value: it is counted in the breakdown but drawn transparent. "
        "`available_sources` lists the sources whose raster is already built. 404 until a "
        "run with that source has built it (POST /api/v1/ingestion/run)."
    ),
)
async def get_fuels_map(source: FuelsSource | None = Query(default=None)):
    source = source or settings.fuels_source
    static_dir = resolve_data_path(settings.static_data_dir)
    tif_path = static_dir / f"fbfm40_{source}.tif"
    if not tif_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"fbfm40_{source}.tif sin construir — corré un run con esta fuente.",
        )

    colors = dict(_FBFM40_COLORS)
    with rasterio.open(tif_path) as src:
        for code in np.unique(src.read(1)).tolist():
            colors.setdefault(int(code), fuel_model_info(int(code))["color"])

    overlay, (classes, total_area_ha) = await asyncio.gather(
        asyncio.to_thread(render_categorical_overlay, tif_path, colors),
        asyncio.to_thread(_class_areas, tif_path, source),
    )
    return _envelope(
        "success",
        {
            "source_id": source,
            "source": f"{SOURCE_LABELS.get(source, source)} → Scott & Burgan FBFM40",
            "available_sources": [
                s for s in SOURCE_LABELS if (static_dir / f"fbfm40_{s}.tif").exists()
            ],
            "classes": classes,
            "total_area_ha": total_area_ha,
            **overlay,
        },
    )
