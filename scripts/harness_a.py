"""IGN-26 harness A — ventanas de 24 h ancladas a lo observado.

Para cada ventana (T0, T1] = (día d 18:00 UTC, día d+1 18:00 UTC):

1. **Semilla**: todas las detecciones FIRMS hasta T0 (el área quemada hasta ese momento).
2. **Referencia**: las detecciones nuevas de (T0, T1] que caen fuera de la semilla.
3. Corre ELMFIRE 24 h con cada uno de los tres mapas de combustible, sobre un dominio
   recortado al frente activo, y puntúa recall y precisión del anillo contra la referencia.

La ventana arranca a las 18:00 UTC para alinearse con el ciclo 18z del GFS y con el paso
de la tarde de VIIRS, así `SIMULATION_TSTART` es 0 sin perder el anclaje al reloj.

**Recall es la métrica confiable; precisión no** (IGN-26 §12.2). Una celda predicha sin
detección puede ser un falso positivo o un hueco del satélite por nubes o por falta de
pasada. La precisión se reporta como cota inferior, no como tasa de error.

El script es reanudable: cada paso se saltea si su salida ya existe, porque la corrida
completa lleva horas y un corte no puede obligar a empezar de cero.

    uv run python scripts/harness_a.py                 # prepara, corre y puntúa todo
    uv run python scripts/harness_a.py --solo-puntuar  # re-puntúa lo ya corrido
    uv run python scripts/harness_a.py --ventanas 2026-01-06 2026-01-08
"""
import argparse
import asyncio
import json
import shutil
import tempfile
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg
import numpy as np
import rasterio
import rasterio.features
from pyproj import Transformer
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds
from shapely.geometry import mapping

from app.config import resolve_data_path, settings
from app.elmfire.builder import (
    fuels_builder,
    ignition_builder,
    namelist_writer,
    perimeter_reconstruction,
    weather_builder,
)

DB_URL = "postgresql://igniteinsights:igniteinsights@localhost:5432/igniteinsights"
API = "http://localhost:8000/api/v1"
RUNNER = "http://localhost:8001/simulate"

# Preparación completa sobre el AOI definitivo: de ahí salen topografía, ADJ y dosel.
BASE_PREP = Path("data/elmfire/inputs/c27d2561-50ba-48d4-b9da-bce1f75e4926")
FUEL_MAPS = Path("data/static/fuel_maps")
RAIZ = Path("data/validation/harness_a")
ESTATICOS = ("dem.tif", "slp.tif", "asp.tif", "adj.tif", "cc.tif", "ch.tif", "cbh.tif", "cbd.tif")
MAPAS = ("worldcover", "mapbiomas", "ccsbap")
HORAS = 24
MARGEN_GRADOS = 0.10          # ~8-11 km: el frente no recorre más que eso en 24 h
# Un modelo de propagación no predice DÓNDE se inicia un foco nuevo. Las detecciones
# nuevas lejos de todo lo que ya ardía son igniciones, no avance del frente, y contarlas
# como "no predicho" mide la ignición y no la propagación. El recall cercano se restringe
# a la referencia dentro de este radio de la semilla, que es el alcance físico en 24 h.
ALCANCE_M = 5000.0
VENTANA_FRENTE = timedelta(hours=48)
CELL_HA = 0.09

# Diez ventanas repartidas en los pulsos de las cinco semanas de actividad, mezclando días
# de crecimiento fuerte y débil para que el resultado no dependa sólo de los picos.
VENTANAS = [
    "2026-01-06", "2026-01-08", "2026-01-09", "2026-01-20", "2026-01-24",
    "2026-01-25", "2026-01-31", "2026-02-01", "2026-02-06", "2026-02-07",
]


# ── datos ─────────────────────────────────────────────────────────────────────

async def detecciones(desde: datetime | None, hasta: datetime) -> list[tuple[float, float]]:
    conn = await asyncpg.connect(DB_URL)
    try:
        filas = await conn.fetch(
            """SELECT ST_X(geom) AS lon, ST_Y(geom) AS lat FROM fire_detections
               WHERE ($1::timestamptz IS NULL OR acq_datetime > $1) AND acq_datetime <= $2
                 AND ST_X(geom) BETWEEN $3 AND $4 AND ST_Y(geom) BETWEEN $5 AND $6""",
            desde, hasta, settings.aoi_west, settings.aoi_east,
            settings.aoi_south, settings.aoi_north,
        )
    finally:
        await conn.close()
    return [(f["lon"], f["lat"]) for f in filas]


