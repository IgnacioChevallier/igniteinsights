"""Benchmark de validación: receta × caso, inmutable y reanudable (IGN-26 §Benchmark).

    uv run python scripts/benchmark.py empaquetar puerto-patriada-2026/ventanas-firms
    uv run python scripts/benchmark.py correr     puerto-patriada-2026/ventanas-firms legacy-ccsbap
    uv run python scripts/benchmark.py puntuar    puerto-patriada-2026/ventanas-firms legacy-ccsbap
    uv run python scripts/benchmark.py tabla      puerto-patriada-2026/ventanas-firms
    uv run python scripts/benchmark.py comparar   <caso>/<receta> <caso>/<receta>
    uv run python scripts/benchmark.py verificar  <caso> <receta>
    uv run python scripts/benchmark.py materializar <caso> <receta> <ventana>

Casos y recetas viven en `benchmarks/` (en git); los objetos en `data/benchmark/objetos/`.
Corre desde el host contra el runner de docker-compose (`docker compose up -d elmfire-runner`).
"""
import argparse
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import rasterio.features
from pyproj import Transformer
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds
from shapely.geometry import Point, mapping

# El .env apunta al nombre del servicio dentro de la red de Docker; desde el host es localhost.
os.environ.setdefault("ELMFIRE_RUNNER_URL", "http://localhost:8001")

from app.elmfire.builder import (  # noqa: E402
    fuels_builder,
    ignition_builder,
    perimeter_reconstruction,
    weather_builder,
)
from app.ingestion.meteorology.gfs.client import GFSClient  # noqa: E402
from app.ingestion.satellite.firms.client import FIRMSClient  # noqa: E402
from app.validation import almacen, cadena  # noqa: E402
from app.validation import definiciones as d  # noqa: E402
from app.validation import puntuacion as p  # noqa: E402

# Nombre en el paquete ← nombre en las preparaciones del harness viejo, con el año de
# cada insumo explícito (IGN-26 §fuga temporal).
LEGADO_COMBUSTIBLES = {"fbfm40_worldcover2021.tif": "worldcover",
                       "fbfm40_mapbiomas2024.tif": "mapbiomas",
                       "fbfm40_ccsbap2017.tif": "ccsbap"}


# ── empaquetado ───────────────────────────────────────────────────────────────

def _guardar_array(datos: np.ndarray, grilla: p.Grilla, dtype: str, nodata=None) -> str:
    perfil = grilla.perfil | {"dtype": dtype, "count": 1, "nodata": nodata}
    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "capa.tif"
        with rasterio.open(ruta, "w", **perfil) as dst:
            dst.write(datos.astype(dtype), 1)
        return almacen.guardar(ruta)


def _discos(puntos: list[tuple[float, float]], grilla: p.Grilla, radio_m: float) -> np.ndarray:
    """Unión de discos de `radio_m` alrededor de cada detección (lon, lat)."""
    if not puntos:
        return np.zeros(grilla.shape, dtype=bool)
    tr = Transformer.from_crs("EPSG:4326", str(grilla.crs), always_xy=True)
    formas = [(mapping(Point(*tr.transform(lon, lat)).buffer(radio_m)), 1) for lon, lat in puntos]
    return rasterio.features.rasterize(formas, out_shape=grilla.shape, transform=grilla.transform,
                                       dtype="uint8").astype(bool)


def _referencia_cicatriz(caso: d.Caso, dem: Path,
                         df: pd.DataFrame | None = None) -> tuple[dict[str, str], dict]:
    """La cicatriz, lo excluido y las bandas de % quemado, ya sobre la grilla del caso.

    Con `hasta_horizonte`, la cicatriz final se trunca a lo que ardía al terminar la última
    ventana: sus celdas a menos de un píxel VIIRS de alguna detección hasta ese momento. El
    resto de la cicatriz ardió después (o no se vio) y va a la exclusión: no es acierto ni
    error. Sin esto, un incendio que siguió creciendo semanas se puntúa a 5 días contra su
    cicatriz de 3 meses (RESULTADOS-CSS-BAP §2).
    """
    ref = caso.datos["referencias"]["cicatriz"]
    run_dir = Path(ref["run"])
    grilla = p.Grilla(dem)
    positivo, excluido = p.cargar_cicatriz(
        run_dir, grilla, tuple(ref.get("excluidas", p.EXCLUIDAS_POR_DEFECTO)))
    extra = {}
    if ref.get("hasta_horizonte"):
        if df is None:
            raise ValueError(f"{caso.id}: `hasta_horizonte` necesita las detecciones FIRMS")
        vistas = _discos(_puntos(df, None, caso.ventanas[-1].fin), grilla,
                         perimeter_reconstruction.VIIRS_PIXEL_M)
        extra = {"cicatriz_final_ha": float(positivo.sum() * grilla.celda_ha),
                 "cicatriz_horizonte_ha": float((positivo & vistas).sum() * grilla.celda_ha)}
        excluido = excluido | (positivo & ~vistas)
        positivo = positivo & vistas
    # Un bit por banda: los tiles vecinos se solapan en el borde y esas celdas cuentan en
    # las dos bandas, como en el harness B original.
    bandas = np.zeros(grilla.shape, dtype="uint8")
    for bit, huella in enumerate(p.bandas_pct(run_dir, grilla).values()):
        bandas[huella] |= 1 << bit
    archivos = {"cicatriz.tif": _guardar_array(positivo, grilla, "uint8"),
                "excluido.tif": _guardar_array(excluido, grilla, "uint8"),
                "bandas_pct.tif": _guardar_array(bandas, grilla, "uint8")}
    origen = {"cicatriz_run": str(run_dir),
              "cicatriz_run_json_sha": almacen.sha256(run_dir / "run.json"),
              "bandas_pct": list(p.bandas_pct(run_dir, grilla))} | extra
    return archivos, origen


