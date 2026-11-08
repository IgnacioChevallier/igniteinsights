"""Puerta meteorológica (DIAGNOSTICO-PRECISION-E2E §3, frente 4), SIN correr ELMFIRE.

Compara el viento a 10 m del GFS (el que recibió ELMFIRE y el crudo) y del SMN WRF 4 km
contra las estaciones El Bolsón, Esquel y Futaleufú, en las horas de corrida de los casos
`pronostico-v6` de los 4 incendios de calibración 2023–2026. Nunca abre un caso de prueba.

    uv run python scripts/diagnostico_viento_estaciones.py

- Estación: SYNOP crudo de Ogimet (el de Meteostat rellena las horas NIL de El Bolsón).
- GFS recibido: la serie GFS cacheada del caso base, u/v interpolados bilinealmente a la
  estación como `derive_wind` los interpola a cada celda, pasados a 20 ft en mph con la regla
  del repo y vueltos a 10 m con la misma regla. GFS crudo: la celda de 0,25° más cercana.
- WRF: `magViento10`/`dirViento10` de los archivos `01H` del bucket público, leídos por rango
  HTTP (sólo esas dos variables), del ciclo más reciente con plazo ≥ 1 h (el análogo del GFS
  encadenado). Celda más cercana y bilineal sobre u/v en la grilla Lambert nativa.

Cachea todo en data/benchmark/cache/{synop,smn-wrf}/ y escribe
benchmarks/diagnosticos/e2e/datos/W_*.csv. Las funciones puras se prueban en
tests/test_diagnostico_viento_estaciones.py.
"""
import json
import math
import re
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from affine import Affine
from pyproj import Transformer

from app.elmfire.builder import weather_builder
from app.validation import almacen
from app.validation import definiciones as d

SALIDA = Path("benchmarks/diagnosticos/e2e/datos")
CACHE = Path("data/benchmark/cache")
CASOS = ["los-alerces-2023/pronostico-v6", "los-alerces-2024/pronostico-v6",
         "epuyen-2025/pronostico-v6", "puerto-patriada-2026/pronostico-v6"]
# id WMO: nombre, lat, lon, altura (m), según Meteostat (bulk stations/lite)
ESTACIONES = {"87800": ("El Bolsón", -41.9667, -71.5167, 337),
              "87803": ("Esquel", -42.9333, -71.15, 789),
              "85832": ("Futaleufú", -43.1892, -71.8489, 317)}
VIENTO_MIN_MS = 5 / 3.6
UTC_ART_H = -3
TARDE_LOCAL_H = range(14, 21)   # 14 a 20 h ART
KT_MS = 0.514444
CRITERIO_DTHETA, CRITERIO_SESGO = 10.0, 0.20

SMN = "https://smn-ar-wrf.s3-us-west-2.amazonaws.com"
# Grilla de los NetCDF 01H (atributos Lambert_Conformal y driver netCDF de GDAL; verificada
# contra lat/lon del archivo en `verificar_grilla_wrf`). El driver HDF5 la lee con el sur arriba.
WRF_CRS = ("+proj=lcc +lat_0=-34.999989 +lon_0=-65 +lat_1=-35 +lat_2=-35 +x_0=0 +y_0=0 "
           "+R=6370000 +units=m +no_defs")
WRF_TRANSFORM = Affine(4000.0, 0.0, -1998000.0, 0.0, -4000.0, 2498000.0)
WRF_FORMA = (1249, 999)


# ── funciones puras ───────────────────────────────────────────────────────────────────────

