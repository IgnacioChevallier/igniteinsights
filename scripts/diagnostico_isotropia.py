"""Tarea I: ¿por qué el crecimiento de P-24 es casi isótropo? SIN correr ELMFIRE.

Frente de isotropía de docs/resultados/pronostico/precision.md. Para
cada reinicio k ≥ 1 de P-24 (`lw-100-obs-001` sobre `*/pronostico-v6`, semilla FIRMS, referencia
sin el anillo, como `pronostico.puntuar`), a 12 y 24 h, el crecimiento predicho y el observado se
reparten en sectores respecto del rumbo observado (semilla → centroide del crecimiento observado):
cabeza ±45°, flancos y retroceso. Exceso = fracción predicha − fracción observada en flancos +
retroceso, estratificado por WAF de la celda, viento a favor o en contra de la pendiente,
semilla dentro o fuera de la cicatriz y orientación.

    uv run python scripts/diagnostico_isotropia.py

Escribe benchmarks/diagnosticos/e2e/datos/I_*.csv. Sólo incendios de calibración.
"""
import csv
import json
import math

import numpy as np
import pandas as pd
import rasterio
import shapely

from app.validation import almacen, cadena, copa
from app.validation import definiciones as d
from app.validation import puntuacion as p
from scripts import diagnostico_error as de

SALIDA = de.SALIDA
PLAZOS_H = (12, 24)
WAF_CORTE = 0.15
CABEZA_GRADOS, RETROCESO_GRADOS = 45.0, 135.0
MIN_CELDAS = 20     # por estrato y por objeto (1,8 ha); fijado antes de ver los resultados
RAZON = 1.5         # DIAGNOSTICO §3 frente 2
PLANO_GRADOS = 3    # como etiquetas_f3: sin orientación definida


# ── funciones puras ───────────────────────────────────────────────────────────────────────

def sectores(semilla: np.ndarray, celdas: np.ndarray, rumbo_obs: float) -> np.ndarray:
    """Por celda de `celdas`: 0 cabeza, 1 flanco, 2 retroceso, según el rumbo desde el centroide
    de la semilla contra `rumbo_obs` (grados desde el norte). El resto, −1."""
    fs, cs = np.nonzero(semilla)
    f, c = np.nonzero(celdas)
    rumbos = np.degrees(np.arctan2(c - cs.mean(), fs.mean() - f)) % 360
    dif = np.abs((rumbos - rumbo_obs + 180) % 360 - 180)
    out = np.full(celdas.shape, -1, dtype=np.int8)
    out[f, c] = np.where(dif <= CABEZA_GRADOS, 0, np.where(dif <= RETROCESO_GRADOS, 1, 2))
    return out


def cuentas(sec: np.ndarray, pred: np.ndarray, ref: np.ndarray, est_pred: np.ndarray,
            est_obs: np.ndarray) -> dict:
    """Celdas del estrato (predicho y observado), cuántas en flancos + retroceso, y FN."""
    mp, mo = pred & est_pred, ref & est_obs
    return {"n_pred": int(mp.sum()), "lados_pred": int((sec[mp] > 0).sum()),
            "n_obs": int(mo.sum()), "lados_obs": int((sec[mo] > 0).sum()),
            "fn": int((mo & ~pred).sum())}


def exceso(n_pred, lados_pred, n_obs, lados_obs, minimo: int = MIN_CELDAS) -> float:
    if n_pred < minimo or n_obs < minimo:
        return math.nan
    return lados_pred / n_pred - lados_obs / n_obs


def mayor(a: float, b: float) -> bool:
    """`a` es un exceso ≥ 1,5× `b` (y es exceso: positivo)."""
    return a > 0 and a >= RAZON * b


def veredicto(e_bajo: float, e_alto: float, e_fuera: float, e_dentro: float) -> str:
    """Criterios registrados del frente 2 (DIAGNOSTICO §3)."""
    if any(math.isnan(x) for x in (e_bajo, e_alto)):
        return "sin dato"
    if mayor(e_bajo, e_alto):
        return "abrigo"
    igual = not mayor(e_alto, e_bajo)
    if igual and not math.isnan(e_fuera + e_dentro) and mayor(e_fuera, e_dentro):
        return "método"
    return "supresión/límite"