def _legado_harness_a(caso: d.Caso) -> dict:
    """Las diez ventanas del harness A, tal como se prepararon (recorte propio cada una)."""
    raiz = Path(caso.datos["empaquetado"]["raiz"])
    ventanas = []
    for v in caso.ventanas:
        base = raiz / f"{v.t0:%Y-%m-%d}" / "base"
        meta = json.loads((base.parent / "meta.json").read_text())
        if datetime.fromisoformat(meta["t0"]) != v.t0:
            raise ValueError(f"{base}: t0 {meta['t0']} no coincide con el caso ({v.t0})")
        archivos = {n: almacen.guardar(base / n) for n in cadena.ESTATICOS}
        archivos |= {n: almacen.guardar(base / f"fbfm40_{viejo}.tif")
                     for n, viejo in LEGADO_COMBUSTIBLES.items()}
        archivos |= {"phi.tif": almacen.guardar(base / "phi.tif"),
                     "ref_firms.tif": almacen.guardar(base / "referencia.tif"),
                     "alcance.tif": almacen.guardar(base / "alcance.tif")}
        ventanas.append(archivos)
    return {"comunes": {}, "ventanas": ventanas, "origen": {"legado": str(raiz)}}


CLIMA = ("ws.tif", "wd.tif", "m1.tif", "m10.tif", "m100.tif")


def _clima_ciclo(ciclo: datetime, horas: int, dem: Path) -> dict[str, str]:
    """Un ciclo GFS con f000..f`horas`, derivado sobre `dem`."""
    from app.config import settings
    from app.ingestion.meteorology.gfs.schemas import GFSCycleInfo

    info = GFSCycleInfo(date=ciclo.date().isoformat(), cycle_hour=ciclo.hour)
    caja = (settings.aoi_west - MARGEN_GFS_GRADOS, settings.aoi_south - MARGEN_GFS_GRADOS,
            settings.aoi_east + MARGEN_GFS_GRADOS, settings.aoi_north + MARGEN_GFS_GRADOS)
    tmp = Path(tempfile.mkdtemp())
    for var in ("u10", "v10", "t2m", "rh"):
        GFSClient().download_variable(info, var, *caja, tmp / f"{var}.tif",
                                      forecast_hours=list(range(horas + 1)))
    weather_builder.derive_wind(tmp / "u10.tif", tmp / "v10.tif", dem, tmp)
    weather_builder.derive_moisture(tmp / "t2m.tif", tmp / "rh.tif", dem, tmp)
    return {n: almacen.guardar(tmp / n) for n in CLIMA}


def _legado_harness_b(caso: d.Caso) -> dict:
    """La corrida de 12 h del harness B: tres directorios que sólo difieren en fbfm40."""
    dirs = {n: Path(caso.datos["empaquetado"]["corridas"][viejo])
            for n, viejo in LEGADO_COMBUSTIBLES.items()}
    base = dirs["fbfm40_ccsbap2017.tif"]
    clima_nuevo = bool(caso.datos["empaquetado"].get("clima_gfs"))
    compartidos = tuple(n for n in (*cadena.ESTATICOS, "phi.tif")
                        if not (clima_nuevo and n in CLIMA))
    comunes = {n: almacen.guardar(base / n) for n in compartidos}
    for nombre, otro in dirs.items():
        distintos = [n for n in compartidos if almacen.sha256(otro / n) != comunes[n]]
        if distintos:
            raise ValueError(f"{otro} difiere de {base} en {distintos}, no sólo en fbfm40")
        comunes[nombre] = almacen.guardar(otro / "fbfm40.tif")
    clima = caso.datos["empaquetado"].get("clima_gfs")
    if clima:   # el clima original era corto: se re-deriva del mismo ciclo con más bandas
        comunes |= _clima_ciclo(datetime.fromisoformat(clima["ciclo"]), clima["horas"],
                                base / "dem.tif")
    archivos, origen = _referencia_cicatriz(caso, base / "dem.tif")
    return {"comunes": comunes | archivos, "ventanas": [{}],
            "origen": origen | {"legado": {n: str(r) for n, r in dirs.items()}}}


# ── casos históricos: FIRMS SP + GFS encadenado ───────────────────────────────

ESTATICOS_PREP = ("dem.tif", "slp.tif", "asp.tif", "adj.tif", "cc.tif", "ch.tif", "cbh.tif",
                  "cbd.tif")
SEMILLA_PUNTUAL_M = 45.0     # una ignición puntual: ~3 × 3 celdas, no un píxel VIIRS
MEDIO_PIXEL_VIIRS_M = perimeter_reconstruction.VIIRS_PIXEL_M / 2
MARGEN_GFS_GRADOS = 0.5      # celdas de 0,25° de sobra para interpolar hasta el borde


