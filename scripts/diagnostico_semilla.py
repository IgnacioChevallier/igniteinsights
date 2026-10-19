"""Diagnóstico de la semilla de P-24 (tarea T), SIN correr ELMFIRE.

¿Por qué la semilla de los 34 reinicios de */pronostico-v6 queda 26-61 % fuera de la cicatriz
final (diagnostico-e2e/notas/D-referencia.md §5, bug 4)? Se re-arma la semilla de cada reinicio
con la regla de `benchmark._pronostico` (acumulada: previa | ignición | reconstrucción de TODAS
las detecciones de la caja hasta el reinicio) y se verifica contra el `phi.tif` guardado. Lo que
cae fuera de la cicatriz final se reparte, en este orden y sin solapes, en:

  a. detecciones ajenas: lo que desaparece al sembrar sólo con las detecciones a ≤ r m de la
     cicatriz (el filtro oráculo `semilla_inicial.radio_cicatriz_m`, r = 500, 1000, 2000);
  e. quema real no marcada: excluido (sin observación, cambio no confirmado, otro incendio) o
     0,1 ≤ dNBR < 0,3 (recomputado de los PRE/POST guardados, sin máscara de nubes: proxy);
  b. margen: fuera del núcleo (el casco cóncavo sin el buffer de 187,5 m; el punto mismo en
     los clústeres de < 4 detecciones, que llevan discos de 375 m);
  d. huella del píxel: dentro del núcleo y de la huella real scan × track de una detección;
  c. relleno del casco: dentro del núcleo y fuera de toda huella.

Además: una regla de tiempo real (conexión espacio-temporal desde la ignición) contra el
oráculo, y el re-puntaje aproximado de P-24 con la semilla filtrada (ver `recortar_prediccion`).
Sólo incendios de calibración.

    uv run python scripts/diagnostico_semilla.py

Escribe T1-T4 en docs/resultados/diagnostico-e2e/datos/. Las funciones puras se prueban en
tests/test_diagnostico_semilla.py.
"""
import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import rasterio.features
import shapely
from pyproj import Transformer
from rasterio.warp import Resampling, reproject
from rasterio.windows import from_bounds
from rasterio.windows import transform as transform_ventana
from shapely.geometry import MultiPoint, mapping

from app.elmfire.builder import perimeter_reconstruction as pr
from app.validation import almacen, cadena, pronostico
from app.validation import definiciones as d
from app.validation import puntuacion as p
from scripts.benchmark import _ventanas_cadena

SALIDA = Path("docs/resultados/diagnostico-e2e/datos")
PROTOCOLO, RECETA = "pronostico-v6", "lw-100-obs-001"
RADIOS_ORACULO_M = (500.0, 1000.0, 2000.0)
RADIO_PRINCIPAL_M = 1000.0
SALTOS_CONEXO_M = (750.0, 1500.0, 3000.0)
ANCLA_IGNICION_M = 5000.0   # = `alcance_m`: las primeras detecciones caen a 1,5-3 km del punto
LEJOS_M = pr.VIIRS_PIXEL_M
DNBR_BAJO = (0.1, 0.3)
CAUSAS = ("a", "e", "b", "d", "c")


# ── funciones puras ───────────────────────────────────────────────────────────────────────

def reconstruir(xy: np.ndarray):
    """(semilla, núcleo) de unas detecciones proyectadas. La semilla es la de
    `reconstruct_burn_polygon`; el núcleo, lo mismo sin el buffer: el casco cóncavo de los
    clústeres de ≥ 4 detecciones y los puntos de los menores."""
    if not len(xy):
        return None, None
    puntos = pr._dedup([tuple(q) for q in xy])
    nucleos = []
    for grupo in pr._cluster(puntos, pr._CLUSTER_EPS_M):
        if len(grupo) >= pr._MIN_HULL_POINTS:
            nucleos.append(shapely.concave_hull(MultiPoint(grupo), ratio=pr._HULL_RATIO,
                                                allow_holes=False))
        else:
            nucleos.append(MultiPoint(grupo))
    return pr.reconstruct_burn_polygon([tuple(q) for q in xy]), shapely.union_all(nucleos)


