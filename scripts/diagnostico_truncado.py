"""Diagnóstico del truncado asimétrico de la cicatriz (tarea T-truncado), SIN correr ELMFIRE.

Con `hasta_horizonte`, la cicatriz se trunca a las celdas a ≤ 375 m de alguna detección FIRMS
(«vistas», `benchmark._referencia_cicatriz`) y el resto de la cicatriz pasa a excluido; pero las
celdas no vistas que NO son cicatriz siguen contando como falso positivo
(diagnostico-e2e/notas/D-referencia.md §5, bug 1). P-24 repite el patrón en
`pronostico.puntuar`. Se re-puntúan las salidas TOA guardadas contra tres referencias:

  A. la actual;
  B. simétrica: también se excluyen las celdas no vistas que no son cicatriz (se puntúa sólo
     dentro de vistas);
  C. simétrica dentro del perímetro final: se excluyen las no vistas sólo dentro del relleno
     (sin huecos) de la cicatriz final. Fuera de ese perímetro nada se quemó nunca, así que
     quemar ahí sigue siendo error.

Para cada receta con iteración en los casos de calibración (benchmarks/particion.json), y para
P-24 (`*/pronostico-v6` con `lw-100-obs-001`) contra la cadena y la persistencia. Además, el costo
de B: lo predicho fuera de vistas y fuera del perímetro final, que B deja de penalizar.

    uv run python scripts/diagnostico_truncado.py

Escribe X1-X4 en docs/resultados/diagnostico-e2e/datos/. Las funciones puras se prueban en
tests/test_diagnostico_truncado.py.
"""
import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio.features
from affine import Affine
from shapely.geometry import Polygon, mapping, shape

from app.elmfire.builder import perimeter_reconstruction as pr
from app.validation import almacen, cadena, pronostico
from app.validation import definiciones as d
from app.validation import puntuacion as p
from scripts.benchmark import _discos, _puntos, _ventanas_cadena

SALIDA = Path("docs/resultados/diagnostico-e2e/datos")
RECETA_P24 = "lw-100-obs-001"
REFERENCIAS = ("A", "B", "C")
NB = (91, 92, 93, 98, 99)


# ── funciones puras ───────────────────────────────────────────────────────────────────────

def rellenar(mascara: np.ndarray) -> np.ndarray:
    """La máscara sin huecos: cada componente hasta su anillo exterior (sin scipy)."""
    if not mascara.any():
        return mascara.copy()
    exteriores = [Polygon(shape(g).exterior) for g, _ in rasterio.features.shapes(
        mascara.astype("uint8"), mask=mascara, transform=Affine.identity())]
    return rasterio.features.rasterize([(mapping(g), 1) for g in exteriores],
                                       out_shape=mascara.shape, transform=Affine.identity(),
                                       dtype="uint8").astype(bool) | mascara


def exclusiones(excluido: np.ndarray, no_vistas: np.ndarray,
                perimetro: np.ndarray) -> dict[str, np.ndarray]:
    """La exclusión de cada referencia. La cicatriz no vista ya está en `excluido` (A), así que
    la parte positiva de la referencia es la misma en las tres."""
    return {"A": excluido, "B": excluido | no_vistas, "C": excluido | (no_vistas & perimetro)}


def perdonado_ha(pred: np.ndarray, excluido: np.ndarray, no_vistas: np.ndarray,
                 perimetro: np.ndarray, celda_ha: float) -> dict:
    """Lo predicho que A cuenta como falso positivo y B deja de puntuar, separado en lo que cae
    dentro del perímetro final (islas o crecimiento posterior: ambiguo) y fuera (sobrequema
    real que B perdona y C no)."""
    libre = pred & ~excluido & no_vistas
    return {"perdonado_dentro_ha": float((libre & perimetro).sum() * celda_ha),
            "perdonado_fuera_ha": float((libre & ~perimetro).sum() * celda_ha),
            "predicho_ha": float((pred & ~excluido).sum() * celda_ha)}


# ── carga ─────────────────────────────────────────────────────────────────────────────────

def casos_calibracion() -> tuple[list[str], set[str]]:
    particion = json.loads(Path("benchmarks/particion.json").read_text())
    return ([c for f in particion["calibracion"].values() for c in f],
            set(particion.get("limites", [])))