def viento_pendiente(wd: np.ndarray, hora_banda: np.ndarray, slp: np.ndarray, asp: np.ndarray,
                     celdas: np.ndarray) -> np.ndarray:
    """0 viento a favor de la pendiente (wd + 180 a < 90° de cuesta arriba, asp + 180), 1 en
    contra, 2 plano; con el `wd` de la banda horaria más cercana a la llegada. El resto, −1."""
    f, c = np.nonzero(celdas)
    b = np.clip(np.rint(hora_banda[f, c]), 0, wd.shape[0] - 1).astype(int)
    dif = np.abs((wd[b, f, c] - asp[f, c] + 180) % 360 - 180)   # (wd+180) − (asp+180)
    lab = np.where(dif < 90, 0, 1)
    lab = np.where((slp[f, c] < PLANO_GRADOS) | (asp[f, c] < 0), 2, lab)
    out = np.full(celdas.shape, -1, dtype=np.int8)
    out[f, c] = lab
    return out


def brota_fuera(semilla: np.ndarray, cic: np.ndarray, celdas: np.ndarray) -> np.ndarray:
    """Para cada celda de `celdas`: si el borde de semilla más cercano cae fuera de la cicatriz."""
    borde = np.argwhere(de._borde(semilla, np.zeros_like(semilla)))
    puntos = np.argwhere(celdas)
    out = np.zeros(celdas.shape, dtype=bool)
    if len(borde) == 0 or len(puntos) == 0:
        return out
    i, j = shapely.STRtree(shapely.points(borde)).query_nearest(shapely.points(puntos),
                                                                all_matches=False)
    fb, cb = borde[j].T
    out[puntos[i, 0], puntos[i, 1]] = ~cic[fb, cb]
    return out


def waf_celdas(cc_pct: np.ndarray, ch_m: np.ndarray, fbfm: np.ndarray,
               profundidad_ft: dict[int, float], crown_ratio: float = 1.0) -> np.ndarray:
    """El ráster WAF que ELMFIRE arma al iniciar, con la profundidad del lecho de cada modelo."""
    out = np.zeros(cc_pct.shape)
    for cod in np.unique(fbfm):
        sel = fbfm == cod
        out[sel] = copa.waf_elmfire(cc_pct[sel] / 100, ch_m[sel],
                                    profundidad_ft.get(int(cod), 0.0), crown_ratio)
    return out


def profundidades(sha: str) -> dict[int, float]:
    with open(almacen.abrir(sha)) as f:
        return {int(r[0]): float(r[11]) for r in csv.reader(f) if r}


# ── un reinicio ───────────────────────────────────────────────────────────────────────────

ORIENT = {"SE_S": (3, 4), "N_NO_O": (0, 7, 6)}   # sectores de etiquetas_f3


