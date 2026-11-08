"""Frente 1 del diagnóstico e2e (fase 3): corregir el método de medición, SIN correr ELMFIRE.

Diseño registrado en docs/resultados/pronostico/precision.md:

(a) Dice de las recetas completas sobre los 7 casos v6 de calibración, con la métrica oficial y con
    la variante corregida: se excluyen SÓLO las islas no vistas (relleno de la cicatriz final sin
    truncar, menos la cicatriz, menos lo visto); el resto se puntúa como en la oficial. Control:
    la oficial reproduce `metricas.json`. La primera lectura del diseño ("sólo dentro de vistas ∪
    cicatriz") fue descartada por la revisión (premia sobre-propagar) y queda en una tabla aparte.
(b) P-24: ΔDice mediano contra la cadena y la persistencia a 12 y 24 h, con y sin el anillo
    "ya visto" en la referencia de crecimiento. Control: sin corrección reproduce
    data/benchmark/p24/tabla-pronostico*-v6.md.

El conjunto de prueba sólo se re-puntúa para informar (tabla aparte); no decide nada.

    uv run python scripts/diagnostico_metrica.py

Escribe benchmarks/diagnosticos/e2e/datos/P3_f1*.csv. Las funciones puras se prueban en
tests/test_diagnostico_metrica.py.
"""
import re
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio.features

from app.elmfire.builder.perimeter_reconstruction import VIIRS_PIXEL_M
from app.validation import almacen, cadena, pronostico
from app.validation import definiciones as d
from app.validation import puntuacion as p
from scripts import benchmark as bm
from scripts import diagnostico_error as de

SALIDA = Path("benchmarks/diagnosticos/e2e/datos")
INCENDIOS_P24 = ("los-alerces-2023", "epuyen-2025", "los-alerces-2024", "puerto-patriada-2026",
                 "los-alerces-2016", "cholila-2015")
RECETA_P24 = "lw-100-obs-001"
TABLAS_P24 = {"firms": "data/benchmark/p24/tabla-pronostico-v6.md",
              "oraculo": "data/benchmark/p24/tabla-pronostico-oraculo-v6.md"}


# ── funciones puras ───────────────────────────────────────────────────────────────────────

def rellenar_huecos(mascara: np.ndarray) -> np.ndarray:
    """Relleno de huecos con fondo 4-conexo: lo que no es máscara y no llega al borde de la
    grilla. Sin scipy: se poligoniza el fondo y se descartan las regiones que tocan el borde."""
    fondo = ~mascara
    alto, ancho = mascara.shape
    huecos = []
    for g, _ in rasterio.features.shapes(fondo.astype("uint8"), mask=fondo, connectivity=4):
        xy = np.array(g["coordinates"][0])
        if xy.min() > 0 and xy[:, 0].max() < ancho and xy[:, 1].max() < alto:
            huecos.append((g, 1))
    if not huecos:
        return mascara.copy()
    return mascara | rasterio.features.rasterize(
        huecos, out_shape=mascara.shape, dtype="uint8").astype(bool)


def islas_no_vistas(cicatriz_final: np.ndarray, vistas: np.ndarray) -> np.ndarray:
    """Huecos del interior de la cicatriz FINAL (sin truncar) que no son cicatriz y que VIIRS no
    vio: celdas donde la referencia truncada no puede decir nada y un modelo que quema el
    interior recibe falsos positivos sin acierto posible."""
    return rellenar_huecos(cicatriz_final) & ~cicatriz_final & ~vistas


def excluido_corregido(excluido: np.ndarray, cicatriz_final: np.ndarray,
                       vistas: np.ndarray) -> np.ndarray:
    """Variante (a), con la enmienda de la revisión: se suman a lo excluido SÓLO las islas no
    vistas; todo lo demás (incluidos los falsos positivos lejos del fuego) se puntúa igual."""
    return excluido | islas_no_vistas(cicatriz_final, vistas)


def excluido_descartado(excluido: np.ndarray, cicatriz_final: np.ndarray,
                        vistas: np.ndarray) -> np.ndarray:
    """Primera lectura del diseño ("sólo dentro de vistas ∪ cicatriz"), DESCARTADA por la
    revisión: excluye todo falso positivo lejos del fuego y premia sobre-propagar."""
    return excluido | ~(vistas | cicatriz_final)