def _recortar(origen: Path, caja: tuple[float, float, float, float]) -> tuple[Path, Window]:
    """Recorta un ráster de la grilla del AOI a la caja del caso, en un archivo temporal."""
    with rasterio.open(origen) as src:
        izq, abajo, der, arriba = transform_bounds("EPSG:4326", src.crs, *caja)
        w = from_bounds(izq, abajo, der, arriba, src.transform).round_offsets().round_lengths()
        w = w.intersection(Window(0, 0, src.width, src.height))
        datos = src.read(window=w)
        perfil = src.profile.copy()
        for clave in ("blockxsize", "blockysize", "tiled"):
            perfil.pop(clave, None)
        perfil.update(height=int(w.height), width=int(w.width), transform=src.window_transform(w))
    destino = Path(tempfile.mkdtemp()) / origen.name
    with rasterio.open(destino, "w", **perfil) as dst:
        dst.write(datos)
    return destino, w


def _firms(caso: d.Caso) -> pd.DataFrame:
    """Todas las detecciones SP de la caja, desde el día anterior a la primera ventana (o desde
    `referencias.firms.desde`, cuando la semilla es lo que FIRMS vio en días previos)."""
    firms = caso.datos["referencias"]["firms"]
    desde = (datetime.fromisoformat(firms["desde"]).date() if "desde" in firms
             else (caso.ventanas[0].inicio - timedelta(days=1)).date())
    return _firms_rango(caso.datos["caja_wgs84"], desde,
                        caso.ventanas[-1].fin.date(),
                        caso.datos["referencias"]["firms"]["fuentes"])


def _firms_rango(caja, desde, hasta, fuentes) -> pd.DataFrame:
    marcos, dia = [], desde
    while dia <= hasta:   # FIRMS limita day_range: de a 5 días
        dias = min(5, (hasta - dia).days + 1)
        marco = FIRMSClient().fetch_active_fires(*caja, day_range=dias, start_date=dia,
                                                 sources=fuentes)
        marcos.append(marco)
        dia += timedelta(days=dias)
    marcos = [m for m in marcos if len(m)]
    if not marcos:
        return pd.DataFrame(columns=["latitude", "longitude", "acq_date", "acq_time", "source",
                                     "acq_datetime"])
    df = pd.concat(marcos, ignore_index=True)
    df["acq_datetime"] = pd.to_datetime(
        df["acq_date"] + " " + df["acq_time"].astype(str).str.zfill(4), format="%Y-%m-%d %H%M",
        utc=True)
    return df.drop_duplicates(["latitude", "longitude", "acq_datetime", "source"]).sort_values(
        "acq_datetime").reset_index(drop=True)


def _puntos(df: pd.DataFrame, desde: datetime | None, hasta: datetime) -> list[tuple[float, float]]:
    sel = df[(df["acq_datetime"] <= hasta) & ((df["acq_datetime"] > desde) if desde else True)]
    return list(zip(sel["longitude"], sel["latitude"]))


def _mascara(puntos: list[tuple[float, float]], dem: Path,
             buffer_m: float | None = None) -> np.ndarray:
    """Misma regla que la semilla (reconstrucción de perímetro) para que semilla y referencia
    se construyan igual, como en el harness A."""
    with rasterio.open(dem) as ref:
        forma = (ref.height, ref.width)
    if not puntos:
        return np.zeros(forma, dtype=bool)
    with tempfile.TemporaryDirectory() as tmp:
        extra = {"buffer_m": buffer_m} if buffer_m else {}
        phi, _ = ignition_builder.build_ignition_layer(puntos, dem, Path(tmp), **extra)
        with rasterio.open(phi) as src:
            return src.read(1) <= 0


def _alcance(puntos: list[tuple[float, float]], dem: Path, radio_m: float) -> np.ndarray:
    """El perímetro de lo quemado dilatado `radio_m`: hasta dónde llega el frente en 24 h."""
    with rasterio.open(dem) as ref:
        crs, transform, forma = ref.crs, ref.transform, (ref.height, ref.width)
    if not puntos:
        return np.zeros(forma, dtype=bool)
    tr = Transformer.from_crs("EPSG:4326", str(crs), always_xy=True)
    poligono = perimeter_reconstruction.reconstruct_burn_polygon(
        [tr.transform(lon, lat) for lon, lat in puntos]).buffer(radio_m)
    return rasterio.features.rasterize([(mapping(poligono), 1)], out_shape=forma,
                                       transform=transform, dtype="uint8").astype(bool)


def _horas_deteccion(df: pd.DataFrame, inicio: datetime, fin: datetime, dem: Path) -> np.ndarray:
    """Horas desde `inicio` de la primera detección que cubre cada celda (-1 si ninguna).
    Cada detección cubre su medio píxel VIIRS alrededor del centro."""
    with rasterio.open(dem) as ref:
        crs, transform, forma = ref.crs, ref.transform, (ref.height, ref.width)
    horas = np.full(forma, np.inf)
    sel = df[(df["acq_datetime"] > inicio) & (df["acq_datetime"] <= fin)]
    tr = Transformer.from_crs("EPSG:4326", str(crs), always_xy=True)
    for _, fila in sel.iterrows():
        x, y = tr.transform(fila["longitude"], fila["latitude"])
        disco = rasterio.features.rasterize([(mapping(Point(x, y).buffer(MEDIO_PIXEL_VIIRS_M)), 1)],
                                            out_shape=forma, transform=transform, dtype="uint8")
        h = (fila["acq_datetime"].to_pydatetime() - inicio).total_seconds() / 3600
        horas = np.where(disco.astype(bool), np.minimum(horas, h), horas)
    return np.where(np.isinf(horas), -1.0, horas)


