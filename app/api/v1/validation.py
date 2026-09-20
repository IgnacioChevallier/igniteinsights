"""
Validation endpoint — expone lo que el modelo predijo contra lo que efectivamente se
quemó, mapa de combustible por mapa de combustible.

Hay dos referencias distintas y no son intercambiables (`IGN-26-VALIDACION.md`):

- **harness A**: detecciones FIRMS nuevas en una ventana de 24 h. Sirve para medir avance
  del frente en muchas ventanas, pero no es independiente del insumo que sembró la corrida.
- **harness B**: la cicatriz final de Sentinel-2. Es la única referencia independiente,
  porque FIRMS construyó la semilla, pero cubre semanas y no una ventana.

Los artefactos los dejan `scripts/harness_a.py` y `scripts/score_against_observed.py`.
Este módulo sólo los lee: la aritmética de la validación no se recalcula acá, para que el
dashboard no pueda mostrar un número distinto del que se documentó.
"""
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.postprocessing.raster_overlay import render_categorical_overlay

router = APIRouter(prefix="/validation", tags=["validation"])

RAIZ = Path("data/validation")

# Códigos del ráster de confusión, comunes a los dos harness.
LEYENDA: dict[int, tuple[str, str]] = {
    1: ("Semilla (ya quemado al empezar)", "#64748b"),
    2: ("Acierto", "#16a34a"),
    3: ("Predicho sin observación", "#f59e0b"),
    4: ("Observado y no predicho", "#dc2626"),
    # 5 = fuera de la cobertura de referencia: sin color, se dibuja transparente.
}
COLORES = {codigo: color for codigo, (_, color) in LEYENDA.items()}


def _envelope(status: str, data=None, error: dict | None = None) -> dict:
    return {
        "status": status,
        "data": data,
        "error": error,
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }


def _raiz() -> Path:
    """`data/` está montado en /app/data dentro del contenedor y es relativo afuera."""
    absoluta = Path("/app") / RAIZ
    return absoluta if absoluta.exists() else RAIZ


def _casos() -> list[dict]:
    raiz = _raiz()
    casos: list[dict] = []
    for harness, etiqueta, referencia in (
        ("harness_a", "A · ventana de 24 h", "Detecciones FIRMS de la ventana siguiente"),
        ("harness_b", "B · cicatriz final", "Cicatriz de Sentinel-2 (dNBR)"),
    ):
        base = raiz / harness
        if not base.exists():
            continue
        for caso_dir in sorted(base.iterdir()):
            if not caso_dir.is_dir():
                continue
            mapas = {}
            for mapa_dir in sorted(caso_dir.iterdir()):
                metricas = mapa_dir / "metrics.json"
                if mapa_dir.is_dir() and metricas.exists():
                    mapas[mapa_dir.name] = json.loads(metricas.read_text())
            if not mapas:
                continue
            meta_path = caso_dir / "meta.json"
            casos.append({
                "id": f"{harness}/{caso_dir.name}",
                "harness": harness,
                "harness_label": etiqueta,
                "referencia": referencia,
                "caso": caso_dir.name,
                "meta": json.loads(meta_path.read_text()) if meta_path.exists() else {},
                "mapas": mapas,
            })
    return casos


@router.get(
    "/cases",
    summary="List the validation cases with their metrics, one entry per fuel map",
    description=(
        "Each case is a scored simulation window: harness A against the next window's "
        "FIRMS detections, harness B against the Sentinel-2 scar. Metrics are read from "
        "the artefacts the scoring scripts wrote, never recomputed here."
    ),
)
async def list_cases():
    casos = await asyncio.to_thread(_casos)
    return _envelope("success", {"cases": casos, "legend": [
        {"code": codigo, "label": etiqueta, "color": color}
        for codigo, (etiqueta, color) in LEYENDA.items()
    ]})


@router.get(
    "/cases/{harness}/{caso}/overlay",
    summary="Get the confusion raster of one case and fuel map as a colorized overlay",
    description=(
        "Renders confusion.tif as a base64 PNG in EPSG:4326: seed, hit, predicted without "
        "observation, and observed but not predicted. Cells outside the reference coverage "
        "carry no colour and are drawn transparent."
    ),
)
async def case_overlay(harness: str, caso: str, mapa: str):
    ruta = _raiz() / harness / caso / mapa / "confusion.tif"
    if not ruta.exists():
        raise HTTPException(status_code=404, detail=f"Sin artefactos para {harness}/{caso}/{mapa}")
    overlay = await asyncio.to_thread(render_categorical_overlay, ruta, COLORES)
    if overlay is None:
        raise HTTPException(status_code=422, detail="El ráster de confusión está vacío")
    metricas = json.loads((ruta.parent / "metrics.json").read_text())
    return _envelope("success", {"mapa": mapa, "metrics": metricas, **overlay})