def excluido_estricto(excluido: np.ndarray, semilla: np.ndarray,
                      vistas_h: np.ndarray) -> np.ndarray:
    """Variante (b): quita de la referencia de crecimiento lo que ya estaba visto al reiniciar
    (`vistas_h <= 0`) y no es semilla; es el anillo que `pronostico.puntuar` cuenta como acierto."""
    return excluido | ((vistas_h <= 0) & ~semilla)


def puesto(valores: dict[str, float]) -> dict[str, int]:
    """Puesto 1 = mayor valor."""
    orden = sorted(valores, key=lambda k: -valores[k])
    return {k: i + 1 for i, k in enumerate(orden)}


def resumen_recetas(filas: pd.DataFrame, variante: str = "corregido") -> pd.DataFrame:
    """Por receta: media y mediana del Dice entre incendios, oficial y de la `variante`, y el
    puesto de cada receta por la media (y por la mediana) con cada métrica."""
    col = f"dice_{variante}"
    r = filas.groupby("receta").agg(
        dice_medio_oficial=("dice_oficial", "mean"),
        dice_mediana_oficial=("dice_oficial", "median"),
        **{f"dice_medio_{variante}": (col, "mean"), f"dice_mediana_{variante}": (col, "median")},
        n=("caso", "nunique"))
    for estad in ("medio", "mediana"):
        for var in ("oficial", variante):
            r[f"puesto_{estad}_{var}"] = pd.Series(puesto(r[f"dice_{estad}_{var}"].to_dict()))
    return r.reset_index().sort_values("dice_medio_oficial", ascending=False)


def leer_control_p24(texto: str) -> dict[tuple[str, int], tuple[float, int]]:
    """{(contra, plazo): (mediana ΔDice, incendios que mejoran)} de una tabla de P-24."""
    patron = re.compile(r"P-24 contra (\w+), (\d+) h \(k ≥ 1\): mediana ΔDice (-?[\d.]+), "
                        r"mejora en (\d+) de")
    return {(m[1], int(m[2])): (float(m[3]), int(m[4])) for m in patron.finditer(texto)}


# ── frente 1 (a) ──────────────────────────────────────────────────────────────────────────

def recetas_completas(casos: list[str]) -> list[str]:
    """Recetas con manifiesto y métricas en TODOS los casos dados (ESTADO-RESEARCH §3: cinco)."""
    por_caso = []
    for cid in casos:
        carpeta = d.ruta_iteracion(cid, "x").parent
        por_caso.append({r.name for r in carpeta.iterdir() if (r / "metricas.json").exists()})
    return sorted(set.intersection(*por_caso))


def contexto(cid: str) -> dict:
    """Cicatriz final, excluido y vistas (r = 375 m) del caso, tal como las arma el empaquetado."""
    caso = d.Caso.cargar(cid)
    paq = caso.paquete()
    com = paq["comunes"]
    arch = com | paq["ventanas"][-1]
    grilla = p.Grilla(almacen.abrir(com["dem.tif"]))
    ref = caso.datos["referencias"]["cicatriz"]
    pos, _ = p.cargar_cicatriz(Path(ref["run"]), grilla,
                               tuple(ref.get("excluidas", p.EXCLUIDAS_POR_DEFECTO)))
    df = pd.read_csv(almacen.abrir(com["firms.csv"]), parse_dates=["acq_datetime"])
    vistas = bm._discos(bm._puntos(df, None, caso.ventanas[-1].fin), grilla, VIIRS_PIXEL_M)
    cic = cadena._leer(arch["cicatriz.tif"]).astype(bool)
    # el empaquetado trunca a vistas sólo con `hasta_horizonte`
    esperada = pos & vistas if ref.get("hasta_horizonte") else pos
    return {"id": cid, "celda_ha": grilla.celda_ha, "pos": pos, "vistas": vistas, "cic": cic,
            "exc": cadena._leer(arch["excluido.tif"]).astype(bool),
            "dif_cicatriz_empaquetada": int((esperada != cic).sum()),
            "hasta_horizonte": bool(ref.get("hasta_horizonte"))}


def pred_final(man: dict) -> tuple[np.ndarray, np.ndarray]:
    """(lo quemado al final de la cadena, semilla del caso), como en `cadena.puntuar`."""
    semilla_caso = cadena._leer(man["ventanas"][0]["insumos"]["phi.tif"]) < 0
    ult = man["ventanas"][-1]
    quemado = (cadena._leer(ult["insumos"]["phi.tif"]) < 0) | (cadena._leer(cadena._toa(
        ult["salidas"])) > 0)
    return quemado, semilla_caso


