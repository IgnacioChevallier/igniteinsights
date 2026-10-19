"""Benchmark de validación: receta × caso, inmutable y reanudable (IGN-26 §Benchmark).

    uv run python scripts/benchmark.py empaquetar puerto-patriada-2026/ventanas-firms
    uv run python scripts/benchmark.py correr     puerto-patriada-2026/ventanas-firms legacy-ccsbap
    uv run python scripts/benchmark.py puntuar    puerto-patriada-2026/ventanas-firms legacy-ccsbap
    uv run python scripts/benchmark.py tabla      puerto-patriada-2026/ventanas-firms
    uv run python scripts/benchmark.py comparar   <caso>/<receta> <caso>/<receta>
    uv run python scripts/benchmark.py verificar  <caso> <receta>
    uv run python scripts/benchmark.py materializar <caso> <receta> <ventana>
    uv run python scripts/benchmark.py modelo     modelo-v0

Casos, recetas y modelos promovidos viven en `benchmarks/` (en git); los objetos en
`data/benchmark/objetos/`. Una receta configura iteraciones; un modelo es un snapshot que ya
pasó el gate productivo y no crea otra clase de corrida.
Corre desde el host contra el runner de docker-compose (`docker compose up -d elmfire-runner`).
"""
import argparse
import csv
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
    canopy_builder,
    fuels_builder,
    ignition_builder,
    perimeter_reconstruction,
    weather_builder,
)
from app.ingestion.meteorology.gfs.client import GFSClient  # noqa: E402
from app.ingestion.satellite.firms.client import FIRMSClient  # noqa: E402
from app.validation import almacen, cadena, copa, pronostico  # noqa: E402
from app.validation import definiciones as d  # noqa: E402
from app.validation import puntuacion as p  # noqa: E402

# Nombre en el paquete ← nombre en las preparaciones del harness viejo, con el año de
# cada insumo explícito (IGN-26 §fuga temporal).
LEGADO_COMBUSTIBLES = {"fbfm40_worldcover2021.tif": "worldcover",
                       "fbfm40_mapbiomas2024.tif": "mapbiomas",
                       "fbfm40_ccsbap2017.tif": "ccsbap"}


# ── empaquetado ───────────────────────────────────────────────────────────────

def _guardar_array(datos: np.ndarray, grilla: p.Grilla, dtype: str, nodata=None) -> str:
    perfil = grilla.perfil | {"dtype": dtype, "count": 1, "nodata": nodata, "compress": "deflate"}
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


OPEN_METEO_ERA5 = "https://archive-api.open-meteo.com/v1/archive"
PASO_ERA5 = 0.25