def reinicio(semilla, horas, vistas, cic, exc, plazo, tstart_s, est: dict, wd, slp, asp) -> list:
    anillo = (vistas <= 0) & ~semilla
    vistos = vistas <= plazo
    excl = exc | anillo | semilla | (cic & ~vistos)
    ref = cic & vistos & ~excl
    pred = np.isfinite(horas) & (horas <= plazo) & ~excl
    base = {"plazo_h": plazo, "celdas_pred": int(pred.sum()), "celdas_obs": int(ref.sum())}
    m = p.metricas(pred, ref, 1.0, excl)
    base |= {"dice": m["dice"], "sesgo": m["sesgo_area"]}
    if ref.sum() < MIN_CELDAS:
        return [base | {"dimension": "todo", "estrato": "todo", "rumbo_obs": math.nan}]
    rumbo = de.eje(semilla, ref, 1.0)[0]
    base["rumbo_obs"] = rumbo
    if pred.any():   # lo predicho contra su propio rumbo: ¿isótropo o sólo mal orientado?
        base["rumbo_pred"] = de.eje(semilla, pred, 1.0)[0]
        base["lados_pred_rumbo_propio"] = float(
            (sectores(semilla, pred, base["rumbo_pred"])[pred] > 0).mean())
    sec = sectores(semilla, pred | ref, rumbo)
    t0 = tstart_s / 3600
    vp_pred = viento_pendiente(wd, horas + t0, slp, asp, pred)
    vp_obs = viento_pendiente(wd, np.clip(vistas, 0, plazo) + t0, slp, asp, ref)
    fuera = brota_fuera(semilla, cic, pred | ref)
    bajo = est["waf"] < WAF_CORTE
    asp_sec = np.where((slp < PLANO_GRADOS) | (asp < 0), 8, np.round(asp / 45).astype(int) % 8)
    orient = {k: np.isin(asp_sec, v) for k, v in ORIENT.items()}
    orient["otras"] = ~(orient["SE_S"] | orient["N_NO_O"])
    todo = np.ones_like(pred)
    estratos = {
        ("todo", "todo"): (todo, todo),
        ("waf", "bajo"): (bajo, bajo), ("waf", "alto"): (~bajo, ~bajo),
        ("viento_pendiente", "a_favor"): (vp_pred == 0, vp_obs == 0),
        ("viento_pendiente", "en_contra"): (vp_pred == 1, vp_obs == 1),
        ("viento_pendiente", "plano"): (vp_pred == 2, vp_obs == 2),
        ("semilla", "fuera"): (fuera, fuera), ("semilla", "dentro"): (~fuera, ~fuera),
    }
    for k, o in orient.items():
        estratos[("orientacion", k)] = (o, o)
        for w, mw in (("bajo", bajo), ("alto", ~bajo)):
            estratos[("waf_x_orientacion", f"{w}|{k}")] = (mw & o, mw & o)
    for w, mw in (("bajo", bajo), ("alto", ~bajo)):
        for v, cod in (("a_favor", 0), ("en_contra", 1)):
            estratos[("waf_x_viento_pendiente", f"{w}|{v}")] = (mw & (vp_pred == cod),
                                                                mw & (vp_obs == cod))
    filas = []
    for (dim, nom), (ep, eo) in estratos.items():
        c = cuentas(sec, pred, ref, ep, eo)
        filas.append(base | {"dimension": dim, "estrato": nom} | c
                     | {"exceso": exceso(c["n_pred"], c["lados_pred"], c["n_obs"], c["lados_obs"])})
    return filas


def reinicios(incendio: str) -> list[dict]:
    cid = f"{incendio}/pronostico-v6"
    if incendio not in {i.split("/")[0] for i in de.casos_calibracion()}:
        raise ValueError(f"{incendio} no es de calibración")
    caso = d.Caso.cargar(cid)
    man = de._manifiesto(cid, de.RECETA_P24)
    paq = caso.paquete()
    cic = cadena._leer(paq["comunes"]["cicatriz.tif"]).astype(bool)
    exc = cadena._leer(paq["comunes"]["excluido.tif"]).astype(bool)
    oficial = json.loads((d.ruta_iteracion(cid, de.RECETA_P24) / "pronostico.json").read_text())
    filas = []
    for v, w in zip(caso.ventanas, man["ventanas"]):
        if w["n"] < 1:
            continue
        ins = w["insumos"]
        semilla = cadena._leer(ins["phi.tif"]) < 0
        horas = p.horas_relativas(cadena._leer(cadena._toa(w["salidas"])), v.tstart_s)
        vistas = cadena._leer(paq["ventanas"][w["n"]]["vistas_horas.tif"]).astype("float64")
        cc = cadena._leer(ins["cc.tif"]).astype("float64")
        ch = cadena._leer(ins["ch.tif"]).astype("float64") / 10
        fbfm = cadena._leer(ins["fbfm40.tif"]).astype(int)
        est = {"waf": waf_celdas(cc, ch, fbfm, profundidades(ins["fuel_models.csv"]))}
        slp = cadena._leer(ins["slp.tif"]).astype("float64")
        asp = cadena._leer(ins["asp.tif"]).astype("float64")
        with rasterio.open(almacen.abrir(ins["wd.tif"])) as s:
            wd = s.read().astype("float64") % 360
        fuera = (semilla & ~cic).sum() / max(semilla.sum(), 1)
        for plazo in PLAZOS_H:
            dice_oficial = oficial[w["n"]]["plazos"][str(plazo)]["p24"]["cicatriz"]["dice"]
            for f in reinicio(semilla, horas, vistas, cic, exc, plazo, v.tstart_s, est, wd,
                              slp, asp):
                filas.append({"incendio": incendio, "k": w["n"], "frac_semilla_fuera": fuera,
                              "dice_oficial": dice_oficial} | f)
        print(incendio, w["n"], flush=True)
    return filas


