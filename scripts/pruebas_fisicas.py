"""Banco de pruebas físicas: ELMFIRE 2025.0212 real sobre dominios sintéticos chicos.

Cada prueba es un experimento controlado con una predicción y una tolerancia. Los insumos
salen de los builders del repo (write_namelist, weather_builder.derive_wind,
raster_aligner._derive_slope_aspect), así que una convención mal puesta en el pipeline
falla acá antes de llegar a una calibración (AUDITORIA-FISICA.md §4).

    uv run python scripts/pruebas_fisicas.py            # todas
    uv run python scripts/pruebas_fisicas.py viento pendiente

Necesita el runner (`make dev-simulation`) y no corre en `make check`. Corre un ELMFIRE por
vez: no lanzarlo mientras la cola del benchmark (data/benchmark/cola_run2.sh) trabaja.
Resultados en data/benchmark/fisica/resultados.json.
"""
import asyncio
import csv
import json
import math
import os
import shutil
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.transform import from_origin

# El .env apunta al servicio dentro de Docker; desde el host es localhost (como benchmark.py).
os.environ.setdefault("ELMFIRE_RUNNER_URL", "http://localhost:8001")

from app.elmfire.builder import (  # noqa: E402
    fuels_builder,
    ignition_builder,
    namelist_writer,
    weather_builder,
)
from app.elmfire.builder.raster_aligner import _derive_slope_aspect  # noqa: E402
from app.elmfire.runner.client import ELMFIRERunnerClient  # noqa: E402
from app.elmfire.runner.schemas import SimulationRequest  # noqa: E402

RAIZ = Path("data/benchmark/fisica")
CONTENEDOR = Path("/app")          # el runner monta ./data en /app/data
CRS = "EPSG:32719"
ORIGEN = (560_000.0, 5_250_000.0)  # esquina NO, dentro del AOI (Los Alerces)
FT_MIN_A_M_S = 0.3048 / 60
MPH_A_M_S = 0.44704

# ── Rothermel (1972) con Albini (1976), la referencia independiente ──────────────────
# Las ecuaciones de Andrews (2018, RMRS-GTR-371), en unidades inglesas, con la carga neta
# pesada por subclase de tamaño (g_ij de Albini 1976), como BehavePlus: con f_ij a secas
# (Rothermel 1972) GR2 da un 17 % menos, porque la herbácea curada y el 1-h caen en la
# misma subclase (SAV ≥ 1200) y ahí g = 1.
SUBCLASES_SAV = (1200.0, 192.0, 96.0, 48.0, 16.0)


def _subclase(sav: float) -> int:
    return next((i for i, lim in enumerate(SUBCLASES_SAV) if sav >= lim), len(SUBCLASES_SAV))

def modelos() -> dict[int, dict]:
    """La tabla que viaja a ELMFIRE (fuel_models.csv), por código."""
    salida = {}
    with fuels_builder.FUEL_MODEL_TABLE.open() as f:
        for fila in csv.reader(f):
            cod, nombre, dinamico, w1, w10, w100, wlh, wlw, s1, slh, slw, prof, mx, h = fila
            salida[int(cod)] = {
                "nombre": nombre, "dinamico": dinamico == ".TRUE.",
                "w": [float(w1), float(w10), float(w100), float(wlh), float(wlw)],
                "sav": [float(s1), 109.0, 30.0, float(slh), float(slw)],
                "prof": float(prof), "mx": float(mx) / 100, "h": float(h)}
    return salida


def waf_sin_dosel(prof_ft: float) -> float:
    """Albini y Baughman (1979), sin dosel: 1,83 / ln((20 + 0,36 H) / 0,13 H)."""
    return 1.83 / math.log((20 + 0.36 * prof_ft) / (0.13 * prof_ft))


def waf_con_dosel(cc_pct: float, ch_m: float) -> float:
    """Albini y Baughman (1979) bajo dosel, con crown ratio 1 y f = CC/3 (BEHAVE)."""
    h_ft = ch_m / 0.3048
    return 0.555 / (math.sqrt(cc_pct / 100 / 3 * h_ft)
                    * math.log((20 + 0.36 * h_ft) / (0.13 * h_ft)))