def rasterizar(geoms, forma, transform) -> np.ndarray:
    geoms = [g for g in geoms if g is not None and not g.is_empty]
    if not geoms:
        return np.zeros(forma, dtype=bool)
    return rasterio.features.rasterize([(mapping(g), 1) for g in geoms], out_shape=forma,
                                       transform=transform, dtype="uint8").astype(bool)


def huellas(xy: np.ndarray, scan_km: np.ndarray, track_km: np.ndarray) -> list:
    """El píxel real de cada detección: scan (a lo ancho de la pasada, ~E-O) × track (~N-S).
    ponytail: rectángulo alineado a la grilla; la órbita está ~10-15° inclinada."""
    return [shapely.box(x - s * 500, y - t * 500, x + s * 500, y + t * 500)
            for (x, y), s, t in zip(xy, scan_km, track_km)]


def conexas(xy: np.ndarray, ignicion_xy: np.ndarray, salto_m: float,
            ancla_m: float = ANCLA_IGNICION_M) -> np.ndarray:
    """Regla de tiempo real: las detecciones unidas a la ignición por una cadena de saltos de
    ≤ `salto_m` (enlace simple), anclada en las que caen a ≤ `ancla_m` de algún punto de
    ignición. Llamada con lo detectado hasta el reinicio, es monótona: sumar detecciones sólo
    une componentes. ponytail: matriz n × n, bien hasta ~10⁴ detecciones."""
    if not len(xy):
        return np.zeros(0, dtype=bool)
    cerca = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1)) <= salto_m
    unidas = (np.hypot(*(xy[:, None, :] - ignicion_xy[None, :, :]).transpose(2, 0, 1))
              <= ancla_m).any(1)
    while True:
        nuevas = unidas | cerca[unidas].any(0)
        if (nuevas == unidas).all():
            return unidas
        unidas = nuevas


def _borde(mascara: np.ndarray) -> np.ndarray:
    """(fila, col) de las celdas de `mascara` con algún vecino (4) fuera: la celda más cercana
    de `mascara` a un punto de afuera siempre es una de éstas."""
    pad = np.pad(mascara, 1)
    interior = pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:]
    return np.argwhere(mascara & ~interior)


def distancia_m(filas_cols: np.ndarray, mascara: np.ndarray, celda_m: float) -> np.ndarray:
    """Metros desde cada (fila, col), fraccional o no, al centro de celda más cercano de
    `mascara`; inf si está vacía."""
    if not mascara.any():
        return np.full(len(filas_cols), np.inf)
    arbol = shapely.STRtree(shapely.points(_borde(mascara)))
    _, dist = arbol.query_nearest(shapely.points(filas_cols), return_distance=True,
                                  all_matches=False)
    return dist * celda_m


def descomponer(s0, sf, nucleo, huella, pos, exc, dnbr_bajo, lejos,
                celda_ha: float) -> dict:
    """Hectáreas de la semilla `s0` fuera de la cicatriz `pos`, por causa excluyente (a, e, b,
    d, c; ver el docstring del módulo), y cuánto de cada una cae en `lejos` (> 375 m del
    borde)."""
    fuera = s0 & ~pos
    resto = fuera.copy()
    capas = {"a": resto & ~sf}
    resto &= sf
    capas["e"] = resto & (exc | dnbr_bajo)
    resto &= ~capas["e"]
    capas["b"] = resto & ~nucleo
    resto &= nucleo
    capas["d"] = resto & huella
    capas["c"] = resto & ~huella
    fila = {"semilla_ha": s0.sum() * celda_ha, "en_cicatriz_ha": (s0 & pos).sum() * celda_ha,
            "fuera_ha": fuera.sum() * celda_ha,
            "fuera_no_excluido_ha": (fuera & ~exc).sum() * celda_ha,
            "fuera_lejos_ha": (fuera & lejos).sum() * celda_ha,
            "filtro_saca_de_cicatriz_ha": (s0 & pos & ~sf).sum() * celda_ha}
    for k, m in capas.items():
        fila[f"{k}_ha"] = m.sum() * celda_ha
        fila[f"{k}_lejos_ha"] = (m & lejos).sum() * celda_ha
    return fila


