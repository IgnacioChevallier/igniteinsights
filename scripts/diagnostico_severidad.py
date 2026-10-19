"""Frente 2 del diagnóstico e2e (fase 3): ¿hubo copa en el bosque el día 1?, SIN Earth Engine
ni ELMFIRE. La severidad dNBR sale de los PRE/POST ya guardados por mask-dataset-gen (sólo lectura).

Diseño registrado en docs/resultados/DIAGNOSTICO-PRECISION-E2E.md §3 (frente 2) y §4:

- dNBR de las celdas de bosque con dosel (fbfm40 TU3, TU5, TL2, TL6, TL8 del mapa de la receta
  `lw-100-001`, cc > 0) dentro de los discos (r = 187,5 m) de las detecciones VIIRS hasta la
  primera pasada + 24 h ("día 1"), contra las del resto del incendio ("días siguientes") y contra
  SH4 (control).
- Fracción con dNBR >= 0,66 (Key y Benson 2006).
- Criterio: hay "evidencia de copa en el día 1" si en Patriada 2026 y Alerces 2024 la fracción
  del día 1 es >= 0,5 y >= 1,5 veces la de los días siguientes.
- Veredicto de tres salidas (enmienda registrada por la revisión antes de ver resultados): SÍ si
  se cumple el criterio en los dos incendios; INDISCRIMINADO si la fracción de los días
  siguientes en bosque es > 0,67, o el control SH4 del día 1 da >= 0,8 veces la fracción del
  bosque del día 1, o el dNBR (Landsat/proxy) no es confiable para ese incendio; NO en otro caso.
  Si hay causa de INDISCRIMINADO en alguno de los dos incendios, prevalece sobre SÍ y NO.
- Secundarias descriptivas: RdNBR = dNBR / sqrt(|NBR_pre|) (Miller y Thode 2007) y FRP media de
  VIIRS día 1 contra días siguientes, bosque contra SH4.

Escala: NBR = (B8 - B12) / (B8 + B12) es un cociente, así que el dNBR = NBR_pre - NBR_post queda
en [-2, 2] (escala 0-1, NO x1000); el umbral 0,66 equivale al 660 de Key y Benson. Las imágenes
guardadas son medianas de reflectancia (S2 SR 0-10000, L8 SR reescalado a la misma escala).

    uv run python scripts/diagnostico_severidad.py

Escribe docs/resultados/diagnostico-e2e/datos/P3_f2*.csv. Las funciones puras se prueban en
tests/test_diagnostico_severidad.py.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import rasterio.transform
from pyproj import Transformer
from rasterio.errors import WindowError
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds, transform

from app.validation import almacen, cadena, pronostico
from app.validation import definiciones as d
from app.validation import puntuacion as p
from scripts import benchmark as bm
from scripts import diagnostico_error as de

SALIDA = Path("docs/resultados/diagnostico-e2e/datos")
RECETA = "lw-100-001"
RADIO_M = 187.5
UMBRAL_ALTA = 0.66
CRITERIO_FRACCION, CRITERIO_RAZON = 0.5, 1.5
CRITERIO_INCENDIOS = ("puerto-patriada-2026", "los-alerces-2024")
SIGUIENTES_MAX = 0.67        # sobre esto, 1,5x es imposible (0,67 * 1,5 > 1)
SH4_MIN_RAZON = 0.8          # SH4 día 1 >= 0,8 x bosque día 1 -> no discrimina copa
ESCALA_LANDSAT_M = 30        # los runs Landsat (2015-16): el proxy local no es confiable (D §4)
B8, B12 = 3, 5   # posiciones en las 6 bandas guardadas (B2, B3, B4, B8, B11, B12)
# fbfm40 = 10 * grupo + número (diagnostico_error.GRUPOS): TU = 16x, TL = 18x, SH = 14x
BOSQUE = {163: "TU3", 165: "TU5", 182: "TL2", 186: "TL6", 188: "TL8"}
CONTROL = {144: "SH4"}


# ── funciones puras ───────────────────────────────────────────────────────────────────────

def nbr(banda_nir: np.ndarray, banda_swir: np.ndarray) -> np.ndarray:
    """(NIR - SWIR2) / (NIR + SWIR2); NaN donde no hay dato o la suma no es positiva."""
    s = banda_nir + banda_swir
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.where(np.isfinite(s) & (s > 0), (banda_nir - banda_swir) / s, np.nan)
    return r


def dnbr(pre: np.ndarray, post: np.ndarray) -> np.ndarray:
    """dNBR = NBR_pre - NBR_post de dos pilas (6, f, c) de reflectancia."""
    return nbr(pre[B8], pre[B12]) - nbr(post[B8], post[B12])


def dias(df: pd.DataFrame, horas_dia1: float = 24.0, desde=None) -> tuple:
    """(instante de corte del día 1, primera pasada). Día 1 = hasta la primera pasada + 24 h;
    con `desde` (la ignición) y no None, hasta la ignición + 24 h (variante de sensibilidad)."""
    primera = pronostico.pasadas(df["acq_datetime"])[0]
    base = desde if desde is not None else primera
    return base + pd.Timedelta(hours=horas_dia1), primera


def fraccion(alta: np.ndarray, valido: np.ndarray, region: np.ndarray) -> dict:
    """Celdas válidas de la región, y qué fracción tiene severidad alta."""
    sel = region & valido
    n = int(sel.sum())
    return {"n_celdas": n, "frac_alta": float((alta & sel).sum() / n) if n else None}


def evaluar_criterio(frac_dia1: float | None, frac_sig: float | None) -> bool:
    if frac_dia1 is None or frac_sig is None:
        return False
    return frac_dia1 >= CRITERIO_FRACCION and frac_dia1 >= CRITERIO_RAZON * frac_sig


def motivos_indiscriminado(frac_dia1: float | None, frac_sig: float | None,
                           frac_sh4_dia1: float | None, escala_m: int) -> list[str]:
    """Por qué el criterio no discrimina copa en este incendio (lista vacía = discrimina)."""
    motivos = []
    if frac_sig is not None and frac_sig > SIGUIENTES_MAX:
        motivos.append(f"bosque de los días siguientes {frac_sig:.2f} > {SIGUIENTES_MAX}")
    if frac_sh4_dia1 is not None and frac_dia1 and frac_sh4_dia1 >= SH4_MIN_RAZON * frac_dia1:
        motivos.append(f"SH4 día 1 {frac_sh4_dia1:.2f} >= {SH4_MIN_RAZON} x bosque día 1")
    if escala_m == ESCALA_LANDSAT_M:
        motivos.append("Landsat: dNBR local no confiable")
    return motivos


def veredicto(cumple: list[bool], motivos: list[list[str]]) -> str:
    """SÍ / NO / INDISCRIMINADO sobre los incendios del criterio; lo indiscriminado prevalece."""
    if any(motivos):
        return "INDISCRIMINADO"
    return "SÍ" if all(cumple) else "NO"


def rdnbr(dnbr_: np.ndarray, nbr_pre: np.ndarray) -> np.ndarray:
    """RdNBR = dNBR / sqrt(|NBR_pre|) (Miller y Thode 2007), escala 0-1 (x1000 en la cita);
    NaN donde el NBR previo es 0."""
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(nbr_pre != 0, dnbr_ / np.sqrt(np.abs(nbr_pre)), np.nan)


# ── lectura de dNBR sobre la grilla del caso ──────────────────────────────────────────────

def _ventana(grilla: p.Grilla, src: rasterio.DatasetReader) -> Window | None:
    """La ventana de la grilla que toca el tile (como `Grilla.traer`)."""
    izq, abajo, der, arriba = transform_bounds(src.crs, grilla.crs, *src.bounds)
    v = from_bounds(izq, abajo, der, arriba, grilla.transform).round_offsets().round_lengths()
    try:
        v = v.intersection(Window(0, 0, grilla.shape[1], grilla.shape[0]))
    except WindowError:
        return None
    return v if v.width > 0 and v.height > 0 else None


def traer_dnbr(run_dir: Path, grilla: p.Grilla,
               ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(válido, alta, dnbr medio, RdNBR medio) del run sobre la grilla, con el criterio de la
    cicatriz: la clase (dNBR válido / dNBR >= 0,66) se decide en el píxel de origen y se lleva
    a la grilla con `Resampling.mode`; el dNBR continuo, con `average` (sólo descriptivo)."""
    valido = np.zeros(grilla.shape, dtype=bool)
    alta = np.zeros(grilla.shape, dtype=bool)
    medio = np.full(grilla.shape, np.nan, dtype="float32")
    rd_medio = np.full(grilla.shape, np.nan, dtype="float32")
    for pre_tif in sorted((run_dir / "imagenes_pre").glob("*.tif")):
        post_tif = run_dir / "imagenes_post" / pre_tif.name
        if not post_tif.exists():
            continue
        with rasterio.open(pre_tif) as a, rasterio.open(post_tif) as b:
            v = _ventana(grilla, a)
            if v is None:
                continue
            pre_px, post_px = a.read().astype("float64"), b.read().astype("float64")
            nbr_pre = nbr(pre_px[B8], pre_px[B12])
            dn = (nbr_pre - nbr(post_px[B8], post_px[B12])).astype("float32")
            rd = rdnbr(dn, nbr_pre).astype("float32")
            geo = dict(src_transform=a.transform, src_crs=a.crs,
                       dst_transform=transform(v, grilla.transform), dst_crs=grilla.crs)
            forma = (int(v.height), int(v.width))
            clases = []
            for fuente in (np.isfinite(dn), np.isfinite(dn) & (np.nan_to_num(dn) >= UMBRAL_ALTA)):
                destino = np.zeros(forma, dtype=np.uint8)
                reproject(fuente.astype(np.uint8), destino, resampling=Resampling.mode, **geo)
                clases.append(destino.astype(bool))
            continuo = np.full(forma, np.nan, dtype="float32")
            reproject(dn, continuo, src_nodata=np.nan, dst_nodata=np.nan,
                      resampling=Resampling.average, **geo)
            rd_cont = np.full(forma, np.nan, dtype="float32")
            reproject(rd, rd_cont, src_nodata=np.nan, dst_nodata=np.nan,
                      resampling=Resampling.average, **geo)
        f, c = int(v.row_off), int(v.col_off)
        h, w = forma
        valido[f:f + h, c:c + w] |= clases[0]
        alta[f:f + h, c:c + w] |= clases[1]
        previo = medio[f:f + h, c:c + w]
        medio[f:f + h, c:c + w] = np.where(np.isnan(previo), continuo, previo)
        previo_rd = rd_medio[f:f + h, c:c + w]
        rd_medio[f:f + h, c:c + w] = np.where(np.isnan(previo_rd), rd_cont, previo_rd)
    return valido, alta, medio, rd_medio


