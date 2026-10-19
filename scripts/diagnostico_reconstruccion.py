"""Cota sin ELMFIRE de cambiar la reconstrucción de la semilla de P-24 (tarea U).

Decisión 2 de docs/resultados/DIAGNOSTICO-PRECISION-E2E.md §6. Diseño y criterios, fijados antes de
correr, en docs/resultados/diagnostico-e2e/notas/U-reconstruccion-semilla.md. Tres reglas de tiempo
real (sin la cicatriz) sobre las detecciones conexas de T: la reconstrucción actual, sólo las
huellas scan × track y el casco sin buffer más las huellas. Cada una se puntúa en dos extremos: el
frente sin cambio (pesimista) y el recorte de Voronoi de T (optimista).

    uv run python -m scripts.diagnostico_reconstruccion

Escribe docs/resultados/diagnostico-e2e/datos/U_*.csv. Sólo incendios de calibración.
"""
import math
from datetime import timedelta

import numpy as np
import pandas as pd
import shapely

from app.validation import cadena, pronostico
from app.validation import definiciones as d
from app.validation import puntuacion as p
from scripts import diagnostico_error as de
from scripts import diagnostico_isotropia as di
from scripts import diagnostico_semilla as ds
from scripts.benchmark import _ventanas_cadena

SALIDA = ds.SALIDA
SALTO_M = 3000.0   # la regla conexa de T: idéntica al oráculo de 2000 m
VARIANTES = ("conexa", "huellas", "nucleo_huellas")
UMBRAL = 0.02


def semilla_variante(nombre: str, casco, nucleo, huellas: list, forma, transform) -> np.ndarray:
    """La reconstrucción de una variante (sin la recursión ni la ignición)."""
    geoms = {"conexa": [casco], "huellas": huellas, "nucleo_huellas": [nucleo, *huellas]}[nombre]
    return ds.rasterizar(geoms, forma, transform)


def retrasar(horas: np.ndarray, s0: np.ndarray, sf: np.ndarray, plazo: float,
             celda_m: float) -> np.ndarray:
    """Estimación intermedia (post hoc): lo que brota de un borde de `s0` que la variante saca
    llega tarde lo que tarda el frente en cruzar lo sacado (distancia del borde a `sf`) a la
    velocidad mediana del reinicio; lo sacado mismo arde cuando el frente lo alcanza.
    ponytail: una velocidad por reinicio y Voronoi sobre el borde; la corrida exacta es ELMFIRE."""
    if not (s0 & ~sf).any() or not sf.any():
        return horas <= plazo
    crece = np.argwhere(np.isfinite(horas) & ~s0)
    if not len(crece):
        return sf.copy()
    borde = ds._borde(s0)
    _, cerca = shapely.STRtree(shapely.points(borde)).query_nearest(
        shapely.points(crece), all_matches=False)
    d_m = np.hypot(*(crece - borde[cerca]).T) * celda_m
    h = horas[crece[:, 0], crece[:, 1]]
    v_m_h = np.median(d_m[h > 0] / h[h > 0])
    retraso = ds.distancia_m(borde, sf, celda_m) / v_m_h
    retraso[sf[borde[:, 0], borde[:, 1]]] = 0.0
    salida = sf.copy()
    llega = h + retraso[cerca] <= plazo
    salida[crece[llega, 0], crece[llega, 1]] = True
    sacado = np.argwhere(s0 & ~sf)
    alcanzado = ds.distancia_m(sacado, sf, celda_m) / v_m_h <= plazo
    salida[sacado[alcanzado, 0], sacado[alcanzado, 1]] = True
    return salida


def borde_inactivo(s0: np.ndarray, det_fc: np.ndarray, celda_m: float) -> np.ndarray:
    """Las celdas del borde de `s0` a más de un píxel VIIRS de toda detección de la última pasada
    (`det_fc`: fila, columna relativas a centros de celda)."""
    borde = ds._borde(s0)
    lejos = np.full(len(borde), np.inf) if not len(det_fc) else \
        shapely.STRtree(shapely.points(det_fc)).query_nearest(
            shapely.points(borde), return_distance=True, all_matches=False)[1] * celda_m
    out = np.zeros_like(s0)
    sel = lejos > ds.LEJOS_M
    out[borde[sel, 0], borde[sel, 1]] = True
    return out