def _clima(caso: d.Caso, dem: Path) -> list[dict[str, str]]:
    """Análisis GFS encadenados para toda la cadena, cortados por ventana y llevados a la
    grilla del caso (la banda 0 de cada ventana es su inicio: TSTART = 0)."""
    w, s_, e, n = caso.datos["caja_wgs84"]
    m = MARGEN_GFS_GRADOS
    caja = (w - m, s_ - m, e + m, n + m)
    inicio = caso.ventanas[0].inicio
    total = int((caso.ventanas[-1].fin - inicio).total_seconds() // 3600)
    # Las series crudas se guardan: bajarlas lleva ~1 h por caso y re-empaquetar no debe
    # repetirlo. Lo que entra al paquete (y a su hash) es lo derivado sobre la grilla.
    clave = f"{inicio:%Y%m%dT%H}_{total}h_" + "_".join(f"{v:.2f}" for v in caja)
    series = Path("data/benchmark/cache/gfs") / clave
    for var in ("u10", "v10", "t2m", "rh"):
        if (series / f"{var}.tif").exists():
            continue
        print(f"  GFS {var}: {total + 1} bandas horarias …", flush=True)
        GFSClient().download_analysis_series(var, inicio, total, *caja, series / f"{var}.tif")
    # Humedad muerta con historial de secado: una serie t2m/rh que arranca `retardo` horas
    # antes de la ignición, para el modelo de retardo (weather_builder.derive_moisture_timelag).
    retardo = int(caso.datos["empaquetado"].get("humedad_retardo_h", 0))
    if retardo:
        previa = Path("data/benchmark/cache/gfs") / (
            f"{inicio - timedelta(hours=retardo):%Y%m%dT%H}_{total + retardo}h_"
            + "_".join(f"{v:.2f}" for v in caja))
        for var in ("t2m", "rh"):
            if not (previa / f"{var}.tif").exists():
                print(f"  GFS {var} con {retardo} h de historia …", flush=True)
                GFSClient().download_analysis_series(
                    var, inicio - timedelta(hours=retardo), total + retardo, *caja,
                    previa / f"{var}.tif")
    # El clima crudo (T y HR a 0,25° y el terreno del GFS, donde valen) pesa poco y deja
    # calcular en la corrida las humedades con criterio (app/validation/humedad.py).
    crudo = bool(caso.datos["empaquetado"].get("clima_crudo"))
    if crudo and not (series / "orog.tif").exists():
        GFSClient().download_analysis_series("orog", inicio, 0, *caja, series / "orog.tif")
    salida = []
    for v in caso.ventanas:
        desde = int((v.inicio - inicio).total_seconds() // 3600)
        cortes = Path(tempfile.mkdtemp())
        for var in ("u10", "v10", "t2m", "rh"):
            with rasterio.open(series / f"{var}.tif") as src:
                datos = src.read(list(range(desde + 1, desde + v.horas + 2)))
                perfil = src.profile | {"count": datos.shape[0]}
            with rasterio.open(cortes / f"{var}.tif", "w", **perfil) as dst:
                dst.write(datos)
        weather_builder.derive_wind(cortes / "u10.tif", cortes / "v10.tif", dem, cortes)
        weather_builder.derive_moisture(cortes / "t2m.tif", cortes / "rh.tif", dem, cortes)
        archivos = {n_: almacen.guardar(cortes / n_)
                    for n_ in ("ws.tif", "wd.tif", "m1.tif", "m10.tif", "m100.tif")}
        if crudo:   # para las humedades con criterio que se calculan en la corrida
            archivos |= {"t2m_gfs.tif": almacen.guardar(cortes / "t2m.tif"),
                         "rh_gfs.tif": almacen.guardar(cortes / "rh.tif"),
                         "orog_gfs.tif": almacen.guardar(series / "orog.tif")}
        if retardo:
            hasta = retardo + desde + v.horas + 1   # bandas de la serie hasta el fin de la ventana
            for var in ("t2m", "rh"):
                with rasterio.open(previa / f"{var}.tif") as src:
                    datos = src.read(list(range(1, hasta + 1)))
                    perfil = src.profile | {"count": datos.shape[0]}
                with rasterio.open(cortes / f"{var}_hist.tif", "w", **perfil) as dst:
                    dst.write(datos)
            rutas = weather_builder.derive_moisture_timelag(
                cortes / "t2m_hist.tif", cortes / "rh_hist.tif", dem, cortes,
                skip_bands=retardo + desde, suffix="_retardo")
            archivos |= {r.name: almacen.guardar(r) for r in rutas}
        salida.append(archivos)
    return salida


def _puntos_ignicion(semilla: dict) -> list[tuple[float, float]]:
    """Tipos de semilla inicial: `punto` (una ignición), `puntos` (varios focos a la misma
    hora) y `firms` (lo observado por FIRMS hasta el inicio, para arrancar un caso en la fase
    explosiva de un incendio que llevaba días latente)."""
    if semilla["tipo"] == "punto":
        return [(semilla["lon"], semilla["lat"])]
    if semilla["tipo"] == "puntos":
        return [(pt["lon"], pt["lat"]) for pt in semilla["puntos"]]
    if semilla["tipo"] == "firms":
        return []
    raise ValueError(f"semilla de tipo desconocido: {semilla['tipo']}")


def _firms_gfs(caso: d.Caso) -> dict:
    datos = caso.datos
    caja = tuple(datos["caja_wgs84"])
    prep = Path(datos["empaquetado"]["preparacion"])
    comunes, recortes = {}, {}
    for nombre in ESTATICOS_PREP:
        recortes[nombre], _ = _recortar(prep / nombre, caja)
        comunes[nombre] = almacen.guardar(recortes[nombre])
    for nombre, ruta in datos["empaquetado"]["mapas"].items():
        comunes[nombre] = almacen.guardar(_recortar(Path(ruta), caja)[0])
    comunes["fuel_models.csv"] = almacen.guardar(fuels_builder.FUEL_MODEL_TABLE)
    dem = recortes["dem.tif"]
    grilla = p.Grilla(dem)

    df = _firms(caso)
    with tempfile.TemporaryDirectory() as tmp:
        csv = Path(tmp) / "firms.csv"
        df.to_csv(csv, index=False)
        comunes["firms.csv"] = almacen.guardar(csv)
    print(f"  FIRMS: {len(df)} detecciones SP, {df['acq_datetime'].min()} → "
          f"{df['acq_datetime'].max()}", flush=True)

    semilla = datos["semilla_inicial"]
    punto = _puntos_ignicion(semilla)
    ignicion = np.zeros(grilla.shape, dtype=bool)
    for pt in punto:   # uno por uno: la reconstrucción de perímetro uniría dos focos cercanos
        ignicion |= _mascara([pt], dem, SEMILLA_PUNTUAL_M)
    alcance_m = datos["referencias"]["firms"].get("alcance_m", 5000.0)
    ventanas = []
    for n, (v, clima) in enumerate(zip(caso.ventanas, _clima(caso, dem))):
        antes = _puntos(df, None, v.inicio)
        if n == 0 and semilla["tipo"] != "firms":
            observado = ignicion
        else:   # lo observado hasta el inicio: FIRMS más los puntos de ignición
            observado = ignicion | _mascara(antes, dem)
        with tempfile.TemporaryDirectory() as tmp:
            phi = ignition_builder.build_ignition_from_mask(observado, dem, Path(tmp))
            archivos = {"phi.tif": almacen.guardar(phi)}
        nuevas = _mascara(_puntos(df, v.inicio, v.fin), dem) & ~observado
        archivos |= {
            "ref_firms.tif": _guardar_array(nuevas, grilla, "uint8"),
            "ref_firms_horas.tif": _guardar_array(
                _horas_deteccion(df, v.inicio, v.fin, dem), grilla, "float32", -1.0),
            "alcance.tif": _guardar_array(_alcance(punto + antes, dem, alcance_m), grilla, "uint8"),
        }
        ventanas.append(archivos | clima)
        print(f"  ventana {n}: {nuevas.sum() * grilla.celda_ha:,.0f} ha de detecciones nuevas",
              flush=True)

    cicatriz, origen = _referencia_cicatriz(caso, dem, df)
    return {"comunes": comunes | cicatriz, "ventanas": ventanas,
            "origen": origen | {"preparacion": str(prep), "firms_detecciones": len(df)}}


EMPAQUETADORES = {"legado_harness_a": _legado_harness_a, "legado_harness_b": _legado_harness_b,
                  "firms_gfs": _firms_gfs}


def empaquetar(caso: d.Caso) -> None:
    if caso.ruta_paquete.exists():
        raise SystemExit(f"{caso.ruta_paquete} ya existe: un paquete es inmutable. Para "
                         "cambiar los datos del incendio, definir otro protocolo.")
    paquete = EMPAQUETADORES[caso.datos["empaquetado"]["tipo"]](caso)
    caso.ruta_paquete.write_text(json.dumps(paquete, indent=2))
    n = len(paquete["comunes"]) + sum(len(v) for v in paquete["ventanas"])
    print(f"{caso.id}: {n} archivos → {caso.ruta_paquete}")


# ── diagnóstico: ¿el caso mide al modelo? ─────────────────────────────────────

DIAGNOSTICOS = d.RAIZ / "diagnosticos"
CACHE_FIRMS = Path("data/benchmark/cache/firms")
PROFUNDIDAD_SEMILLA_M = 90.0   # una ignición a menos del borde nace rodeada de no-cicatriz
# Una detección "cae en la cicatriz" si su centro está a menos de un píxel VIIRS: el píxel
# mide 375 m en el nadir y más hacia el borde de la pasada, y el fuego puede ocupar sólo
# una parte de él.
TOLERANCIA_VIIRS_M = perimeter_reconstruction.VIIRS_PIXEL_M


def _firms_diagnostico(incendio: str, caja, desde, hasta, fuentes) -> pd.DataFrame:
    ruta = CACHE_FIRMS / f"{incendio}_{desde}_{hasta}.csv"
    if ruta.exists():
        df = pd.read_csv(ruta)
        df["acq_datetime"] = pd.to_datetime(df["acq_datetime"], utc=True)
        return df
    df = _firms_rango(caja, desde, hasta, fuentes)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False)
    return df


def _agrupar(xy: np.ndarray, radio_m: float) -> np.ndarray:
    """Componentes conexas de puntos a menos de `radio_m` (O(n²), n son miles a lo sumo)."""
    grupo = np.full(len(xy), -1)
    for i in range(len(xy)):
        if grupo[i] >= 0:
            continue
        grupo[i], pila = i, [i]
        while pila:
            j = pila.pop()
            cerca = np.nonzero((grupo < 0) & (np.hypot(*(xy - xy[j]).T) <= radio_m))[0]
            grupo[cerca] = i
            pila.extend(cerca)
    return grupo


def _fraccion(serie: pd.Series) -> float | None:
    return round(float(serie.mean()), 3) if len(serie) else None


def _metros(d_: float) -> float | None:
    return None if np.isinf(d_) else round(d_)


def diagnosticar(caso: d.Caso) -> dict:
    """Máscara contra FIRMS e ignición contra cicatriz y DEM, antes de puntuar nada.

    Si la máscara no se corresponde con las detecciones del período, o la ignición no
    está en la cicatriz, el caso no mide al modelo (RESULTADOS-CSS-BAP §Casos).
    """
    datos = caso.datos
    run_dir = Path(datos["referencias"]["cicatriz"]["run"])
    run = json.loads((run_dir / "run.json").read_text())
    conf = run["configuration"]
    inicio_fuego = datetime.fromisoformat(conf["fire_start_date"]).date()
    pre, post = conf["windows"]["pre"], conf["windows"]["post"]
    caja = tuple(datos["caja_wgs84"])
    prep = Path(datos["empaquetado"]["preparacion"])
    dem_path, _ = _recortar(prep / "dem.tif", caja)
    combustible = next(Path(r) for n, r in datos["empaquetado"]["mapas"].items() if "ccsbap" in n)
    fbfm, _ = _recortar(combustible, caja)
    grilla = p.Grilla(dem_path)
    celda_m = abs(grilla.transform.a)
    with rasterio.open(dem_path) as src:
        dem = src.read(1)
    with rasterio.open(fbfm) as src:
        fuel = src.read(1)
    positivo, excluido = p.cargar_cicatriz(run_dir, grilla)
    valida = run_dir / "calidad" / "observacion_valida"
    cubierta = grilla.mosaico(sorted(valida.glob("*.tif"))) if valida.is_dir() else ~excluido
    otras = np.zeros_like(positivo)
    for capa in p.EXCLUIDAS_POR_DEFECTO:
        if (run_dir / capa).is_dir():
            otras |= grilla.mosaico(sorted((run_dir / capa).glob("*.tif")))

    desde = inicio_fuego - timedelta(days=3)
    hasta = datetime.fromisoformat(post["start"]).date()
    fuentes = datos["referencias"]["firms"]["fuentes"]
    df = _firms_diagnostico(caso.incendio, caja, desde, hasta, fuentes)
    tr = Transformer.from_crs("EPSG:4326", str(grilla.crs), always_xy=True)
    inv = Transformer.from_crs(str(grilla.crs), "EPSG:4326", always_xy=True)
    xs, ys = tr.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    filas, cols = rasterio.transform.rowcol(grilla.transform, xs, ys)
    filas, cols = np.asarray(filas), np.asarray(cols)
    en_grilla = (filas >= 0) & (filas < grilla.shape[0]) & (cols >= 0) & (cols < grilla.shape[1])
    clase, dist = [], []
    for f, c, ok in zip(filas, cols, en_grilla):
        if not ok:
            clase.append("fuera_grilla")
            dist.append(np.inf)
            continue
        dp = p.distancia_a(positivo, f, c, celda_m, 10_000)
        dist.append(dp)
        if dp <= TOLERANCIA_VIIRS_M:
            clase.append("cicatriz")
        elif p.distancia_a(otras, f, c, celda_m, TOLERANCIA_VIIRS_M) <= TOLERANCIA_VIIRS_M:
            clase.append("exclusion")
        elif not cubierta[f, c]:
            clase.append("sin_observacion")
        else:
            clase.append("afuera")
    df["clase"], df["dist_cicatriz_m"] = clase, dist
    df["x"], df["y"] = xs, ys

    # Actividad del incendio: detecciones en la cicatriz o a menos de 2 km.
    propias = df[df["dist_cicatriz_m"] <= 2000].copy()
    propias["dia"] = propias["acq_datetime"].dt.tz_convert("America/Argentina/Buenos_Aires").dt.date
    discos = np.zeros(grilla.shape, dtype=bool)
    por_dia = []
    for dia, grupo in propias.groupby("dia"):
        discos |= _mascara(list(zip(grupo["longitude"], grupo["latitude"])), dem_path)
        por_dia.append({"dia": str(dia), "detecciones": len(grupo),
                        "en_cicatriz": int((grupo["clase"] == "cicatriz").sum()),
                        "area_firms_acum_ha": round(float(discos.sum() * grilla.celda_ha), 1)})

    afuera = df[df["clase"].isin(["afuera", "sin_observacion"])]
    grupos = []
    if len(afuera):
        g = _agrupar(afuera[["x", "y"]].to_numpy(), 1500.0)
        for _, sub in afuera.groupby(g):
            lon, lat = inv.transform(sub["x"].mean(), sub["y"].mean())
            grupos.append({"detecciones": len(sub), "lon": round(lon, 4), "lat": round(lat, 4),
                           "desde": str(sub["acq_datetime"].min()),
                           "hasta": str(sub["acq_datetime"].max()),
                           "dist_cicatriz_m": _metros(float(sub["dist_cicatriz_m"].min())),
                           "sin_observacion": int((sub["clase"] == "sin_observacion").sum())})
        grupos.sort(key=lambda x: -x["detecciones"])

    def punto(nombre, lon, lat, hora=None) -> dict:
        x, y = tr.transform(lon, lat)
        f, c = rasterio.transform.rowcol(grilla.transform, x, y)
        salida = {"nombre": nombre, "lon": lon, "lat": lat, "hora": hora}
        if not (0 <= f < grilla.shape[0] and 0 <= c < grilla.shape[1]):
            return salida | {"en_grilla": False}
        salida |= {"altura_m": round(float(dem[f, c])), "combustible": int(fuel[f, c]),
                   "dist_cicatriz_m": _metros(p.distancia_a(positivo, f, c, celda_m, 20_000)),
                   "profundidad_m": _metros(p.distancia_a(~positivo, f, c, celda_m, 2000))
                   if positivo[f, c] else 0}
        if len(propias):
            primera = propias["acq_datetime"].min()
            iniciales = propias[propias["acq_datetime"] <= primera + timedelta(hours=12)]
            salida["primera_deteccion"] = str(primera)
            salida["dist_primeras_m"] = round(float(np.hypot(iniciales["x"] - x,
                                                             iniciales["y"] - y).min()))
            if hora:
                salida["antes_de_primera"] = datetime.fromisoformat(hora) < primera
            primeras = propias[propias["acq_datetime"] == primera]
            lon0, lat0 = inv.transform(primeras["x"].mean(), primeras["y"].mean())
            f0, c0 = rasterio.transform.rowcol(grilla.transform, primeras["x"].mean(),
                                               primeras["y"].mean())
            salida["primera_pasada"] = {"detecciones": len(primeras), "lon": round(lon0, 5),
                                        "lat": round(lat0, 5),
                                        "altura_m": round(float(dem[f0, c0]))}
        # La alternativa del protocolo: la celda de la cicatriz más cercana a >90 m del borde,
        # sobre combustible.
        interior = positivo & (fuel > 100)   # NB son 91-99
        profundo = np.zeros_like(interior)
        r = int(PROFUNDIDAD_SEMILLA_M // celda_m)
        for df_, dc in [(a, b) for a in range(-r, r + 1) for b in range(-r, r + 1)
                        if np.hypot(a, b) * celda_m <= PROFUNDIDAD_SEMILLA_M]:
            profundo |= ~np.roll(np.roll(positivo, df_, 0), dc, 1)
        interior &= ~profundo
        ff, cc = np.nonzero(interior)
        if ff.size:
            k = int(np.argmin(np.hypot(ff - f, cc - c)))
            lon2, lat2 = inv.transform(*rasterio.transform.xy(grilla.transform, ff[k], cc[k]))
            salida["celda_interior"] = {
                "lon": round(lon2, 5), "lat": round(lat2, 5),
                "dist_m": round(float(np.hypot(ff[k] - f, cc[k] - c) * celda_m)),
                "altura_m": round(float(dem[ff[k], cc[k]])), "combustible": int(fuel[ff[k], cc[k]])}
        return salida

    semillas = []
    ip = conf.get("event_filter", {}).get("ignition_point")
    if ip:
        semillas.append(punto("mask-dataset-gen", ip["longitude"], ip["latitude"]))
    s = datos.get("semilla_inicial")
    if s:
        for lon, lat in _puntos_ignicion(s):
            semillas.append(punto("caso", lon, lat, s.get("hora")))

    cuenta = df["clase"].value_counts().to_dict()
    cerca = df[df["dist_cicatriz_m"] <= 5000]
    area = float(positivo.sum() * grilla.celda_ha)
    primera = propias["acq_datetime"].min() if len(propias) else None
    ultima = propias["acq_datetime"].max() if len(propias) else None
    zona = _mascara(list(zip(propias["longitude"], propias["latitude"])), dem_path) | positivo
    informe = {
        "caso": caso.id, "cicatriz_run": str(run_dir),
        "firms": {"fuentes": fuentes, "desde": str(desde), "hasta": str(hasta),
                  "detecciones": len(df), "por_clase": cuenta,
                  "a_5km": len(cerca),
                  "fraccion_en_cicatriz_a_5km": _fraccion(cerca["clase"] == "cicatriz"),
                  "fraccion_en_exclusion_a_5km": _fraccion(cerca["clase"] == "exclusion"),
                  "primera": str(primera), "ultima": str(ultima),
                  "por_dia": por_dia, "grupos_afuera": grupos[:12]},
        "mascara": {"area_ha": round(area, 1),
                    "area_oficial_ha": conf.get("reference", {}).get("burned_area_ha"),
                    "area_run_ha": run.get("comparison_to_parent", {}).get("target_hectares"),
                    "excluido_en_zona_ha":
                        round(float((excluido & zona).sum() * grilla.celda_ha), 1),
                    "cobertura_valida_en_zona": round(float(cubierta[zona].mean()), 3)
                    if zona.any() else None,
                    "pre": pre, "post": post,
                    "pre_antes_de_firms": primera is not None
                    and datetime.fromisoformat(pre["end_inclusive"]).date() < primera.date(),
                    "post_despues_de_firms": ultima is not None
                    and datetime.fromisoformat(post["start"]).date() > ultima.date()},
        "semillas": semillas,
    }
    DIAGNOSTICOS.mkdir(parents=True, exist_ok=True)
    (DIAGNOSTICOS / f"{caso.incendio}.json").write_text(
        json.dumps(informe, indent=2, ensure_ascii=False, default=str))
    print(json.dumps(informe, indent=2, ensure_ascii=False, default=str))
    return informe


# ── informes ──────────────────────────────────────────────────────────────────

def _fmt(v) -> str:
    return "—" if v is None else f"{v:.3f}" if isinstance(v, float) else str(v)


def tabla(caso: d.Caso) -> None:
    """Todas las recetas corridas sobre el caso, lado a lado."""
    raiz = d.ruta_iteracion(caso.id, "")
    filas = []
    for dir_receta in sorted(raiz.iterdir()) if raiz.exists() else []:
        ruta = dir_receta / "metricas.json"
        if ruta.exists():
            filas.append(json.loads(ruta.read_text()))
    print(f"{caso.id}: {len(filas)} recetas")
    print(f"{'receta':28s}{'dice':>8s}{'ref':>5s}{'sesgo':>8s}{'forma':>8s}{'t*':>6s}"
          f"{'recall F':>10s}{'prec. F':>9s}  factores")
    for m in filas:
        pr = m["principal"] or {}
        ag = (m["agregado_firms"] or {}).get("incremento", {})
        alarma = " ⚠" if pr.get("alarma_sesgo") else ""
        ref = {"cicatriz": "C", "firms": "F"}.get(pr.get("referencia"), "")
        ai = pr.get("area_igualada") or {}
        hora = f"{ai['hora']:.0f}" + ("" if ai.get("alcanzada") else "+") if ai.get("hora") else "—"
        print(f"{m['receta']:28s}{_fmt(pr.get('dice')):>8s}{ref:>5s}"
              f"{_fmt(pr.get('sesgo_area')):>8s}{_fmt(ai.get('dice')):>8s}{hora:>6s}"
              f"{_fmt(ag.get('recall')):>10s}{_fmt(ag.get('precision')):>9s}  "
              f"{m['factores']}{alarma}")


def resumen() -> None:
    """Cada receta contra cada caso: la misma versión del modelo entre incendios.

    Sólo compara métricas principales con la misma referencia (cicatriz o FIRMS), que es lo
    que fija la política de semilla de la receta.
    """
    raiz = d.RAIZ / "iteraciones"
    celdas: dict[str, dict[str, dict]] = {}
    for ruta in sorted(raiz.glob("*/*/*/metricas.json")):
        m = json.loads(ruta.read_text())
        if m.get("principal"):
            celdas.setdefault(m["receta"], {})[m["caso"]] = m["principal"]
    casos = sorted({c for fila in celdas.values() for c in fila})
    print(f"{'receta':26s}" + "".join(f"{c[:26]:>28s}" for c in casos))
    for receta, fila in sorted(celdas.items()):
        textos = []
        for c in casos:
            pr = fila.get(c)
            if pr is None:
                textos.append("")
                continue
            sesgo = f" s{pr['sesgo_area']:.2f}" if pr.get("sesgo_area") is not None else ""
            ref = "C" if pr["referencia"] == "cicatriz" else "F"
            alarma = " ⚠" if pr.get("alarma_sesgo") else ""
            textos.append(f"{ref} {_fmt(pr['dice'])}{sesgo}{alarma}")
        print(f"{receta:26s}" + "".join(f"{t:>28s}" for t in textos))


def comparar(a_id: str, b_id: str) -> dict:
    def partes(i: str) -> tuple[str, str]:
        incendio, protocolo, receta = i.split("/")
        return f"{incendio}/{protocolo}", receta
    a, b = (d.cargar_manifiesto(*partes(i)) for i in (a_id, b_id))
    if a is None or b is None:
        raise SystemExit("alguna de las dos iteraciones no corrió")
    diff = d.comparar(a, b)
    diff["deltas"] = d.deltas(*(d.cargar_metricas(*partes(i)) for i in (a_id, b_id)))
    print(json.dumps(diff, indent=2, ensure_ascii=False))
    return diff


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("empaquetar").add_argument("caso")
    sub.add_parser("diagnosticar").add_argument("caso")
    for nombre in ("correr", "puntuar", "verificar"):
        s = sub.add_parser(nombre)
        s.add_argument("caso")
        s.add_argument("recetas", nargs="+")
    sub.add_parser("tabla").add_argument("caso")
    sub.add_parser("resumen")
    s = sub.add_parser("comparar")
    s.add_argument("a")
    s.add_argument("b")
    s = sub.add_parser("materializar")
    s.add_argument("caso")
    s.add_argument("receta")
    s.add_argument("ventana", type=int)
    args = ap.parse_args()

    caso = d.Caso.cargar(args.caso) if hasattr(args, "caso") else None
    if args.cmd == "resumen":
        resumen()
    elif args.cmd == "empaquetar":
        empaquetar(caso)
    elif args.cmd == "diagnosticar":
        diagnosticar(caso)
    elif args.cmd == "tabla":
        tabla(caso)
    elif args.cmd == "comparar":
        comparar(args.a, args.b)
    elif args.cmd == "materializar":
        manifiesto = d.cargar_manifiesto(caso.id, args.receta)
        v = manifiesto["ventanas"][args.ventana]
        insumos, salidas = cadena._rutas(caso, d.Receta.cargar(args.receta), args.ventana)
        almacen.materializar(v["insumos"], insumos)
        almacen.materializar(v["salidas"], salidas)
        print(f"ventana {args.ventana} → {insumos.parent}")
    else:
        for receta_id in args.recetas:
            receta = d.Receta.cargar(receta_id)
            if args.cmd == "correr":
                cadena.correr(caso, receta)
                cadena.puntuar(caso, receta)
            elif args.cmd == "puntuar":
                cadena.puntuar(caso, receta)
            else:
                for r in cadena.verificar(caso, receta):
                    print(f"  ventana {r['n']}: {'igual' if r['toa_igual'] else 'DISTINTO'}")
        if args.cmd != "verificar":
            tabla(caso)


if __name__ == "__main__":
    main()