def rothermel(fm: dict, m1: float, m10: float, m100: float, lh: float, lw: float,
              u20_mph: float = 0.0, waf: float | None = None, pendiente_grados: float = 0.0,
              ) -> dict:
    """Velocidad de cabeza (ft/min) y lo que hace falta para la elipse. Humedades en %."""
    w, sav = list(fm["w"]), list(fm["sav"])
    mois = [m1 / 100, m10 / 100, m100 / 100, lh / 100, lw / 100]
    # Scott y Burgan: transferencia dinámica de la herbácea viva a muerta (curada).
    clases = [(w[0], sav[0], mois[0], "d"), (w[1], sav[1], mois[1], "d"),
              (w[2], sav[2], mois[2], "d")]
    if fm["dinamico"]:
        curado = min(max((120 - lh) / 90, 0.0), 1.0)
        clases.append((w[3] * curado, sav[3], mois[0], "d"))
        clases.append((w[3] * (1 - curado), sav[3], mois[3], "v"))
    else:
        clases.append((w[3], sav[3], mois[3], "v"))
    clases.append((w[4], sav[4], mois[4], "v"))
    clases = [c for c in clases if c[0] > 0]
    rhop, st, se = 32.0, 0.0555, 0.010   # ELMFIRE usa ST = 0,055
    area = {"d": 0.0, "v": 0.0}
    for wi, si, _, cat in clases:
        area[cat] += si * wi / rhop
    total = area["d"] + area["v"]

    def f(c):  # fracción de área dentro de su categoría
        return c[1] * c[0] / rhop / area[c[3]]
    sig_cat = {k: sum(f(c) * c[1] for c in clases if c[3] == k) if area[k] else 0 for k in area}
    fcat = {k: area[k] / total for k in area}
    sigma = sum(fcat[k] * sig_cat[k] for k in area)
    beta = sum(c[0] for c in clases) / (fm["prof"] * rhop)
    beta_op = 3.348 * sigma ** -0.8189
    rho_b = sum(c[0] for c in clases) / fm["prof"]
    a = 133 * sigma ** -0.7913
    gmax = sigma ** 1.5 / (495 + 0.0594 * sigma ** 1.5)
    gamma = gmax * (beta / beta_op) ** a * math.exp(a * (1 - beta / beta_op))
    eta_s = min(0.174 * se ** -0.19, 1.0)
    # humedad de extinción de lo vivo
    muertos = [c for c in clases if c[3] == "d"]
    vivos = [c for c in clases if c[3] == "v"]
    mx = {"d": fm["mx"]}
    if vivos:
        num = sum(c[0] * math.exp(-138 / c[1]) for c in muertos)
        den = sum(c[0] * math.exp(-500 / c[1]) for c in vivos)
        mf = sum(c[0] * math.exp(-138 / c[1]) * c[2] for c in muertos) / num
        mx["v"] = max(2.9 * num / den * (1 - mf / fm["mx"]) - 0.226, fm["mx"])
    ir = 0.0
    for k in area:
        if not area[k]:
            continue
        cs = [c for c in clases if c[3] == k]
        g = {sub: sum(f(c) for c in cs if _subclase(c[1]) == sub) for sub in range(6)}
        wn = sum(g[_subclase(c[1])] * c[0] for c in cs) * (1 - st)
        m = sum(f(c) * c[2] for c in cs)
        r = min(m / mx[k], 1.0)
        eta_m = max(0.0, 1 - 2.59 * r + 5.11 * r ** 2 - 3.52 * r ** 3)
        ir += gamma * wn * fm["h"] * eta_m * eta_s
    xi = math.exp((0.792 + 0.681 * sigma ** 0.5) * (beta + 0.1)) / (192 + 0.2595 * sigma)
    rho_eps_q = rho_b * sum(fcat[c[3]] * f(c) * math.exp(-138 / c[1]) * (250 + 1116 * c[2])
                            for c in clases)
    c_ = 7.47 * math.exp(-0.133 * sigma ** 0.55)
    b_ = 0.02526 * sigma ** 0.54
    e_ = 0.715 * math.exp(-3.59e-4 * sigma)
    waf = waf_sin_dosel(fm["prof"]) if waf is None else waf
    u = min(u20_mph * waf * 88.0, 0.9 * ir)          # ft/min a media llama, con el límite
    phi_w = c_ * u ** b_ * (beta / beta_op) ** -e_ if u > 0 else 0.0
    phi_s = 5.275 * beta ** -0.3 * math.tan(math.radians(pendiente_grados)) ** 2
    r0 = ir * xi / rho_eps_q if ir > 0 else 0.0
    # viento efectivo (para la elipse): el que da phi_w + phi_s sin pendiente
    phi = phi_w + phi_s
    u_ef = (phi / (c_ * (beta / beta_op) ** -e_)) ** (1 / b_) if phi > 0 else 0.0
    return {"r0": r0, "ros": r0 * (1 + phi_w + phi_s), "ir": ir, "u_ef_ft_min": u_ef}


def anderson_lb(u_ef_ft_min: float) -> float:
    """Relación largo/ancho de Anderson (1983) como la usa ELMFIRE (viento efectivo en m/s)."""
    u = u_ef_ft_min * FT_MIN_A_M_S
    return min(0.936 * math.exp(0.2566 * u) + 0.461 * math.exp(-0.1548 * u) - 0.397, 8.0)


# ── dominio, corrida y medidas ──────────────────────────────────────────────────────

def _grilla(n: int, celda: float, filas: int | None = None) -> dict:
    return {"driver": "GTiff", "height": filas or n, "width": n, "crs": CRS,
            "transform": from_origin(ORIGEN[0], ORIGEN[1], celda, celda)}


def _escribir(perfil: dict, ruta: Path, valor, dtype: str, bandas: int | None = None) -> None:
    alto, ancho = perfil["height"], perfil["width"]
    datos = np.asarray(valor, dtype="float64")
    if datos.ndim == 0:
        datos = np.full((1, alto, ancho), float(datos))
    elif datos.ndim == 1:                   # una serie: una banda uniforme por valor
        datos = np.broadcast_to(datos[:, None, None], (len(datos), alto, ancho))
    elif datos.ndim == 2:
        datos = datos[None]
    with rasterio.open(ruta, "w", **perfil, count=datos.shape[0], dtype=dtype) as dst:
        dst.write(datos.astype(dtype))