def _manifiesto(caso_id: str, receta: str) -> dict:
    man = d.cargar_manifiesto(caso_id, receta)
    if man is None:
        raise FileNotFoundError(f"{caso_id}/{receta} no corrió")
    return man


def puntuar_receta(ctx: dict, receta: str) -> dict | None:
    man = d.cargar_manifiesto(ctx["id"], receta)
    if man is None:
        return None
    quemado, semilla = pred_final(man)
    pred, ref = quemado & ~semilla, ctx["cic"] & ~semilla
    exc_co = excluido_corregido(ctx["exc"], ctx["pos"], ctx["vistas"])
    exc_de = excluido_descartado(ctx["exc"], ctx["pos"], ctx["vistas"])
    of = p.metricas(pred, ref, ctx["celda_ha"], ctx["exc"])
    co = p.metricas(pred, ref, ctx["celda_ha"], exc_co)
    de_ = p.metricas(pred, ref, ctx["celda_ha"], exc_de)
    guardada = ((d.cargar_metricas(ctx["id"], receta) or {}).get("principal") or {}).get("dice")
    return {"caso": ctx["id"], "receta": receta, "dice_metricas_json": guardada,
            "dice_oficial": of["dice"], "dice_corregido": co["dice"],
            "dice_descartada": de_["dice"],
            "islas_no_vistas_ha": float((exc_co & ~ctx["exc"]).sum() * ctx["celda_ha"]),
            "sesgo_oficial": of["sesgo_area"], "sesgo_corregido": co["sesgo_area"],
            "precision_oficial": of["precision"], "precision_corregida": co["precision"],
            "recall_oficial": of["recall"], "recall_corregido": co["recall"],
            "fp_ha_quitados": of["fp_ha"] - co["fp_ha"],
            "dominio_oficial_ha": float((~ctx["exc"]).sum() * ctx["celda_ha"]),
            "dominio_corregido_ha": float((~exc_co).sum() * ctx["celda_ha"]),
            "dominio_descartada_ha": float((~exc_de).sum() * ctx["celda_ha"]),
            "dif_cicatriz_empaquetada": ctx["dif_cicatriz_empaquetada"]}


def frente_1a() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    casos = de.casos_calibracion()
    recetas = recetas_completas(casos)
    print("recetas completas:", recetas, flush=True)
    filas = []
    for cid in casos:
        ctx = contexto(cid)
        filas += [f for r in recetas if (f := puntuar_receta(ctx, r))]
        print(cid, flush=True)
        del ctx
    cal = pd.DataFrame(filas)
    cal["incendio"] = cal["caso"].str.split("/").str[0]
    cal["control_ok"] = (cal["dice_oficial"] - cal["dice_metricas_json"]).abs() < 1e-9
    # prueba: sólo informativo, con las recetas que tengan corrida en cada caso
    part = de.particion()["prueba"]
    prueba = []
    for cid in part["gfs"] + part["era5"]:
        ctx = contexto(cid)
        prueba += [f for r in recetas if (f := puntuar_receta(ctx, r))]
        del ctx
    pr = pd.DataFrame(prueba)
    pr["incendio"] = pr["caso"].str.split("/").str[0]
    pr["etiqueta"] = "prueba: sólo informativo"
    return cal, resumen_recetas(cal), pr


# ── frente 1 (b) ──────────────────────────────────────────────────────────────────────────