def cargar(caso_id: str) -> dict:
    """La referencia del paquete y lo necesario para B y C: vistas a 375 m hasta el fin de la
    última ventana (la regla de `_referencia_cicatriz`) y el perímetro de la cicatriz final."""
    caso = d.Caso.cargar(caso_id)
    paq = caso.paquete()
    grilla = p.Grilla(almacen.abrir(paq["comunes"]["dem.tif"]))
    ref = caso.datos["referencias"]["cicatriz"]
    final, _ = p.cargar_cicatriz(Path(ref["run"]), grilla,
                                 tuple(ref.get("excluidas", p.EXCLUIDAS_POR_DEFECTO)))
    df = pd.read_csv(almacen.abrir(paq["comunes"]["firms.csv"]), parse_dates=["acq_datetime"])
    vistas = _discos(_puntos(df, None, caso.ventanas[-1].fin), grilla, pr.VIIRS_PIXEL_M)
    cic = cadena._leer(paq["comunes"]["cicatriz.tif"]).astype(bool)
    exc = cadena._leer(paq["comunes"]["excluido.tif"]).astype(bool)
    if ref.get("hasta_horizonte") and not (cic == (final & vistas)).all():
        raise ValueError(f"{caso_id}: las vistas no reproducen la cicatriz truncada del paquete")
    return {"caso": caso, "paq": paq, "grilla": grilla, "cic": cic, "exc": exc,
            "final": final, "vistas": vistas, "perimetro": rellenar(final),
            "truncada": bool(ref.get("hasta_horizonte"))}


# ── tablas ────────────────────────────────────────────────────────────────────────────────

def x1_calibracion(c: dict, limites: set[str]) -> list[dict]:
    """Por receta, la principal (última ventana, acumulado contra la cicatriz) con A, B y C,
    como `cadena.puntuar`. Más dos predicciones de control: el perímetro final perfecto
    (quemable, sin NB: el techo de islas de D §4) y todo el dominio quemado."""
    caso, g = c["caso"], c["grilla"]
    no_vistas = ~c["vistas"]
    excl = exclusiones(c["exc"], no_vistas, c["perimetro"])
    filas, quemable = [], None
    for dir_receta in sorted(d.ruta_iteracion(caso.id, "x").parent.iterdir()):
        man = d.cargar_manifiesto(caso.id, dir_receta.name)
        metr = d.cargar_metricas(caso.id, dir_receta.name)
        if man is None or metr is None:
            continue
        receta = d.Receta.cargar(dir_receta.name)
        semilla0 = cadena._leer(man["ventanas"][0]["insumos"]["phi.tif"]) < 0
        ultima = man["ventanas"][-1]
        semilla = cadena._leer(ultima["insumos"]["phi.tif"]) < 0
        quemado = semilla | (cadena._leer(cadena._toa(ultima["salidas"])) > 0)
        ya = semilla0 if receta.semilla == "prediccion" else semilla
        if quemable is None:
            codigos = cadena._leer(man["ventanas"][0]["insumos"]["fbfm40.tif"])
            quemable = (codigos > 0) & ~np.isin(codigos, NB)
            controles = {"_perimetro_perfecto": c["perimetro"] & quemable,
                         "_todo_quemado": np.ones(g.shape, dtype=bool)}
        preds = {receta.id: quemado} | ({} if filas else controles)
        for nombre, pred in preds.items():
            fila = {"caso": caso.id, "incendio": caso.incendio, "limite": caso.id in limites,
                    "receta": nombre}
            for r, e in excl.items():
                m = p.metricas(pred & ~ya, c["cic"] & ~ya, g.celda_ha, e | ya)
                fila |= {f"dice_{r}": m["dice"], f"sesgo_{r}": m["sesgo_area"],
                         f"observado_ha_{r}": m["observado_ha"]}
            fila |= perdonado_ha(pred & ~ya, c["exc"] | ya, no_vistas, c["perimetro"],
                                 g.celda_ha)
            if not nombre.startswith("_"):
                fila["dice_guardado"] = metr["principal"]["dice"]
            filas.append(fila)
    return filas


def x2_resumen(filas: list[dict]) -> pd.DataFrame:
    """Media y mediana por receta (con y sin el caso límite) y el puesto en cada referencia.
    Sólo recetas con iteración en todos los casos."""
    df = pd.DataFrame(filas)
    df = df[~df["receta"].str.startswith("_")]
    n = df.groupby("receta")["caso"].nunique()
    df = df[df["receta"].isin(n[n == n.max()].index)]
    salida = []
    for etiqueta, sub in (("7 casos", df), ("sin límite", df[~df["limite"]])):
        g = sub.groupby("receta")
        res = pd.DataFrame({f"{f}_{r}": getattr(g[f"dice_{r}"], f)()
                            for r in REFERENCIAS for f in ("mean", "median")})
        for r in REFERENCIAS:
            res[f"puesto_mean_{r}"] = res[f"mean_{r}"].rank(ascending=False).astype(int)
            res[f"puesto_median_{r}"] = res[f"median_{r}"].rank(ascending=False).astype(int)
        salida.append(res.reset_index().assign(conjunto=etiqueta))
    return pd.concat(salida, ignore_index=True)