def recortar_prediccion(pred: np.ndarray, s0: np.ndarray, sf: np.ndarray) -> np.ndarray:
    """Aproximación sin ELMFIRE de la corrida con la semilla filtrada: lo que el filtro saca de
    la semilla deja de estar quemado, y cada celda de crecimiento se atribuye a la celda de `s0`
    más cercana y se conserva sólo si ésa sigue en `sf`.
    ponytail: Voronoi sobre la semilla; no ve que el frente que queda pueda llegar en 12-24 h a
    lo que se sacó. Correr ELMFIRE si la diferencia importa."""
    if not (s0 & ~sf).any():
        return pred
    crece = np.argwhere(pred & ~s0)
    salida = sf.copy()
    if len(crece):
        borde = _borde(s0)
        _, cerca = shapely.STRtree(shapely.points(borde)).query_nearest(
            shapely.points(crece), all_matches=False)
        f, c = borde[cerca].T
        queda = sf[f, c]
        salida[crece[queda, 0], crece[queda, 1]] = True
    return salida


# ── carga ─────────────────────────────────────────────────────────────────────────────────

def casos_calibracion() -> list[str]:
    particion = json.loads(Path("benchmarks/particion.json").read_text())
    calib = {c.split("/")[0] for f in particion["calibracion"].values() for c in f}
    return [f"{inc}/{PROTOCOLO}" for inc in sorted(calib)
            if (d.RAIZ / "casos" / inc / f"{PROTOCOLO}.json").exists()]


def dnbr_en_grilla(run: Path, grilla: p.Grilla) -> np.ndarray:
    """dNBR (B8/B12) medio por celda desde los PRE/POST del run; NaN sin dato."""
    lienzo = np.full(grilla.shape, np.nan, dtype="float32")
    for pre in sorted((run / "imagenes_pre").glob("*.tif")):
        with rasterio.open(pre) as a, rasterio.open(run / "imagenes_post" / pre.name) as b:
            nbr = [(s[0] - s[1]) / np.where(s[0] + s[1] == 0, np.nan, s[0] + s[1])
                   for s in (a.read((4, 6)).astype("float32"), b.read((4, 6)).astype("float32"))]
            izq, abajo, der, arriba = rasterio.warp.transform_bounds(a.crs, grilla.crs, *a.bounds)
            v = from_bounds(izq, abajo, der, arriba, grilla.transform).round_offsets()
            v = v.round_lengths()
            f0, c0 = max(int(v.row_off), 0), max(int(v.col_off), 0)
            f1 = min(int(v.row_off + v.height), grilla.shape[0])
            c1 = min(int(v.col_off + v.width), grilla.shape[1])
            if f1 <= f0 or c1 <= c0:
                continue
            destino = np.full((f1 - f0, c1 - c0), np.nan, dtype="float32")
            reproject(source=(nbr[0] - nbr[1]).astype("float32"), destination=destino,
                      src_transform=a.transform, src_crs=a.crs, src_nodata=np.nan,
                      dst_transform=transform_ventana(
                          rasterio.windows.Window(c0, f0, c1 - c0, f1 - f0), grilla.transform),
                      dst_crs=grilla.crs, dst_nodata=np.nan, resampling=Resampling.average)
            sub = lienzo[f0:f1, c0:c1]
            np.copyto(sub, destino, where=np.isnan(sub))
    return lienzo