def filas_p24(protocolo: str) -> dict[str, list[dict]]:
    """Por variante ('con_anillo' = actual, 'sin_anillo' = estricta), las filas de P-24 por
    reinicio y plazo para `pronostico.resumir`, re-puntuando salidas guardadas."""
    filas: dict[str, dict] = {"con_anillo": {}, "sin_anillo": {}}
    for inc in INCENDIOS_P24:
        caso = d.Caso.cargar(f"{inc}/{protocolo}")
        man = _manifiesto(caso.id, RECETA_P24)
        paq = caso.paquete()
        cad = caso.datos["cadena"]
        cadena_v0 = bm._ventanas_cadena(cad["caso"], cad["receta"])
        grilla = p.Grilla(almacen.abrir(paq["comunes"]["dem.tif"]))
        cic = cadena._leer(paq["comunes"]["cicatriz.tif"]).astype(bool)
        exc = cadena._leer(paq["comunes"]["excluido.tif"]).astype(bool)
        previa = None
        for v, w in zip(caso.ventanas, man["ventanas"]):
            a = paq["ventanas"][w["n"]]
            semilla = cadena._leer(w["insumos"]["phi.tif"]) < 0
            horas = np.nan_to_num(p.horas_relativas(cadena._leer(cadena._toa(w["salidas"])),
                                                    v.tstart_s), nan=np.inf)
            vistas = cadena._leer(a["vistas_horas.tif"])
            det = cadena._leer(a["ref_firms_horas.tif"])
            for plazo in caso.datos["plazos"]:
                preds = {"p24": horas <= plazo,
                         "cadena": pronostico.quemado_en(cadena_v0, v.inicio + timedelta(
                             hours=plazo))}
                if previa is not None:
                    preds["persistencia"] = pronostico.persistencia(
                        semilla, previa[1], (v.inicio - previa[0]).total_seconds() / 3600, plazo,
                        grilla)
                for var, ex in (("con_anillo", exc),
                                ("sin_anillo", excluido_estricto(exc, semilla, vistas))):
                    f = filas[var].setdefault((inc, w["n"]), {"incendio": inc, "n": w["n"],
                                                              "plazos": {}})
                    f["plazos"][str(plazo)] = {k: pronostico.puntuar(
                        pr, semilla, cic, ex, vistas, det, plazo, grilla.celda_ha)
                        for k, pr in preds.items()}
            previa = (v.inicio, semilla)
        print(caso.id, flush=True)
    return {var: list(f.values()) for var, f in filas.items()}


def frente_1b() -> tuple[pd.DataFrame, pd.DataFrame]:
    resumen, por_incendio = [], []
    for semilla, protocolo in (("firms", "pronostico-v6"), ("oraculo", "pronostico-oraculo-v6")):
        control = leer_control_p24(Path(TABLAS_P24[semilla]).read_text())
        for var, filas in filas_p24(protocolo).items():
            for contra in ("cadena", "persistencia"):
                for plazo in (12, 24):
                    r = pronostico.resumir(filas, plazo, contra)
                    esperado = control[(contra, plazo)]
                    resumen.append({
                        "semilla": semilla, "referencia": var, "contra": contra, "plazo_h": plazo,
                        "mediana_delta": r["mediana_delta"], "mejoran": r["mejoran"], "n": r["n"],
                        "control_tabla_delta": esperado[0], "control_tabla_mejoran": esperado[1],
                        "control_ok": (round(r["mediana_delta"], 3) == esperado[0]
                                       and r["mejoran"] == esperado[1])
                        if var == "con_anillo" else None})
                    por_incendio += [{
                        "semilla": semilla, "referencia": var, "contra": contra, "plazo_h": plazo,
                        "incendio": inc, "dice_p24": m["p24"], "dice_contra": m[contra],
                        "delta": m["p24"] - m[contra]} for inc, m in r["incendios"].items()]
    return pd.DataFrame(resumen), pd.DataFrame(por_incendio)


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    cal, res, prueba = frente_1a()
    desc = cal[["caso", "receta", "dice_oficial", "dice_descartada", "dominio_descartada_ha"]]
    desc = desc.assign(etiqueta="variante descartada por la revisión (premia sobre-propagar)")
    desc.to_csv(SALIDA / "P3_f1a_variante_descartada_por_incendio.csv", index=False)
    resumen_recetas(cal, "descartada").assign(etiqueta=desc["etiqueta"].iloc[0]).to_csv(
        SALIDA / "P3_f1a_variante_descartada_resumen.csv", index=False)
    cal = cal.drop(columns=["dice_descartada", "dominio_descartada_ha"])
    cal.to_csv(SALIDA / "P3_f1a_dice_por_incendio.csv", index=False)
    res.to_csv(SALIDA / "P3_f1a_resumen_recetas.csv", index=False)
    prueba.to_csv(SALIDA / "P3_f1a_prueba_solo_informativo.csv", index=False)
    resumen, por_incendio = frente_1b()
    resumen.to_csv(SALIDA / "P3_f1b_p24_resumen.csv", index=False)
    por_incendio.to_csv(SALIDA / "P3_f1b_p24_por_incendio.csv", index=False)
    print(res.to_string())
    print(resumen.to_string())


if __name__ == "__main__":
    main()