# ── el diagnóstico ────────────────────────────────────────────────────────────────────────

def ventanas_dnbr(run_dir: Path) -> dict:
    """Fechas de PRE y POST y escala del run (mask-dataset-gen/.../metadata.csv)."""
    m = pd.read_csv(run_dir / "metadata.csv")
    return {"pre": "; ".join(sorted(m["fecha_pre"].dropna().unique())),
            "post": "; ".join(sorted(m["fecha_post"].dropna().unique())),
            "escala_m": int(m["escala_m"].iloc[0])}


def grupos_combustible(fuel: np.ndarray, cc: np.ndarray) -> dict[str, np.ndarray]:
    """bosque con dosel (cc > 0), cada combustible por separado, y el control SH4 (sin cc)."""
    g = {"bosque": np.isin(fuel, list(BOSQUE)) & (cc > 0)}
    g |= {f"{nombre}": (fuel == cod) & (cc > 0) for cod, nombre in BOSQUE.items()}
    g |= {nombre: fuel == cod for cod, nombre in CONTROL.items()}
    return g


def _q(x: np.ndarray, q: float) -> float | None:
    x = x[np.isfinite(x)]
    return float(np.percentile(x, q)) if x.size else None


def frp_por_periodo(df: pd.DataFrame, grilla: p.Grilla, grupos: dict[str, np.ndarray],
                    corte: pd.Timestamp) -> list[dict]:
    """FRP media (MW) de las detecciones cuyo píxel cae en bosque con dosel o en SH4, antes y
    después del corte del día 1. Descriptivo."""
    tr = Transformer.from_crs("EPSG:4326", str(grilla.crs), always_xy=True)
    x, y = tr.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    f, c = rasterio.transform.rowcol(grilla.transform, x, y)
    f, c = np.asarray(f), np.asarray(c)
    dentro = (f >= 0) & (f < grilla.shape[0]) & (c >= 0) & (c < grilla.shape[1])
    filas = []
    for nombre in ("bosque", "SH4"):
        en = np.zeros(len(df), bool)
        en[dentro] = grupos[nombre][f[dentro], c[dentro]]
        for periodo, sel in (("dia1", df["acq_datetime"] <= corte),
                             ("siguientes", df["acq_datetime"] > corte)):
            frp = df.loc[en & sel.to_numpy(), "frp"].dropna()
            filas.append({"grupo": nombre, "periodo": periodo, "n_detecciones": len(frp),
                          "frp_media_mw": float(frp.mean()) if len(frp) else None,
                          "frp_mediana_mw": float(frp.median()) if len(frp) else None})
    return filas