def parsear_synop(texto: str) -> pd.DataFrame:
    """Líneas de Ogimet `IIiii,AAAA,MM,DD,HH,mm,AAXX YYGGi IIiii iRixhVV Nddff [00fff] …=`
    → t (UTC), dirección (grados desde donde sopla; NaN si calma o variable) y rapidez (m/s).
    Sólo reportes en nudos (iw 3–4): los de Futaleufú en m/s (iw 1) son los automáticos de
    las horas intermedias, con un ff 1,5× el de las sinópticas vecinas en nudos (unidad
    incierta; Meteostat tampoco los usa). Salta NIL y grupos con '/'."""
    filas = []
    for linea in texto.splitlines():
        partes = linea.split(",")
        if len(partes) < 7 or not partes[0].isdigit():
            continue
        grupos = partes[6].rstrip("=").split()
        if "NIL" in grupos or len(grupos) < 5 or grupos[0] != "AAXX":
            continue
        iw, nddff = grupos[1][4], grupos[4]
        if iw not in "34" or "/" in nddff[1:]:
            continue
        dd, ff = int(nddff[1:3]), int(nddff[3:5])
        if ff == 99:   # rapidez ≥ 99: va en el grupo siguiente 00fff
            if len(grupos) < 6 or not grupos[5].startswith("00"):
                continue
            ff = int(grupos[5][2:])
        rapidez = ff * KT_MS
        direccion = float(dd * 10 % 360) if 1 <= dd <= 36 else math.nan
        anio, mes, dia, hora, minuto = map(int, partes[1:6])
        t = datetime(anio, mes, dia, hora, minuto, tzinfo=UTC)
        filas.append((t, direccion, rapidez))
    return pd.DataFrame(filas, columns=["t", "dir", "vel"]).drop_duplicates("t")


def dif_angular(modelo: np.ndarray, obs: np.ndarray) -> np.ndarray:
    """modelo − obs en [−180, 180)."""
    return (modelo - obs + 180.0) % 360.0 - 180.0