def exceso_flancos(pred, semilla, cic, exc, vistas, plazo) -> float:
    """El exceso de flanco + retroceso de I (todo el crecimiento), con la semilla dada."""
    excl = exc | ((vistas <= 0) & ~semilla) | semilla | (cic & ~(vistas <= plazo))
    ref, pr = cic & (vistas <= plazo) & ~excl, pred & ~excl
    if ref.sum() < di.MIN_CELDAS:
        return math.nan
    sec = di.sectores(semilla, pr | ref, de.eje(semilla, ref, 1.0)[0])
    todo = np.ones_like(pr)
    c = di.cuentas(sec, pr, ref, todo, todo)
    return di.exceso(c["n_pred"], c["lados_pred"], c["n_obs"], c["lados_obs"])


def reinicios(cid: str) -> list[dict]:
    c = ds.cargar(cid)
    caso, g, df = c["caso"], c["grilla"], c["df"]
    man = d.cargar_manifiesto(caso.id, ds.RECETA)
    cad = _ventanas_cadena(caso.datos["cadena"]["caso"], caso.datos["cadena"]["receta"])
    cic = cadena._leer(c["paq"]["comunes"]["cicatriz.tif"]).astype(bool)
    exc = cadena._leer(c["paq"]["comunes"]["excluido.tif"]).astype(bool)
    xy, scan, track = df[["x", "y"]].to_numpy(), df["scan"].to_numpy(), df["track"].to_numpy()
    previos = {v: c["ignicion"] for v in VARIANTES}
    filas = []
    for v, w in zip(caso.ventanas, man["ventanas"]):
        if w["n"] < 1:
            continue
        s0 = cadena._leer(w["insumos"]["phi.tif"]) < 0
        sel = (df["acq_datetime"] <= v.inicio).to_numpy()
        usa = ds.conexas(xy[sel], c["ign_xy"], SALTO_M)
        casco, nucleo = ds.reconstruir(xy[sel][usa])
        hue = ds.huellas(xy[sel][usa], scan[sel][usa], track[sel][usa])
        arch = c["paq"]["ventanas"][w["n"]]
        vistas = cadena._leer(arch["vistas_horas.tif"]).astype("float64")
        det = cadena._leer(arch["ref_firms_horas.tif"])
        horas = np.nan_to_num(p.horas_relativas(cadena._leer(cadena._toa(w["salidas"])),
                                                v.tstart_s), nan=np.inf)
        semillas = {"actual": s0}
        for nom in VARIANTES:
            previos[nom] = previos[nom] | c["ignicion"] | semilla_variante(
                nom, casco, nucleo, hue, g.shape, g.transform)
            semillas[nom] = previos[nom]
        for nom, sf in semillas.items():
            sf_ef = sf & s0
            base = {"incendio": caso.incendio, "k": w["n"], "variante": nom,
                    "semilla_ha": sf_ef.sum() * g.celda_ha,
                    "fuera_de_la_usada_ha": (sf & ~s0).sum() * g.celda_ha,
                    "semilla_fuera_cicatriz": float((sf_ef & ~cic).sum() / max(sf_ef.sum(), 1))}
            for plazo in pronostico.PLAZOS_H:
                quemado_cad = pronostico.quemado_en(cad, v.inicio + timedelta(hours=plazo))
                dice_cad = pronostico.puntuar(quemado_cad, sf_ef, cic, exc, vistas, det, plazo,
                                              g.celda_ha)["cicatriz"]["dice"]
                todo_q = horas <= plazo
                vor = ds.recortar_prediccion(todo_q, s0, sf_ef)
                # cota superior (post hoc, con la cicatriz): de lo que Voronoi saca, sólo lo FP
                oraculo = todo_q & ~(todo_q & ~vor & ~cic)
                retraso = retrasar(horas, s0, sf_ef, plazo, c["celda_m"])
                for ext, pred in (("sin_cambio", todo_q), ("voronoi", vor),
                                  ("oraculo", oraculo), ("retraso", retraso)):
                    m = pronostico.puntuar(pred, sf_ef, cic, exc, vistas, det, plazo,
                                           g.celda_ha)["cicatriz"]
                    filas.append(base | {"plazo_h": plazo, "extremo": ext, "dice": m["dice"],
                                         "sesgo": m["sesgo_area"], "dice_cadena": dice_cad,
                                         "exceso_flancos": exceso_flancos(
                                             pred & ~sf_ef, sf_ef, cic, exc, vistas, plazo)})
        # agregado 2: sólo crece el borde activo (Voronoi sobre el borde, semilla intacta)
        ultima = ((df["acq_datetime"] <= v.inicio) & (df["acq_datetime"] > v.inicio - timedelta(
            hours=pronostico.SEPARACION_PASADAS_H))).to_numpy()
        cols, fil = ~g.transform * (xy[ultima, 0], xy[ultima, 1])
        inactivo = borde_inactivo(s0, np.column_stack([fil - 0.5, cols - 0.5]), c["celda_m"])
        base = {"incendio": caso.incendio, "k": w["n"], "variante": "frente_activo",
                "semilla_ha": s0.sum() * g.celda_ha,
                "borde_activo": 1 - inactivo.sum() / max(len(ds._borde(s0)), 1)}
        for plazo in pronostico.PLAZOS_H:
            pred = ds.recortar_prediccion(horas <= plazo, s0, s0 & ~inactivo)
            m = pronostico.puntuar(pred, s0, cic, exc, vistas, det, plazo, g.celda_ha)["cicatriz"]
            dice_cad = next(f["dice_cadena"] for f in filas if f["k"] == w["n"]
                            and f["variante"] == "actual" and f["plazo_h"] == plazo)
            filas.append(base | {"plazo_h": plazo, "extremo": "voronoi", "dice": m["dice"],
                                 "sesgo": m["sesgo_area"], "dice_cadena": dice_cad,
                                 "exceso_flancos": exceso_flancos(pred & ~s0, s0, cic, exc,
                                                                  vistas, plazo)})
        print(cid, w["n"], flush=True)
    return filas