def cargar(caso_id: str) -> dict:
    caso = d.Caso.cargar(caso_id)
    paq = caso.paquete()
    grilla = p.Grilla(almacen.abrir(paq["comunes"]["dem.tif"]))
    run = Path(caso.datos["referencias"]["cicatriz"]["run"])
    pos, exc = p.cargar_cicatriz(run, grilla)
    df = pd.read_csv(almacen.abrir(paq["comunes"]["firms.csv"]), parse_dates=["acq_datetime"])
    tr = Transformer.from_crs("EPSG:4326", str(grilla.crs), always_xy=True)
    df["x"], df["y"] = tr.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    celda_m = abs(grilla.transform.a)
    cols, filas = ~grilla.transform * (df["x"].to_numpy(), df["y"].to_numpy())
    rc = np.column_stack([filas - 0.5, cols - 0.5])   # relativo a centros de celda
    fi, ci = np.floor(filas).astype(int), np.floor(cols).astype(int)
    dentro = (fi >= 0) & (fi < grilla.shape[0]) & (ci >= 0) & (ci < grilla.shape[1])
    en_pos = np.zeros(len(df), dtype=bool)
    en_pos[dentro] = pos[fi[dentro], ci[dentro]]
    df["dist_cicatriz_m"] = np.where(en_pos, 0.0, distancia_m(rc, pos, celda_m))
    ign = [(caso.datos["semilla_inicial"]["lon"], caso.datos["semilla_inicial"]["lat"])]
    dnbr = dnbr_en_grilla(run, grilla)
    return {"caso": caso, "paq": paq, "grilla": grilla, "pos": pos, "exc": exc, "df": df,
            "celda_m": celda_m, "ign_xy": np.array([tr.transform(*q) for q in ign]),
            "ignicion": cadena._leer(paq["ventanas"][0]["phi.tif"]) < 0,
            "dnbr_bajo": (dnbr >= DNBR_BAJO[0]) & (dnbr < DNBR_BAJO[1]),
            "dnbr_con_dato": float(np.isfinite(dnbr).mean())}


def variantes(c: dict) -> dict[str, np.ndarray]:
    """Por variante, qué detecciones siembran (máscara sobre `df`), evaluada a cada reinicio
    para las conexas (la regla sólo ve lo detectado hasta ahí)."""
    df = c["df"]
    v = {"actual": lambda sel: np.ones(sel.sum(), dtype=bool)}
    for r in RADIOS_ORACULO_M:
        v[f"oraculo_{r:.0f}"] = lambda sel, r=r: df["dist_cicatriz_m"].to_numpy()[sel] <= r
    for s in SALTOS_CONEXO_M:
        v[f"conexo_{s:.0f}"] = lambda sel, s=s: conexas(df[["x", "y"]].to_numpy()[sel],
                                                       c["ign_xy"], s)
    return v


def semillas(c: dict) -> dict[str, list[dict]]:
    """Semilla y núcleo de cada reinicio (n ≥ 1), por variante, con la recursión de
    `_pronostico`: observado = previo | ignición | reconstrucción(antes)."""
    df, g = c["df"], c["grilla"]
    xy, scan, track = df[["x", "y"]].to_numpy(), df["scan"].to_numpy(), df["track"].to_numpy()
    salida = {}
    for nombre, elegir in variantes(c).items():
        previo, previo_nuc, lista = c["ignicion"], c["ignicion"], []
        for n, v in enumerate(c["caso"].ventanas):
            if n == 0:
                continue
            sel = (df["acq_datetime"] <= v.inicio).to_numpy()
            usa = elegir(sel)
            semilla, nucleo = reconstruir(xy[sel][usa])
            s = previo | c["ignicion"] | rasterizar([semilla], g.shape, g.transform)
            nuc = previo_nuc | c["ignicion"] | rasterizar([nucleo], g.shape, g.transform)
            lista.append({"n": n, "inicio": v.inicio, "semilla": s, "nucleo": nuc,
                          "huella": rasterizar(huellas(xy[sel][usa], scan[sel][usa],
                                                       track[sel][usa]), g.shape, g.transform),
                          "detecciones": int(sel.sum()), "usadas": int(usa.sum()),
                          "usadas_lejos": int((df["dist_cicatriz_m"].to_numpy()[sel][usa]
                                               > RADIO_PRINCIPAL_M).sum())})
            previo, previo_nuc = s, nuc
        salida[nombre] = lista
    return salida