async def assets_gfs(ciclo: datetime) -> dict[str, Path]:
    conn = await asyncpg.connect(DB_URL)
    try:
        filas = await conn.fetch(
            """SELECT DISTINCT ON (asset_type) asset_type, file_path FROM raster_assets
               WHERE asset_type IN ('gfs_u10','gfs_v10','gfs_t2m','gfs_rh') AND valid_time = $1
               ORDER BY asset_type, created_at DESC""",
            ciclo,
        )
    finally:
        await conn.close()
    return {f["asset_type"]: resolve_data_path(f["file_path"]) for f in filas}


def clima_sirve(rutas: dict[str, Path], bandas: int, caja: tuple[float, ...]) -> bool:
    """Que estén las cuatro variables, con bandas suficientes y cubriendo el recorte."""
    if len(rutas) < 4:
        return False
    oeste, sur, este, norte = caja
    for ruta in rutas.values():
        if not ruta.exists():
            return False
        with rasterio.open(ruta) as src:
            b = src.bounds
            fuera = b.left > oeste or b.right < este or b.bottom > sur or b.top < norte
            if src.count < bandas or fuera:
                return False
    return True


def post(url: str, cuerpo: dict | None = None, timeout: int = 7200) -> dict:
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(url, data=datos, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


# ── rásters ───────────────────────────────────────────────────────────────────

def ventana_recorte(caja: tuple[float, float, float, float]) -> Window:
    with rasterio.open(BASE_PREP / "dem.tif") as ref:
        izq, abajo, der, arriba = transform_bounds("EPSG:4326", ref.crs, *caja)
        w = from_bounds(izq, abajo, der, arriba, ref.transform).round_offsets().round_lengths()
        return w.intersection(Window(0, 0, ref.width, ref.height))


def recortar(origen: Path, destino: Path, w: Window) -> None:
    with rasterio.open(origen) as src:
        datos = src.read(window=w)
        perfil = src.profile.copy()
        for clave in ("blockxsize", "blockysize", "tiled"):
            perfil.pop(clave, None)
        perfil.update(height=int(w.height), width=int(w.width),
                      transform=src.window_transform(w))
    with rasterio.open(destino, "w", **perfil) as dst:
        dst.write(datos)


def mascara_de_puntos(puntos: list[tuple[float, float]], referencia: Path,
                      buffer_m: float | None = None) -> np.ndarray:
    """Rasteriza detecciones con el mismo buffer que usa la semilla, para que la
    referencia y la semilla estén construidas con la misma regla."""
    with rasterio.open(referencia) as ref:
        forma = (ref.height, ref.width)
    if not puntos:
        return np.zeros(forma, dtype=bool)
    with tempfile.TemporaryDirectory() as tmp:
        extra = {"buffer_m": buffer_m} if buffer_m else {}
        phi, _ = ignition_builder.build_ignition_layer(puntos, referencia, Path(tmp), **extra)
        with rasterio.open(phi) as src:
            return src.read(1) <= 0


def alcance_desde(puntos: list[tuple[float, float]], referencia: Path,
                  radio_m: float) -> np.ndarray:
    """Hasta dónde puede llegar el frente en la ventana: el perímetro de la semilla
    dilatado `radio_m`. `build_ignition_layer` no sirve para esto — su `buffer_m` sólo
    afecta a las detecciones aisladas, no a las que entran en una envolvente."""
    with rasterio.open(referencia) as ref:
        crs, transform, forma = ref.crs, ref.transform, (ref.height, ref.width)
    if not puntos:
        return np.zeros(forma, dtype=bool)
    tr = Transformer.from_crs("EPSG:4326", str(crs), always_xy=True)
    proyectados = [tr.transform(lon, lat) for lon, lat in puntos]
    poligono = perimeter_reconstruction.reconstruct_burn_polygon(proyectados).buffer(radio_m)
    pintado = rasterio.features.rasterize(
        [(mapping(poligono), 1)], out_shape=forma, transform=transform, dtype="uint8"
    )
    return pintado.astype(bool)


# ── pasos ─────────────────────────────────────────────────────────────────────

def preparar(dia: str) -> dict:
    t0 = datetime.fromisoformat(f"{dia}T18:00:00+00:00")
    t1 = t0 + timedelta(hours=HORAS)
    base = RAIZ / dia / "base"
    meta_path = RAIZ / dia / "meta.json"
    if meta_path.exists() and (base / "elmfire.data").exists():
        return json.loads(meta_path.read_text())
    base.mkdir(parents=True, exist_ok=True)

    semilla_pts = asyncio.run(detecciones(None, t0))
    nuevas_pts = asyncio.run(detecciones(t0, t1))
    frente = asyncio.run(detecciones(t0 - VENTANA_FRENTE, t1))
    if not frente:
        raise SystemExit(f"{dia}: sin detecciones en el frente activo")

    lons, lats = zip(*frente)
    caja = (min(lons) - MARGEN_GRADOS, min(lats) - MARGEN_GRADOS,
            max(lons) + MARGEN_GRADOS, max(lats) + MARGEN_GRADOS)
    w = ventana_recorte(caja)
    print(f"  {dia}: recorte {int(w.width)}×{int(w.height)} celdas · semilla "
          f"{len(semilla_pts)} det. · nuevas {len(nuevas_pts)} det.", flush=True)

    for nombre in ESTATICOS:
        recortar(BASE_PREP / nombre, base / nombre, w)
    for mapa in MAPAS:
        recortar(FUEL_MAPS / f"fbfm40_{mapa}.tif", base / f"fbfm40_{mapa}.tif", w)
    referencia = base / "dem.tif"

    # Clima: ciclo 18z del día d, 25 bandas horarias. Si no está o no cubre, se ingesta.
    rutas = asyncio.run(assets_gfs(t0))
    if not clima_sirve(rutas, HORAS + 1, caja):
        print(f"  {dia}: ingestando GFS {dia} 18z …", flush=True)
        post(f"{API}/ingestion/gfs/run?gfs_date={dia}", timeout=3600)
        rutas = asyncio.run(assets_gfs(t0))
        if not clima_sirve(rutas, HORAS + 1, caja):
            raise SystemExit(f"{dia}: el GFS ingestado no alcanza (bandas o cobertura)")
    weather_builder.derive_wind(rutas["gfs_u10"], rutas["gfs_v10"], referencia, base)
    weather_builder.derive_moisture(rutas["gfs_t2m"], rutas["gfs_rh"], referencia, base)

    ignition_builder.build_ignition_layer(semilla_pts, referencia, base)
    with rasterio.open(base / "phi.tif") as src:
        semilla = src.read(1) <= 0
    nuevas = mascara_de_puntos(nuevas_pts, referencia) & ~semilla
    alcance = alcance_desde(semilla_pts, referencia, ALCANCE_M)
    perfil = rasterio.open(referencia).profile | {"dtype": "uint8", "nodata": None, "count": 1}
    for nombre, datos in (("semilla.tif", semilla), ("referencia.tif", nuevas),
                          ("alcance.tif", alcance)):
        with rasterio.open(base / nombre, "w", **perfil) as dst:
            dst.write(datos.astype("uint8"), 1)

    shutil.copy2(fuels_builder.FUEL_MODEL_TABLE, base / namelist_writer.FUEL_MODEL_FILE)
    namelist_writer.write_namelist(
        base.resolve(), (RAIZ / dia / "salidas").resolve(), simulation_hours=HORAS,
        output_path=base / "elmfire.data", simulation_tstart_s=0.0,
    )

    meta = {
        "dia": dia, "t0": t0.isoformat(), "t1": t1.isoformat(),
        "ciclo_gfs": t0.isoformat(), "caja_wgs84": caja,
        "recorte": {"col_off": int(w.col_off), "row_off": int(w.row_off),
                    "width": int(w.width), "height": int(w.height)},
        "detecciones_semilla": len(semilla_pts), "detecciones_nuevas": len(nuevas_pts),
        "semilla_ha": float(semilla.sum() * CELL_HA),
        "referencia_ha": float(nuevas.sum() * CELL_HA),
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta


def correr(dia: str, mapa: str) -> None:
    nombre = f"ha_{dia}_{mapa}"
    inputs = Path("data/elmfire/inputs") / nombre
    outputs = Path("data/elmfire/outputs") / nombre
    if sorted(outputs.glob("time_of_arrival*.tif")):
        return
    base = RAIZ / dia / "base"
    shutil.rmtree(inputs, ignore_errors=True)
    inputs.mkdir(parents=True)
    outputs.mkdir(parents=True, exist_ok=True)

    for f in base.iterdir():
        propios = ("elmfire.data", "semilla.tif", "referencia.tif")
        if f.name.startswith("fbfm40_") or f.name in propios:
            continue
        (inputs / f.name).hardlink_to(f)
    (inputs / "fbfm40.tif").hardlink_to(base / f"fbfm40_{mapa}.tif")

    texto = (base / "elmfire.data").read_text()
    texto = texto.replace(str(base.resolve()), f"/app/data/elmfire/inputs/{nombre}")
    texto = texto.replace(str((RAIZ / dia / "salidas").resolve()),
                          f"/app/data/elmfire/outputs/{nombre}")
    (inputs / "elmfire.data").write_text(texto)

    print(f"  {dia} · {mapa}: corriendo …", flush=True)
    inicio = datetime.now(UTC)
    post(RUNNER, {
        "elmfire_data_path": f"/app/data/elmfire/inputs/{nombre}/elmfire.data",
        "inputs_dir": f"/app/data/elmfire/inputs/{nombre}",
        "outputs_dir": f"/app/data/elmfire/outputs/{nombre}",
        "simulation_hours": HORAS, "dtdump_s": 3600.0,
    })
    print(f"  {dia} · {mapa}: listo en {(datetime.now(UTC) - inicio).seconds // 60} min",
          flush=True)


def puntuar(dia: str, mapa: str) -> dict | None:
    nombre = f"ha_{dia}_{mapa}"
    toa = sorted(Path("data/elmfire/outputs", nombre).glob("time_of_arrival*.tif"))
    if not toa:
        return None
    base = RAIZ / dia / "base"
    with rasterio.open(toa[-1]) as src:
        quemado = src.read(1) > 0
    with rasterio.open(base / "semilla.tif") as src:
        semilla = src.read(1).astype(bool)
        perfil = src.profile
    with rasterio.open(base / "referencia.tif") as src:
        ref = src.read(1).astype(bool)
    if not (base / "alcance.tif").exists():   # backfill para ventanas preparadas antes
        semilla_pts = asyncio.run(detecciones(None, datetime.fromisoformat(
            json.loads((RAIZ / dia / "meta.json").read_text())["t0"])))
        alcance = alcance_desde(semilla_pts, base / "dem.tif", ALCANCE_M)
        with rasterio.open(base / "alcance.tif", "w", **(perfil | {"dtype": "uint8"})) as dst:
            dst.write(alcance.astype("uint8"), 1)
    with rasterio.open(base / "alcance.tif") as src:
        alcance = src.read(1).astype(bool)

    pred = quemado & ~semilla
    tp, fp, fn = pred & ref, pred & ~ref, ~pred & ref
    # 0 nada · 1 semilla · 2 acierto · 3 predicho sin detección · 4 detección no predicha
    confusion = np.zeros(semilla.shape, dtype="uint8")
    confusion[semilla] = 1
    confusion[tp] = 2
    confusion[fp] = 3
    confusion[fn] = 4
    salida = RAIZ / dia / mapa
    salida.mkdir(parents=True, exist_ok=True)
    with rasterio.open(salida / "confusion.tif", "w", **(perfil | {"dtype": "uint8"})) as dst:
        dst.write(confusion, 1)

    n_tp, n_fp, n_fn = int(tp.sum()), int(fp.sum()), int(fn.sum())
    # Recall cercano: sólo sobre la referencia alcanzable desde la semilla en 24 h.
    tp_cerca, fn_cerca = int((tp & alcance).sum()), int((fn & alcance).sum())
    metricas = {
        "dia": dia, "mapa": mapa,
        "acierto_ha": n_tp * CELL_HA, "sin_deteccion_ha": n_fp * CELL_HA,
        "no_predicho_ha": n_fn * CELL_HA, "predicho_ha": (n_tp + n_fp) * CELL_HA,
        "recall": n_tp / (n_tp + n_fn) if n_tp + n_fn else None,
        "precision": n_tp / (n_tp + n_fp) if n_tp + n_fp else None,
        "iou": n_tp / (n_tp + n_fp + n_fn) if n_tp + n_fp + n_fn else None,
        "tp": n_tp, "fp": n_fp, "fn": n_fn,
        "recall_cercano": tp_cerca / (tp_cerca + fn_cerca) if tp_cerca + fn_cerca else None,
        "referencia_cercana_ha": (tp_cerca + fn_cerca) * CELL_HA,
        "tp_cerca": tp_cerca, "fn_cerca": fn_cerca,
    }
    (salida / "metrics.json").write_text(json.dumps(metricas, indent=2))
    return metricas


def resumir(resultados: list[dict]) -> dict:
    resumen: dict = {
        "harness": "A", "horas": HORAS,
        "ventanas": sorted({r["dia"] for r in resultados}), "por_mapa": {},
    }
    print(f"\n{'mapa':12s}{'ventanas':>9s}{'recall':>9s}{'r. cercano':>12s}"
          f"{'precisión':>11s}{'IoU':>8s}{'acierto ha':>12s}")
    for mapa in MAPAS:
        filas = [r for r in resultados if r["mapa"] == mapa]
        tp = sum(r["tp"] for r in filas)
        fp = sum(r["fp"] for r in filas)
        fn = sum(r["fn"] for r in filas)
        tp_c = sum(r["tp_cerca"] for r in filas)
        fn_c = sum(r["fn_cerca"] for r in filas)
        agregado = {
            "ventanas": len(filas),
            "recall": tp / (tp + fn) if tp + fn else None,
            "precision": tp / (tp + fp) if tp + fp else None,
            "iou": tp / (tp + fp + fn) if tp + fp + fn else None,
            "acierto_ha": tp * CELL_HA,
            "recall_cercano": tp_c / (tp_c + fn_c) if tp_c + fn_c else None,
            # recall por ventana: la dispersión dice si el promedio esconde algo
            "recall_por_ventana": [r["recall"] for r in sorted(filas, key=lambda r: r["dia"])],
        }
        resumen["por_mapa"][mapa] = agregado
        fmt = lambda v: f"{v:.3f}" if v is not None else "  —"  # noqa: E731
        print(f"{mapa:12s}{len(filas):9d}{fmt(agregado['recall']):>9s}"
              f"{fmt(agregado['recall_cercano']):>12s}{fmt(agregado['precision']):>11s}"
              f"{fmt(agregado['iou']):>8s}{agregado['acierto_ha']:12,.0f}")
    (RAIZ / "summary.json").write_text(json.dumps(resumen, indent=2))
    return resumen


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ventanas", nargs="+", default=VENTANAS)
    ap.add_argument("--solo-puntuar", action="store_true")
    args = ap.parse_args()

    for dia in args.ventanas:
        if not args.solo_puntuar:
            preparar(dia)
            for mapa in MAPAS:
                correr(dia, mapa)

    resultados = [m for dia in args.ventanas for mapa in MAPAS if (m := puntuar(dia, mapa))]
    print("\n=== Por ventana ===")
    for r in sorted(resultados, key=lambda r: (r["dia"], r["mapa"])):
        rec = f"{r['recall']:.3f}" if r["recall"] is not None else "—"
        pre = f"{r['precision']:.3f}" if r["precision"] is not None else "—"
        print(f"  {r['dia']} {r['mapa']:11s} recall {rec:>6s} · precisión {pre:>6s} · "
              f"predicho {r['predicho_ha']:8,.0f} ha")
    resumir(resultados)


if __name__ == "__main__":
    main()
