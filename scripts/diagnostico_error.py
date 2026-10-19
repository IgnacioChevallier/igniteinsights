"""Diagnóstico de error de modelo-v0 (tarea F), SIN correr ELMFIRE.

Todo sale del TOA y las referencias ya guardadas en el almacén del benchmark. Sólo incendios de
calibración (benchmarks/particion.json): una receta `lw-100-001` sobre `calibracion-v6` y P-24
(`lw-100-obs-001` sobre `pronostico-v6`). Nunca se abre un caso de prueba.

    uv run python scripts/diagnostico_error.py

Escribe las tablas en docs/resultados/diagnostico-e2e/datos/ (F1 … F6).
Las funciones puras (FSS, distancia de perímetro, eje, ADJ offline, ROS) se prueban en
tests/test_diagnostico_error.py con rásters sintéticos.
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import rasterio.features
import shapely
from pyproj import Transformer

from app.ensemble.sources import _read_gefs_fields  # misma lectura que el ensamble
from app.validation import almacen, cadena, pronostico
from app.validation import definiciones as d
from app.validation import puntuacion as p

SALIDA = Path("docs/resultados/diagnostico-e2e/datos")
RECETA, RECETA_P24 = "lw-100-001", "lw-100-obs-001"
ESCALAS_CELDAS = (1, 3, 7, 15, 33, 67)   # 30 m … ~2 km con celdas de 30 m
PIXEL_VIIRS_M = 375.0
UTC_ART_H = -3
ADJ_LIM = (0.25, 4.0)   # DIA-1 §3.1
GRUPOS = {9: "NB", 10: "GR", 12: "GS", 14: "SH", 16: "TU", 18: "TL"}   # código // 10


# ── funciones puras ───────────────────────────────────────────────────────────────────────

def suma_ventana(a: np.ndarray, n: int) -> np.ndarray:
    """Suma en ventanas n×n centradas (ceros fuera de la grilla), con imagen integral."""
    r = n // 2
    c = np.pad(a.astype("float64"), ((r + 1, r), (r + 1, r))).cumsum(0).cumsum(1)
    return c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]


def recorte(*mascaras: np.ndarray, margen: int = 70) -> tuple[slice, slice]:
    """Caja de la unión de las máscaras más `margen` celdas (el dominio del FSS)."""
    u = np.any(mascaras, axis=0)
    f, c = np.nonzero(u)
    h, w = u.shape
    return (slice(max(f.min() - margen, 0), min(f.max() + margen + 1, h)),
            slice(max(c.min() - margen, 0), min(c.max() + margen + 1, w)))


def fss(pred: np.ndarray, ref: np.ndarray, valido: np.ndarray, n: int) -> float | None:
    """Fractions Skill Score (Roberts y Lean 2008) con ventana de n×n celdas. Las celdas no
    válidas (exclusión, semilla) no cuentan: las fracciones se normalizan por las válidas."""
    v = suma_ventana(valido, n)
    ok = valido & (v > 0)
    pf = np.where(ok, suma_ventana(pred & valido, n) / np.maximum(v, 1), 0)
    of = np.where(ok, suma_ventana(ref & valido, n) / np.maximum(v, 1), 0)
    den = (pf ** 2).sum() + (of ** 2).sum()
    return float(1 - ((pf - of) ** 2).sum() / den) if den else None


def fss_util(ref: np.ndarray, valido: np.ndarray) -> float:
    """FSS de un pronóstico aleatorio con la misma fracción: 0,5 + f/2 (umbral de «útil»)."""
    return 0.5 + 0.5 * ref[valido].mean()


def _borde(region: np.ndarray, descartar: np.ndarray) -> np.ndarray:
    """Celdas de `region` con algún vecino (4) fuera, salvo las pegadas a `descartar`."""
    pad = np.pad(region, 1, mode="edge")
    interior = pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:]
    return region & ~interior & (suma_ventana(descartar, 3) == 0)


def _dist_a(origen: np.ndarray, destino: np.ndarray) -> np.ndarray:
    """Distancia (celdas) de cada punto de `origen` (N×2) al más cercano de `destino`."""
    arbol = shapely.STRtree(shapely.points(destino))
    _, dist = arbol.query_nearest(shapely.points(origen), return_distance=True,
                                  all_matches=False)
    return dist


def distancia_perimetro(a: np.ndarray, b: np.ndarray, descartar: np.ndarray,
                        celda_m: float) -> dict:
    """Distancia entre los bordes de dos regiones: Hausdorff 95 % (el mayor de los dos
    percentiles 95 dirigidos), distancia media simétrica (ASSD) y la mediana."""
    ba = np.argwhere(_borde(a, descartar))
    bb = np.argwhere(_borde(b, descartar))
    if len(ba) == 0 or len(bb) == 0:
        return {"hd95_m": None, "assd_m": None, "mediana_m": None}
    dab, dba = _dist_a(ba, bb) * celda_m, _dist_a(bb, ba) * celda_m
    todo = np.concatenate([dab, dba])
    return {"hd95_m": float(max(np.percentile(dab, 95), np.percentile(dba, 95))),
            "assd_m": float(todo.mean()), "mediana_m": float(np.median(todo))}


def rumbo(dx: float, dy: float) -> float:
    """Grados desde el norte en sentido horario."""
    return float(np.degrees(np.arctan2(dx, dy)) % 360)


def eje(semilla: np.ndarray, crecimiento: np.ndarray, celda_m: float) -> tuple[float, float]:
    """(rumbo, distancia_m) del centroide de la semilla al del crecimiento (norte arriba)."""
    fs, cs = np.nonzero(semilla)
    fc, cc = np.nonzero(crecimiento)
    dx, dy = (cc.mean() - cs.mean()) * celda_m, (fs.mean() - fc.mean()) * celda_m
    return rumbo(dx, dy), float(math.hypot(dx, dy))


def dif_angulo(a: float, b: float) -> float:
    return (a - b + 180) % 360 - 180


def adj_k(a_ini: float, a_fin_sim: float, a_fin_obs: float) -> tuple[float, bool]:
    """ADJ_k = clamp(r_obs / r_sim, 1/4, 4) con r = √(A_fin/π) − √(A_ini/π) (DIA-1 §3.1).
    Devuelve (ADJ, saturado). Con r_sim ≤ 0 el cociente se dispara: tope."""
    r_obs = max(math.sqrt(a_fin_obs) - math.sqrt(a_ini), 0.0)
    r_sim = math.sqrt(a_fin_sim) - math.sqrt(a_ini)   # el π se cancela en el cociente
    crudo = r_obs / r_sim if r_sim > 0 else math.inf
    adj = min(max(crudo, ADJ_LIM[0]), ADJ_LIM[1])
    return adj, not ADJ_LIM[0] < crudo < ADJ_LIM[1]


def crecimiento_con_adj(a_ini: float, g_pred: float, adj: float) -> float:
    """Crecimiento predicho si el radio equivalente del crecimiento escala ~ADJ (la velocidad
    es lineal en ADJ): √(A_ini+G') = √A_ini + ADJ·(√(A_ini+G) − √A_ini)."""
    r = math.sqrt(a_ini + g_pred) - math.sqrt(a_ini)
    return (math.sqrt(a_ini) + adj * r) ** 2 - a_ini


def correlacion(x: list[float], y: list[float]) -> dict:
    """Pearson, Spearman, pendiente y persistencia de signo de pares (x_{k−1}, x_k)."""
    if len(x) < 3:
        return {"n": len(x), "pearson": None, "spearman": None, "pendiente": None,
                "mismo_signo": None}
    a, b = np.array(x), np.array(y)
    rk = lambda v: np.argsort(np.argsort(v)).astype(float)  # noqa: E731
    return {"n": len(x), "pearson": float(np.corrcoef(a, b)[0, 1]),
            "spearman": float(np.corrcoef(rk(a), rk(b))[0, 1]),
            "pendiente": float(np.polyfit(a, b, 1)[0]),
            "mismo_signo": float((np.sign(a) == np.sign(b)).mean())}


def ros_empirica(prev_xy: np.ndarray, nuevos_xy: np.ndarray, dt_h: np.ndarray,
                 minimo_m: float = PIXEL_VIIRS_M / 2, maximo_m: float = 5000.0) -> pd.DataFrame:
    """Para cada detección nueva: distancia al centro de detección previa más cercano y ROS
    d/Δt (m/min). Menos de medio píxel: el mismo píxel re-detectado (no es celda nueva); más
    de `maximo_m`: salto o otro foco. Devuelve sólo las intermedias, con su índice original."""
    dist = _dist_a(nuevos_xy, prev_xy)
    sel = (dist >= minimo_m) & (dist <= maximo_m) & (dt_h > 0)
    return pd.DataFrame({"i": np.nonzero(sel)[0], "d_m": dist[sel],
                         "ros_obs_m_min": dist[sel] / (dt_h[sel] * 60)})


# ── carga de casos ────────────────────────────────────────────────────────────────────────

def _manifiesto(caso_id: str, receta: str) -> dict:
    m = d.cargar_manifiesto(caso_id, receta)
    if m is None:
        raise FileNotFoundError(f"{caso_id}/{receta} no corrió")
    return m


def particion() -> dict:
    return json.loads(Path("benchmarks/particion.json").read_text())


def casos_calibracion() -> list[str]:
    cal = particion()["calibracion"]
    return cal["gfs"] + cal["era5"]


def cargar(caso_id: str) -> dict:
    """Rásters de un caso de calibración y la línea de tiempo cosida de la receta vigente."""
    if caso_id not in casos_calibracion():
        raise ValueError(f"{caso_id} no es de calibración")
    caso = d.Caso.cargar(caso_id)
    rec = d.Receta.cargar(RECETA)
    man = _manifiesto(caso_id, RECETA)
    paq = caso.paquete()
    com = paq["comunes"]
    grilla = p.Grilla(almacen.abrir(com["dem.tif"]))
    t0 = caso.ventanas[0].inicio
    lineas, det = [], np.full(grilla.shape, np.nan)
    for v, w, arch in zip(caso.ventanas, man["ventanas"], paq["ventanas"]):
        off = (v.inicio - t0).total_seconds() / 3600
        semilla = cadena._leer(w["insumos"]["phi.tif"]) < 0
        lineas.append((off, p.horas_relativas(cadena._leer(cadena._toa(w["salidas"])),
                                              v.tstart_s), semilla))
        h = cadena._leer(arch["ref_firms_horas.tif"])
        det = np.fmin(det, np.where(h >= 0, off + h, np.nan))
    semilla0 = lineas[0][2]
    mapa = f"fbfm40_{rec.combustible['fuente']}{rec.anio_combustible(caso)}.tif"
    return {
        "id": caso_id, "incendio": caso.incendio, "caso": caso, "grilla": grilla, "t0": t0,
        "limite": caso_id in particion()["limites"],
        "horizonte_h": (caso.ventanas[-1].fin - t0).total_seconds() / 3600,
        "cosido": p.coser(lineas), "semilla": semilla0, "det": det,
        "cicatriz": cadena._leer(com["cicatriz.tif"]).astype(bool),
        "excluido": cadena._leer(com["excluido.tif"]).astype(bool),
        "fuel": cadena._leer(com[mapa]), "slp": cadena._leer(com["slp.tif"]),
        "asp": cadena._leer(com["asp.tif"]), "cc": cadena._leer(com["cc.tif"]),
        "firms": com["firms.csv"],
    }


def nombre_combustible(codigo: int) -> str:
    return f"{GRUPOS.get(codigo // 10, '?')}{codigo % 10}"


# ── F1 velocidad vs dirección ─────────────────────────────────────────────────────────────

def f1_f4(c: dict) -> tuple[dict, list[dict], list[dict]]:
    """Por incendio: t*, Dice, eje, FSS y distancia de perímetro al horizonte y a área igualada."""
    g, ha = c["grilla"], c["grilla"].celda_ha
    excl, sem, cic, cos = c["excluido"], c["semilla"], c["cicatriz"], c["cosido"]
    fuera = excl | sem
    valido = ~fuera
    pred_h = np.isfinite(cos) & ~sem
    ref = cic & ~sem
    ai = p.area_igualada(np.where(sem, np.nan, cos), cic, ha, fuera)
    m_h = p.metricas(pred_h & valido, ref & valido, ha)
    t_star = ai["hora"]
    pred_t = pred_h & (np.nan_to_num(cos, nan=np.inf) <= t_star)
    fila = {"incendio": c["incendio"], "caso": c["id"], "limite": c["limite"],
            "horizonte_h": c["horizonte_h"], "t_star_h": t_star,
            "t_star_sobre_horizonte": t_star / c["horizonte_h"],
            "t_star_alcanzada": ai["alcanzada"], "sesgo_area_h": m_h["sesgo_area"],
            "dice_horizonte": m_h["dice"], "dice_area_igualada": ai["dice"],
            "precision_t_star": ai["precision"], "observado_ha": m_h["observado_ha"],
            "predicho_ha": m_h["predicho_ha"]}
    cm = g.transform.a
    for nombre, pred in (("h", pred_h), ("t", pred_t)):
        rp, dp = eje(sem, pred & valido, cm)
        ro, do = eje(sem, ref & valido, cm)
        fila[f"rumbo_pred_{nombre}"] = rp
        fila[f"rumbo_obs_{nombre}"] = ro
        fila[f"dif_angulo_{nombre}_grados"] = dif_angulo(rp, ro)
        fila[f"dist_eje_pred_{nombre}_m"] = dp
        fila[f"dist_eje_obs_{nombre}_m"] = do
    caja = recorte(pred_h | ref | sem)
    fss_filas, dist_filas = [], []
    for nombre, pred in (("horizonte", pred_h), ("area_igualada", pred_t)):
        v = valido[caja]
        pr, rf = (pred & valido)[caja], (ref & valido)[caja]
        umbral = fss_util(rf, v)
        for n in ESCALAS_CELDAS:
            fss_filas.append({"incendio": c["incendio"], "limite": c["limite"], "corte": nombre,
                              "escala_m": n * cm, "fss": fss(pr, rf, v, n),
                              "fss_util": umbral})
        dm = distancia_perimetro((pred | sem)[caja], (cic | sem)[caja], excl[caja], cm)
        dist_filas.append({"incendio": c["incendio"], "limite": c["limite"], "corte": nombre,
                           **dm})
    return fila, fss_filas, dist_filas


# ── F2 error de tiempo de llegada ─────────────────────────────────────────────────────────

BINS_H = [(0, 12), (12, 24), (24, 48), (48, 72), (72, 1e9)]


def f2(c: dict) -> tuple[list[dict], list[dict]]:
    """TOA predicho (línea de tiempo cosida) − hora de la primera detección que cubre la celda
    (medio píxel VIIRS), sobre las celdas con detección fuera de la semilla y la exclusión."""
    sel = np.isfinite(c["det"]) & ~c["semilla"] & ~c["excluido"]
    det, cos = c["det"][sel], c["cosido"][sel]
    alc = np.isfinite(cos)
    err = cos - det
    def resumen(e: np.ndarray, n_tot: int) -> dict:
        if e.size == 0:
            return {"n_det": n_tot, "n_alcanzadas": 0}
        q1, med, q3 = np.percentile(e, [25, 50, 75])
        return {"n_det": n_tot, "n_alcanzadas": int(e.size), "frac_nunca": 1 - e.size / n_tot,
                "mediana_h": med, "q1_h": q1, "q3_h": q3, "iqr_h": q3 - q1,
                "frac_antes_de_deteccion": float((e < 0).mean())}
    base = {"incendio": c["incendio"], "limite": c["limite"]}
    res = [base | resumen(err[alc], int(sel.sum()))
           | {"pendiente_h_por_h": float(np.polyfit(det[alc], err[alc], 1)[0])
              if alc.sum() > 2 else None,
              "spearman_toa_deteccion": correlacion(list(det[alc]), list(cos[alc]))["spearman"]
              if alc.sum() > 2 else None}]
    por_t = []
    for lo, hi in BINS_H:
        b = (det >= lo) & (det < hi)
        if b.any():
            por_t.append(base | {"desde_h": lo, "hasta_h": None if hi > 1e8 else hi}
                         | resumen(err[b & alc], int(b.sum())))
    return res, por_t


# ── F3 estratos ───────────────────────────────────────────────────────────────────────────

def tabla_estratos(etiq: np.ndarray, nombres: dict, pred: np.ndarray, ref: np.ndarray,
                   valido: np.ndarray, ha: float, usar: str = "ambos") -> list[dict]:
    """TP/FP/FN y tasas por estrato. etiq < 0 = fuera de la tabla. tasa_fn = FN/(TP+FN);
    tasa_fp = FP/(TP+FP) (1 − precisión). `usar` anula la tasa que el estrato no define."""
    filas = []
    p_, r_ = pred & valido, ref & valido
    for k, nom in nombres.items():
        m = (etiq == k) & valido
        tp, fp, fn = (int((m & x).sum()) for x in (p_ & r_, p_ & ~r_, ~p_ & r_))
        filas.append({"estrato": nom, "area_ha": m.sum() * ha, "tp_ha": tp * ha, "fp_ha": fp * ha,
                      "fn_ha": fn * ha,
                      "tasa_fn": fn / (tp + fn) if tp + fn and usar != "fp" else None,
                      "tasa_fp": fp / (tp + fp) if tp + fp and usar != "fn" else None})
    return filas


def etiquetas_f3(c: dict) -> dict[str, tuple[np.ndarray, dict]]:
    """Cada dimensión de estratificación: (etiquetas por celda, {etiqueta: nombre})."""
    fuel = c["fuel"].astype(int)
    cod = sorted(int(x) for x in np.unique(fuel))
    pen = np.digitize(c["slp"], [5, 15, 25, 35])
    pen_n = {0: "0-5°", 1: "5-15°", 2: "15-25°", 3: "25-35°", 4: ">35°"}
    asp = c["asp"].astype(float)
    sec = (np.round(asp / 45).astype(int)) % 8
    nodata = (asp < 0) | (c["slp"] < 3)
    sec = np.where(nodata, 8, sec)
    sec_n = dict(enumerate(["N", "NE", "E", "SE", "S", "SO", "O", "NO", "plano/sin dato"]))
    dos = np.digitize(c["cc"], [1, 20, 50, 80])
    dos_n = {0: "0 %", 1: "1-20 %", 2: "20-50 %", 3: "50-80 %", 4: "80-100 %"}
    return {"combustible": (fuel, {k: nombre_combustible(k) for k in cod}),
            "grupo_combustible": (fuel // 10, {k: v for k, v in GRUPOS.items()
                                               if (fuel // 10 == k).any()}),
            "pendiente": (pen, pen_n), "orientacion": (sec, sec_n), "dosel": (dos, dos_n)}


def f3(c: dict, vistas_h: np.ndarray | None) -> list[dict]:
    ha = c["grilla"].celda_ha
    valido = ~(c["excluido"] | c["semilla"])
    pred = np.isfinite(c["cosido"]) & ~c["semilla"]
    ref = c["cicatriz"] & ~c["semilla"]
    filas = []
    for dim, (etiq, nom) in etiquetas_f3(c).items():
        filas += [{"dimension": dim} | f for f in tabla_estratos(etiq, nom, pred, ref, valido, ha)]
    bloque = lambda h: (np.floor(((h + UTC_ART_H) % 24) / 3)).astype(int)  # noqa: E731
    nombres_h = {k: f"{3 * k:02d}-{3 * k + 3:02d} h ART" for k in range(8)}
    h_pred = c["t0"].hour + c["t0"].minute / 60 + np.nan_to_num(c["cosido"], nan=0)
    et_pred = np.where(pred, bloque(h_pred), -1)
    filas += [{"dimension": "hora_llegada_predicha"} | f
              for f in tabla_estratos(et_pred, nombres_h, pred, ref, valido, ha, usar="fp")]
    obs_h = vistas_h if vistas_h is not None else c["det"]
    h_obs = c["t0"].hour + c["t0"].minute / 60 + np.nan_to_num(obs_h, nan=0)
    et_obs = np.where(ref & np.isfinite(obs_h), bloque(h_obs), -1)
    filas += [{"dimension": "hora_deteccion_observada"} | f
              for f in tabla_estratos(et_obs, nombres_h, pred, ref, valido, ha, usar="fn")]
    return [{"incendio": c["incendio"], "limite": c["limite"]} | f for f in filas]


def agrupar_estratos(df: pd.DataFrame) -> pd.DataFrame:
    """Suma sobre incendios (no límite) y reescribe las tasas; razón = tasa / tasa global."""
    cuentas = ["area_ha", "tp_ha", "fp_ha", "fn_ha"]
    tot = df[~df["limite"]].groupby(["dimension", "estrato"], sort=False)[cuentas].sum()
    tot = tot.reset_index().assign(incendio="TODOS", limite=False)
    df = pd.concat([df, tot], ignore_index=True)
    df["tasa_fn"] = df["fn_ha"] / (df["tp_ha"] + df["fn_ha"])
    df["tasa_fp"] = df["fp_ha"] / (df["tp_ha"] + df["fp_ha"])
    g = df[df["dimension"] == "combustible"].groupby("incendio")[cuentas].sum()
    glob_fn = (g["fn_ha"] / (g["tp_ha"] + g["fn_ha"])).to_dict()
    glob_fp = (g["fp_ha"] / (g["tp_ha"] + g["fp_ha"])).to_dict()
    sin_fn, sin_fp = df["dimension"] == "hora_llegada_predicha", \
        df["dimension"] == "hora_deteccion_observada"
    df.loc[sin_fn, ["fn_ha", "tasa_fn"]] = np.nan
    df.loc[sin_fp, ["fp_ha", "tasa_fp"]] = np.nan
    df["razon_fn"] = df["tasa_fn"] / df["incendio"].map(glob_fn)
    df["razon_fp"] = df["tasa_fp"] / df["incendio"].map(glob_fp)
    tot_dim = df.groupby(["incendio", "dimension"])[cuentas].transform("sum")
    df["frac_area"] = df["area_ha"] / tot_dim["area_ha"]
    df["frac_fn"] = df["fn_ha"] / tot_dim["fn_ha"]
    df["frac_fp"] = df["fp_ha"] / tot_dim["fp_ha"]
    return df


# ── F5 calibración secuencial (P-24) ──────────────────────────────────────────────────────

def f5(incendio: str) -> tuple[list[dict], list[dict]]:
    """Sesgo de crecimiento por reinicio y efecto offline de un ADJ_k asimilado."""
    cid = f"{incendio}/pronostico-v6"
    caso = d.Caso.cargar(cid)
    man = _manifiesto(cid, RECETA_P24)
    filas = json.loads((d.ruta_iteracion(cid, RECETA_P24) / "pronostico.json").read_text())
    ha = p.Grilla(almacen.abrir(caso.paquete()["comunes"]["dem.tif"])).celda_ha
    semillas = [cadena._leer(w["insumos"]["phi.tif"]) < 0 for w in man["ventanas"]]
    toas = [p.horas_relativas(cadena._leer(cadena._toa(w["salidas"])), v.tstart_s)
            for v, w in zip(caso.ventanas, man["ventanas"])]
    salida = []
    for k, f in enumerate(filas):
        fila = {"incendio": incendio, "k": k, "horas_desde_ignicion": f["horas_desde_ignicion"],
                "semilla_ha": f["semilla_ha"]}
        for plazo in ("12", "24"):
            m = f["plazos"][plazo]["p24"]["cicatriz"]
            fila[f"sesgo_{plazo}"] = m["sesgo_area"]
            fila[f"pred_ha_{plazo}"], fila[f"obs_ha_{plazo}"] = m["predicho_ha"], m["observado_ha"]
        if k >= 1:   # ADJ_k desde la ventana k−1, que ya corrió y cubre [T_{k−1}, T_k]
            dt_h = (caso.ventanas[k].inicio - caso.ventanas[k - 1].inicio).total_seconds() / 3600
            nuevas = int(((toas[k - 1] <= dt_h) & ~semillas[k - 1]).sum())
            a_ini = semillas[k - 1].sum() * ha
            adj, sat = adj_k(a_ini, a_ini + nuevas * ha, semillas[k].sum() * ha)
            fila |= {"dt_ventana_prev_h": dt_h, "adj": adj, "adj_saturado": sat,
                     "usa_ventana0": k == 1}
            for plazo in ("12", "24"):
                g, o = fila[f"pred_ha_{plazo}"], fila[f"obs_ha_{plazo}"]
                if g > 0 and o > 0:
                    g2 = crecimiento_con_adj(fila["semilla_ha"], g, adj)
                    fila[f"sesgo_{plazo}_adj"] = g2 / o
                    fila[f"mejora_log_{plazo}"] = abs(math.log(g / o)) - abs(math.log(g2 / o))
        salida.append(fila)
    return salida, filas


def f5_resumen(df: pd.DataFrame) -> list[dict]:
    """Autocorrelación de log(sesgo_k) con log(sesgo_{k−1}) dentro de cada incendio y efecto
    agregado del ADJ offline. Variante «k≥2» (sin la ventana 0, que parte de la ignición)."""
    out = []
    for plazo in ("12", "24"):
        for variante, kmin in (("k>=2", 2), ("k>=1", 1)):
            for inc in [*df["incendio"].unique(), "TODOS"]:
                d_ = df if inc == "TODOS" else df[df["incendio"] == inc]
                d_ = d_[d_["incendio"].isin(df[~df["limite"]]["incendio"])]
                x: list[float] = []
                y: list[float] = []
                xc: list[float] = []
                yc: list[float] = []
                for i, grp in d_.groupby("incendio"):
                    s = grp.set_index("k")[f"sesgo_{plazo}"]
                    for k in s.index:
                        if k >= kmin and k - 1 in s.index and s[k] > 0 and s[k - 1] > 0:
                            x.append(math.log(s[k - 1]))
                            y.append(math.log(s[k]))
                    # centrado por incendio: quita el nivel medio de cada uno (sesgo sistemático)
                    if len(x) > len(xc):
                        nuevo_x, nuevo_y = x[len(xc):], y[len(xc):]
                        m = float(np.mean(nuevo_x + nuevo_y))
                        xc += [v - m for v in nuevo_x]
                        yc += [v - m for v in nuevo_y]
                fila = {"plazo_h": plazo, "variante": variante, "incendio": inc,
                        **correlacion(x, y),
                        "pearson_centrado": correlacion(xc, yc)["pearson"]}
                a = d_[(d_["k"] >= kmin) & d_[f"mejora_log_{plazo}"].notna()]
                fila |= {"reinicios_adj": len(a),
                         "mejoran": int((a[f"mejora_log_{plazo}"] > 0).sum()),
                         "empeoran": int((a[f"mejora_log_{plazo}"] < 0).sum()),
                         "mediana_abs_log_antes": float(np.median(
                             np.abs(np.log(a[f"pred_ha_{plazo}"] / a[f"obs_ha_{plazo}"]))))
                         if len(a) else None,
                         "mediana_abs_log_despues": float(np.median(
                             np.abs(np.log(a[f"sesgo_{plazo}_adj"])))) if len(a) else None,
                         "mediana_mejora_log": float(a[f"mejora_log_{plazo}"].median())
                         if len(a) else None,
                         "adj_saturados": int(a["adj_saturado"].sum()) if len(a) else 0}
                out.append(fila)
    return out


# ── F6 ROS empírica entre pasadas ─────────────────────────────────────────────────────────

def f6(incendio: str, caso_base: dict) -> pd.DataFrame:
    """Detecciones nuevas de cada pasada contra el frente detectado hasta la pasada previa: ROS
    observada d/Δt y la que da el TOA de P-24 (reinicio en la pasada previa) en la misma celda."""
    cid = f"{incendio}/pronostico-v6"
    caso = d.Caso.cargar(cid)
    man = _manifiesto(cid, RECETA_P24)
    g = caso_base["grilla"]
    df = pd.read_csv(almacen.abrir(caso_base["firms"]), parse_dates=["acq_datetime"])
    df["acq_datetime"] = pd.to_datetime(df["acq_datetime"], utc=True)
    tr = Transformer.from_crs("EPSG:4326", str(g.crs), always_xy=True)
    df["x"], df["y"] = tr.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    df["fila"], df["col"] = rasterio.transform.rowcol(g.transform, df["x"].to_numpy(),
                                                      df["y"].to_numpy())
    dentro = (df["fila"] >= 0) & (df["fila"] < g.shape[0]) & (df["col"] >= 0) \
        & (df["col"] < g.shape[1])
    df = df[dentro].copy()
    # sólo el incendio: a menos de 1 km de la cicatriz y fuera de la exclusión
    cerca = suma_ventana(caso_base["cicatriz"], 67) > 0
    f_, c_ = df["fila"].to_numpy(), df["col"].to_numpy()
    df = df[cerca[f_, c_] & ~caso_base["excluido"][f_, c_]]
    fin = caso.ventanas[-1].fin
    df = df[(df["acq_datetime"] > caso_base["t0"]) & (df["acq_datetime"] <= fin)]
    df = df.sort_values("acq_datetime").reset_index(drop=True)
    df["pasada"] = (df["acq_datetime"].diff() > pd.Timedelta(hours=pronostico
                    .SEPARACION_PASADAS_H)).cumsum()
    ign = np.argwhere(caso_base["semilla"]).mean(0)
    ign_xy = np.array([[g.transform.c + (ign[1] + .5) * g.transform.a,
                        g.transform.f + (ign[0] + .5) * g.transform.e]])
    filas = []
    for k in range(1, len(caso.ventanas)):   # ventana k reinicia al final de la pasada k−1
        previas = df[df["pasada"] < k]
        nuevas = df[df["pasada"] == k]
        if previas.empty or nuevas.empty:
            continue
        inicio = caso.ventanas[k].inicio
        prev_xy = np.vstack([ign_xy, previas[["x", "y"]].to_numpy()])
        dt_h = ((nuevas["acq_datetime"] - pd.Timestamp(inicio)).dt.total_seconds() / 3600
                ).to_numpy()
        r = ros_empirica(prev_xy, nuevas[["x", "y"]].to_numpy(), dt_h)
        if r.empty:
            continue
        sub = nuevas.iloc[r["i"]].reset_index(drop=True)
        r = r.drop(columns="i").join(sub[["fila", "col"]])
        w = man["ventanas"][k]
        semilla = cadena._leer(w["insumos"]["phi.tif"]) < 0
        toa_h = p.horas_relativas(cadena._leer(cadena._toa(w["salidas"])),
                                  caso.ventanas[k].tstart_s)
        t_mod = toa_h[r["fila"].to_numpy(), r["col"].to_numpy()]
        en_semilla = semilla[r["fila"].to_numpy(), r["col"].to_numpy()]
        r["dt_obs_h"] = ((sub["acq_datetime"] - pd.Timestamp(inicio))
                         .dt.total_seconds() / 3600).to_numpy()
        r["t_mod_h"] = np.where(en_semilla, np.nan, t_mod)
        r["en_semilla"] = en_semilla
        r["ros_mod_m_min"] = r["d_m"] / (r["t_mod_h"] * 60)
        r["codigo"] = caso_base["fuel"][r["fila"].to_numpy(), r["col"].to_numpy()].astype(int)
        r["incendio"], r["k"] = incendio, k
        filas.append(r)
    return pd.concat(filas, ignore_index=True) if filas else pd.DataFrame()


def f6_resumen(df: pd.DataFrame, umbral_d_m: float, minimo: int = 30) -> pd.DataFrame:
    """Por combustible (código y grupo): ROS observada y del modelo en las mismas celdas.
    `umbral_d_m`: distancia mínima al frente previo para contar la detección como celda nueva
    (375 m = un píxel entero; 187,5 m admite re-detecciones del mismo píxel desde otra órbita)."""
    df = df[~df["en_semilla"] & (df["d_m"] >= umbral_d_m)].copy()
    df["grupo"] = df["codigo"].map(lambda c: GRUPOS.get(c // 10, "?"))
    df["combustible"] = df["codigo"].map(nombre_combustible)
    out = []
    for nivel, col in (("grupo", "grupo"), ("combustible", "combustible")):
        for nom, g in df.groupby(col):
            if len(g) < minimo:
                continue
            alc = g["t_mod_h"].notna()
            ros_mod = g["ros_mod_m_min"].where(alc, 0.0)   # sin llegada en 24 h: censurada en 0
            out.append({
                "umbral_d_m": umbral_d_m, "nivel": nivel, "combustible": nom, "n_celdas": len(g),
                "n_incendios": g["incendio"].nunique(),
                "ros_obs_mediana": g["ros_obs_m_min"].median(),
                "ros_obs_q1": g["ros_obs_m_min"].quantile(.25),
                "ros_obs_q3": g["ros_obs_m_min"].quantile(.75),
                "frac_modelo_no_llega_24h": 1 - alc.mean(),
                "ros_mod_mediana_alcanzadas": g.loc[alc, "ros_mod_m_min"].median(),
                "ros_mod_mediana_censurada": ros_mod.median(),
                "razon_mod_obs_alcanzadas": g.loc[alc, "ros_mod_m_min"].median()
                / g["ros_obs_m_min"].median(),
                "mediana_t_mod_menos_t_obs_h": (g.loc[alc, "t_mod_h"]
                                                - g.loc[alc, "dt_obs_h"]).median(),
                "dt_obs_mediana_h": g["dt_obs_h"].median(),
                "d_mediana_m": g["d_m"].median()})
    return pd.DataFrame(out)


# ── ejecución ─────────────────────────────────────────────────────────────────────────────

def vistas_ultima_ventana(incendio: str, t0, shape) -> np.ndarray | None:
    """Hora (desde t0 del caso) de la primera detección a ≤ 1 píxel, del paquete P-24."""
    try:
        caso = d.Caso.cargar(f"{incendio}/pronostico-v6")
        arch = caso.paquete()["ventanas"][-1]
    except FileNotFoundError:
        return None
    v = cadena._leer(arch["vistas_horas.tif"]).astype("float64")
    off = (caso.ventanas[-1].inicio - t0).total_seconds() / 3600
    return np.where(np.isfinite(v) & (v < 1e6), off + v, np.nan) if v.shape == shape else None


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    f1s, fss_f, dist_f, f2r, f2t, f3r, f5r, f6r = [], [], [], [], [], [], [], []
    for cid in casos_calibracion():
        print(cid, flush=True)
        c = cargar(cid)
        a, b, cdist = f1_f4(c)
        f1s.append(a)
        fss_f += b
        dist_f += cdist
        r, t = f2(c)
        f2r += r
        f2t += t
        f3r += f3(c, vistas_ultima_ventana(c["incendio"], c["t0"], c["cosido"].shape))
        if (Path("benchmarks/casos") / c["incendio"] / "pronostico-v6.json").exists():
            filas, _ = f5(c["incendio"])
            for f in filas:
                f["limite"] = c["limite"]
            f5r += filas
            f6r.append(f6(c["incendio"], c))
        del c
    pd.DataFrame(f1s).to_csv(SALIDA / "F1_velocidad_direccion.csv", index=False)
    pd.DataFrame(fss_f).to_csv(SALIDA / "F4_fss.csv", index=False)
    pd.DataFrame(dist_f).to_csv(SALIDA / "F4_distancia_perimetro.csv", index=False)
    pd.DataFrame(f2r).to_csv(SALIDA / "F2_toa_resumen.csv", index=False)
    pd.DataFrame(f2t).to_csv(SALIDA / "F2_toa_por_tiempo.csv", index=False)
    agrupar_estratos(pd.DataFrame(f3r)).to_csv(SALIDA / "F3_estratos.csv", index=False)
    f5d = pd.DataFrame(f5r)
    f5d.to_csv(SALIDA / "F5_sesgo_por_reinicio.csv", index=False)
    pd.DataFrame(f5_resumen(f5d)).to_csv(SALIDA / "F5_autocorrelacion_adj.csv", index=False)
    f6d = pd.concat(f6r, ignore_index=True)
    f6d.to_csv(SALIDA / "F6_celdas_nuevas.csv.gz", index=False)
    pd.concat([f6_resumen(f6d, u) for u in (PIXEL_VIIRS_M, PIXEL_VIIRS_M / 2)]).to_csv(
        SALIDA / "F6_ros_por_combustible.csv", index=False)


# ── S2 · F7 elongación y eje de lo quemado ────────────────────────────────────────────────

ELONG_MIN_EJE = 1.3     # por debajo, el eje de la elipse es ruido y no se informa
BOOT_REPLICAS = 200


def _momentos(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """(elongación, eje) de una nube de celdas: √(λ1/λ2) de su covarianza y el rumbo del eje
    mayor en grados desde el norte, módulo 180. NaN con menos de 10 celdas."""
    if len(x) < 10:
        return math.nan, math.nan
    ev, vec = np.linalg.eigh(np.cov(np.vstack([x, y])))
    v = vec[:, 1]
    return (float(np.sqrt(ev[1] / max(ev[0], 1e-12))),
            float(np.degrees(np.arctan2(v[0], -v[1])) % 180))


def elongacion(m: np.ndarray, replicas: int = BOOT_REPLICAS, semilla: int = 0) -> dict:
    """Elongación y eje de la máscara `m`, con intervalo 95 % por bootstrap de celdas. El eje
    crudo se informa siempre; `eje` sólo si la elongación pasa de ELONG_MIN_EJE. El intervalo
    del eje es circular módulo 180 (desvíos al estimado, envueltos en (−90, 90])."""
    y, x = np.nonzero(m)
    e, a = _momentos(x, y)
    out = {"n_celdas": len(x), "elong": e, "eje_crudo": a,
           "eje": a if e > ELONG_MIN_EJE else math.nan}
    if len(x) < 10 or replicas == 0:
        return out | dict.fromkeys(("elong_lo", "elong_hi", "eje_lo", "eje_hi"), math.nan)
    rng = np.random.default_rng(semilla)
    es, ds = [], []
    for _ in range(replicas):
        i = rng.integers(0, len(x), len(x))
        eb, ab = _momentos(x[i], y[i])
        es.append(eb)
        ds.append((ab - a + 90) % 180 - 90)
    lo, hi = np.percentile(es, [2.5, 97.5])
    dlo, dhi = np.percentile(ds, [2.5, 97.5])
    return out | {"elong_lo": float(lo), "elong_hi": float(hi),
                  "eje_lo": float((a + dlo) % 180), "eje_hi": float((a + dhi) % 180)}


def componente_mayor(m: np.ndarray) -> np.ndarray:
    """La componente conexa (8-vecinos) de más celdas de `m`."""
    formas = [g for g, _ in rasterio.features.shapes(m.astype("uint8"), mask=m, connectivity=8)]
    if not formas:
        return m
    etiq = rasterio.features.rasterize([(g, i + 1) for i, g in enumerate(formas)],
                                       out_shape=m.shape, dtype="int32")
    return etiq == np.bincount(etiq[etiq > 0]).argmax()


# Variantes de F7: (nombre, objeto observado, objeto predicho)
F7_PARES = (
    ("A_actual", "obs_trunc", "pred_H_recorte"),
    ("B_actual_t_star", "obs_trunc", "pred_t_recorte"),
    ("C_final_sin_recorte", "obs_final", "pred_H_sinrecorte"),
    ("D_final_sin_recorte_t_star", "obs_final", "pred_t_sinrecorte"),
    ("E_solo_sin_recorte", "obs_trunc", "pred_H_sinrecorte"),
    ("F_mayor_actual", "obs_trunc_mayor", "pred_H_recorte_mayor"),
    ("G_mayor_final_sin_recorte", "obs_final_mayor", "pred_H_sinrecorte_mayor"),
)


def f7_objetos(c: dict) -> dict[str, np.ndarray]:
    """Las máscaras cuya forma se compara. `recorte` = quitar de lo predicho la cicatriz que
    el truncado a `vistas` excluye (exclusión del caso); `sinrecorte` sólo excluye la base."""
    sem, cos, cic, exc = c["semilla"], c["cosido"], c["cicatriz"], c["excluido"]
    ref = c["caso"].datos["referencias"]["cicatriz"]
    final, exc_base = p.cargar_cicatriz(Path(ref["run"]), c["grilla"],
                                        tuple(ref.get("excluidas", p.EXCLUIDAS_POR_DEFECTO)))
    ai = p.area_igualada(np.where(sem, np.nan, cos), cic, c["grilla"].celda_ha, exc | sem)
    fin = np.isfinite(cos)
    en_t = np.nan_to_num(cos, nan=np.inf) <= ai["hora"] if ai["hora"] is not None else fin
    o = {"obs_trunc": (cic | sem) & ~exc, "obs_final": (final | sem) & ~exc_base,
         "pred_H_recorte": (fin | sem) & ~exc, "pred_H_sinrecorte": (fin | sem) & ~exc_base,
         "pred_t_recorte": (en_t | sem) & ~exc, "pred_t_sinrecorte": (en_t | sem) & ~exc_base}
    for k in ("obs_trunc", "obs_final", "pred_H_recorte", "pred_H_sinrecorte"):
        o[f"{k}_mayor"] = componente_mayor(o[k])
    return o


def f7(c: dict) -> list[dict]:
    """Filas largas (incendio, objeto) con elongación, eje e intervalos bootstrap."""
    return [{"incendio": c["incendio"], "objeto": k, **elongacion(m)}
            for k, m in f7_objetos(c).items()]


def f7_resumen(df: pd.DataFrame) -> pd.DataFrame:
    """Por variante, sobre los incendios no límite (df ya sin límite): mediana de la elongación
    predicha y observada, en cuántos lo predicho es más redondo (y en cuántos con intervalos
    disjuntos) y |Δeje| sólo donde ambas elongaciones pasan ELONG_MIN_EJE."""
    ix = df.set_index(["incendio", "objeto"])
    filas = []
    for nom, ob, pr in F7_PARES:
        incs = df["incendio"].unique()
        eo = np.array([ix.loc[(i, ob), "elong"] for i in incs])
        ep = np.array([ix.loc[(i, pr), "elong"] for i in incs])
        disj = [ix.loc[(i, pr), "elong_hi"] < ix.loc[(i, ob), "elong_lo"] for i in incs]
        ao = np.array([ix.loc[(i, ob), "eje"] for i in incs])
        ap = np.array([ix.loc[(i, pr), "eje"] for i in incs])
        ok = np.isfinite(ao) & np.isfinite(ap)
        dif = np.abs((ap - ao + 90) % 180 - 90)[ok]
        filas.append({"variante": nom, "obs": ob, "pred": pr, "n": len(incs),
                      "elong_obs_mediana": float(np.median(eo)),
                      "elong_pred_mediana": float(np.median(ep)),
                      "pred_mas_redondo": int((ep < eo).sum()),
                      "pred_mas_redondo_ic_disjunto": int(sum(disj)),
                      "n_eje_definido_ambos": int(ok.sum()),
                      "dif_eje_mediana_grados": float(np.median(dif)) if ok.any() else math.nan,
                      "dif_eje_mayor_45": int((dif > 45).sum())})
    return pd.DataFrame(filas)


# ── S1 · F1 por reinicio de P-24 ─────────────────────────────────────────────────────────

def s1_reinicio(semilla: np.ndarray, horas: np.ndarray, vistas: np.ndarray, cic: np.ndarray,
                exc: np.ndarray, plazo: float, ha: float, celda_m: float) -> dict:
    """Un reinicio a `plazo` h con la referencia de crecimiento ESTRICTA: se excluyen (ni acierto
    ni error) las celdas ya vistas al reiniciar (vistas ≤ 0) que no están en la semilla, además
    de lo que `pronostico.puntuar` ya excluye. t* se busca dentro de [0, plazo]."""
    anillo = (vistas <= 0) & ~semilla
    vistos = vistas <= plazo
    excl = exc | anillo | semilla | (cic & ~vistos)
    ref = cic & vistos & ~semilla
    h = np.where(np.isfinite(horas) & (horas <= plazo) & ~semilla, horas, np.nan)
    pred = np.isfinite(h)
    m = p.metricas(pred, ref, ha, excl)
    ai = p.area_igualada(h, ref, ha, excl)
    pc, rc = pred & ~excl, ref & ~excl
    fila = {"sesgo": m["sesgo_area"], "dice": m["dice"], "precision": m["precision"],
            "recall": m["recall"], "pred_ha": m["predicho_ha"], "obs_ha": m["observado_ha"],
            "t_star_h": ai["hora"], "t_star_alcanzada": ai["alcanzada"],
            "dice_t_star": ai["dice"], "precision_t_star": ai.get("precision")}
    if m["observado_ha"] and m["predicho_ha"]:
        fila["abs_ln_sesgo"] = abs(math.log(m["sesgo_area"]))
        fila["delta_dice_t_star"] = (ai["dice"] - m["dice"]) if ai["alcanzada"] else math.nan
    if pc.any() and rc.any() and semilla.any():
        rp, dp = eje(semilla, pc, celda_m)
        ro, do = eje(semilla, rc, celda_m)
        fila |= {"rumbo_pred": rp, "rumbo_obs": ro, "dif_angulo": dif_angulo(rp, ro),
                 "abs_dif_angulo": abs(dif_angulo(rp, ro))}
        for nom, a, b in (("crec", pc, rc), ("total", pc | semilla, rc | semilla)):
            fila[f"elong_pred_{nom}"] = elongacion(a, replicas=0)["elong"]
            fila[f"elong_obs_{nom}"] = elongacion(b, replicas=0)["elong"]
    return fila


def s1(incendio: str) -> list[dict]:
    """Los reinicios k ≥ 1 de P-24 (semilla FIRMS) de un incendio de calibración, a 12 y 24 h."""
    cid = f"{incendio}/pronostico-v6"
    if incendio not in {i.split("/")[0] for i in casos_calibracion()}:
        raise ValueError(f"{incendio} no es de calibración")
    caso = d.Caso.cargar(cid)
    man = _manifiesto(cid, RECETA_P24)
    paq = caso.paquete()
    g = p.Grilla(almacen.abrir(paq["comunes"]["dem.tif"]))
    cic = cadena._leer(paq["comunes"]["cicatriz.tif"]).astype(bool)
    exc = cadena._leer(paq["comunes"]["excluido.tif"]).astype(bool)
    filas = []
    for v, w in zip(caso.ventanas, man["ventanas"]):
        if w["n"] < 1:
            continue
        semilla = cadena._leer(w["insumos"]["phi.tif"]) < 0
        horas = p.horas_relativas(cadena._leer(cadena._toa(w["salidas"])), v.tstart_s)
        vistas = cadena._leer(paq["ventanas"][w["n"]]["vistas_horas.tif"]).astype("float64")
        for plazo in (12, 24):
            filas.append({"incendio": incendio, "k": w["n"], "plazo_h": plazo}
                         | s1_reinicio(semilla, horas, vistas, cic, exc, plazo, g.celda_ha,
                                       g.transform.a))
    return filas


def s1_resumen(df: pd.DataFrame) -> pd.DataFrame:
    """Por plazo e incendio (y TODOS): medianas de |ln sesgo|, ΔDice a área igualada (sólo donde
    se alcanza t*), |Δángulo| y elongaciones; cuántos reinicios no alcanzan el área."""
    filas = []
    for plazo in (12, 24):
        sub = df[df["plazo_h"] == plazo]
        for inc, g in [*sub.groupby("incendio"), ("TODOS", sub)]:
            alc = g["t_star_alcanzada"].astype(bool)
            filas.append({
                "plazo_h": plazo, "incendio": inc, "n": len(g), "n_alcanza_area": int(alc.sum()),
                "mediana_abs_ln_sesgo": g["abs_ln_sesgo"].median(),
                "mediana_sesgo": g["sesgo"].median(),
                "mediana_dice": g["dice"].median(),
                "mediana_dice_t_star": g.loc[alc, "dice_t_star"].median(),
                "mediana_delta_dice_t_star": g["delta_dice_t_star"].median(),
                "mediana_precision": g["precision"].median(),
                "mediana_recall": g["recall"].median(),
                "mediana_precision_no_alcanza": g.loc[~alc, "precision"].median(),
                "mediana_abs_dif_angulo": g["abs_dif_angulo"].median(),
                "mediana_elong_pred_crec": g["elong_pred_crec"].median(),
                "mediana_elong_obs_crec": g["elong_obs_crec"].median(),
                "mediana_elong_pred_total": g["elong_pred_total"].median(),
                "mediana_elong_obs_total": g["elong_obs_total"].median()})
    return pd.DataFrame(filas)


# ── S3 · cruces de F3 ─────────────────────────────────────────────────────────────────

def cruces_f3(c: dict) -> list[dict]:
    """TU × orientación y grupo de combustible × pendiente: TP/FP/FN y tasas, con n de celdas."""
    ha = c["grilla"].celda_ha
    valido = ~(c["excluido"] | c["semilla"])
    pred = np.isfinite(c["cosido"]) & ~c["semilla"]
    ref = c["cicatriz"] & ~c["semilla"]
    et = etiquetas_f3(c)
    tu = (c["fuel"].astype(int) // 10 == 16).astype(int)
    sec, sec_n = et["orientacion"]
    pen, pen_n = et["pendiente"]
    gr = c["fuel"].astype(int) // 10
    cruces = {
        "TU_x_orientacion": (tu * 10 + sec,
                             {t * 10 + k: f"{'TU' if t else 'no-TU'} | {n}"
                              for t in (0, 1) for k, n in sec_n.items()}),
        "grupo_x_pendiente": (gr * 10 + pen,
                              {k * 10 + j: f"{n} | {pn}" for k, n in GRUPOS.items()
                               for j, pn in pen_n.items()})}
    filas = []
    for dim, (etiq, nombres) in cruces.items():
        for f in tabla_estratos(etiq, nombres, pred, ref, valido, ha):
            filas.append({"incendio": c["incendio"], "limite": c["limite"], "cruce": dim,
                          "n_celdas": round(f["area_ha"] / ha)} | f)
    return filas


def cruces_agrupar(df: pd.DataFrame) -> pd.DataFrame:
    """Suma sobre incendios no límite (TODOS) y recalcula las tasas."""
    cuentas = ["n_celdas", "area_ha", "tp_ha", "fp_ha", "fn_ha"]
    tot = df[~df["limite"]].groupby(["cruce", "estrato"], sort=False)[cuentas].sum()
    tot = tot.reset_index().assign(incendio="TODOS", limite=False)
    df = pd.concat([df, tot], ignore_index=True)
    df["tasa_fn"] = df["fn_ha"] / (df["tp_ha"] + df["fn_ha"])
    df["tasa_fp"] = df["fp_ha"] / (df["tp_ha"] + df["fp_ha"])
    return df


SECTORES_SE_S = ("SE", "S")
SECTORES_REF = ("N", "NO", "O")


def senal_se_s(df: pd.DataFrame) -> pd.DataFrame:
    """Tasa de FN en SE+S contra N+NO+O, dentro y fuera de TU: razón agrupada y en cuántos de los
    incendios (no límite) la razón es > 1. Sólo celdas con orientación definida (pendiente ≥ 3°)."""
    o = df[(df["cruce"] == "TU_x_orientacion") & ~df["limite"]].copy()
    o[["tu", "sector"]] = o["estrato"].str.split(" \\| ", expand=True)
    filas = []
    for tu in ("TU", "no-TU"):
        def tasa(g: pd.DataFrame, sectores: tuple) -> float:
            s = g[(g["tu"] == tu) & g["sector"].isin(sectores)]
            return s["fn_ha"].sum() / (s["tp_ha"].sum() + s["fn_ha"].sum())
        def celdas(sectores: tuple) -> int:
            return int(o[(o["tu"] == tu) & o["sector"].isin(sectores)
                         & (o["incendio"] == "TODOS")]["n_celdas"].sum())
        pooled = o[o["incendio"] == "TODOS"]
        por_inc = [tasa(g, SECTORES_SE_S) / tasa(g, SECTORES_REF)
                   for i, g in o[o["incendio"] != "TODOS"].groupby("incendio")]
        filas.append({"zona": tu, "tasa_fn_SE_S": tasa(pooled, SECTORES_SE_S),
                      "tasa_fn_N_NO_O": tasa(pooled, SECTORES_REF),
                      "razon": tasa(pooled, SECTORES_SE_S) / tasa(pooled, SECTORES_REF),
                      "n_celdas_SE_S": celdas(SECTORES_SE_S),
                      "n_celdas_N_NO_O": celdas(SECTORES_REF),
                      "incendios_razon_mayor_1": int(sum(r > 1 for r in por_inc)),
                      "incendios": len(por_inc)})
    return pd.DataFrame(filas)


def main_s() -> None:
    """Corre S1–S3 (`uv run python -c "import scripts.diagnostico_error as de; de.main_s()"`)."""
    SALIDA.mkdir(parents=True, exist_ok=True)
    f7r, cr = [], []
    for cid in casos_calibracion():
        c = cargar(cid)
        cr += cruces_f3(c)
        if not c["limite"]:
            f7r += f7(c)
        del c
    f7d = pd.DataFrame(f7r)
    f7d.to_csv(SALIDA / "S2_f7_elongacion_variantes.csv", index=False)
    f7_resumen(f7d).to_csv(SALIDA / "S2_f7_resumen.csv", index=False)
    crd = cruces_agrupar(pd.DataFrame(cr))
    crd.to_csv(SALIDA / "S3_cruces_f3.csv", index=False)
    senal_se_s(crd).to_csv(SALIDA / "S3_senal_se_s.csv", index=False)
    incendios = sorted({i.split("/")[0] for i in casos_calibracion()
                        if i not in particion()["limites"]})
    s1d = pd.DataFrame([f for i in incendios for f in s1(i)])
    s1d.to_csv(SALIDA / "S1_p24_por_reinicio.csv", index=False)
    s1_resumen(s1d).to_csv(SALIDA / "S1_p24_resumen.csv", index=False)


# ── S5 · dispersión de ENTRADA del ensamble GEFS ──────────────────────────────────────────

TARDE_UTC = (15, 18, 21)   # 12, 15 y 18 h ART: las horas de mayor propagación
RAIZ_ENSAMBLE = Path("data/ensemble-poc")


def dispersion_viento(u: np.ndarray, v: np.ndarray) -> tuple[float, float, float]:
    """(desvío estándar circular de la dirección en grados, coeficiente de variación de la
    rapidez, rapidez media) entre los miembros (eje 0), promediados sobre las celdas del
    dominio. Desvío circular = √(−2 ln R), con R el largo de la resultante de los versores."""
    vel = np.hypot(u, v)
    ang = np.arctan2(-u, -v)   # dirección «desde»
    r = np.hypot(np.cos(ang).mean(0), np.sin(ang).mean(0))
    sd = np.degrees(np.sqrt(-2 * np.log(np.clip(r, 1e-12, 1))))
    cv = vel.std(0, ddof=1) / np.maximum(vel.mean(0), 1e-9)
    return float(sd.mean()), float(cv.mean()), float(vel.mean())


def s5_caso(raiz: Path) -> list[dict]:
    """Por hora de pronóstico (GRIB retenidos de los 31 miembros), la dispersión de entrada."""
    miembros = sorted(x.name for x in (raiz / "sources").iterdir()
                      if (x / "manifest.json").exists())
    man = json.loads((raiz / "sources" / miembros[0] / "manifest.json").read_text())
    bbox = tuple(man["bbox_wgs84"])
    filas = []
    for h, valido in zip(man["source_hours"], man["source_valid_at"]):
        uv = [_read_gefs_fields(raiz / "sources" / m / "source" / f"f{h:03d}.grib2", bbox)[0]
              for m in miembros]
        sd, cv, vel = dispersion_viento(np.stack([x["u10"] for x in uv]),
                                        np.stack([x["v10"] for x in uv]))
        t = pd.Timestamp(valido)
        filas.append({"n_miembros": len(miembros), "hora_utc": t.hour, "valido": valido,
                      "tarde": t.hour in TARDE_UTC, "sd_dir_grados": sd, "cv_rapidez": cv,
                      "rapidez_media_ms": vel})
    return filas


def main_s5() -> None:
    """`uv run python -c "import scripts.diagnostico_error as de; de.main_s5()"`."""
    SALIDA.mkdir(parents=True, exist_ok=True)
    casos = json.loads((RAIZ_ENSAMBLE / "calibration-backtests-consolidated.json").read_text())
    filas = []
    for c in casos["cases"]:
        for f in s5_caso(Path(c["artifacts"]["root"])):
            filas.append({"caso": c["case_id"], "incendio": c["fire"]} | f)
    df = pd.DataFrame(filas)
    df.to_csv(SALIDA / "S5_dispersion_entrada_gefs.csv", index=False)
    por_caso = df.groupby(["incendio", "caso"]).apply(lambda g: pd.Series({
        "sd_dir_mediana": g["sd_dir_grados"].median(), "cv_mediana": g["cv_rapidez"].median(),
        "sd_dir_tarde": g.loc[g["tarde"], "sd_dir_grados"].median(),
        "cv_tarde": g.loc[g["tarde"], "cv_rapidez"].median(),
        "rapidez_media": g["rapidez_media_ms"].mean()}), include_groups=False).reset_index()
    por_caso.to_csv(SALIDA / "S5_dispersion_por_caso.csv", index=False)
    cols = ["sd_dir_mediana", "cv_mediana", "sd_dir_tarde", "cv_tarde", "rapidez_media"]
    por_caso.groupby("incendio")[cols].median().reset_index().to_csv(
        SALIDA / "S5_dispersion_por_incendio.csv", index=False)


if __name__ == "__main__":
    main()