# ── tablas ────────────────────────────────────────────────────────────────────────────────

def t1_t2(c: dict, ss: dict) -> tuple[list[dict], list[dict]]:
    """T1: descomposición por reinicio (contra cada oráculo). T2: por variante, qué saca."""
    inc, ha = c["caso"].incendio, c["grilla"].celda_ha
    afuera = ss["actual"][-1]["semilla"] & ~c["pos"]   # la semilla es acumulada: contiene a todas
    lejos = np.zeros_like(afuera)
    lejos[afuera] = distancia_m(np.argwhere(afuera), c["pos"], c["celda_m"]) > LEJOS_M
    t1, t2 = [], []
    for k, base in enumerate(ss["actual"]):
        phi = cadena._leer(c["paq"]["ventanas"][base["n"]]["phi.tif"]) < 0
        for nombre, lista in ss.items():
            f = lista[k]
            fila = {"incendio": inc, "n": base["n"], "variante": nombre,
                    "detecciones": f["detecciones"], "usadas": f["usadas"],
                    "usadas_a_mas_de_1000m": f["usadas_lejos"],
                    "reproduce_phi": bool((base["semilla"] == phi).all()),
                    "celdas_distintas_phi": int((base["semilla"] != phi).sum()),
                    "sf_fuera_de_s0_ha": (f["semilla"] & ~base["semilla"]).sum() * ha}
            fila |= descomponer(base["semilla"], f["semilla"], f["nucleo"], f["huella"],
                                c["pos"], c["exc"], c["dnbr_bajo"], lejos, ha)
            (t1 if nombre.startswith("oraculo") else t2).append(fila)
    return t1, t2


def t3(c: dict) -> list[dict]:
    """Detecciones: distancia del centro a la cicatriz contra la media huella scan × track."""
    df = c["df"]
    media_diag = 500 * np.hypot(df["scan"], df["track"])
    filas = []
    for etiqueta, sel in (("todas", np.ones(len(df), bool)),
                          ("legitimas_1000", df["dist_cicatriz_m"] <= RADIO_PRINCIPAL_M)):
        x = df[sel]
        filas.append({"incendio": c["caso"].incendio, "grupo": etiqueta, "n": len(x),
                      "centro_fuera": float((x["dist_cicatriz_m"] > 0).mean()),
                      "fuera_mas_media_huella": float(
                          (x["dist_cicatriz_m"] > media_diag[sel]).mean()),
                      "fuera_mas_375": float((x["dist_cicatriz_m"] > 375).mean()),
                      "dist_mediana_si_fuera_m": float(
                          x.loc[x["dist_cicatriz_m"] > 0, "dist_cicatriz_m"].replace(
                              np.inf, np.nan).median()),
                      "media_huella_mediana_m": float(media_diag[sel].median()),
                      "scan_mediana_km": float(x["scan"].median()),
                      "track_mediana_km": float(x["track"].median())})
    return filas