def uv(vel: np.ndarray, direccion: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Rapidez y dirección meteorológica ("desde") a u/v, como `speed_direction_to_uv`."""
    t = np.radians(direccion)
    return -vel * np.sin(t), -vel * np.cos(t)


def vel_dir(u: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.hypot(u, v), (np.degrees(np.arctan2(-u, -v)) + 360.0) % 360.0


def bilineal(a: np.ndarray, fila: float, col: float) -> np.ndarray:
    """Interpolación bilineal de a[..., H, W] en (fila, col) contados desde el centro de la
    celda [0, 0]."""
    f0, c0 = int(math.floor(fila)), int(math.floor(col))
    df, dc = fila - f0, col - c0
    return ((1 - df) * (1 - dc) * a[..., f0, c0] + (1 - df) * dc * a[..., f0, c0 + 1]
            + df * (1 - dc) * a[..., f0 + 1, c0] + df * dc * a[..., f0 + 1, c0 + 1])


def fila_col(transform: Affine, x: float, y: float) -> tuple[float, float]:
    """Índice fraccionario (fila, col) desde el centro de la celda [0, 0]."""
    col, fila = ~transform * (x, y)
    return fila - 0.5, col - 0.5


def elegir_ciclo(hora: datetime, plazos: dict[datetime, set[int]]) -> tuple[datetime, int]:
    """El ciclo más reciente que tiene `hora` con plazo ≥ 1 h (el f000 es la condición
    inicial, sin la dinámica de 4 km)."""
    for ciclo in sorted(plazos, reverse=True):
        plazo = int((hora - ciclo).total_seconds() // 3600)
        if plazo >= 1 and plazo in plazos[ciclo]:
            return ciclo, plazo
    raise LookupError(f"ningún ciclo WRF cubre {hora:%Y-%m-%d %H} UTC")


def metricas(obs_dir: np.ndarray, obs_vel: np.ndarray, mod_dir: np.ndarray,
             mod_vel: np.ndarray) -> dict[str, float]:
    da = dif_angular(np.asarray(mod_dir, float), np.asarray(obs_dir, float))
    ev = np.asarray(mod_vel, float) - np.asarray(obs_vel, float)
    rad = np.radians(da)
    return {"n": len(da),
            "err_ang_medio": float(np.mean(np.abs(da))),
            "err_ang_mediano": float(np.median(np.abs(da))),
            "desvio_dir_mediano": float(np.median(da)),
            "desvio_dir_circular": float(np.degrees(np.arctan2(np.sin(rad).mean(),
                                                               np.cos(rad).mean()))),
            "sd_dir_circular": float(np.degrees(np.sqrt(-2 * np.log(np.hypot(
                np.sin(rad).mean(), np.cos(rad).mean()))))),
            "vel_obs_media": float(np.mean(obs_vel)),
            "sesgo_vel": float(np.mean(ev)),
            "cociente_vel": float(np.mean(mod_vel) / np.mean(obs_vel)),
            "rmse_vel": float(np.sqrt(np.mean(ev ** 2)))}


def pasa_estacion(gfs: dict[str, float], wrf: dict[str, float]) -> bool:
    """Frente 4: WRF baja el error angular mediano ≥ 10° y el |sesgo| de rapidez ≥ 20 %."""
    return (gfs["err_ang_mediano"] - wrf["err_ang_mediano"] >= CRITERIO_DTHETA
            and abs(wrf["sesgo_vel"]) <= (1 - CRITERIO_SESGO) * abs(gfs["sesgo_vel"]))


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


# ── datos ─────────────────────────────────────────────────────────────────────────────────

def horas_de_corrida(caso: d.Caso) -> list[datetime]:
    """Unión de las horas enteras que tocan las ventanas (de la hora del inicio a la del fin)."""
    horas: set[datetime] = set()
    for v in caso.ventanas:
        h = v.inicio.replace(minute=0, second=0, microsecond=0)
        while h <= v.fin:
            horas.add(h)
            h += timedelta(hours=1)
    return sorted(horas)


def synop(estacion: str, desde: datetime, hasta: datetime) -> pd.DataFrame:
    ruta = CACHE / "synop" / f"{estacion}_{desde:%Y%m%d%H}_{hasta:%Y%m%d%H}.txt"
    if not ruta.exists():
        url = (f"https://www.ogimet.com/cgi-bin/getsynop?block={estacion}"
               f"&begin={desde:%Y%m%d%H%M}&end={hasta:%Y%m%d%H%M}")
        texto = urllib.request.urlopen(url, timeout=60).read().decode("latin-1")
        if not texto.startswith(estacion):
            raise RuntimeError(f"Ogimet {estacion}: respuesta inesperada: {texto[:200]!r}")
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto)
        time.sleep(15)   # Ogimet limita la frecuencia de pedidos
    return parsear_synop(ruta.read_text())


def meteostat(estacion: str) -> pd.DataFrame | None:
    ruta = CACHE / f"{estacion}.csv.gz"
    if not ruta.exists():
        return None
    cols = "date,hour,temp,dwpt,rhum,prcp,snow,wdir,wspd,wpgt,pres,tsun,coco".split(",")
    df = pd.read_csv(ruta, names=cols)
    df["t"] = (pd.to_datetime(df["date"]) + pd.to_timedelta(df["hour"], unit="h")) \
        .dt.tz_localize("UTC")
    df = df.set_index("t")[["wdir", "wspd"]]
    return df[~df.index.duplicated()]


def serie_gfs(base: d.Caso) -> tuple[Path, datetime]:
    """La serie GFS cruda que usó el empaquetado del caso base (`benchmark._clima`): la de
    data/benchmark/cache/gfs cuya caja contiene la del caso y cubre sus horas."""
    w, s, e, n = base.datos["caja_wgs84"]
    inicio, fin = base.ventanas[0].inicio, base.ventanas[-1].fin
    for ruta in sorted((CACHE / "gfs").glob("*_*h_*")):
        t, h, *caja = ruta.name.split("_")
        t0 = datetime.strptime(t, "%Y%m%dT%H").replace(tzinfo=UTC)
        cw, cs, ce, cn = map(float, caja)
        if (t0 == inicio and t0 + timedelta(hours=int(h[:-1])) >= fin
                and cw < w and cs < s and ce > e and cn > n and (ruta / "u10.tif").exists()):
            return ruta, t0
    raise FileNotFoundError(f"{base.id}: sin serie GFS en la caché")


def gfs_en_estacion(serie: Path, t0: datetime, lat: float, lon: float,
                    horas: list[datetime]) -> pd.DataFrame | None:
    """None si la estación cae fuera de la serie (el repo no interpola hasta ahí)."""
    with rasterio.open(serie / "u10.tif") as su, rasterio.open(serie / "v10.tif") as sv:
        fila, col = fila_col(su.transform, lon, lat)
        if not (0 <= fila < su.height - 1 and 0 <= col < su.width - 1):
            return None
        bandas = [int((h - t0).total_seconds() // 3600) + 1 for h in horas]
        u, v = su.read(bandas), sv.read(bandas)
    ub, vb = bilineal(u, fila, col), bilineal(v, fila, col)
    # lo que recibe ELMFIRE (derive_wind): 20 ft en mph; vuelta a 10 m con la misma regla
    ws_mph = np.hypot(ub, vb) * weather_builder.wind_height_factor() * weather_builder.MS_TO_MPH
    _, wd = vel_dir(ub, vb)
    fc, cc = int(round(fila)), int(round(col))
    vc, dc = vel_dir(u[:, fc, cc], v[:, fc, cc])
    ws_10m = ws_mph / weather_builder.MS_TO_MPH / weather_builder.wind_height_factor()
    return pd.DataFrame({"t": horas, "gfs_recibido_vel": ws_10m, "gfs_recibido_dir": wd,
                         "gfs_crudo_vel": vc, "gfs_crudo_dir": dc})


def verificar_paquete(base: d.Caso, serie: Path, t0: datetime) -> float:
    """Diferencia relativa máxima entre el ws.tif del paquete (ventana 0) y la bilineal de la
    serie en 5 celdas: confirma que `gfs_en_estacion` reproduce lo que recibió ELMFIRE."""
    ventana0 = base.paquete()["ventanas"][0]
    peor = 0.0
    with rasterio.open(almacen.abrir(ventana0["ws.tif"])) as ws:
        tr = Transformer.from_crs(ws.crs, "EPSG:4326", always_xy=True)
        for fr in (0.2, 0.4, 0.5, 0.6, 0.8):
            f, c = int(ws.height * fr), int(ws.width * (1 - fr))
            lon, lat = tr.transform(*(ws.transform * (c + 0.5, f + 0.5)))
            paquete = ws.read(1)[f, c]
            calc = gfs_en_estacion(serie, t0, lat, lon, [base.ventanas[0].t0])
            assert calc is not None
            mph = calc["gfs_recibido_vel"].iloc[0] * weather_builder.wind_height_factor() \
                * weather_builder.MS_TO_MPH
            peor = max(peor, abs(mph / paquete - 1))
    return peor


def listado_wrf(dias: list[datetime]) -> dict[datetime, dict[int, int]]:
    """{ciclo: {plazo: bytes}} de los 01H en el bucket, para los días pedidos (cacheado)."""
    ruta = CACHE / "smn-wrf" / "listado.json"
    previo = json.loads(ruta.read_text()) if ruta.exists() else {}
    for dia in dias:
        clave = f"{dia:%Y/%m/%d}"
        if clave in previo:
            continue
        xml = urllib.request.urlopen(
            f"{SMN}/?list-type=2&prefix=DATA/WRF/DET/{clave}/", timeout=60).read().decode()
        if "<IsTruncated>true" in xml:
            raise RuntimeError(f"listado de {clave} truncado")
        previo[clave] = {k.split("/")[-1]: int(s) for k, s in zip(
            re.findall(r"<Key>([^<]*)</Key>", xml), re.findall(r"<Size>(\d+)</Size>", xml))}
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(previo, indent=1))
    plazos: dict[datetime, dict[int, int]] = {}
    for archivos in previo.values():
        for nombre, tam in archivos.items():
            m = re.fullmatch(r"WRFDETAR_01H_(\d{8})_(\d{2})_(\d{3})\.nc", nombre)
            if m:
                ciclo = datetime.strptime(m[1] + m[2], "%Y%m%d%H").replace(tzinfo=UTC)
                plazos.setdefault(ciclo, {})[int(m[3])] = tam
    return plazos


def url_wrf(ciclo: datetime, plazo: int) -> str:
    return (f"{SMN}/DATA/WRF/DET/{ciclo:%Y/%m/%d/%H}/"
            f"WRFDETAR_01H_{ciclo:%Y%m%d_%H}_{plazo:03d}.nc")


def ventana_wrf() -> tuple[slice, slice, Affine]:
    """Recorte de la grilla WRF que contiene las tres estaciones con 2 celdas de margen."""
    tr = Transformer.from_crs("EPSG:4326", WRF_CRS, always_xy=True)
    fc = [fila_col(WRF_TRANSFORM, *tr.transform(lon, lat))
          for _, lat, lon, _ in ESTACIONES.values()]
    f0, f1 = int(min(f for f, _ in fc)) - 2, int(max(f for f, _ in fc)) + 3
    c0, c1 = int(min(c for _, c in fc)) - 2, int(max(c for _, c in fc)) + 3
    return slice(f0, f1), slice(c0, c1), WRF_TRANSFORM * Affine.translation(c0, f0)


def leer_wrf(ciclo: datetime, plazo: int) -> np.ndarray:
    """(2, h, w): magViento10 y dirViento10 del recorte, con el norte arriba (cacheado)."""
    ruta = CACHE / "smn-wrf" / f"{ciclo:%Y%m%d%H}_{plazo:03d}.npy"
    if ruta.exists():
        return np.load(ruta)
    filas, cols, _ = ventana_wrf()
    capas = []
    for var in ("magViento10", "dirViento10"):
        # una sola variable por rango HTTP: ~4 MB contra ~35 MB del archivo entero
        with rasterio.open(f'HDF5:"/vsicurl/{url_wrf(ciclo, plazo)}"://{var}') as src:
            if src.shape != WRF_FORMA:
                raise RuntimeError(f"{url_wrf(ciclo, plazo)}: grilla {src.shape}")
            capas.append(src.read(1)[::-1][filas, cols])
    datos = np.stack(capas).astype("float32")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(".tmp.npy")
    np.save(temporal, datos)
    temporal.rename(ruta)   # una corrida cortada no deja un .npy a medias
    return datos


def verificar_grilla_wrf(ciclo: datetime, plazo: int) -> float:
    """Distancia máxima (km) entre el lat/lon del archivo y el de WRF_CRS/WRF_TRANSFORM en el
    recorte: confirma la georreferencia y el volteo de filas."""
    filas, cols, transform = ventana_wrf()
    leido = {}
    for var in ("lat", "lon"):
        with rasterio.open(f'HDF5:"/vsicurl/{url_wrf(ciclo, plazo)}"://{var}') as src:
            leido[var] = src.read(1)[::-1][filas, cols]
    tr = Transformer.from_crs(WRF_CRS, "EPSG:4326", always_xy=True)
    peor = 0.0
    for f in range(leido["lat"].shape[0]):
        for c in range(leido["lat"].shape[1]):
            lon, lat = tr.transform(*(transform * (c + 0.5, f + 0.5)))
            peor = max(peor, distancia_km(lat, lon, leido["lat"][f, c], leido["lon"][f, c]))
    return peor


def wrf_en_estaciones(horas: list[datetime],
                      plazos: dict[datetime, dict[int, int]]) -> pd.DataFrame:
    elegidos = {h: elegir_ciclo(h, {c: set(p) for c, p in plazos.items()}) for h in horas}
    # procesos y no hilos: el driver HDF5 de GDAL serializa los hilos (~10 s por hora)
    with ProcessPoolExecutor(max_workers=8) as pool:
        datos = dict(zip(horas, pool.map(leer_wrf, *zip(*(elegidos[h] for h in horas)))))
    _, _, transform = ventana_wrf()
    tr = Transformer.from_crs("EPSG:4326", WRF_CRS, always_xy=True)
    filas = []
    for est, (_, lat, lon, _) in ESTACIONES.items():
        fila, col = fila_col(transform, *tr.transform(lon, lat))
        for h in horas:
            mag, dir_ = datos[h]
            u, v = uv(mag, dir_)
            vb, db = vel_dir(bilineal(u, fila, col), bilineal(v, fila, col))
            fc, cc = int(round(fila)), int(round(col))
            filas.append({"estacion": est, "t": h, "wrf_ciclo": elegidos[h][0],
                          "wrf_plazo": elegidos[h][1],
                          "wrf_cercano_vel": mag[fc, cc], "wrf_cercano_dir": dir_[fc, cc] % 360,
                          "wrf_bilineal_vel": float(vb), "wrf_bilineal_dir": float(db)})
    return pd.DataFrame(filas)


# ── tablas ────────────────────────────────────────────────────────────────────────────────

FUENTES = ("gfs_recibido", "gfs_crudo", "wrf_cercano", "wrf_bilineal")


def tabla_metricas(horas: pd.DataFrame) -> pd.DataFrame:
    filas = []
    grupos = [("total", horas)] + list(horas.groupby("estacion"))
    for est, g in grupos:
        for franja, sub in (("todas", g), ("tarde", g[g["tarde"]]), ("resto", g[~g["tarde"]])):
            for fuente in FUENTES:
                if len(sub) < 3:
                    continue
                filas.append({"estacion": est, "franja": franja, "fuente": fuente,
                              **metricas(sub["obs_dir"], sub["obs_vel"],
                                         sub[f"{fuente}_dir"], sub[f"{fuente}_vel"])})
    return pd.DataFrame(filas)


def main() -> None:
    particion = json.loads(Path("benchmarks/particion.json").read_text())
    plazos = None
    estaciones, disponibilidad, horas_tabla, verif = [], [], [], []
    for caso_id in CASOS:
        caso = d.Caso.cargar(caso_id)
        base = d.Caso.cargar(caso.datos["empaquetado"]["base"])
        if base.id not in particion["calibracion"]["gfs"]:
            raise ValueError(f"{base.id} no es de calibración")
        horas = horas_de_corrida(caso)
        serie, t0 = serie_gfs(base)
        verif.append((caso.incendio, verificar_paquete(base, serie, t0)))
        dias = sorted({(h - timedelta(hours=k)).replace(hour=0)
                       for h in horas for k in (0, 24)})
        plazos = listado_wrf(dias)
        for dia in dias:
            ciclos = sorted(c for c in plazos if c.date() == dia.date())
            disponibilidad.append({
                "incendio": caso.incendio, "dia": f"{dia:%Y-%m-%d}",
                "ciclos": " ".join(f"{c:%H}" for c in ciclos),
                "plazos_01h_por_ciclo": " ".join(str(len(plazos[c])) for c in ciclos),
                "gb_01h_por_ciclo_medio": round(np.mean([sum(plazos[c].values())
                                                         for c in ciclos]) / 1e9, 2)
                if ciclos else None})
        wrf = wrf_en_estaciones(horas, plazos)
        ignicion = caso.datos["semilla_inicial"]
        desde, hasta = horas[0] - timedelta(hours=1), horas[-1] + timedelta(hours=1)
        for est, (nombre, lat, lon, alt) in ESTACIONES.items():
            obs = synop(est, desde, hasta).set_index("t")
            ms = meteostat(est)
            obs_h = obs.reindex(horas)
            ms_h = ms.reindex(horas) if ms is not None else None
            coincide = (np.isclose(ms_h["wspd"], obs_h["vel"] * 3.6, atol=1.0)
                        if ms_h is not None else np.zeros(len(horas), bool))
            gfs = gfs_en_estacion(serie, t0, lat, lon, horas)
            estaciones.append({
                "incendio": caso.incendio, "estacion": est, "nombre": nombre, "lat": lat,
                "lon": lon, "altura_m": alt,
                "distancia_ignicion_km": round(distancia_km(lat, lon, ignicion["lat"],
                                                            ignicion["lon"]), 1),
                "horas_corrida": len(horas), "horas_synop": int(obs_h["vel"].notna().sum()),
                "horas_synop_viento_mayor_5": int((obs_h["vel"] > VIENTO_MIN_MS).sum()),
                "horas_meteostat": int(ms_h["wspd"].notna().sum()) if ms_h is not None else 0,
                "meteostat_igual_synop": int(coincide.sum()),
                "en_serie_gfs": gfs is not None})
            if gfs is None:
                continue
            fila = obs_h.rename(columns={"dir": "obs_dir", "vel": "obs_vel"}).reset_index() \
                .merge(gfs, on="t").merge(wrf[wrf["estacion"] == est].drop(columns="estacion"),
                                          on="t")
            fila.insert(0, "estacion", nombre)
            fila.insert(0, "incendio", caso.incendio)
            horas_tabla.append(fila)
    print("ws del paquete contra la bilineal de la serie (máx. dif. relativa):", verif)
    primero = min(plazos) if plazos else None
    if primero is not None:
        print(f"grilla WRF: error máx. de georreferencia "
              f"{verificar_grilla_wrf(primero, 1):.3f} km")
    horas_df = pd.concat(horas_tabla, ignore_index=True)
    horas_df["hora_local"] = (pd.to_datetime(horas_df["t"]).dt.hour + UTC_ART_H) % 24
    horas_df["tarde"] = horas_df["hora_local"].isin(TARDE_LOCAL_H)
    validas = horas_df[(horas_df["obs_vel"] > VIENTO_MIN_MS) & horas_df["obs_dir"].notna()]
    met = tabla_metricas(validas)
    por_incendio = pd.DataFrame([{"incendio": inc, **metricas(
        g["obs_dir"], g["obs_vel"], g["gfs_recibido_dir"], g["gfs_recibido_vel"])}
        for inc, g in validas.groupby("incendio")])
    s5 = pd.read_csv(SALIDA / "S5_dispersion_por_incendio.csv")
    gefs = por_incendio.merge(s5, on="incendio")
    gefs["error_vel_relativo"] = gefs["rmse_vel"] / gefs["vel_obs_media"]
    criterio = []
    todas = met[met["franja"] == "todas"]
    for est in validas["estacion"].unique():
        g = todas[todas["estacion"] == est].set_index("fuente")
        for wrf_f in ("wrf_bilineal", "wrf_cercano"):
            gg, ww = g.loc["gfs_recibido"], g.loc[wrf_f]
            criterio.append({"estacion": est, "wrf": wrf_f, "n": int(gg["n"]),
                             "gfs_err_ang_mediano": gg["err_ang_mediano"],
                             "wrf_err_ang_mediano": ww["err_ang_mediano"],
                             "reduccion_ang": gg["err_ang_mediano"] - ww["err_ang_mediano"],
                             "gfs_sesgo_vel": gg["sesgo_vel"], "wrf_sesgo_vel": ww["sesgo_vel"],
                             "reduccion_sesgo_rel": 1 - abs(ww["sesgo_vel"]) / abs(gg["sesgo_vel"]),
                             "pasa": pasa_estacion(gg.to_dict(), ww.to_dict())})
    SALIDA.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(estaciones).to_csv(SALIDA / "W_estaciones.csv", index=False)
    pd.DataFrame(disponibilidad).drop_duplicates(["incendio", "dia"]) \
        .to_csv(SALIDA / "W_wrf_disponibilidad.csv", index=False)
    horas_df.to_csv(SALIDA / "W_horas.csv", index=False, float_format="%.3f")
    met.to_csv(SALIDA / "W_metricas.csv", index=False, float_format="%.3f")
    pd.DataFrame([{"incendio": inc, "estacion": est, "fuente": f, **metricas(
        g["obs_dir"], g["obs_vel"], g[f"{f}_dir"], g[f"{f}_vel"])}
        for (inc, est), g in validas.groupby(["incendio", "estacion"]) for f in FUENTES]) \
        .to_csv(SALIDA / "W_metricas_por_incendio.csv", index=False, float_format="%.3f")
    pd.DataFrame(criterio).to_csv(SALIDA / "W_criterio.csv", index=False, float_format="%.3f")
    gefs.to_csv(SALIDA / "W_gefs_contra_error.csv", index=False, float_format="%.3f")
    print(pd.DataFrame(criterio).to_string())


if __name__ == "__main__":
    main()