# ── resumen y veredicto ───────────────────────────────────────────────────────────────────

def resumir(df: pd.DataFrame) -> pd.DataFrame:
    """Por plazo, incendio (y TODOS), dimensión y estrato: mediana del exceso por reinicio
    (principal) y exceso con las celdas sumadas sobre los mismos reinicios (secundario)."""
    filas = []
    for (plazo, dim, nom), g in df[df["dimension"].notna()].groupby(
            ["plazo_h", "dimension", "estrato"], sort=False):
        for inc, h in [*g.groupby("incendio"), ("TODOS", g)]:
            u = h[h["exceso"].notna()]
            s = u[["n_pred", "lados_pred", "n_obs", "lados_obs", "fn"]].sum()
            filas.append({
                "plazo_h": plazo, "incendio": inc, "dimension": dim, "estrato": nom,
                "n_reinicios": len(u), "mediana_exceso": u["exceso"].median(),
                "reinicios_exceso_pos": int((u["exceso"] > 0).sum()),
                "mediana_lados_pred": (u["lados_pred"] / u["n_pred"]).median(),
                "mediana_lados_obs": (u["lados_obs"] / u["n_obs"]).median(),
                "exceso_sumado": exceso(*s[["n_pred", "lados_pred", "n_obs", "lados_obs"]]),
                "n_pred": int(s["n_pred"]), "n_obs": int(s["n_obs"]),
                "tasa_fn": s["fn"] / s["n_obs"] if s["n_obs"] else math.nan})
    return pd.DataFrame(filas)


def veredictos(res: pd.DataFrame) -> pd.DataFrame:
    filas = []
    t = res[res["incendio"] == "TODOS"].set_index(["plazo_h", "dimension", "estrato"])
    for plazo in PLAZOS_H:
        for col in ("mediana_exceso", "exceso_sumado"):
            e = {k: t.loc[(plazo, dim, k), col]
                 for dim, k in (("waf", "bajo"), ("waf", "alto"),
                                ("semilla", "fuera"), ("semilla", "dentro"))}
            filas.append({"plazo_h": plazo, "estadistico": col, "exceso_waf_bajo": e["bajo"],
                          "exceso_waf_alto": e["alto"], "exceso_semilla_fuera": e["fuera"],
                          "exceso_semilla_dentro": e["dentro"],
                          "razon_waf": e["bajo"] / e["alto"] if e["alto"] else math.nan,
                          "veredicto": veredicto(e["bajo"], e["alto"], e["fuera"], e["dentro"])})
    return pd.DataFrame(filas)


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    incendios = sorted({i.split("/")[0] for i in de.casos_calibracion()
                        if i not in de.particion()["limites"]})
    df = pd.DataFrame([f for i in incendios for f in reinicios(i)])
    todo = df[df["dimension"] == "todo"]
    dif = (todo["dice"] - todo["dice_oficial"]).abs()
    print(f"control contra pronostico.json: {int((dif > 1e-9).sum())} de {len(todo)} difieren")
    df.to_csv(SALIDA / "I_isotropia_por_reinicio.csv", index=False)
    res = resumir(df)
    res.to_csv(SALIDA / "I_isotropia_resumen.csv", index=False)
    ver = veredictos(res)
    ver.to_csv(SALIDA / "I_isotropia_veredicto.csv", index=False)
    print(ver.to_string())


if __name__ == "__main__":
    main()