def t4(c: dict, ss: dict) -> list[dict]:
    """P-24 re-puntuado (con el anillo excluido, `pronostico.puntuar` actual) para cada
    variante, con la predicción recortada por `recortar_prediccion`."""
    caso, g = c["caso"], c["grilla"]
    man = d.cargar_manifiesto(caso.id, RECETA)
    cad = _ventanas_cadena(caso.datos["cadena"]["caso"], caso.datos["cadena"]["receta"])
    cic = cadena._leer(c["paq"]["comunes"]["cicatriz.tif"]).astype(bool)
    exc = cadena._leer(c["paq"]["comunes"]["excluido.tif"]).astype(bool)
    filas = {nombre: [] for nombre in ss}
    previas = {nombre: (caso.ventanas[0].inicio, c["ignicion"]) for nombre in ss}
    for k, base in enumerate(ss["actual"]):
        v, w = caso.ventanas[base["n"]], man["ventanas"][base["n"]]
        arch = c["paq"]["ventanas"][base["n"]]
        horas = np.nan_to_num(p.horas_relativas(cadena._leer(cadena._toa(w["salidas"])),
                                                v.tstart_s), nan=np.inf)
        vistas = cadena._leer(arch["vistas_horas.tif"])
        det = cadena._leer(arch["ref_firms_horas.tif"])
        for nombre, lista in ss.items():
            sf = lista[k]["semilla"]
            fila = {"incendio": caso.incendio, "n": base["n"], "plazos": {}}
            for plazo in caso.datos["plazos"]:
                preds = {"p24": recortar_prediccion(horas <= plazo, base["semilla"], sf),
                         "cadena": pronostico.quemado_en(cad, v.inicio + timedelta(hours=plazo)),
                         "persistencia": pronostico.persistencia(
                             sf, previas[nombre][1],
                             (v.inicio - previas[nombre][0]).total_seconds() / 3600, plazo, g)}
                fila["plazos"][str(plazo)] = {
                    m: pronostico.puntuar(pr_, sf, cic, exc, vistas, det, plazo, g.celda_ha)
                    for m, pr_ in preds.items()}
            filas[nombre].append(fila)
            previas[nombre] = (v.inicio, sf)
    return [{"variante": nombre, **f} for nombre, lst in filas.items() for f in lst]


def t4_resumen(filas: list[dict]) -> pd.DataFrame:
    salida = []
    for nombre in dict.fromkeys(f["variante"] for f in filas):
        sub = [f for f in filas if f["variante"] == nombre]
        for plazo in pronostico.PLAZOS_H:
            fila = {"variante": nombre, "plazo_h": plazo}
            for contra in ("cadena", "persistencia"):
                r = pronostico.resumir(sub, plazo, contra)
                fila[f"mediana_delta_{contra}"] = r["mediana_delta"]
                fila[f"mejoran_{contra}"] = f"{r['mejoran']}/{r['n']}"
                if contra == "cadena":
                    fila |= {f"dice_{i}": m["p24"] for i, m in r["incendios"].items()}
            ses = [f["plazos"][str(plazo)]["p24"]["cicatriz"]["sesgo_area"] for f in sub]
            fila["sesgo_p24_mediana"] = float(np.median([s for s in ses if s is not None]))
            salida.append(fila)
    return pd.DataFrame(salida)


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    r1, r2, r3, r4 = [], [], [], []
    for cid in casos_calibracion():
        c = cargar(cid)
        print(cid, f"dNBR con dato en {c['dnbr_con_dato']:.0%} de la grilla", flush=True)
        ss = semillas(c)
        a, b = t1_t2(c, ss)
        r1 += a
        r2 += b
        r3 += t3(c)
        r4 += t4(c, ss)
    pd.DataFrame(r1).to_csv(SALIDA / "T1_semilla_descomposicion.csv", index=False)
    pd.DataFrame(r2).to_csv(SALIDA / "T2_semilla_filtros.csv", index=False)
    pd.DataFrame(r3).to_csv(SALIDA / "T3_detecciones_huella.csv", index=False)
    (SALIDA / "T4_p24_semilla_filtrada.json").write_text(json.dumps(r4, indent=1))
    t4_resumen(r4).to_csv(SALIDA / "T4_p24_resumen.csv", index=False)


if __name__ == "__main__":
    main()