def x3_pronostico(c: dict) -> list[dict]:
    """P-24 con A, B y C reusando `pronostico.puntuar`: B y C entran como exclusión extra (las
    celdas no vistas al plazo, todas o dentro del perímetro final)."""
    caso_id = f"{c['caso'].incendio}/pronostico-v6"
    caso = d.Caso.cargar(caso_id)
    paq = caso.paquete()
    if paq["comunes"]["dem.tif"] != c["paq"]["comunes"]["dem.tif"]:
        raise ValueError(f"{caso_id} no comparte la grilla del caso base")
    g = c["grilla"]
    man = d.cargar_manifiesto(caso_id, RECETA_P24)
    guardado = json.loads((d.ruta_iteracion(caso_id, RECETA_P24) / "pronostico.json").read_text())
    cad = _ventanas_cadena(caso.datos["cadena"]["caso"], caso.datos["cadena"]["receta"])
    cic = cadena._leer(paq["comunes"]["cicatriz.tif"]).astype(bool)
    exc = cadena._leer(paq["comunes"]["excluido.tif"]).astype(bool)
    filas, previa = {r: [] for r in REFERENCIAS}, None
    for v, w, fg in zip(caso.ventanas, man["ventanas"], guardado, strict=True):
        arch = paq["ventanas"][w["n"]]
        semilla = cadena._leer(w["insumos"]["phi.tif"]) < 0
        horas = np.nan_to_num(p.horas_relativas(cadena._leer(cadena._toa(w["salidas"])),
                                                v.tstart_s), nan=np.inf)
        vistas = cadena._leer(arch["vistas_horas.tif"])
        det = cadena._leer(arch["ref_firms_horas.tif"])
        filas_n = {r: {"incendio": caso.incendio, "n": w["n"], "plazos": {}} for r in REFERENCIAS}
        for plazo in caso.datos["plazos"]:
            preds = {"p24": horas <= plazo,
                     "cadena": pronostico.quemado_en(cad, v.inicio + timedelta(hours=plazo))}
            if previa is not None:
                preds["persistencia"] = pronostico.persistencia(
                    semilla, previa[1], (v.inicio - previa[0]).total_seconds() / 3600, plazo, g)
            no_vistas = vistas > plazo
            for r, e in exclusiones(exc, no_vistas, c["perimetro"]).items():
                filas_n[r]["plazos"][str(plazo)] = {
                    m: pronostico.puntuar(pr_, semilla, cic, e, vistas, det, plazo, g.celda_ha)
                    | {"perdonado": perdonado_ha(pr_ & ~semilla, exc | semilla, no_vistas,
                                                 c["perimetro"], g.celda_ha)}
                    for m, pr_ in preds.items()}
            a = filas_n["A"]["plazos"][str(plazo)]["p24"]["cicatriz"]["dice"]
            b = fg["plazos"][str(plazo)]["p24"]["cicatriz"]["dice"]
            if a != b and not (a is not None and b is not None and abs(a - b) < 1e-9):
                raise ValueError(f"{caso_id} n={w['n']} {plazo} h: A no reproduce lo guardado")
        for r in REFERENCIAS:
            filas[r].append(filas_n[r])
        previa = (v.inicio, semilla)
    return [{"referencia": r, **f} for r, lst in filas.items() for f in lst]


def x4_resumen(filas: list[dict]) -> pd.DataFrame:
    salida = []
    for r in REFERENCIAS:
        sub = [f for f in filas if f["referencia"] == r]
        for plazo in pronostico.PLAZOS_H:
            fila = {"referencia": r, "plazo_h": plazo}
            for contra in ("cadena", "persistencia"):
                res = pronostico.resumir(sub, plazo, contra)
                fila[f"mediana_delta_{contra}"] = res["mediana_delta"]
                fila[f"mejoran_{contra}"] = f"{res['mejoran']}/{res['n']}"
                for inc, m in res["incendios"].items():
                    fila[f"dice_p24_{inc}"] = m["p24"]
                    fila[f"dice_{contra}_{inc}"] = m[contra]
            for inc in dict.fromkeys(f["incendio"] for f in sub):
                ses = [f["plazos"][str(plazo)]["p24"]["cicatriz"]["sesgo_area"] for f in sub
                       if f["incendio"] == inc and f["n"] > 0]
                fila[f"sesgo_p24_{inc}"] = float(np.median([s for s in ses if s is not None]))
                per = [f["plazos"][str(plazo)]["p24"]["perdonado"] for f in sub
                       if f["incendio"] == inc and f["n"] > 0]
                fila[f"perdonado_fuera_frac_{inc}"] = (
                    sum(x["perdonado_fuera_ha"] for x in per)
                    / max(sum(x["predicho_ha"] for x in per), 1e-9))
            salida.append(fila)
    return pd.DataFrame(salida)


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    casos, limites = casos_calibracion()
    r1, r3 = [], []
    for cid in casos:
        c = cargar(cid)
        print(cid, flush=True)
        r1 += x1_calibracion(c, limites)
        if (d.RAIZ / "casos" / c["caso"].incendio / "pronostico-v6.json").exists():
            r3 += x3_pronostico(c)
    pd.DataFrame(r1).to_csv(SALIDA / "X1_truncado_por_receta.csv", index=False)
    x2_resumen(r1).to_csv(SALIDA / "X2_truncado_orden_recetas.csv", index=False)
    (SALIDA / "X3_truncado_p24.json").write_text(json.dumps(r3, indent=1))
    x4_resumen(r3).to_csv(SALIDA / "X4_truncado_p24_resumen.csv", index=False)


if __name__ == "__main__":
    main()