def dominio(nombre: str, *, n: int = 121, filas: int | None = None, celda: float = 30.0,
            fbfm: int = 102,
            dem=1000.0, slp=None, asp=None, cc=0, ch=0, cbh=0, cbd=0,
            ws=0.0, wd=270.0, m1=6.0, m10=8.0, m100=10.0, adj=1.0,
            ignicion: np.ndarray | None = None, radio_m: float = 45.0) -> Path:
    """Arma insumos sintéticos. `ws`… aceptan escalar, serie (una banda por hora) o
    array. Sin `slp`/`asp` explícitos se derivan del `dem` con raster_aligner. `n` son las
    columnas; `filas`, si difiere, hace el dominio rectangular."""
    insumos = RAIZ / nombre / "insumos"
    shutil.rmtree(insumos.parent, ignore_errors=True)
    insumos.mkdir(parents=True)
    perfil = _grilla(n, celda, filas)
    _escribir(perfil, insumos / "dem.tif", dem, "int16")
    if slp is None:
        _derive_slope_aspect(insumos / "dem.tif", insumos / "slp.tif", insumos / "asp.tif", celda)
    else:
        _escribir(perfil, insumos / "slp.tif", slp, "int16")
        _escribir(perfil, insumos / "asp.tif", asp if asp is not None else 0, "int16")
    for nombre_, valor in (("fbfm40", fbfm), ("cc", cc), ("ch", ch), ("cbh", cbh), ("cbd", cbd)):
        _escribir(perfil, insumos / f"{nombre_}.tif", valor, "int16")
    clima = {"ws": ws, "wd": wd, "m1": m1, "m10": m10, "m100": m100}
    bandas = max(len(v) if np.ndim(v) == 1 else 1 for v in clima.values())
    for nombre_, valor in clima.items():   # ELMFIRE exige la misma serie en todos
        if np.ndim(valor) == 0 and bandas > 1:
            valor = [valor] * bandas
        _escribir(perfil, insumos / f"{nombre_}.tif", valor, "float32")
    _escribir(perfil, insumos / "adj.tif", adj, "float32")
    if ignicion is None:
        ff, cc = np.mgrid[0:perfil["height"], 0:n]
        ignicion = np.hypot(ff - (perfil["height"] - 1) / 2, cc - (n - 1) / 2) * celda <= radio_m
    ignition_builder.build_ignition_from_mask(ignicion, insumos / "dem.tif", insumos)
    shutil.copy2(fuels_builder.FUEL_MODEL_TABLE, insumos / "fuel_models.csv")
    return insumos


def phi_anterior(insumos: Path) -> None:
    """Reescribe phi.tif como lo escribía ignition_builder antes del hallazgo 2: distancia
    L1 con signo en metros afuera, -1 adentro."""
    with rasterio.open(insumos / "phi.tif") as src:
        quemado, perfil, celda = src.read(1) < 0, src.profile, abs(src.transform.a)
    d = np.where(quemado, 0.0, np.inf)
    for _ in range(2):   # barrido L1 en las cuatro direcciones
        for i in range(1, d.shape[0]):
            d[i] = np.minimum(d[i], d[i - 1] + 1)
        for j in range(1, d.shape[1]):
            d[:, j] = np.minimum(d[:, j], d[:, j - 1] + 1)
        d = d[::-1, ::-1]
    phi = np.where(quemado, -1.0, d * celda).astype("float32")
    with rasterio.open(insumos / "phi.tif", "w", **perfil) as dst:
        dst.write(phi, 1)


def correr(insumos: Path, horas: int, *, namelist_anterior: bool = False,
           clima_sin_rellenar: bool = False, **kw) -> np.ndarray:
    """Corre ELMFIRE y devuelve el TOA (s, absoluto; ≤ 0 = no quemó)."""
    salidas = insumos.parent / "salidas"
    shutil.rmtree(salidas, ignore_errors=True)
    salidas.mkdir()
    nl = insumos / "elmfire.data"
    namelist_writer.write_namelist(insumos.resolve(), salidas.resolve(), simulation_hours=horas,
                                   output_path=nl, **kw)
    if clima_sin_rellenar:   # antes del hallazgo 5: el clima con la forma del combustible
        with rasterio.open(insumos / "dem.tif") as src:
            ancho = src.width
        for var in namelist_writer.WEATHER_RASTERS:
            with rasterio.open(insumos / f"{var}.tif") as src:
                datos, perfil = src.read()[:, :, :ancho], src.profile | {"width": ancho}
            with rasterio.open(insumos / f"{var}.tif", "w", **perfil) as dst:
                dst.write(datos)
    texto = nl.read_text()
    if namelist_anterior:   # el namelist de antes del hallazgo 1: sin &MONTE_CARLO
        texto = texto[:texto.index("\n&MONTE_CARLO")] + "\n"
    for ruta in (insumos, salidas):
        texto = texto.replace(str(ruta.resolve()), str(CONTENEDOR / ruta))
    nl.write_text(texto)
    asyncio.run(ELMFIRERunnerClient().run_simulation(SimulationRequest(
        elmfire_data_path=str(CONTENEDOR / nl), inputs_dir=str(CONTENEDOR / insumos),
        outputs_dir=str(CONTENEDOR / salidas), simulation_hours=horas)))
    toas = sorted(salidas.glob("time_of_arrival*.tif"))
    if not toas:
        raise RuntimeError(f"{insumos}: ELMFIRE no dejó time_of_arrival")
    with rasterio.open(toas[-1]) as src:
        return src.read(1).astype("float64")


def ros_rayo(toa: np.ndarray, angulo: float, celda: float, r_min: float = 150.0,
             centro: tuple[float, float] | None = None) -> float:
    """Velocidad (m/min) hacia `angulo` (0 = N, horario): pendiente de la distancia contra
    el TOA en las celdas quemadas del rayo, desde `r_min` hasta el borde del fuego."""
    n = toa.shape[0]
    f0, c0 = centro if centro else ((n - 1) / 2, (n - 1) / 2)
    a = math.radians(angulo)
    rs = np.arange(r_min, n * celda, celda / 2)
    fs = np.round(f0 - rs * math.cos(a) / celda).astype(int)
    cs = np.round(c0 + rs * math.sin(a) / celda).astype(int)
    dentro = (fs >= 1) & (fs < n - 1) & (cs >= 1) & (cs < n - 1)
    rs, fs, cs = rs[dentro], fs[dentro], cs[dentro]
    t = toa[fs, cs]
    quemado = t > 0
    if quemado.sum() < 4:
        return 0.0
    corte = np.argmin(quemado) if not quemado.all() else len(quemado)   # tramo contiguo
    rs, t = rs[:corte], t[:corte]
    if len(rs) < 4:
        return 0.0
    return float(np.polyfit(t, rs, 1)[0] * 60)