def _era5_serie(var: str, inicio: datetime, horas: int, caja, destino: Path) -> None:
    """ERA5 horario de Open-Meteo, en la grilla de 0,25° y con el mismo formato que las series
    del GFS (EPSG:4326, una banda por hora) para que el resto del empaquetado no cambie.

    Sin reducción de escala (`elevation=nan`): cada valor es el de la celda de ERA5 a la altura
    de su terreno, que se guarda como `orog`, igual que el GFS. Baja las cinco variables juntas.
    """
    import httpx

    o, s_, e, n = caja
    lats = np.arange(np.floor(n / PASO_ERA5), np.ceil(s_ / PASO_ERA5) - 1, -1) * PASO_ERA5
    lons = np.arange(np.ceil(o / PASO_ERA5), np.floor(e / PASO_ERA5) + 1) * PASO_ERA5
    puntos = [(la, lo) for la in lats for lo in lons]
    fin = inicio + timedelta(hours=horas)
    horario = ("temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_direction_10m")
    datos = {v: np.full((horas + 1, len(lats), len(lons)), np.nan, dtype="float32")
             for v in horario}
    orog = np.full((1, len(lats), len(lons)), np.nan, dtype="float32")
    for k in range(0, len(puntos), 50):
        lote = puntos[k:k + 50]
        r = httpx.get(OPEN_METEO_ERA5, timeout=120, params={
            "latitude": ",".join(f"{la:.2f}" for la, _ in lote),
            "longitude": ",".join(f"{lo:.2f}" for _, lo in lote),
            "elevation": ",".join("nan" for _ in lote),
            "start_date": inicio.date().isoformat(), "end_date": fin.date().isoformat(),
            "hourly": ",".join(horario), "models": "era5", "wind_speed_unit": "ms",
            "timezone": "GMT"})
        r.raise_for_status()
        respuestas = r.json() if len(lote) > 1 else [r.json()]
        for (la, lo), resp in zip(lote, respuestas):
            i, j = int(np.argmin(abs(lats - la))), int(np.argmin(abs(lons - lo)))
            tiempos = pd.to_datetime(resp["hourly"]["time"], utc=True)
            sel = (tiempos >= pd.Timestamp(inicio)) & (tiempos <= pd.Timestamp(fin))
            for v in horario:
                datos[v][:, i, j] = np.asarray(resp["hourly"][v], dtype="float32")[sel]
            orog[0, i, j] = resp["elevation"]
    ws, wd = datos["wind_speed_10m"], np.radians(datos["wind_direction_10m"])
    capas = {"t2m": datos["temperature_2m"] + 273.15, "rh": datos["relative_humidity_2m"],
             "u10": -ws * np.sin(wd), "v10": -ws * np.cos(wd), "orog": orog}
    transform = rasterio.transform.from_origin(lons[0] - PASO_ERA5 / 2, lats[0] + PASO_ERA5 / 2,
                                               PASO_ERA5, PASO_ERA5)
    destino.parent.mkdir(parents=True, exist_ok=True)
    for nombre, a in capas.items():
        if nombre != var and (destino.parent / f"{nombre}.tif").exists():
            continue   # no pisar una serie ya cortada (p. ej. al bajar sólo el terreno)
        if nombre != "orog" and a.shape[0] != horas + 1:
            raise ValueError(f"ERA5 {nombre}: {a.shape[0]} bandas, se esperaban {horas + 1}")
        with rasterio.open(destino.parent / f"{nombre}.tif", "w", driver="GTiff",
                           height=a.shape[1], width=a.shape[2], count=a.shape[0],
                           dtype="float32", crs="EPSG:4326", transform=transform) as dst:
            dst.write(a)


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
    fuente = caso.datos["empaquetado"].get("clima_fuente", "gfs")
    cache = Path("data/benchmark/cache") / fuente

    def bajar(var: str, desde: datetime, horas: int, destino: Path) -> None:
        if destino.exists():
            return
        # Una serie ya bajada con la misma caja que cubra [desde, desde + horas] alcanza:
        # se corta con el desfase (p. ej. la ignición 2 h más tarde, o una serie más larga).
        sufijo = "_".join(f"{v:.2f}" for v in caja)
        for otra in sorted(cache.glob(f"*_*h_{sufijo}")):
            inicio_otra = datetime.strptime(otra.name.split("_")[0], "%Y%m%dT%H").replace(
                tzinfo=desde.tzinfo)
            desfase = int((desde - inicio_otra).total_seconds() // 3600)
            if (desfase < 0 or int(otra.name.split("_")[1][:-1]) < desfase + horas
                    or not (otra / f"{var}.tif").exists()):
                continue
            with rasterio.open(otra / f"{var}.tif") as src:
                if src.count < desfase + horas + 1:
                    continue
                datos = src.read(list(range(desfase + 1, desfase + horas + 2)))
                perfil = src.profile | {"count": datos.shape[0]}
            destino.parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(destino, "w", **perfil) as dst:
                dst.write(datos)
            return
        print(f"  {fuente} {var}: {horas + 1} bandas horarias desde {desde} …", flush=True)
        if fuente == "era5":
            _era5_serie(var, desde, horas, caja, destino)
        else:
            GFSClient().download_analysis_series(var, desde, horas, *caja, destino)

    clave = f"{inicio:%Y%m%dT%H}_{total}h_" + "_".join(f"{v:.2f}" for v in caja)
    series = cache / clave
    for var in ("u10", "v10", "t2m", "rh"):
        bajar(var, inicio, total, series / f"{var}.tif")
    # Humedad muerta con historial de secado: una serie t2m/rh que arranca `retardo` horas
    # antes de la ignición, para el modelo de retardo (weather_builder.derive_moisture_timelag).
    retardo = int(caso.datos["empaquetado"].get("humedad_retardo_h", 0))
    if retardo:
        previa = cache / (f"{inicio - timedelta(hours=retardo):%Y%m%dT%H}_{total + retardo}h_"
                          + "_".join(f"{v:.2f}" for v in caja))
        for var in ("t2m", "rh"):
            bajar(var, inicio - timedelta(hours=retardo), total + retardo, previa / f"{var}.tif")
    # El clima crudo (T y HR a 0,25° y el terreno del GFS, donde valen) pesa poco y deja
    # calcular en la corrida las humedades con criterio (app/validation/humedad.py).
    crudo = bool(caso.datos["empaquetado"].get("clima_crudo"))
    if crudo:
        bajar("orog", inicio, 0, series / "orog.tif")
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
        factor = caso.datos["empaquetado"].get("factor_viento_fuente")
        if factor:   # homogeneiza la fuente (ERA5 → GFS), AUDITORIA-FISICA loop D
            with rasterio.open(cortes / "ws.tif") as src:
                perfil, ws = src.profile, src.read()
            with rasterio.open(cortes / "ws.tif", "w", **perfil) as dst:
                dst.write((ws * float(factor)).astype(perfil["dtype"]))
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
        estacion = caso.datos["empaquetado"].get("viento_estacion")
        if estacion:   # diagnóstico: el viento medido, uniforme en el dominio, en vez del GFS
            archivos |= _viento_de_estacion(estacion, v.inicio, v.horas, dem, cortes)
        salida.append(archivos)
    return salida


def _viento_de_estacion(estacion: str, inicio: datetime, horas: int, dem: Path,
                        cortes: Path) -> dict[str, str]:
    """ws/wd uniformes con la serie horaria de una estación de Meteostat (10 m, km/h), bajada
    a 20 pies con el mismo perfil logarítmico que el GFS. Las horas sin dato se interpolan."""
    cols = "date,hour,temp,dwpt,rhum,prcp,snow,wdir,wspd,wpgt,pres,tsun,coco".split(",")
    df = pd.read_csv(Path("data/benchmark/cache") / f"{estacion}.csv.gz", names=cols)
    df["t"] = pd.to_datetime(df["date"]) + pd.to_timedelta(df["hour"], unit="h")
    df = df.set_index("t").sort_index()
    horas_ = pd.date_range(inicio.replace(tzinfo=None), periods=horas + 1, freq="h")
    u = -(df["wspd"] * np.sin(np.radians(df["wdir"])))
    w = -(df["wspd"] * np.cos(np.radians(df["wdir"])))
    u, w = (x.reindex(x.index.union(horas_)).interpolate("time").reindex(horas_)
            for x in (u, w))
    ws_mph = np.hypot(u, w).to_numpy() / 3.6 * weather_builder.wind_height_factor() \
        * weather_builder.MS_TO_MPH
    wd = (np.degrees(np.arctan2(-u, -w)).to_numpy() + 360.0) % 360.0
    with rasterio.open(dem) as ref:
        forma = (ref.height, ref.width)
    rutas = {}
    for nombre, serie in (("ws.tif", ws_mph), ("wd.tif", wd)):
        datos = np.broadcast_to(serie[:, None, None], (len(serie), *forma)).astype("float32")
        weather_builder._write_like_reference(dem, cortes / nombre, datos)
        rutas[nombre] = almacen.guardar(cortes / nombre)
    return rutas


def _atlas_viento(dem: Path, conf: dict) -> dict[str, str]:
    """El atlas de WindNinja del caso (app/validation/viento.py), cacheado por DEM y ajustes:
    son 16 corridas de WindNinja y re-empaquetar no debe repetirlas."""
    from app.validation import viento

    resolucion, vegetacion = float(conf.get("resolucion_m", 90)), conf.get("vegetacion", "brush")
    clave = f"{almacen.sha256(dem)[:16]}_{resolucion:.0f}m_{vegetacion}_{viento.DIRECCIONES}"
    cache = Path("data/benchmark/cache/windninja") / clave
    if not (cache / "atlas_v.tif").exists():
        print(f"  WindNinja: {viento.DIRECCIONES} direcciones a {resolucion:.0f} m …", flush=True)
        u, v, perfil = viento.atlas(dem, Path("data/benchmark/trabajo/windninja") / clave,
                                    resolucion, vegetacion)
        cache.mkdir(parents=True, exist_ok=True)
        viento.guardar(u, v, perfil, cache)
    return {n: almacen.guardar(cache / n) for n in ("atlas_u.tif", "atlas_v.tif")}


def _cerca_de(df: pd.DataFrame, mascara: np.ndarray, grilla: p.Grilla,
              radio_m: float) -> pd.DataFrame:
    """Las detecciones a menos de `radio_m` de la máscara (la cicatriz del incendio)."""
    tr = Transformer.from_crs("EPSG:4326", str(grilla.crs), always_xy=True)
    xs, ys = tr.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    filas, cols = rasterio.transform.rowcol(grilla.transform, xs, ys)
    celda = abs(grilla.transform.a)
    dentro = [0 <= f < grilla.shape[0] and 0 <= c < grilla.shape[1]
              and p.distancia_a(mascara, f, c, celda, radio_m) <= radio_m
              for f, c in zip(filas, cols)]
    return df[np.array(dentro, dtype=bool)].reset_index(drop=True)


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


def _semilla_conexa(puntos: list[tuple[float, float]], semilla: dict,
                    grilla: p.Grilla) -> list[tuple[float, float]]:
    """Las detecciones que siembran. Con `semilla_inicial.filtro_conexo_m`, sólo las del
    incendio que arrancó en la ignición (`perimeter_reconstruction.connected_to_anchors`, la
    regla de tiempo real); sin él, todo lo detectado en la caja, otros incendios incluidos
    (diagnostico-e2e/notas/T-semilla.md §2.2)."""
    salto = semilla.get("filtro_conexo_m")
    if not salto or not puntos:
        return puntos
    anclas = _puntos_ignicion(semilla)
    if not anclas:
        raise ValueError("`filtro_conexo_m` necesita puntos de ignición (tipo punto o puntos)")
    tr = Transformer.from_crs("EPSG:4326", str(grilla.crs), always_xy=True)
    quedan = perimeter_reconstruction.connected_to_anchors(
        [tr.transform(*pt) for pt in puntos], [tr.transform(*pt) for pt in anclas], float(salto))
    return [pt for pt, q in zip(puntos, quedan) if q]


def _firms_gfs(caso: d.Caso) -> dict:
    datos = caso.datos
    caja = tuple(datos["caja_wgs84"])
    prep = Path(datos["empaquetado"]["preparacion"])
    comunes, recortes = {}, {}
    for nombre in ESTATICOS_PREP:
        recortes[nombre], _ = _recortar(prep / nombre, caja)
        comunes[nombre] = almacen.guardar(recortes[nombre])
    mapas = {}
    for nombre, ruta in datos["empaquetado"]["mapas"].items():
        mapas[nombre], _ = _recortar(Path(ruta), caja)
        comunes[nombre] = almacen.guardar(mapas[nombre])
    if "dosel_por_combustible" in datos["empaquetado"]:
        # docs/crosswalk/DECISIONES-MODELO-V0 §2 y §3 (protocolos -v6): el CBH del tipo de
        # bosque del mapa del caso y sin dosel donde Hansen vio pérdida antes del año del
        # mapa y del año, así que se deriva por caso y no en la preparación.
        dosel = datos["empaquetado"]["dosel_por_combustible"]
        canopy_builder.derive_cbh_cbd(
            recortes["cc.tif"], recortes["ch.tif"], recortes["cbh.tif"], recortes["cbd.tif"],
            mapas[dosel["mapa"]], _recortar(Path(dosel["perdida_hansen"]), caja)[0],
            caso.anio_fuego)
        for nombre in ("cc.tif", "ch.tif", "cbh.tif", "cbd.tif"):
            comunes[nombre] = almacen.guardar(recortes[nombre])
    comunes["fuel_models.csv"] = almacen.guardar(fuels_builder.FUEL_MODEL_TABLE)
    dem = recortes["dem.tif"]
    grilla = p.Grilla(dem)
    if "viento_atlas" in datos["empaquetado"]:
        comunes |= _atlas_viento(dem, datos["empaquetado"]["viento_atlas"])

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
    radio = semilla.get("radio_cicatriz_m")
    if radio:   # la semilla observada, sólo del incendio objetivo (no de otros de la caja)
        positivo, _ = p.cargar_cicatriz(Path(datos["referencias"]["cicatriz"]["run"]), grilla)
        df = _cerca_de(df, positivo, grilla, float(radio))
    for n, (v, clima) in enumerate(zip(caso.ventanas, _clima(caso, dem))):
        antes = _puntos(df, None, v.inicio)
        if n == 0 and semilla["tipo"] != "firms":
            observado = ignicion
        else:   # lo observado hasta el inicio: FIRMS más los puntos de ignición
            observado = ignicion | _mascara(_semilla_conexa(antes, semilla, grilla), dem)
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


def _ampliar_mapas(caso: d.Caso) -> dict:
    """El paquete de otro caso, byte a byte, más mapas de combustible: lo único que cambia
    entre las iteraciones de dos mapas es `fbfm40` (docs/resultados/COMPARACION-MAPAS-V5.md)."""
    datos = caso.datos["empaquetado"]
    base = d.Caso.cargar(datos["base"]).paquete()
    with rasterio.open(almacen.abrir(base["comunes"]["dem.tif"])) as dem:
        grilla = (dem.shape, dem.transform, dem.crs)
    nuevos = {}
    for nombre, ruta in datos["mapas"].items():
        recorte, _ = _recortar(Path(ruta), tuple(caso.datos["caja_wgs84"]))
        with rasterio.open(recorte) as src:
            if (src.shape, src.transform, src.crs) != grilla:
                raise ValueError(f"{ruta} no está en la grilla del dem de {datos['base']}")
        nuevos[nombre] = almacen.guardar(recorte)
        if nombre in base["comunes"] and base["comunes"][nombre] != nuevos[nombre]:
            raise ValueError(f"{nombre} difiere del de {datos['base']}")
    return {"comunes": base["comunes"] | nuevos, "ventanas": base["ventanas"],
            "origen": base["origen"] | {"base": datos["base"], "mapas": datos["mapas"]}}


def _viento_diurno(caso: d.Caso) -> dict:
    """El paquete de otro caso, byte a byte, más el viento de cada hora de cada ventana con los
    flujos de ladera diurnos de WindNinja (`wn_u.tif`, `wn_v.tif`; AUDITORIA-FISICA loop M).
    La entrada de cada hora es el viento medio del dominio (ws/wd del paquete, a 20 pies) y la
    temperatura media del clima crudo."""
    from app.validation import viento

    datos = caso.datos["empaquetado"]
    base = d.Caso.cargar(datos["base"]).paquete()
    dem = almacen.abrir(base["comunes"]["dem.tif"])
    ventanas = []
    for n, (v, archivos) in enumerate(zip(caso.ventanas, base["ventanas"], strict=True)):
        with rasterio.open(almacen.abrir(archivos["ws.tif"])) as a, \
                rasterio.open(almacen.abrir(archivos["wd.tif"])) as b, \
                rasterio.open(almacen.abrir(archivos["t2m_gfs.tif"])) as t:
            ws, wd, t2m = a.read(), np.radians(b.read()), t.read()
        este = (-ws * np.sin(wd)).mean(axis=(1, 2))
        norte = (-ws * np.cos(wd)).mean(axis=(1, 2))
        desde = (np.degrees(np.arctan2(-este, -norte)) + 360.0) % 360.0
        horas = [v.inicio + timedelta(hours=k) for k in range(ws.shape[0])]
        print(f"  ventana {n}: WindNinja diurno, {len(horas)} horas …", flush=True)
        u, w, perfil = viento.diurno(
            dem, Path("data/benchmark/trabajo/windninja-diurno") / caso.id / f"v{n}",
            np.hypot(este, norte), desde, np.nanmean(t2m, axis=(1, 2)) - 273.15, horas,
            float(datos.get("resolucion_m", 90)), datos.get("vegetacion", "brush"))
        with tempfile.TemporaryDirectory() as tmp:
            ru, rv = viento.guardar(u, w, perfil, Path(tmp))
            ventanas.append(archivos | {"wn_u.tif": almacen.guardar(ru),
                                        "wn_v.tif": almacen.guardar(rv)})
    return {"comunes": base["comunes"], "ventanas": ventanas,
            "origen": base["origen"] | {"base": datos["base"], "viento_diurno": viento.IMAGEN}}


# ── P-24: pronóstico desde el perímetro observado (DIA-1-PROPUESTA §2) ──────────

REFERENCIAS_VENTANA = {"phi.tif", "ref_firms.tif", "ref_firms_horas.tif", "alcance.tif"}


def _horas_por_pasada(df: pd.DataFrame, origen: datetime, hasta: datetime, dem: Path,
                      radio_m: float, desde: datetime | None = None) -> np.ndarray:
    """Horas desde `origen` de la primera detección a menos de `radio_m` de cada celda (inf si
    ninguna), entre `desde` (excluido) y `hasta`. Rasteriza de a una hora de adquisición y no de
    a una detección como `_horas_deteccion`: con las ~10⁵ detecciones de Patriada, aquélla tarda
    horas."""
    grilla = p.Grilla(dem)
    horas = np.full(grilla.shape, np.inf)
    sel = df[(df["acq_datetime"] <= hasta)
             & ((df["acq_datetime"] > desde) if desde is not None else True)]
    tr = Transformer.from_crs("EPSG:4326", str(grilla.crs), always_xy=True)
    for t, grupo in sel.groupby("acq_datetime"):
        xs, ys = tr.transform(grupo["longitude"].to_numpy(), grupo["latitude"].to_numpy())
        disco = rasterio.features.rasterize(
            [(mapping(Point(x, y).buffer(radio_m)), 1) for x, y in zip(xs, ys)],
            out_shape=grilla.shape, transform=grilla.transform, dtype="uint8").astype(bool)
        horas[disco] = np.minimum(horas[disco], (t - origen).total_seconds() / 3600)
    return horas


def _clima_desde_base(base: d.Caso, ventanas: list[dict], nombre: str, h0: int, n: int) -> str:
    """`n` bandas horarias de `nombre` desde la hora `h0` del caso base, tomadas de sus ventanas
    (el mismo clima que corrió la cadena, sin volver a bajar ni derivar nada)."""
    inicio = base.ventanas[0].inicio
    desfases = [int((v.inicio - inicio).total_seconds() // 3600) for v in base.ventanas]
    horas = [v.horas for v in base.ventanas]
    bandas = []
    for h in range(h0, h0 + n):
        j, b = pronostico.hora_en_base(h, desfases, horas)
        with rasterio.open(almacen.abrir(ventanas[j][nombre])) as src:
            bandas.append(src.read(b + 1))
            perfil = src.profile | {"count": n}
    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / nombre
        with rasterio.open(ruta, "w", **perfil) as dst:
            dst.write(np.stack(bandas))
        return almacen.guardar(ruta)


def _pronostico(caso: d.Caso) -> dict:
    """P-24: un caso de calibración re-cortado en ventanas de 24 h que arrancan en cada pasada
    VIIRS. Estáticos, mapas, dosel, FIRMS, cicatriz y clima son los del caso base byte a byte, así
    que contra la cadena de modelo-v0 lo único distinto es la semilla:

    - `firms`: lo observado hasta el reinicio, acumulado (la reconstrucción sola no es monótona);
    - `oraculo`: la cicatriz ya vista por VIIRS. Usa la cicatriz final, que en tiempo real no
      existe; separa el error de la reconstrucción del de la propagación.

    La ventana 0 es la del caso base (desde la ignición) y cada ventana trae `vistas_horas.tif`:
    la hora de la primera detección a menos de un píxel, para la referencia por plazo."""
    datos = caso.datos["empaquetado"]
    base_caso = d.Caso.cargar(datos["base"])
    if any(v.tstart_s for v in base_caso.ventanas) or not base_caso.contiguo:
        raise ValueError(f"{datos['base']}: el clima se re-arma por hora desde ventanas contiguas "
                         "que arrancan en su banda 0")
    base = base_caso.paquete()
    comunes = base["comunes"]
    dem = almacen.abrir(comunes["dem.tif"])
    grilla = p.Grilla(dem)
    df = pd.read_csv(almacen.abrir(comunes["firms.csv"]), parse_dates=["acq_datetime"])
    semilla = caso.datos["semilla_inicial"]
    radio = semilla.get("radio_cicatriz_m")
    if radio:   # como el caso base: sólo las detecciones del incendio objetivo
        positivo, _ = p.cargar_cicatriz(Path(caso.datos["referencias"]["cicatriz"]["run"]), grilla)
        df = _cerca_de(df, positivo, grilla, float(radio))
    ignicion = cadena._leer(base["ventanas"][0]["phi.tif"]) < 0
    cicatriz = cadena._leer(comunes["cicatriz.tif"]).astype(bool)
    punto = _puntos_ignicion(semilla)
    alcance_m = caso.datos["referencias"]["firms"].get("alcance_m", 5000.0)
    inicio0 = base_caso.ventanas[0].inicio
    ventanas, previo = [], ignicion
    for n, v in enumerate(caso.ventanas):
        if v.fin > base_caso.ventanas[-1].fin:
            raise ValueError(f"ventana {n}: termina después del caso base")
        if n == 0:
            if v != base_caso.ventanas[0]:
                raise ValueError("la ventana 0 tiene que ser la del caso base")
            archivos, observado = dict(base["ventanas"][0]), ignicion
        else:
            h0 = int((v.t0 - inicio0).total_seconds() // 3600)
            bandas = pronostico.bandas_necesarias(v.horas, v.tstart_s)
            archivos = {}
            for nombre, sha in base["ventanas"][0].items():
                if nombre in REFERENCIAS_VENTANA:
                    continue
                with rasterio.open(almacen.abrir(sha)) as src:
                    multibanda = src.count > 1
                archivos[nombre] = (_clima_desde_base(base_caso, base["ventanas"], nombre, h0,
                                                      bandas) if multibanda else sha)
            antes = _puntos(df, None, v.inicio)
            if datos["semilla"] == "oraculo":
                vistas = _horas_por_pasada(df, v.inicio, v.inicio, dem,
                                           perimeter_reconstruction.VIIRS_PIXEL_M)
                observado = ignicion | (cicatriz & np.isfinite(vistas))
            else:
                observado = previo | ignicion | _mascara(_semilla_conexa(antes, semilla, grilla),
                                                         dem)
            with tempfile.TemporaryDirectory() as tmp:
                archivos["phi.tif"] = almacen.guardar(
                    ignition_builder.build_ignition_from_mask(observado, dem, Path(tmp)))
            nuevas = _mascara(_puntos(df, v.inicio, v.fin), dem) & ~observado
            det = _horas_por_pasada(df, v.inicio, v.fin, dem, MEDIO_PIXEL_VIIRS_M, desde=v.inicio)
            archivos |= {
                "ref_firms.tif": _guardar_array(nuevas, grilla, "uint8"),
                "ref_firms_horas.tif": _guardar_array(np.where(np.isinf(det), -1.0, det), grilla,
                                                      "float32", -1.0),
                "alcance.tif": _guardar_array(_alcance(punto + antes, dem, alcance_m), grilla,
                                              "uint8"),
            }
        archivos["vistas_horas.tif"] = _guardar_array(
            _horas_por_pasada(df, v.inicio, v.fin, dem, perimeter_reconstruction.VIIRS_PIXEL_M),
            grilla, "float32")
        previo = observado
        ventanas.append(archivos)
        print(f"  ventana {n} ({v.inicio:%d-%m %H:%M}): semilla "
              f"{observado.sum() * grilla.celda_ha:,.0f} ha", flush=True)
    return {"comunes": comunes, "ventanas": ventanas,
            "origen": base["origen"] | {"base": datos["base"], "semilla": datos["semilla"]}}


EMPAQUETADORES = {"legado_harness_a": _legado_harness_a, "legado_harness_b": _legado_harness_b,
                  "firms_gfs": _firms_gfs, "ampliar_mapas": _ampliar_mapas,
                  "viento_diurno": _viento_diurno, "pronostico": _pronostico}


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


SECTORES = ("N", "NE", "E", "SE", "S", "SO", "O", "NO")


def _rumbo(dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    """Sector (0 = N, en sentido horario) hacia donde está cada celda desde el origen."""
    return (np.round((np.degrees(np.arctan2(dx, dy)) % 360) / 45).astype(int)) % 8


def analizar(caso: d.Caso, receta: d.Receta) -> dict:
    """Las preguntas del loop, para una iteración: ¿sobre o sub-propaga, cuándo y dónde?

    - Curva: área predicha (fuera de la semilla y de la exclusión) contra la cicatriz ya
      alcanzada por detecciones VIIRS, hora a hora.
    - Dónde: aciertos, falsos positivos y no predichos de la última ventana por grupo de
      combustible, altura, pendiente y rumbo desde la ignición, con el viento medio al lado.
    """
    from app.validation import cadena

    manifiesto = d.cargar_manifiesto(caso.id, receta.id)
    paquete = caso.paquete()
    comunes = paquete["comunes"]
    leer = cadena._leer
    grilla = p.Grilla(almacen.abrir(comunes["dem.tif"]))
    ha = grilla.celda_ha
    dem, pend = leer(comunes["dem.tif"]), leer(comunes["slp.tif"])
    mapa = f"fbfm40_{receta.combustible['fuente']}{receta.anio_combustible(caso)}.tif"
    fuel = leer(comunes[mapa])
    cicatriz = leer(comunes["cicatriz.tif"]).astype(bool)
    excluido = leer(comunes["excluido.tif"]).astype(bool)
    semilla = leer(manifiesto["ventanas"][0]["insumos"]["phi.tif"]) < 0
    vistas = cadena.VISTAS / caso.id / receta.id
    with rasterio.open(vistas / "linea_tiempo.tif") as src:
        llegada = src.read(1) / 3600.0   # horas desde el inicio del caso; <0 = no llegó
    donde = ~excluido & ~semilla

    # Curva: lo observado hasta la hora h es la cicatriz a un píxel de alguna detección.
    df = pd.read_csv(almacen.abrir(comunes["firms.csv"]))
    df["acq_datetime"] = pd.to_datetime(df["acq_datetime"], utc=True)
    inicio = caso.ventanas[0].inicio
    total_h = int((caso.ventanas[-1].fin - inicio).total_seconds() // 3600)
    curva = []
    for h in range(6, total_h + 1, 6):
        vistas_h = _discos(_puntos(df, None, inicio + timedelta(hours=h)), grilla,
                           perimeter_reconstruction.VIIRS_PIXEL_M)
        pred = (llegada > 0) & (llegada <= h) & donde
        curva.append({"h": h, "predicho_ha": round(float(pred.sum() * ha)),
                      "observado_ha": round(float((cicatriz & vistas_h & donde).sum() * ha))})

    # Dónde: la confusión de la última ventana.
    n = len(manifiesto["ventanas"]) - 1
    with rasterio.open(vistas / f"v{n}" / "confusion.tif") as src:
        conf = src.read(1)
    ff, cc = np.nonzero(semilla)
    f0, c0 = ff.mean(), cc.mean()
    filas, cols = np.indices(conf.shape)
    celda = abs(grilla.transform.a)
    dx, dy = (cols - c0) * celda, (f0 - filas) * celda
    rumbo = _rumbo(dx, dy)
    dist = np.hypot(dx, dy)
    grupos = {"GR": (101, 109), "GS": (121, 124), "SH": (141, 149), "TU": (161, 165),
              "TL": (181, 189), "NB": (91, 99)}
    clases = {"acierto": cadena.ACIERTO, "falso_positivo": cadena.PREDICHO_SIN_OBS,
              "no_predicho": cadena.OBS_SIN_PREDECIR}
    donde_err = {}
    for nombre, codigo in clases.items():
        m = conf == codigo
        if not m.any():
            donde_err[nombre] = {"ha": 0}
            continue
        donde_err[nombre] = {
            "ha": round(float(m.sum() * ha)),
            "altura_m": [round(float(q)) for q in np.percentile(dem[m], [25, 50, 75])],
            "pendiente_grados": round(float(np.median(pend[m]))),
            "dist_ignicion_km": round(float(np.median(dist[m])) / 1000, 1),
            "combustible_ha": {g: round(float((m & (fuel >= a) & (fuel <= b)).sum() * ha))
                               for g, (a, b) in grupos.items()},
            "rumbo_ha": {SECTORES[k]: round(float((m & (rumbo == k)).sum() * ha))
                         for k in range(8)},
        }
    # Viento en la ignición, por ventana: medio y de la tarde (13-19 h locales, ~16-22 UTC).
    vientos = []
    for v, ventana in zip(caso.ventanas, paquete["ventanas"]):
        with rasterio.open(almacen.abrir(ventana["ws.tif"])) as a, \
                rasterio.open(almacen.abrir(ventana["wd.tif"])) as b:
            ws, wd = a.read()[:, int(f0), int(c0)], b.read()[:, int(f0), int(c0)]
        horas = np.array([(v.inicio + timedelta(hours=k)).hour for k in range(len(ws))])
        tarde = (horas >= 16) & (horas <= 22)
        u = -(ws * np.sin(np.radians(wd)))
        w = -(ws * np.cos(np.radians(wd)))
        def media(sel):
            if not sel.any():   # una ventana corta (p. ej. las 6 h finales de h54) sin tarde
                return {"mph": None, "desde_grados": None}
            uu, ww = u[sel].mean(), w[sel].mean()
            return {"mph": round(float(ws[sel].mean()), 1),
                    "desde_grados": round(float((np.degrees(np.arctan2(-uu, -ww))) % 360))}
        vientos.append({"n": v.inicio.isoformat(), "medio": media(np.ones_like(tarde)),
                        "tarde": media(tarde), "max_mph": round(float(ws.max()), 1)})
    # Rumbo del frente observado cada día (el cuartil más lejano de las detecciones desde la
    # ignición) contra hacia dónde empuja el viento medio del GFS en la ignición.
    tr = Transformer.from_crs("EPSG:4326", str(grilla.crs), always_xy=True)
    xs, ys = tr.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    x0, y0 = rasterio.transform.xy(grilla.transform, int(f0), int(c0))
    for v, viento in zip(caso.ventanas, vientos):
        sel = ((df["acq_datetime"] > pd.Timestamp(v.inicio))
               & (df["acq_datetime"] <= pd.Timestamp(v.fin))).to_numpy()
        if sel.sum() < 4:
            continue
        dx, dy = xs[sel] - x0, ys[sel] - y0
        lejos = np.hypot(dx, dy) >= np.percentile(np.hypot(dx, dy), 75)
        viento["frente_rumbo"] = round(float(np.degrees(np.arctan2(dx[lejos].mean(),
                                                                   dy[lejos].mean())) % 360))
        viento["gfs_hacia"] = (viento["medio"]["desde_grados"] + 180) % 360
        viento["desvio"] = (viento["frente_rumbo"] - viento["gfs_hacia"] + 180) % 360 - 180
    informe = {"caso": caso.id, "receta": receta.id, "curva": curva, "donde": donde_err,
               "ignicion_altura_m": round(float(dem[int(f0), int(c0)])), "viento": vientos}
    destino = d.ruta_iteracion(caso.id, receta.id) / "analisis.json"
    destino.write_text(json.dumps(informe, indent=2, ensure_ascii=False))
    _imprimir_analisis(informe)
    return informe


def _imprimir_analisis(a: dict) -> None:
    print(f"{a['caso']} · {a['receta']} (ignición a {a['ignicion_altura_m']} m)")
    print("  curva (h: predicho/observado ha): " + "  ".join(
        f"{c['h']}:{c['predicho_ha']}/{c['observado_ha']}" for c in a["curva"]))
    for nombre, m in a["donde"].items():
        if not m.get("ha"):
            print(f"  {nombre:15s} 0 ha")
            continue
        comb = " ".join(f"{g}{v}" for g, v in m["combustible_ha"].items() if v)
        rumbo = " ".join(f"{g}{v}" for g, v in m["rumbo_ha"].items() if v)
        print(f"  {nombre:15s} {m['ha']:6d} ha  alt {m['altura_m']}  pend {m['pendiente_grados']}°"
              f"  dist {m['dist_ignicion_km']} km | {comb} | {rumbo}")
    print("  frente observado vs GFS (rumbo/hacia, desvío): " + "  ".join(
        f"{v.get('frente_rumbo', '—')}/{v.get('gfs_hacia', '—')} ({v.get('desvio', '—'):+})"
        if "desvio" in v else "—" for v in a["viento"]))
    print("  viento (medio / tarde desde°·mph / máx): " + "  ".join(
        f"{v['medio']['desde_grados']}·{v['medio']['mph']}/{v['tarde']['desde_grados']}·"
        f"{v['tarde']['mph']}/{v['max_mph']}" for v in a["viento"]))


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
          f"{'iou':>7s}{'prec.':>7s}{'recall':>7s}  factores")
    for m in filas:
        pr = cadena.principal_completa(m) or {}
        alarma = " ⚠" if pr.get("alarma_sesgo") else ""
        ref = {"cicatriz": "C", "firms": "F"}.get(pr.get("referencia"), "")
        ai = pr.get("area_igualada") or {}
        hora = f"{ai['hora']:.0f}" + ("" if ai.get("alcanzada") else "+") if ai.get("hora") else "—"
        print(f"{m['receta']:28s}{_fmt(pr.get('dice')):>8s}{ref:>5s}"
              f"{_fmt(pr.get('sesgo_area')):>8s}{_fmt(ai.get('dice')):>8s}{hora:>6s}"
              f"{_fmt(pr.get('iou')):>7s}{_fmt(pr.get('precision')):>7s}"
              f"{_fmt(pr.get('recall')):>7s}  "
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


def _casos(conjunto: dict[str, list[str]], fuente: str) -> list[str]:
    """Los casos de una fuente de clima, o de todas (`todas`): la receta es una sola."""
    return [c for f in conjunto.values() for c in f] if fuente == "todas" else conjunto[fuente]


def _filas(casos: list[str]) -> dict[str, dict[str, dict]]:
    """{receta: {caso: principal}} para las iteraciones puntuadas contra la cicatriz."""
    filas: dict[str, dict[str, dict]] = {}
    for caso_id in casos:
        caso = d.Caso.cargar(caso_id)
        horizonte = (caso.ventanas[-1].fin - caso.ventanas[0].inicio).total_seconds() / 3600
        raiz = d.ruta_iteracion(caso_id, "")
        for ruta in sorted(raiz.glob("*/metricas.json")) if raiz.exists() else []:
            m = json.loads(ruta.read_text())
            pr = cadena.principal_completa(m) or {}
            if pr.get("referencia") != "cicatriz":
                continue
            ai = pr.get("area_igualada") or {}
            t = ai.get("hora") if ai.get("alcanzada") else None
            filas.setdefault(m["receta"], {})[caso_id] = {
                "dice": pr["dice"], "iou": pr["iou"], "precision": pr["precision"],
                "recall": pr["recall"], "sesgo": pr["sesgo_area"], "alarma": pr["alarma_sesgo"],
                "forma": ai.get("dice"), "dt": abs(t - horizonte) if t is not None else horizonte}
    return filas


def validar(fuente: str = "gfs") -> None:
    """Validación cruzada dejando un incendio afuera sobre los casos de calibración.

    Para cada incendio, se elige con los demás la receta de mayor Dice medio sin alarmas de
    sesgo (los casos límite de `particion.json` no cuentan para la restricción), y se mide
    cómo le va al que quedó afuera. Sólo recetas corridas en todos los casos.
    """
    particion = json.loads((d.RAIZ / "particion.json").read_text())
    casos = _casos(particion["calibracion"], fuente)
    limites = set(particion.get("limites", []))
    filas = {r: f for r, f in _filas(casos).items() if len(f) == len(casos)}
    print(f"validación cruzada, calibración/{fuente}: {len(casos)} casos, {len(filas)} recetas")
    afuera = []
    for k in casos:
        otros = [c for c in casos if c != k]
        factibles = {r: f for r, f in filas.items()
                     if not any(f[c]["alarma"] for c in otros if c not in limites)}
        if not factibles:
            print(f"  {k}: ninguna receta factible sin él")
            continue
        mejor = max(factibles, key=lambda r: np.mean([factibles[r][c]["dice"] for c in otros]))
        x = filas[mejor][k]
        afuera.append(x)
        mejor_propio = max(filas, key=lambda r: filas[r][k]["dice"])
        print(f"  sin {k:40s} → {mejor:22s} {x['dice']:.3f}/{x['sesgo']:.2f}"
              f"{'⚠' if x['alarma'] else ' '}  (su mejor posible: {mejor_propio} "
              f"{filas[mejor_propio][k]['dice']:.3f})")
    if afuera:
        print(f"  Dice fuera de muestra: media {np.mean([x['dice'] for x in afuera]):.3f}, "
              f"mediana {np.median([x['dice'] for x in afuera]):.3f}")


def objetivo(conjunto: str = "calibracion", fuente: str = "gfs") -> None:
    """La función objetivo de RESULTADOS-CSS-BAP sobre un conjunto de la partición.

    Principal: media y mediana del Dice al horizonte contra la cicatriz. Restricción: ningún
    caso con alarma de sesgo. Desempate: forma (Dice a área igualada) y |t* − horizonte|.
    Sólo recetas corridas en todos los casos del conjunto.
    """
    particion = json.loads((d.RAIZ / "particion.json").read_text())
    casos = _casos(particion[conjunto], fuente)
    filas = _filas(casos)
    print(f"{conjunto}/{fuente}: {len(casos)} casos; las medias de recetas incompletas (n < "
          f"{len(casos)}) no son comparables")
    cortos = [c.split("/")[0].replace("los-alerces", "alerces").replace("puerto-", "")[:13]
              for c in casos]
    print(f"{'receta':24s}{'n':>2s}{'media':>7s}{'mediana':>8s}{'alarm':>6s}{'forma':>7s}"
          f"{'|Δt*|':>7s}{'iou':>6s}{'prec':>6s}{'rec':>6s}  "
          + "  ".join(f"{c:>13s}" for c in cortos))
    orden = sorted(filas.items(), key=lambda kv: (-len(kv[1]),
                                                  -np.mean([v["dice"] for v in kv[1].values()])))
    for receta, f in orden:
        v = [f[c] for c in casos if c in f]
        celdas = "  ".join(f"{f[c]['dice']:.3f}/{f[c]['sesgo']:.2f}{'⚠' if f[c]['alarma'] else ' '}"
                           if c in f else f"{'—':>13s}" for c in casos)
        print(f"{receta:24s}{len(v):2d}{np.mean([x['dice'] for x in v]):7.3f}"
              f"{np.median([x['dice'] for x in v]):8.3f}{sum(x['alarma'] for x in v):6d}"
              f"{np.mean([x['forma'] or 0 for x in v]):7.3f}{np.mean([x['dt'] for x in v]):7.1f}"
              + "".join(f"{np.mean([x[k] for x in v]):6.3f}"
                        for k in ("iou", "precision", "recall"))
              + "  " + celdas)


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


def mostrar_modelo(modelo_id: str) -> None:
    """Valida y muestra el snapshot promovido sin ejecutar ELMFIRE."""
    modelo = d.Modelo.cargar(modelo_id)
    modelo.validar()
    print(json.dumps({
        "modelo": modelo.id,
        "estado": modelo.estado,
        "fecha_corte": modelo.fecha_corte,
        "receta": modelo.receta,
        "casos": len(modelo.casos),
        "codigo_sha": modelo.codigo_sha,
        "resultados": modelo.resultados,
        "gate": "válido",
    }, indent=2, ensure_ascii=False))


# ── P-24 y diagnóstico de copa (DIA-1-PROPUESTA §2 y §4) ──────────────────────

def crear_pronostico(base_id: str, semilla: str) -> d.Caso:
    """Escribe el caso P-24 de un caso de calibración: la ventana 0 del base y un reinicio de 24 h
    en cada pasada VIIRS que deje 24 h dentro del horizonte del base (§2.4)."""
    base = d.Caso.cargar(base_id)
    protocolo = {"firms": "pronostico-v6", "oraculo": "pronostico-oraculo-v6"}[semilla]
    ruta = d.RAIZ / "casos" / base.incendio / f"{protocolo}.json"
    if ruta.exists():
        raise SystemExit(f"{ruta} ya existe")
    df = pd.read_csv(almacen.abrir(base.paquete()["comunes"]["firms.csv"]),
                     parse_dates=["acq_datetime"])
    inicio, fin = base.ventanas[0].inicio, base.ventanas[-1].fin
    tiempos = df.loc[(df["acq_datetime"] > inicio) & (df["acq_datetime"] <= fin), "acq_datetime"]
    reinicios = [t.to_pydatetime() for t in pronostico.pasadas(tiempos)
                 if t.to_pydatetime() + timedelta(hours=24) <= fin]
    v0 = base.ventanas[0]
    datos = {k: base.datos[k] for k in ("anio_fuego", "caja_wgs84", "semilla_inicial",
                                         "referencias", "clima") if k in base.datos}
    datos = {
        "descripcion": (
            f"P-24 (docs/resultados/DIA-1-PROPUESTA.md §2) sobre `{base_id}`: la ventana 0 del "
            "caso base (desde la ignición) y un reinicio de 24 h en cada pasada VIIRS SP (última "
            "detección de cada grupo separado por menos de 2 h) que deja 24 h dentro del "
            "horizonte. "
            + ("Semilla: lo observado por FIRMS hasta el reinicio, acumulado."
               if semilla == "firms" else
               "Semilla oráculo: la cicatriz dNBR ya vista por VIIRS al reinicio (diagnóstico: "
               "usa la cicatriz final).")
            + " Estáticos, mapas, dosel, cicatriz y clima son los del caso base."),
        **datos,
        "ventanas": [{"t0": v0.t0.isoformat(), "horas": v0.horas}]
                    + [pronostico.ventana_desde(t) for t in reinicios],
        "empaquetado": {"tipo": "pronostico", "base": base_id, "semilla": semilla},
        "plazos": list(pronostico.PLAZOS_H),
        "cadena": {"caso": base_id, "receta": "lw-100-001"},
    }
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
    print(f"{ruta}: {len(reinicios)} reinicios")
    return d.Caso.cargar(f"{base.incendio}/{protocolo}")


def _ventanas_cadena(caso_id: str, receta_id: str) -> list:
    caso = d.Caso.cargar(caso_id)
    manifiesto = d.cargar_manifiesto(caso_id, receta_id)
    if manifiesto is None:
        raise FileNotFoundError(f"{caso_id}/{receta_id} no corrió")
    return [(v.inicio, v.fin, cadena._leer(w["insumos"]["phi.tif"]) < 0,
             p.horas_relativas(cadena._leer(cadena._toa(w["salidas"])), v.tstart_s))
            for v, w in zip(caso.ventanas, manifiesto["ventanas"])]


def puntuar_pronostico(caso: d.Caso, receta_id: str) -> list[dict]:
    """Por reinicio y plazo, el crecimiento de P-24, de la cadena de modelo-v0 y de la
    persistencia contra la misma referencia (§2.4). Se guarda junto a la iteración."""
    manifiesto = d.cargar_manifiesto(caso.id, receta_id)
    if manifiesto is None:
        raise FileNotFoundError(f"{caso.id}/{receta_id} no corrió")
    paquete = caso.paquete()
    cad = caso.datos["cadena"]
    if d.Caso.cargar(cad["caso"]).paquete()["comunes"]["dem.tif"] != paquete["comunes"]["dem.tif"]:
        raise ValueError(f"{caso.id} y {cad['caso']} no comparten la grilla")
    cadena_v0 = _ventanas_cadena(cad["caso"], cad["receta"])
    grilla = p.Grilla(almacen.abrir(paquete["comunes"]["dem.tif"]))
    cicatriz = cadena._leer(paquete["comunes"]["cicatriz.tif"]).astype(bool)
    excluido = cadena._leer(paquete["comunes"]["excluido.tif"]).astype(bool)
    filas, previa = [], None
    for v, w in zip(caso.ventanas, manifiesto["ventanas"]):
        archivos = paquete["ventanas"][w["n"]]
        semilla = cadena._leer(w["insumos"]["phi.tif"]) < 0
        horas = np.nan_to_num(p.horas_relativas(cadena._leer(cadena._toa(w["salidas"])),
                                                v.tstart_s), nan=np.inf)
        vistas = cadena._leer(archivos["vistas_horas.tif"])
        det = cadena._leer(archivos["ref_firms_horas.tif"])
        fila = {"incendio": caso.incendio, "n": w["n"], "inicio": v.inicio.isoformat(),
                "horas_desde_ignicion": (v.inicio - caso.ventanas[0].inicio).total_seconds() / 3600,
                "semilla_ha": float(semilla.sum() * grilla.celda_ha), "plazos": {}}
        for plazo in caso.datos["plazos"]:
            preds = {"p24": horas <= plazo,
                     "cadena": pronostico.quemado_en(cadena_v0, v.inicio + timedelta(hours=plazo))}
            if previa is not None:
                preds["persistencia"] = pronostico.persistencia(
                    semilla, previa[1], (v.inicio - previa[0]).total_seconds() / 3600, plazo,
                    grilla)
            fila["plazos"][str(plazo)] = {
                nombre: pronostico.puntuar(pred, semilla, cicatriz, excluido, vistas, det, plazo,
                                           grilla.celda_ha)
                for nombre, pred in preds.items()}
        filas.append(fila)
        previa = (v.inicio, semilla)
    destino = d.ruta_iteracion(caso.id, receta_id) / "pronostico.json"
    destino.write_text(json.dumps(filas, indent=2, ensure_ascii=False))
    return filas


def tabla_pronostico(receta_id: str, casos: list[str]) -> None:
    filas = []
    for caso_id in casos:
        filas += puntuar_pronostico(d.Caso.cargar(caso_id), receta_id)
    for plazo in pronostico.PLAZOS_H:
        print(f"\n## Crecimiento a {plazo} h (Dice / sesgo contra la cicatriz ya vista)\n")
        print("| Incendio | k | h desde ign. | semilla ha | obs. ha | P-24 | cadena v0 "
              "| persistencia |")
        print("|---|---:|---:|---:|---:|---|---|---|")
        for f in filas:
            m = f["plazos"][str(plazo)]
            celdas = [f"{_fmt(m[c]['cicatriz']['dice'])} / {_fmt(m[c]['cicatriz']['sesgo_area'])}"
                      if c in m else "—" for c in ("p24", "cadena", "persistencia")]
            print(f"| {f['incendio']} | {f['n']} | {f['horas_desde_ignicion']:.1f} | "
                  f"{f['semilla_ha']:,.0f} | {m['p24']['cicatriz']['observado_ha']:,.0f} | "
                  + " | ".join(celdas) + " |")
        for contra in ("cadena", "persistencia"):
            r = pronostico.resumir(filas, plazo, contra)
            print(f"\nP-24 contra {contra}, {plazo} h (k ≥ 1): mediana ΔDice "
                  f"{_fmt(r['mediana_delta'])}, mejora en {r['mejoran']} de {r['n']} incendios")
            protocolo = casos[0].split("/")[1]
            r_path = (d.RAIZ / "diagnosticos"
                      / f"{protocolo}-{receta_id}-{contra}-{plazo}h.json")
            r_path.write_text(json.dumps(r, indent=2, ensure_ascii=False))


def diagnosticar_copa(caso: d.Caso, receta_id: str = "lw-100-001") -> dict:
    """§4: en las celdas de bosque (TU, TL) con dosel que la cicatriz y VIIRS dan por quemadas
    cada día, ¿qué parte hace copa según CFIS (ajustado en rodales de coníferas) y qué parte según
    Van Wagner sobre Rothermel con el WAF de ELMFIRE? Cuenta cualquier hora del día hasta la de la
    primera detección de la celda. Ninguna corrida, ningún parámetro ajustado."""
    receta = d.Receta.cargar(receta_id)
    paquete = caso.paquete()
    comunes = paquete["comunes"]
    dem = almacen.abrir(comunes["dem.tif"])
    grilla = p.Grilla(dem)
    fbfm = cadena._leer(comunes[f"fbfm40_{receta.combustible['fuente']}"
                                f"{receta.anio_combustible(caso)}.tif"])
    cc = cadena._leer(comunes["cc.tif"]) / 100.0
    ch, cbh = cadena._leer(comunes["ch.tif"]) / 10.0, cadena._leer(comunes["cbh.tif"]) / 10.0
    con_dosel = ((cc >= 0.15) & (ch >= 2.0) & (cbh > 0) & (cadena._leer(comunes["cbd.tif"]) > 0)
                 & np.isin(fbfm, [*range(161, 166), *range(181, 190)]))
    cicatriz = cadena._leer(comunes["cicatriz.tif"]).astype(bool)
    df = pd.read_csv(almacen.abrir(comunes["firms.csv"]), parse_dates=["acq_datetime"])
    inicio = caso.ventanas[0].inicio
    vistas = _horas_por_pasada(df, inicio, caso.ventanas[-1].fin, dem,
                               perimeter_reconstruction.VIIRS_PIXEL_M)
    with open(almacen.abrir(comunes["fuel_models.csv"])) as fh:
        modelos = {int(r[0]): r for r in csv.reader(fh) if r}
    viva = cadena.HUMEDAD_VIVA_BASE | receta.parametros
    lh, lw = viva["lh_moisture_pct"] / 100, viva["lw_moisture_pct"] / 100
    dias = []
    for n, v in enumerate(caso.ventanas):
        desfase = (v.inicio - inicio).total_seconds() / 3600
        celdas = con_dosel & cicatriz & (vistas > desfase) & (vistas <= desfase + v.horas)
        clima = {}
        for nom in ("ws", "m1", "m10", "m100"):
            with rasterio.open(almacen.abrir(paquete["ventanas"][n][f"{nom}.tif"])) as src:
                clima[nom] = src.read()
        cfis_bajo = np.zeros(grilla.shape, bool)
        cfis_alto = np.zeros(grilla.shape, bool)
        van_wagner = np.zeros(grilla.shape, bool)
        por_modelo = {}
        for codigo in np.unique(fbfm[celdas]):
            fila = modelos.get(int(codigo))
            if fila is None or float(fila[3]) + float(fila[4]) <= 0:
                continue
            sel = celdas & (fbfm == codigo)
            prof_ft = float(fila[11])
            fsg = np.maximum(cbh[sel] - prof_ft * copa.PIE_M, 0.0)
            waf = copa.waf_elmfire(cc[sel], ch[sel], prof_ft)
            i0 = copa.intensidad_critica(cbh[sel])
            antes_de_verse = vistas[sel] - desfase   # horas desde el inicio de la ventana
            for b in range(clima["ws"].shape[0]):
                ws, m1 = clima["ws"][b][sel], clima["m1"][b][sel]
                ya = b <= antes_de_verse + 1
                u10 = ws * copa.MPH_20FT_A_KMH_10M
                for destino, con_100h in ((cfis_bajo, False), (cfis_alto, True)):
                    destino[sel] |= ya & (copa.prob_cfis(
                        u10, fsg, copa.consumo_superficial(fila, con_100h), m1) >= copa.CFIS_CORTE)
                _, flin = copa.rothermel(fila, m1 / 100, clima["m10"][b][sel] / 100,
                                         clima["m100"][b][sel] / 100, lh, lw, ws * waf * 88.0)
                van_wagner[sel] |= ya & (flin > i0)
            por_modelo[fila[1]] = {
                "ha": float(sel.sum() * grilla.celda_ha),
                "cfis_bajo": float((cfis_bajo & sel).sum() / sel.sum()),
                "cfis_alto": float((cfis_alto & sel).sum() / sel.sum()),
                "van_wagner": float((van_wagner & sel).sum() / sel.sum()),
                "cbh_m": float(np.median(cbh[sel])), "waf": float(np.median(waf))}
        total = celdas.sum()
        dias.append({"n": n, "inicio": v.inicio.isoformat(),
                     "con_dosel_ha": float(total * grilla.celda_ha),
                     **{k: float((m & celdas).sum() / total) if total else None
                        for k, m in (("cfis_bajo", cfis_bajo), ("cfis_alto", cfis_alto),
                                     ("van_wagner", van_wagner))},
                     "por_modelo": por_modelo})
    salida = {"caso": caso.id, "receta": receta_id, "dias": dias}
    destino = d.RAIZ / "diagnosticos" / "copa" / f"{caso.incendio}.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(salida, indent=2, ensure_ascii=False))
    print(f"\n{caso.id}: fracción del bosque quemado con dosel que hace copa antes de verse")
    print("| Día | con dosel ha | CFIS (SFC bajo) | CFIS (SFC alto) | Van Wagner + Rothermel |")
    print("|---:|---:|---:|---:|---:|")
    for dia in dias:
        print(f"| {dia['n'] + 1} | {dia['con_dosel_ha']:,.0f} | {_fmt(dia['cfis_bajo'])} | "
              f"{_fmt(dia['cfis_alto'])} | {_fmt(dia['van_wagner'])} |")
    return salida


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("empaquetar").add_argument("caso")
    sub.add_parser("diagnosticar").add_argument("caso")
    for nombre in ("correr", "puntuar", "verificar", "analizar"):
        s = sub.add_parser(nombre)
        s.add_argument("caso")
        s.add_argument("recetas", nargs="+")
    sub.add_parser("tabla").add_argument("caso")
    sub.add_parser("resumen")
    s = sub.add_parser("objetivo")
    s.add_argument("conjunto", nargs="?", default="calibracion")
    s.add_argument("fuente", nargs="?", default="gfs")
    sub.add_parser("validar").add_argument("fuente", nargs="?", default="gfs")
    sub.add_parser("modelo").add_argument("modelo")
    s = sub.add_parser("comparar")
    s.add_argument("a")
    s.add_argument("b")
    s = sub.add_parser("materializar")
    s.add_argument("caso")
    s.add_argument("receta")
    s.add_argument("ventana", type=int)
    s = sub.add_parser("crear-pronostico", help="caso P-24 desde un caso de calibración")
    s.add_argument("caso")
    s.add_argument("--semilla", choices=("firms", "oraculo"), default="firms")
    s = sub.add_parser("pronostico", help="tabla P-24 contra la cadena y la persistencia")
    s.add_argument("receta")
    s.add_argument("casos", nargs="+")
    s = sub.add_parser("copa", help="CFIS contra Van Wagner + Rothermel, sin correr nada")
    s.add_argument("caso")
    args = ap.parse_args()

    if args.cmd == "crear-pronostico":
        crear_pronostico(args.caso, args.semilla)
        return
    caso = d.Caso.cargar(args.caso) if hasattr(args, "caso") else None
    if args.cmd == "pronostico":
        tabla_pronostico(args.receta, args.casos)
    elif args.cmd == "copa":
        diagnosticar_copa(caso)
    elif args.cmd == "resumen":
        resumen()
    elif args.cmd == "objetivo":
        objetivo(args.conjunto, args.fuente)
    elif args.cmd == "validar":
        validar(args.fuente)
    elif args.cmd == "modelo":
        mostrar_modelo(args.modelo)
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
            elif args.cmd == "analizar":
                analizar(caso, receta)
            else:
                for r in cadena.verificar(caso, receta):
                    print(f"  ventana {r['n']}: {'igual' if r['toa_igual'] else 'DISTINTO'}")
        if args.cmd not in ("verificar", "analizar"):
            tabla(caso)


if __name__ == "__main__":
    main()
