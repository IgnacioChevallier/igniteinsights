"""
Validation endpoint — lo que cada versión del modelo predijo contra lo que se quemó.

El benchmark (`app/validation/`, `docs/resultados/IGN-26-VALIDACION.md` §Benchmark) se organiza en
**incendio → protocolo (caso) → receta (versión del modelo)**. Cada iteración es inmutable:
su manifiesto y sus métricas viven en `benchmarks/iteraciones/`, y las vistas derivadas
(confusión y tiempos de llegada) en `data/benchmark/vistas/`. Este módulo sólo los lee: la
aritmética de la validación no se recalcula acá, para que el dashboard no pueda mostrar un
número distinto del que se documentó.

Los dos endpoints `/cases` del final son el visor de los harness viejos; se van cuando las
recetas `legacy-*` reproducen docs/historico/RESULTADOS.md dentro del benchmark.
"""
import asyncio
import functools
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import rasterio
from fastapi import APIRouter, HTTPException

from app.postprocessing.isochrone_converter import _burned_area_polygons
from app.postprocessing.raster_overlay import render_categorical_overlay
from app.validation import definiciones as d
from app.validation.cadena import VISTAS

router = APIRouter(prefix="/validation", tags=["validation"])

RAIZ = Path("data/validation")

# Códigos del ráster de confusión, comunes a los dos harness.
LEYENDA: dict[int, tuple[str, str]] = {
    1: ("Ya quemado al empezar la ventana", "#64748b"),
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


def _vistas() -> Path:
    absoluta = Path("/app") / VISTAS
    return absoluta if absoluta.exists() else VISTAS


def _recetas_del_caso(caso: d.Caso) -> list[dict]:
    raiz = d.ruta_iteracion(caso.id, "")
    salida = []
    for dir_receta in sorted(raiz.iterdir()) if raiz.exists() else []:
        manifiesto = d.cargar_manifiesto(caso.id, dir_receta.name)
        metricas = d.cargar_metricas(caso.id, dir_receta.name)
        if manifiesto is None:
            continue
        salida.append({
            "receta": dir_receta.name, "padre": manifiesto.get("padre"),
            "motivo": manifiesto.get("motivo"), "factores": manifiesto["factores"],
            "git": manifiesto["git"], "ventanas_corridas": len(manifiesto["ventanas"]),
            "puntuada": metricas is not None,
            "principal": (metricas or {}).get("principal"),
            "agregado_firms": (metricas or {}).get("agregado_firms"),
        })
    return salida


def _incendios() -> list[dict]:
    raiz = d.RAIZ / "casos"
    incendios = []
    for dir_incendio in sorted(raiz.iterdir()) if raiz.exists() else []:
        protocolos = []
        for ruta in sorted(dir_incendio.glob("*.json")):
            if ruta.name.endswith(".paquete.json"):
                continue
            caso = d.Caso.cargar(f"{dir_incendio.name}/{ruta.stem}")
            recetas = _recetas_del_caso(caso)
            protocolos.append({
                "protocolo": caso.protocolo, "caso": caso.id,
                "descripcion": caso.datos.get("descripcion", ""),
                "contiguo": caso.contiguo,
                "referencias": sorted(caso.datos.get("referencias", {})),
                "ventanas": [{"n": n, "inicio": v.inicio.isoformat(), "horas": v.horas}
                             for n, v in enumerate(caso.ventanas)],
                "recetas": recetas,
            })
        if protocolos:
            incendios.append({"incendio": dir_incendio.name, "protocolos": protocolos})
    return incendios


@functools.lru_cache(maxsize=16)
def _isocronas(ruta: Path, _estampa: tuple) -> dict:
    """Polígonos acumulados por hora, con el mismo código que las isócronas del mapa."""
    with rasterio.open(ruta) as src:
        maximo = float(src.read(1).max())
    niveles = [3600.0 * h for h in range(1, math.ceil(maximo / 3600) + 1)]
    return _burned_area_polygons(ruta, niveles)


def _caso_y_receta(incendio: str, protocolo: str, receta: str) -> tuple[d.Caso, dict, dict]:
    try:
        caso = d.Caso.cargar(f"{incendio}/{protocolo}")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Sin caso {incendio}/{protocolo}") from exc
    manifiesto = d.cargar_manifiesto(caso.id, receta)
    metricas = d.cargar_metricas(caso.id, receta)
    if manifiesto is None or metricas is None:
        raise HTTPException(status_code=404, detail=f"{caso.id}/{receta} no está puntuada")
    return caso, manifiesto, metricas


@router.get(
    "/fires",
    summary="List fires, their validation protocols, and the model recipes run on each",
    description=(
        "Fire → protocol (a frozen case: seed, windows, references) → recipe (a model "
        "version). Recipes are only comparable within one protocol, or the same recipe "
        "across protocols. Each recipe carries its headline metric and declared factors."
    ),
)
async def list_fires():
    incendios = await asyncio.to_thread(_incendios)
    return _envelope("success", {"fires": incendios, "legend": [
        {"code": codigo, "label": etiqueta, "color": color}
        for codigo, (etiqueta, color) in LEYENDA.items()
    ]})


@router.get(
    "/iterations/{incendio}/{protocolo}/{receta}",
    summary="Get one iteration's manifest summary and per-window metrics",
    description=(
        "Per-window metrics against each reference, the headline metric, the declared "
        "factors and the recipe's parent. Input and output hashes are omitted: they live "
        "in benchmarks/iteraciones/…/manifiesto.json."
    ),
)
async def get_iteration(incendio: str, protocolo: str, receta: str):
    caso, manifiesto, metricas = _caso_y_receta(incendio, protocolo, receta)
    vistas = _vistas() / caso.id / receta
    return _envelope("success", {
        "caso": caso.id, "receta": receta, "padre": manifiesto.get("padre"),
        "motivo": manifiesto.get("motivo"), "factores": manifiesto["factores"],
        "git": manifiesto["git"], "elmfire": manifiesto["elmfire"],
        "linea_de_tiempo": (vistas / "linea_tiempo.tif").exists(),
        "ventanas": metricas["ventanas"], "principal": metricas["principal"],
        "agregado_firms": metricas["agregado_firms"],
    })


@router.get(
    "/iterations/{incendio}/{protocolo}/{receta}/isochrones",
    summary="Get the iteration's predicted burned area per hour as GeoJSON",
    description=(
        "Without `ventana`, the whole chain stitched into one timeline (hours since the "
        "case start), available when every window shares the grid. With `ventana`, that "
        "window alone, in hours since the window start. Same shape as the map's isochrones: "
        "cumulative polygons with `arrival_hours`. The seed is not included."
    ),
)
async def get_iteration_isochrones(incendio: str, protocolo: str, receta: str,
                                   ventana: int | None = None):
    caso, _, _ = _caso_y_receta(incendio, protocolo, receta)
    base = _vistas() / caso.id / receta
    ruta = base / "linea_tiempo.tif" if ventana is None else base / f"v{ventana}" / "llegada.tif"
    if not ruta.exists():
        raise HTTPException(status_code=404, detail=f"Sin tiempos de llegada en {ruta.name}")
    st = ruta.stat()
    geojson = await asyncio.to_thread(_isocronas, ruta, (st.st_mtime_ns, st.st_size))
    return _envelope("success", geojson)


@router.get(
    "/iterations/{incendio}/{protocolo}/{receta}/windows/{n}/overlay",
    summary="Get one window's confusion raster as a colorized overlay",
    description=(
        "Already burned at the window start, hit, predicted without observation, and "
        "observed but not predicted. Excluded cells (no valid observation, or change the "
        "reference does not attribute to this fire) are drawn transparent."
    ),
)
async def get_window_overlay(incendio: str, protocolo: str, receta: str, n: int):
    caso, _, metricas = _caso_y_receta(incendio, protocolo, receta)
    ruta = _vistas() / caso.id / receta / f"v{n}" / "confusion.tif"
    if not ruta.exists():
        raise HTTPException(status_code=404, detail=f"Sin confusión para la ventana {n}")
    overlay = await asyncio.to_thread(render_categorical_overlay, ruta, COLORES)
    if overlay is None:
        raise HTTPException(status_code=422, detail="El ráster de confusión está vacío")
    return _envelope("success", {"ventana": n, "metrics": metricas["ventanas"][n], **overlay})


@router.get(
    "/compare",
    summary="Compare two iterations: declared factors, undeclared changes, metric deltas",
    description=(
        "`a` and `b` are `<fire>/<protocol>/<recipe>`. Only two recipes on the same protocol, "
        "or the same recipe on two protocols, are comparable; anything else is a 422."
    ),
)
async def compare_iterations(a: str, b: str):
    partes = [i.rsplit("/", 1) for i in (a, b)]
    ma, mb = (d.cargar_manifiesto(*x) for x in partes)
    xa, xb = (d.cargar_metricas(*x) for x in partes)
    if ma is None or mb is None or xa is None or xb is None:
        raise HTTPException(status_code=404, detail="Alguna de las dos iteraciones no existe")
    try:
        diff = d.comparar(ma, mb)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _envelope("success", diff | {"deltas": d.deltas(xa, xb)})


# ── visor de los harness viejos (se va en el paso 7 del plan) ─────────────────

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
        "Renders confusion.tif as a base64 Web Mercator PNG: seed, hit, predicted without "
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