def forma(toa: np.ndarray, celda: float, radio_m: float = 45.0, r_min: float = 150.0) -> dict:
    """Rumbo de la cabeza (de la ignición al centroide de lo quemado), su velocidad sobre
    ese rayo y la relación largo/ancho del área, descontando el disco de ignición."""
    n = toa.shape[0]
    filas, cols = np.nonzero(toa > 0)
    x = (cols - (n - 1) / 2) * celda
    y = ((n - 1) / 2 - filas) * celda
    cabeza = math.degrees(math.atan2(x.mean(), y.mean())) % 360 if len(x) else 0.0
    a = math.radians(cabeza)
    largo = np.ptp(x * math.sin(a) + y * math.cos(a)) + celda - 2 * radio_m if len(x) else 0
    ancho = np.ptp(x * math.cos(a) - y * math.sin(a)) + celda - 2 * radio_m if len(x) else 0
    return {"cabeza": round(cabeza, 1), "ros_cabeza": ros_rayo(toa, cabeza, celda, r_min),
            "lw": float(largo / ancho) if ancho > 0 else float("inf"),
            "desplazamiento_m": float(math.hypot(x.mean(), y.mean())) if len(x) else 0.0,
            "area_ha": float((toa > 0).sum() * celda * celda / 1e4)}


def vs_max(insumos: Path) -> float:
    """La velocidad de cabeza que ELMFIRE calculó (ráster vs, ft/min), en m/min."""
    with rasterio.open(sorted((insumos.parent / "salidas").glob("vs_*.tif"))[-1]) as src:
        return float(src.read(1).max() * 0.3048)