def resumir(df: pd.DataFrame) -> pd.DataFrame:
    """Por variante, extremo y plazo: Dice medio por incendio, ΔDice mediano contra `conexa` y
    contra la cadena (como `pronostico.resumir`), y la mediana del exceso de flancos."""
    ok = df[df["dice"].notna() & df["dice_cadena"].notna()]
    media = ok.groupby(["variante", "extremo", "plazo_h", "incendio"])[
        ["dice", "dice_cadena"]].mean()
    ref = media.xs("conexa", level="variante")["dice"]
    act = media.xs(("actual", "sin_cambio"), level=["variante", "extremo"])["dice"]
    filas = []
    for (var, ext, plazo), g in media.groupby(level=["variante", "extremo", "plazo_h"]):
        g = g.droplevel(["variante", "extremo", "plazo_h"])
        dc = g["dice"] - ref.loc[(ext, plazo)]
        da = g["dice"] - act.loc[plazo]
        dcad = g["dice"] - g["dice_cadena"]
        exc_f = df[(df["variante"] == var) & (df["extremo"] == ext) & (df["plazo_h"] == plazo)]
        filas.append({"variante": var, "extremo": ext, "plazo_h": plazo,
                      "mediana_delta_vs_conexa": dc.median(),
                      "mejoran_vs_conexa": int((dc > 0).sum()),
                      "peor_delta_vs_conexa": dc.min(),
                      "mediana_delta_vs_actual": da.median(),
                      "mejoran_vs_actual": int((da > 0).sum()),
                      "mediana_delta_vs_cadena": dcad.median(),
                      "ganan_a_cadena": int((dcad > 0).sum()),
                      "mediana_exceso_flancos": exc_f["exceso_flancos"].median(),
                      "semilla_fuera_cicatriz_mediana": exc_f["semilla_fuera_cicatriz"].median(),
                      **{f"dice_{i}": x for i, x in g["dice"].items()}})
    return pd.DataFrame(filas)


def veredicto(res: pd.DataFrame) -> str:
    """Criterio de cierre registrado: en el extremo optimista, ninguna variante llega a +0,02."""
    opt = res[(res["extremo"] == "voronoi") & res["variante"].isin(["huellas", "nucleo_huellas"])]
    pasan = opt[opt["mediana_delta_vs_conexa"] >= UMBRAL]
    if pasan.empty:
        return "cierra: se mantiene la reconstrucción (con el filtro conexo de T)"
    return "propone corrida exacta de: " + ", ".join(sorted(set(pasan["variante"])))


def main() -> None:
    df = pd.DataFrame([f for cid in ds.casos_calibracion() for f in reinicios(cid)])
    df.to_csv(SALIDA / "U_reconstruccion_por_reinicio.csv", index=False)
    res = resumir(df)
    res.to_csv(SALIDA / "U_reconstruccion_resumen.csv", index=False)
    print(res.drop(columns=[c for c in res if c.startswith("dice_")]).round(3).to_string())
    print(veredicto(res))


if __name__ == "__main__":
    main()