def incendio(cid: str) -> tuple[list[dict], dict, list[dict]]:
    caso = d.Caso.cargar(cid)
    paq = caso.paquete()
    com = paq["comunes"]
    grilla = p.Grilla(almacen.abrir(com["dem.tif"]))
    ref = caso.datos["referencias"]["cicatriz"]
    run = Path(ref["run"])
    pos, _ = p.cargar_cicatriz(run, grilla, tuple(ref.get("excluidas", p.EXCLUIDAS_POR_DEFECTO)))
    exc = cadena._leer(com["excluido.tif"]).astype(bool)
    man = de._manifiesto(cid, RECETA)
    ins = man["ventanas"][0]["insumos"]
    fuel, cc = cadena._leer(ins["fbfm40.tif"]), cadena._leer(ins["cc.tif"])
    df = pd.read_csv(almacen.abrir(com["firms.csv"]), parse_dates=["acq_datetime"])
    fin = caso.ventanas[-1].fin
    df = df[df["acq_datetime"] <= fin]
    valido, alta, medio, rd_medio = traer_dnbr(run, grilla)
    valido = valido & ~exc
    gr = grupos_combustible(fuel, cc)
    filas = []
    meta = ventanas_dnbr(run) | {"incendio": caso.incendio, "caso": cid,
                                 "primera_pasada": str(dias(df)[1]),
                                 "ignicion": caso.ventanas[0].inicio}
    for definicion, desde in (("primera_pasada+24h", None),
                              ("ignicion+24h (sensibilidad)", caso.ventanas[0].inicio)):
        corte, _ = dias(df, desde=desde)
        d1 = bm._discos(bm._puntos(df, None, corte), grilla, RADIO_M)
        resto = bm._discos(bm._puntos(df[df["acq_datetime"] > corte], None, fin), grilla,
                           RADIO_M) & ~d1
        for variante, filtro in (("todas_las_celdas", np.ones_like(pos)),
                                 ("solo_cicatriz", pos)):
            for periodo, region in (("dia1", d1), ("siguientes", resto)):
                for nombre, g in gr.items():
                    f = fraccion(alta, valido, region & g & filtro)
                    sel = region & g & filtro & valido
                    filas.append({
                        "incendio": caso.incendio, "definicion_dia1": definicion,
                        "celdas": variante, "periodo": periodo, "grupo": nombre,
                        "n_celdas": f["n_celdas"], "area_ha": f["n_celdas"] * grilla.celda_ha,
                        "frac_alta": f["frac_alta"],
                        "dnbr_medio_mediana": _q(medio[sel], 50),
                        "rdnbr_p25": _q(rd_medio[sel], 25), "rdnbr_mediana": _q(rd_medio[sel], 50),
                        "rdnbr_p75": _q(rd_medio[sel], 75),
                        "frac_dnbr_ge_1": float((medio[sel] >= 1.0).sum() / f["n_celdas"])
                        if f["n_celdas"] else None})
    # sanidad: el dNBR guardado separa la cicatriz del resto (en celdas válidas del caso)
    dentro, fuera = valido & pos, valido & ~pos
    meta |= {"dnbr_mediana_cicatriz": float(np.nanmedian(medio[dentro])),
             "dnbr_mediana_fuera": float(np.nanmedian(medio[fuera])),
             "frac_cicatriz_dnbr_ge_03": float((medio[dentro] >= 0.3).mean()),
             "frac_cicatriz_alta": float((alta & dentro).sum() / max(int(dentro.sum()), 1)),
             "n_detecciones_dia1": int((df["acq_datetime"] <= dias(df)[0]).sum()),
             "celda_ha": grilla.celda_ha}
    corte1, _ = dias(df)
    frp = [{"incendio": caso.incendio} | r for r in frp_por_periodo(df, grilla, gr, corte1)]
    return filas, meta, frp


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    filas, metas, frp = [], [], []
    for cid in de.casos_calibracion():
        f, m, r = incendio(cid)
        filas += f
        metas.append(m)
        frp += r
        print(cid, flush=True)
    tabla = pd.DataFrame(filas)
    tabla.to_csv(SALIDA / "P3_f2_severidad.csv", index=False)
    meta = pd.DataFrame(metas)
    meta.to_csv(SALIDA / "P3_f2_ventanas_y_sanidad.csv", index=False)
    pd.DataFrame(frp).to_csv(SALIDA / "P3_f2_frp.csv", index=False)

    base = tabla[(tabla["definicion_dia1"] == "primera_pasada+24h")
                 & (tabla["celdas"] == "todas_las_celdas")]
    escala = meta.set_index("incendio")["escala_m"]
    crit = []
    for inc, g in base.groupby("incendio", sort=False):
        fr = g.pivot(index="grupo", columns="periodo", values="frac_alta")
        d1, sig, sh4 = fr.loc["bosque", "dia1"], fr.loc["bosque", "siguientes"], fr.loc[
            "SH4", "dia1"]
        mot = motivos_indiscriminado(d1, sig, sh4, int(escala[inc]))
        crit.append({"incendio": inc, "en_criterio": inc in CRITERIO_INCENDIOS,
                     "frac_dia1": d1, "frac_siguientes": sig, "frac_sh4_dia1": sh4,
                     "razon_dia1_siguientes": d1 / sig if sig else None,
                     "razon_sh4_bosque_dia1": sh4 / d1 if d1 and pd.notna(sh4) else None,
                     "cumple": evaluar_criterio(d1, sig), "motivos_indiscriminado": "; ".join(mot)})
    crit = pd.DataFrame(crit)
    crit.to_csv(SALIDA / "P3_f2_criterio.csv", index=False)
    dos = crit[crit["en_criterio"]]
    v = veredicto(dos["cumple"].tolist(), [m.split("; ") if m else [] for m in
                                           dos["motivos_indiscriminado"]])
    print(crit.to_string())
    print("VEREDICTO DEL FRENTE 2:", v)


if __name__ == "__main__":
    main()