def dif_angular(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


# ── registro ─────────────────────────────────────────────────────────────────────────

RESULTADOS: list[dict] = []


def chequear(prueba: str, medida: str, esperado, obtenido, ok: bool, nota: str = "") -> None:
    fila = {"prueba": prueba, "medida": medida, "esperado": esperado, "obtenido": obtenido,
            "ok": bool(ok), "nota": nota}
    RESULTADOS.append(fila)
    marca = "OK  " if ok else "FALLA"
    print(f"  [{marca}] {medida}: esperado {esperado}, obtenido {obtenido} {nota}", flush=True)


def _r(x: float, d: int = 2) -> float:
    return round(float(x), d)


def dentro(obtenido: float, esperado: float, tol: float) -> bool:
    return abs(obtenido - esperado) <= tol * abs(esperado)


# ── pruebas ──────────────────────────────────────────────────────────────────────────

FM = modelos()
HUMEDAD: dict[str, Any] = {"m1": 6.0, "m10": 8.0, "m100": 10.0}
VIVA = {"lh": namelist_writer.DEFAULT_LH_MOISTURE_PCT,
        "lw": namelist_writer.DEFAULT_LW_MOISTURE_PCT}


def _ros_ref(fbfm: int, u20: float = 0.0, **kw) -> dict:
    h = {"m1": HUMEDAD["m1"], "m10": HUMEDAD["m10"], "m100": HUMEDAD["m100"]} | VIVA
    h |= {k: v for k, v in kw.items() if k in h}
    extra = {k: v for k, v in kw.items() if k not in h}
    return rothermel(FM[fbfm], h["m1"], h["m10"], h["m100"], h["lh"], h["lw"], u20, **extra)


def prueba_simetria() -> None:
    """Plano, sin viento, GR2 uniforme: círculo centrado, a la velocidad de Rothermel."""
    ref = _ros_ref(102)["ros"] * 0.3048
    toa = correr(dominio("simetria", n=161, celda=10.0, **HUMEDAD), 4)
    ros = np.array([ros_rayo(toa, a, 10.0, r_min=60.0) for a in np.arange(0, 360, 45.0)])
    chequear("simetria", "máx/mín de la velocidad en 8 rumbos", "≤ 1,15",
             _r(ros.max() / ros.min(), 3), ros.max() / ros.min() <= 1.15)
    chequear("simetria", "velocidad media (m/min) contra Rothermel", _r(ref, 3),
             _r(ros.mean(), 3), dentro(ros.mean(), ref, 0.10))
    fo = forma(toa, 10.0)
    chequear("simetria", "centroide contra la ignición (m)", "≤ 10", _r(fo["desplazamiento_m"]),
             fo["desplazamiento_m"] <= 10)


def prueba_nivel() -> None:
    """El campo phi inicial. Con la distancia en metros que escribía ignition_builder el
    frente avanzaba a la mitad de la velocidad que ELMFIRE calcula; con ±1 (la convención
    de los tutoriales de ELMFIRE) avanza a esa velocidad."""
    for anterior in (True, False):
        etiqueta = "phi en metros (anterior)" if anterior else "phi ±1"
        for ws in (0.0, 10.0):
            insumos = dominio(f"nivel-{'metros' if anterior else 'uno'}-{ws:.0f}", n=161,
                              celda=10.0 if ws == 0 else 30.0, ws=ws, wd=270.0, **HUMEDAD)
            if anterior:
                phi_anterior(insumos)
            celda = 10.0 if ws == 0 else 30.0
            toa = correr(insumos, 4 if ws == 0 else 1)
            v = ros_rayo(toa, 90.0, celda, r_min=60.0 if ws == 0 else 150.0)
            calc = vs_max(insumos)
            chequear("nivel", f"{etiqueta}, {ws:.0f} mph: avance del frente / velocidad "
                     "calculada por ELMFIRE", "0,9–1,1", _r(v / calc, 3),
                     0.9 <= v / calc <= 1.1, f"({_r(v)} contra {_r(calc)} m/min)")


def prueba_viento() -> None:
    """Viento uniforme desde cuatro rumbos: la cabeza va a wd + 180, a la velocidad y la
    relación largo/ancho de Rothermel/Anderson. Después, la ruta del benchmark: wd desde
    u/v con weather_builder.derive_wind."""
    for wd in (270.0, 0.0, 90.0, 180.0):
        toa = correr(dominio(f"viento-{wd:03.0f}", ws=10.0, wd=wd, **HUMEDAD), 1)
        fo = forma(toa, 30.0)
        chequear("viento", f"wd={wd:.0f}: rumbo de la cabeza", (wd + 180) % 360, fo["cabeza"],
                 dif_angular(fo["cabeza"], wd + 180) <= 5)
    lws = []
    for ws in (5.0, 10.0, 20.0):
        ref = _ros_ref(102, ws)
        toa = correr(dominio(f"viento-lw-{ws:.0f}", n=201, ws=ws, wd=270.0, **HUMEDAD), 1)
        fo = forma(toa, 30.0)
        chequear("viento", f"{ws:.0f} mph: velocidad de cabeza (m/min) contra Rothermel",
                 _r(ref["ros"] * 0.3048), _r(fo["ros_cabeza"]),
                 dentro(fo["ros_cabeza"], ref["ros"] * 0.3048, 0.10))
        esperado = anderson_lb(ref["u_ef_ft_min"])
        lws.append(fo["lw"])
        chequear("viento", f"{ws:.0f} mph: largo/ancho contra Anderson", _r(esperado),
                 _r(fo["lw"]), dentro(fo["lw"], esperado, 0.15))
    chequear("viento", "largo/ancho crece con el viento", "monótona", [_r(x) for x in lws],
             all(a < b for a, b in zip(lws, lws[1:])))
    # Ruta del benchmark: u10 = +5 m/s (del oeste) en una grilla EPSG:4326 → derive_wind.
    insumos = dominio("viento-uv", **HUMEDAD)
    with tempfile.TemporaryDirectory() as tmp:
        with rasterio.open(insumos / "dem.tif") as ref_:
            from rasterio.warp import transform_bounds
            w, s_, e, n_ = transform_bounds(ref_.crs, "EPSG:4326", *ref_.bounds)
        perfil = {"driver": "GTiff", "height": 8, "width": 8, "crs": "EPSG:4326",
                  "transform": from_origin(w - 0.5, n_ + 0.5, (e - w + 1) / 8, (n_ - s_ + 1) / 8)}
        for comp, valor in (("u10", 5.0), ("v10", 0.0)):
            _escribir(perfil, Path(tmp) / f"{comp}.tif", valor, "float32")
        (insumos / "ws.tif").unlink()
        (insumos / "wd.tif").unlink()
        weather_builder.derive_wind(Path(tmp) / "u10.tif", Path(tmp) / "v10.tif",
                                    insumos / "dem.tif", insumos)
    with rasterio.open(insumos / "wd.tif") as src:
        wd_uv = float(np.median(src.read(1)))
    fo = forma(correr(insumos, 1), 30.0)
    chequear("viento", "u10 = +5 m/s: wd derivado", 270.0, _r(wd_uv), dif_angular(wd_uv, 270) < 1)
    chequear("viento", "u10 = +5 m/s: la cabeza va al este", 90.0, fo["cabeza"],
             dif_angular(fo["cabeza"], 90) <= 5)


def prueba_pendiente() -> None:
    """Ladera plana inclinada, sin viento, en cuatro orientaciones. El dem sube hacia
    `sube`; slp/asp salen de raster_aligner. El fuego tiene que subir a R0 (1 + phi_s)."""
    n, celda, grados = 121, 30.0, 20.0
    filas, cols = np.mgrid[0:n, 0:n]
    x = (cols - (n - 1) / 2) * celda
    y = ((n - 1) / 2 - filas) * celda
    ref = _ros_ref(102, pendiente_grados=grados)
    for sube in (0.0, 90.0, 180.0, 270.0):
        a = math.radians(sube)
        dem = 1500 + math.tan(math.radians(grados)) * (x * math.sin(a) + y * math.cos(a))
        insumos = dominio(f"pendiente-{sube:03.0f}", dem=dem, **HUMEDAD)
        with rasterio.open(insumos / "slp.tif") as s1, rasterio.open(insumos / "asp.tif") as s2:
            slp, asp = float(np.median(s1.read(1))), float(np.median(s2.read(1)))
        fo = forma(correr(insumos, 2), celda)
        chequear("pendiente", f"sube hacia {sube:.0f}: slp (grados) / asp (mira a)",
                 f"{grados:.0f} / {(sube + 180) % 360:.0f}", f"{slp:.0f} / {asp:.0f}",
                 abs(slp - grados) <= 1 and dif_angular(asp, sube + 180) <= 1)
        chequear("pendiente", f"sube hacia {sube:.0f}: rumbo de la cabeza", sube, fo["cabeza"],
                 dif_angular(fo["cabeza"], sube) <= 5)
        # La velocidad sobre la ladera: ELMFIRE avanza en planta ros · cos(pendiente).
        v_ladera = fo["ros_cabeza"] / math.cos(math.radians(grados))
        chequear("pendiente", f"sube hacia {sube:.0f}: velocidad ladera arriba (m/min)",
                 _r(ref["ros"] * 0.3048), _r(v_ladera), dentro(v_ladera, ref["ros"] * 0.3048, 0.10))


def prueba_humedad() -> None:
    """Velocidad sin viento monótona decreciente en m1 y nula sobre la extinción (GR2: 15 %);
    LW frena el arbustal (SH4) y LH el pastizal dinámico (GR2). Humedades en %: si ELMFIRE
    las leyera como fracción, la velocidad no coincidiría con Rothermel."""
    ros = []
    for m in (3.0, 6.0, 10.0, 13.0):
        toa = correr(dominio(f"humedad-m1-{m:.0f}", ws=10.0, m1=m, m10=m + 2, m100=m + 4), 1)
        v = forma(toa, 30.0)["ros_cabeza"]
        ref = _ros_ref(102, 10.0, m1=m, m10=m + 2, m100=m + 4)["ros"] * 0.3048
        ros.append(v)
        chequear("humedad", f"m1 = {m:.0f} %: velocidad de cabeza (m/min) contra Rothermel",
                 _r(ref), _r(v), dentro(v, ref, 0.10))
    chequear("humedad", "velocidad decrece con la humedad muerta", "monótona",
             [_r(x) for x in ros], all(a > b for a, b in zip(ros, ros[1:])))
    toa = correr(dominio("humedad-m1-16", ws=10.0, m1=16.0, m10=18.0, m100=20.0), 1)
    area = float((toa > 0).sum() * 900 / 1e4)
    chequear("humedad", "m1 = 16 % (> Mx 15 %): área quemada (ha)", 0.0, _r(area), area < 0.5)
    for fbfm, clave, valores in ((144, "lw", (60.0, 110.0, 200.0)),
                                 (122, "lh", (30.0, 60.0, 90.0))):
        vs = []
        for val in valores:
            toa = correr(dominio(f"humedad-{clave}-{val:.0f}", fbfm=fbfm, ws=10.0, **HUMEDAD), 2,
                         **{f"{clave}_moisture_pct": val})
            v = forma(toa, 30.0)["ros_cabeza"]
            ref = _ros_ref(fbfm, 10.0, **{clave: val})["ros"] * 0.3048
            vs.append(v)
            chequear("humedad", f"{FM[fbfm]['nombre']} {clave.upper()} = {val:.0f} %: "
                     "velocidad (m/min) contra Rothermel", _r(ref), _r(v), dentro(v, ref, 0.10))
        chequear("humedad", f"{FM[fbfm]['nombre']}: velocidad decrece con {clave.upper()}",
                 "monótona", [_r(x) for x in vs], all(a >= b for a, b in zip(vs, vs[1:])))


def prueba_combustible() -> None:
    """Velocidad de cabeza de varios modelos con 10 mph a 20 pies, contra Rothermel."""
    for fbfm in (102, 122, 144, 165, 183, 188):
        ref = _ros_ref(fbfm, 10.0)["ros"] * 0.3048
        celda = 30.0 if ref > 3 else 10.0          # que la cabeza recorra ~40 celdas
        horas = max(1, math.ceil(40 * celda / ref / 60))
        toa = correr(dominio(f"combustible-{fbfm}", fbfm=fbfm, celda=celda, n=201, ws=10.0,
                             **HUMEDAD), horas)
        v = forma(toa, celda, r_min=5 * celda)["ros_cabeza"]
        chequear("combustible", f"{FM[fbfm]['nombre']}: velocidad de cabeza (m/min)", _r(ref),
                 _r(v), dentro(v, ref, 0.10), f"({horas} h, celda {celda:.0f} m)")


def prueba_dosel() -> None:
    """WAF bajo dosel (Albini y Baughman) y activación de la copa."""
    waf = waf_con_dosel(60, 20)
    ref = _ros_ref(165, 20.0, waf=waf)["ros"] * 0.3048
    toa = correr(dominio("dosel-waf", fbfm=165, celda=10.0, n=161, ws=20.0, cc=60, ch=200,
                         cbh=100, cbd=5, **HUMEDAD), 2)
    v = forma(toa, 10.0, r_min=60.0)["ros_cabeza"]
    chequear("dosel", f"TU5 bajo CC 60 %/CH 20 m (WAF {waf:.3f}): velocidad (m/min)",
             _r(ref), _r(v), dentro(v, ref, 0.10))
    # CH = 0 con CC ≥ 15 %: ELMFIRE deja WAF = 0 (sin viento).
    toa = correr(dominio("dosel-ch0", fbfm=165, celda=10.0, n=161, ws=20.0, cc=60, ch=0,
                         **HUMEDAD), 2)
    fo = forma(toa, 10.0, r_min=60.0)
    r0 = _ros_ref(165)["ros"] * 0.3048
    chequear("dosel", "CC 60 %, CH 0: la cabeza avanza como sin viento (WAF 0)", _r(r0),
             _r(fo["ros_cabeza"]), dentro(fo["ros_cabeza"], r0, 0.15),
             "(incoherencia de insumos que ELMFIRE resuelve sin viento)")
    # Copa: superficie intensa (SH7, seco, 25 mph) bajo un dosel bajo y denso.
    base = {"fbfm": 147, "celda": 30.0, "n": 201, "ws": 25.0, "cc": 80, "ch": 150, "cbh": 10,
            "cbd": 20, "m1": 3.0, "m10": 4.0, "m100": 5.0}
    toa1 = correr(dominio("dosel-copa", **base), 1, crown_fire_model=1)
    toa0 = correr(dominio("dosel-sin-copa", **base), 1, crown_fire_model=0)
    a1, a0 = (toa1 > 0).sum(), (toa0 > 0).sum()
    chequear("dosel", "CBH 1 m, SH7 seco a 25 mph: área con copa / sin copa", "> 1,5",
             _r(a1 / max(a0, 1)), a1 > 1.5 * a0)


def prueba_tiempo() -> None:
    """El clima cambia entre bandas. Hora 0 sin viento, desde la hora 1 viento de 20 mph
    del oeste: la cabeza tiene que ir al este. Con el namelist anterior (sin
    NUM_METEOROLOGY_TIMES) ELMFIRE se queda con la banda 0 y el fuego es un círculo."""
    serie = [0.0] + [20.0] * 4
    for anterior in (True, False):
        toa = correr(dominio(f"tiempo-bandas-{'anterior' if anterior else 'nuevo'}", n=201,
                             ws=serie, wd=270.0, **HUMEDAD), 2, namelist_anterior=anterior)
        fo = forma(toa, 30.0)
        chequear("tiempo", f"{'namelist anterior' if anterior else 'con NUM_METEOROLOGY_TIMES'}"
                 ": desplazamiento al este con viento desde la hora 1 (m)", "> 500",
                 _r(fo["desplazamiento_m"], 0), fo["desplazamiento_m"] > 500 and
                 dif_angular(fo["cabeza"], 90) <= 5, f"(cabeza {fo['cabeza']:.0f}°)")
    # Banda n = clima a n × DT absoluto: con TSTART = 2 h y viento sólo desde la banda 2,
    # el fuego tiene viento desde el arranque y avanza como con viento constante.
    serie = [0.0, 0.0, 10.0, 10.0, 10.0, 10.0]
    toa = correr(dominio("tiempo-tstart", ws=serie, wd=270.0, **HUMEDAD), 1,
                 simulation_tstart_s=7200.0)
    t = toa[toa > 0]
    chequear("tiempo", "TSTART = 2 h: TOA absoluto (mínimo ≥ 7200 s)", "≥ 7200",
             _r(t.min(), 0), t.min() >= 7200)
    fo = forma(np.where(toa > 0, toa - 7200, 0), 30.0)
    ref = _ros_ref(102, 10.0)["ros"] * 0.3048
    chequear("tiempo", "TSTART = 2 h, viento desde la banda 2: velocidad de cabeza", _r(ref),
             _r(fo["ros_cabeza"]), dentro(fo["ros_cabeza"], ref, 0.10))
    # Interpolación de wd entre bandas: 170° ↔ 190° (viento del sur). La cabeza va al norte.
    for transformado in (False, True):
        serie_wd = np.array([170.0, 190.0] * 3)
        if transformado:
            serie_wd = weather_builder.wd_for_elmfire(serie_wd[:, None, None])[:, 0, 0]
        toa = correr(dominio(f"tiempo-wd-sur-{'transformado' if transformado else 'crudo'}",
                             ws=15.0, wd=serie_wd, **HUMEDAD), 2)
        fo = forma(toa, 30.0)
        chequear("tiempo", f"wd 170°/190° {'con wd_for_elmfire' if transformado else 'crudo'}"
                 ": rumbo de la cabeza", 0.0, fo["cabeza"],
                 dif_angular(fo["cabeza"], 0) <= 10 and fo["desplazamiento_m"] > 200,
                 f"(desplazamiento {fo['desplazamiento_m']:.0f} m)")
    # Cadena: 2 h de una vez contra 1 h + 1 h sembrando con lo quemado.
    toa = correr(dominio("tiempo-cadena-2h", ws=10.0, wd=270.0, **HUMEDAD), 2)
    with rasterio.open(RAIZ / "tiempo-cadena-2h" / "insumos" / "phi.tif") as src:
        a2 = int(((src.read(1) < 0) | (toa > 0)).sum())
    insumos = dominio("tiempo-cadena-1h", ws=10.0, wd=270.0, **HUMEDAD)
    t1 = correr(insumos, 1)
    with rasterio.open(insumos / "phi.tif") as src:
        semilla = src.read(1) < 0
    insumos2 = dominio("tiempo-cadena-1h+1h", ws=10.0, wd=270.0,
                       ignicion=semilla | (t1 > 0), **HUMEDAD)
    t2 = correr(insumos2, 1)
    with rasterio.open(insumos2 / "phi.tif") as src:
        a11 = int(((src.read(1) < 0) | (t2 > 0)).sum())
    chequear("tiempo", "cadena 1 h + 1 h contra 2 h: cociente de áreas", "0,9–1,1",
             _r(a11 / a2, 3), 0.9 <= a11 / a2 <= 1.1)


def prueba_georreferencia() -> None:
    """Un punto con lon/lat conocidos cae en su celda, y el TOA sale en la grilla del dem."""
    from pyproj import Transformer
    celda = 30.0
    fila, col = 40, 80
    x = ORIGEN[0] + (col + 0.5) * celda
    y = ORIGEN[1] - (fila + 0.5) * celda
    lon, lat = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True).transform(x, y)
    insumos = dominio("georreferencia", **HUMEDAD)
    ignition_builder.build_ignition_layer([(lon, lat)], insumos / "dem.tif", insumos,
                                          buffer_m=45.0)
    with rasterio.open(insumos / "phi.tif") as src:
        semilla = src.read(1) < 0
    ff, cc = np.nonzero(semilla)
    chequear("georreferencia", "centro de la semilla (fila, col)", (fila, col),
             (_r(ff.mean(), 1), _r(cc.mean(), 1)),
             abs(ff.mean() - fila) <= 0.5 and abs(cc.mean() - col) <= 0.5)
    toa = correr(insumos, 2)
    salida = sorted((insumos.parent / "salidas").glob("time_of_arrival*.tif"))[-1]
    with rasterio.open(salida) as s, rasterio.open(insumos / "dem.tif") as d:
        misma = s.transform == d.transform and s.shape == d.shape and s.crs == d.crs
    chequear("georreferencia", "TOA en la grilla del dem", True, misma, misma)
    filas, cols = np.nonzero((toa > 0) | semilla)
    desvio = math.hypot(filas.mean() - fila, cols.mean() - col)
    chequear("georreferencia", "centroide del fuego sin viento contra la ignición (celdas)",
             "≤ 1", _r(desvio), desvio <= 1)


def prueba_grilla() -> None:
    """Grilla de clima más alta que ancha. MAP_FINE_TO_COARSE (elmfire_subs.f90) acota la
    fila del clima con NCOLS en vez de NROWS: las filas con IY > NCOLS (contadas desde el
    sur) leerían el clima de la fila NCOLS. Dominio de 81 columnas × 161 filas; viento de
    20 mph del oeste sólo en una mitad, calma en la otra. La franja norte (IY 82…161) es la
    que el acotamiento mandaría a la fila 81, que ya es la calma del sur.
    write_namelist rellena el clima al este hasta NCOLS = NROWS (hallazgo 5, corregido);
    `sin-relleno` lo recorta después para reproducir el bug."""
    n, filas, celda, col = 81, 161, 30.0, 20
    franja = filas - n                          # filas (desde arriba) con IY > NCOLS
    norte = np.zeros((filas, n))
    norte[:franja] = 20.0
    ff, cc = np.mgrid[0:filas, 0:n]
    casos = (("control-sur", 20.0 - norte, franja + n // 2, False),
             ("franja-norte-sin-relleno", norte, franja // 2, True),
             ("franja-norte", norte, franja // 2, False))
    for nombre, ws, fila, sin_relleno in casos:
        insumos = dominio(f"grilla-{nombre}", n=n, filas=filas, ws=ws, wd=270.0,
                          ignicion=np.hypot(ff - fila, cc - col) * celda <= 45.0, **HUMEDAD)
        toa = correr(insumos, 2, clima_sin_rellenar=sin_relleno)
        with rasterio.open(insumos / "ws.tif") as src:
            forma_clima = f"clima {src.width}×{src.height}"
        quemado_f, quemado_c = np.nonzero(toa > 0)
        este = float((quemado_c.mean() - col) * celda) if len(quemado_c) else 0.0
        sur = float((quemado_f.mean() - fila) * celda) if len(quemado_f) else 0.0
        esperado, ok = ("< 100 (bug reproducido)", este < 100) if sin_relleno else ("> 500",
                                                                                   este > 500)
        chequear("grilla", f"{nombre}: desplazamiento al este con viento del oeste (m)",
                 esperado, _r(este, 0), ok,
                 f"(norte-sur {-sur:.0f} m, IY de la ignición {filas - fila}, {forma_clima}, "
                 f"{len(quemado_c)} celdas)")


def prueba_supresion() -> None:
    """&SUPPRESSION (ataque ampliado, plantilla del proveedor): viento del oeste en GR2, 3 h.
    Con contención 0 %/día el quemado es el mismo que sin supresión (el grupo se lee y no
    frena nada; el TOA se corre hasta un paso porque el ataque ampliado llama a UNTAG_CELLS
    cada DT_EXTENDED_ATTACK); con contención, menos área, la cola y los flancos frenados
    primero (los sectores más lentos) y la cabeza casi intacta."""
    kw = {"ws": 5.0, "wd": 270.0, **HUMEDAD}
    sin = correr(dominio("supresion-sin", n=201, **kw), 3)
    cero = correr(dominio("supresion-cero", n=201, **kw), 3,
                  suppression={"MAX_CONTAINMENT_PER_DAY": 0.0})
    mismo = np.array_equal(sin > 0, cero > 0)
    corrimiento = float(np.abs(sin - cero)[(sin > 0) & (cero > 0)].max())
    chequear("supresion", "contención 0 %/día: mismo quemado, TOA corrido < 300 s",
             "mismo / < 300", f"{'mismo' if mismo else 'distinto'} / {corrimiento:.0f}",
             mismo and corrimiento < 300)
    fo_sin = forma(sin, 30.0)
    cola_sin = ros_rayo(sin, 270.0, 30.0, r_min=60.0)
    for nombre, cambios in (("proveedor", {}), ("fuerte", {"MAX_CONTAINMENT_PER_DAY": 480.0})):
        con = correr(dominio(f"supresion-{nombre}", n=201, **kw), 3, suppression=cambios)
        fo = forma(con, 30.0)
        chequear("supresion", f"{nombre}: área (ha) menor que sin supresión",
                 f"< {_r(fo_sin['area_ha'], 0)}", _r(fo["area_ha"], 0),
                 fo["area_ha"] < fo_sin["area_ha"])
        chequear("supresion", f"{nombre}: cabeza (m/min) casi intacta", _r(fo_sin["ros_cabeza"]),
                 _r(fo["ros_cabeza"]), dentro(fo["ros_cabeza"], fo_sin["ros_cabeza"], 0.15))
        cola = ros_rayo(con, 270.0, 30.0, r_min=60.0)
        chequear("supresion", f"{nombre}: la cola (m/min) no avanza más que sin supresión",
                 f"<= {_r(cola_sin)}", _r(cola), cola <= cola_sin + 1e-6)


PRUEBAS: dict[str, Callable[[], None]] = {
    "simetria": prueba_simetria, "nivel": prueba_nivel, "viento": prueba_viento,
    "pendiente": prueba_pendiente,
    "humedad": prueba_humedad, "combustible": prueba_combustible, "dosel": prueba_dosel,
    "tiempo": prueba_tiempo, "georreferencia": prueba_georreferencia, "grilla": prueba_grilla,
    "supresion": prueba_supresion,
}


def main() -> None:
    nombres = sys.argv[1:] or list(PRUEBAS)
    destino = RAIZ / "resultados.json"
    previos = json.loads(destino.read_text()) if destino.exists() else []
    previos = [r for r in previos if r["prueba"] not in nombres]
    for nombre in nombres:
        print(f"== {nombre}", flush=True)
        PRUEBAS[nombre]()
    RAIZ.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(previos + RESULTADOS, indent=2, ensure_ascii=False))
    fallas = [r for r in RESULTADOS if not r["ok"]]
    print(f"\n{len(RESULTADOS) - len(fallas)} de {len(RESULTADOS)} chequeos OK")
    for r in fallas:
        print(f"  FALLA {r['prueba']}: {r['medida']} (esperado {r['esperado']}, "
              f"obtenido {r['obtenido']})")


if __name__ == "__main__":
    main()
