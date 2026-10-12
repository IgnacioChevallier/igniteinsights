"""¿La lenga de altura arde menos que la vegetación vecina, a igualdad de exposición al fuego?

Evidencia regional FUERA del benchmark para docs/resultados/HUMEDAD-ALTURA-PROPUESTA.md. Sólo
lee: no toca app/, recetas ni casos, y no corre ELMFIRE.

Diseño (fijado antes de mirar los resultados):

- Grilla: UTM 19S a 90 m sobre toda la cobertura de CCS-BAP de Chubut y Río Negro.
- Vegetación ANTERIOR al fuego: CCS-BAP 2013 para las temporadas 2014-2017 y CCS-BAP 2017 para
  las 2018-2026 (temporada = julio a junio, rotulada por su junio). Las temporadas 2001-2013 no
  entran: el mapa 2013 ya las ve como remanente, y eso sesgaría a favor de "la lenga no arde".
- Fuego: MODIS MCD64A1 v6.1 (BurnDate > 0 en la temporada), vía Earth Engine. Control a 30 m:
  las cicatrices dNBR de mask-dataset-gen de tres incendios de 2015 que NO están en el
  benchmark (Cerro Plataforma, Currumahuida, Desemboque), con el mapa 2013.
- Exclusión: todo evento cuya envolvente toque una cicatriz de los 11 incendios del benchmark
  (benchmarks/particion.json) más 2 km sale entero.
- Exposición: la envolvente de un evento es todo lo que está a <= 1 km de lo quemado en la
  temporada; las envolventes conexas son los eventos. Dentro de la envolvente, el fuego y el
  tiempo son los mismos para la lenga y para sus vecinas; se comparan fracciones quemadas por
  clase y banda de 200 m del DEM COP30. Eventos con < 100 ha quemadas, fuera.

Uso (dependencias fuera del proyecto; credenciales de Earth Engine del usuario):

    uv run --with scipy --with earthengine-api python scripts/lenga_altura_regional.py

Escribe la caché y la tabla larga en data/validation/lenga_altura/ (ignorado por git).
"""
import glob
import io
import json
import urllib.request
from pathlib import Path

import geopandas as gpd
import numpy as np
import pyogrio
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from scipy import ndimage

from app.elmfire.builder.fuels_builder import ccsbap_fuel_code

SALIDA = Path("data/validation/lenga_altura")
DATASETS = Path("datasets")
MASCARAS = Path("../mask-dataset-gen/dataset")
PROYECTO_EE = "ee-nachochevallier"
CRS, RES = "EPSG:32719", 90.0
ENVOLVENTE_M, EXCLUSION_M, MIN_HA = 1000.0, 2000.0, 100.0
BANDAS = np.arange(200, 2201, 200)
HA = RES * RES / 1e4
TEMPORADAS = range(2014, 2027)
EXTRA_30M = ["cerro-plataforma-2015", "currumahuida-2015", "desemboque-2015"]

# Clases de análisis (Ley_N1, Ley_N2). Quemable o no lo decide el crosswalk de modelo-v0.
CLASES = {1: "Lenga (TF Le)", 2: "Lenga achaparrada (OFL Le)", 3: "Coihue/ciprés/mixto (TF)",
          4: "Ñire (TF y OFL)", 5: "Matorral (otras OFL)", 6: "Estepa/altoandina (OT Herb)",
          7: "Remanente (OT Rem Dist Rec)", 8: "Otras quemables"}


def clase(n1: str, n2: str, n3: str) -> int:
    try:
        if ccsbap_fuel_code(n1, n2, n3) in (91, 92, 93, 98, 99):
            return 0
    except KeyError:
        return 0
    if n1 == "TF":
        return {"Le": 1, "Co": 3, "Ci": 3, "Mx": 3, "Ñi": 4}.get(n2, 8)
    if n1 == "OFL":
        return {"Le": 2, "Ñi": 4}.get(n2, 5)
    return {"Herb-Subarb": 6, "Rem Dist Rec": 7}.get(n2, 8)


def shp(prov: str, anio: int) -> Path:
    return next(DATASETS.glob(f"{prov}_{anio}_*/cob_{anio}_N3_aok_{prov}.shp"))


def grilla() -> tuple[rasterio.Affine, tuple[int, int]]:
    info = [pyogrio.read_info(shp(p, a)) for p in ("CH", "RN") for a in (2013, 2017)]
    cajas = np.array([i["total_bounds"] for i in info])
    esquinas = [(x, y) for x in (cajas[:, 0].min(), cajas[:, 2].max())
                for y in (cajas[:, 1].min(), cajas[:, 3].max())]
    caja = gpd.GeoSeries(gpd.points_from_xy(*zip(*esquinas)), crs=info[0]["crs"]).to_crs(CRS)
    x0, y1 = np.floor(caja.x.min() / RES) * RES, np.ceil(caja.y.max() / RES) * RES
    w = int(np.ceil((caja.x.max() - x0) / RES))
    h = int(np.ceil((y1 - caja.y.min()) / RES))
    return from_origin(x0, y1, RES, RES), (h, w)


def mapa_clases(anio: int, transform, forma) -> np.ndarray:
    ruta = SALIDA / f"clases_{anio}.npy"
    if ruta.exists():
        return np.load(ruta)
    salida = np.zeros(forma, "uint8")
    for prov in ("CH", "RN"):
        gdf = gpd.read_file(shp(prov, anio), columns=["Ley_N1", "Ley_N2", "Ley_N3"]).to_crs(CRS)
        leyes = gdf[["Ley_N1", "Ley_N2", "Ley_N3"]].fillna("").itertuples(index=False)
        c = [clase(*f) for f in leyes]
        capa = rasterize(zip(gdf.geometry, c), out_shape=forma, transform=transform, fill=0,
                         dtype="uint8")
        salida = np.where(capa > 0, capa, salida)
    np.save(ruta, salida)
    return salida


def bajar_ee(imagen, nombre: str, transform, forma, dtype) -> np.ndarray:
    """La imagen en la grilla, en franjas de filas para no pasar el límite de descarga."""
    ruta = SALIDA / f"{nombre}.npy"
    if ruta.exists():
        return np.load(ruta)
    h, w = forma
    salida = np.zeros(forma, dtype)
    for f0 in range(0, h, 1500):
        filas = min(1500, h - f0)
        t = transform * rasterio.Affine.translation(0, f0)
        url = imagen.getDownloadURL({"crs": CRS, "crs_transform": list(t)[:6],
                                     "dimensions": f"{w}x{filas}", "format": "GEO_TIFF"})
        with urllib.request.urlopen(url) as r, rasterio.open(io.BytesIO(r.read())) as src:
            salida[f0:f0 + filas] = src.read(1)
    np.save(ruta, salida)
    return salida


def quemado_mascaras(casos: list[str], transform, forma, umbral: float) -> np.ndarray:
    """Fracción de cada celda cubierta por las máscaras dNBR de los casos (run vigente)."""
    acumulado = np.zeros(forma, "float32")
    for caso in casos:
        run = _run_vigente(caso)
        for tif in sorted(glob.glob(f"{MASCARAS}/{caso}/runs/{run}/mascaras/*.tif")):
            with rasterio.open(tif) as src:
                destino = np.zeros(forma, "float32")
                reproject(src.read(1).astype("float32"), destino, src_transform=src.transform,
                          src_crs=src.crs, dst_transform=transform, dst_crs=CRS,
                          resampling=Resampling.average, src_nodata=None, dst_nodata=0)
                acumulado = np.maximum(acumulado, destino)
    return acumulado >= umbral


def _run_vigente(caso: str) -> str:
    for proto in sorted(Path(f"benchmarks/casos/{caso}").glob("calibracion*v6*.json")):
        return Path(json.loads(proto.read_text())["referencias"]["cicatriz"]["run"]).name
    return "event-filter-001"


def casos_benchmark() -> list[str]:
    p = json.loads(Path("benchmarks/particion.json").read_text())
    return sorted({c.split("/")[0] for g in ("calibracion", "prueba") for lista in p[g].values()
                   for c in lista})


def eventos(quemado: np.ndarray, excluir: np.ndarray, clases: np.ndarray, dem: np.ndarray,
            fuente: str, etiqueta: str) -> list[dict]:
    """Por evento (envolvente conexa) × clase × banda: celdas expuestas y quemadas."""
    if not quemado.any():
        return []
    envolvente = ndimage.distance_transform_edt(~quemado) * RES <= ENVOLVENTE_M
    lab, n = ndimage.label(envolvente, structure=np.ones((3, 3)))
    banda = np.digitize(dem, BANDAS)
    filas = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        en = lab[sl] == i
        if (excluir[sl] & en).any() or (quemado[sl] & en).sum() * HA < MIN_HA:
            continue
        c, b, q = clases[sl][en], banda[sl][en], quemado[sl][en]
        valido = c > 0
        clave = c[valido].astype(int) * 100 + b[valido]
        expuesto = np.bincount(clave, minlength=1000)
        ardido = np.bincount(clave, weights=q[valido], minlength=1000)
        for k in np.nonzero(expuesto)[0]:
            filas.append({"fuente": fuente, "evento": f"{etiqueta}-{i}", "clase": int(k // 100),
                          "banda": int(BANDAS[k % 100 - 1]) if k % 100 else 0,
                          "expuesto_ha": float(expuesto[k] * HA),
                          "quemado_ha": float(ardido[k] * HA)})
    return filas


def main() -> None:
    import ee
    import pandas as pd

    SALIDA.mkdir(parents=True, exist_ok=True)
    ee.Initialize(project=PROYECTO_EE)
    transform, forma = grilla()
    print("grilla", forma, transform)
    clases = {a: mapa_clases(a, transform, forma) for a in (2013, 2017)}
    dem = bajar_ee(ee.ImageCollection("COPERNICUS/DEM/GLO30").select("DEM").mosaic().toInt16(),
                   "dem_cop30", transform, forma, "int16")

    bench = quemado_mascaras(casos_benchmark(), transform, forma, umbral=0.01)
    excluir = ndimage.distance_transform_edt(~bench) * RES <= EXCLUSION_M
    print(f"exclusión benchmark: {excluir.sum() * HA:,.0f} ha")

    mcd = ee.ImageCollection("MODIS/061/MCD64A1").select("BurnDate")
    filas = []
    for t in TEMPORADAS:
        img = (mcd.filterDate(f"{t - 1}-07-01", f"{t}-07-01").map(lambda i: i.gt(0)).max()
               .unmask(0).toByte())
        q = bajar_ee(img, f"mcd64a1_{t}", transform, forma, "uint8").astype(bool)
        mapa = clases[2013 if t <= 2017 else 2017]
        filas += eventos(q, excluir, mapa, dem, "MCD64A1", str(t))
        print(t, f"quemado {q.sum() * HA:,.0f} ha")
    for caso in EXTRA_30M:
        q = quemado_mascaras([caso], transform, forma, umbral=0.5)
        filas += eventos(q, excluir, clases[2013], dem, "dNBR30", caso)
    tabla = pd.DataFrame(filas)
    tabla.to_csv(SALIDA / "tabla_larga.csv", index=False)
    resumir(tabla)


def resumir(tabla) -> None:
    import pandas as pd

    pd.set_option("display.width", 200)
    for fuente, t in tabla.groupby("fuente"):
        print(f"\n===== {fuente}: {t.evento.nunique()} eventos, "
              f"{t.quemado_ha.sum():,.0f} ha quemadas en CCS-BAP =====")
        g = t.groupby(["clase", "banda"])[["expuesto_ha", "quemado_ha"]].sum()
        g["fq"] = g.quemado_ha / g.expuesto_ha
        piv = g["fq"].unstack("banda").round(3)
        piv.index = [CLASES[i] for i in piv.index]
        print("Fracción quemada por clase (fila) y banda (desde, m):\n", piv)
        exp = g["expuesto_ha"].unstack("banda").round(0)
        exp.index = [CLASES[i] for i in exp.index]
        print("Expuesto (ha):\n", exp)
        for lenga in (1, 2):
            contraste(t, lenga, fuente)


def contraste(t, lenga: int, fuente: str, min_ha: float = 25.0, n_boot: int = 2000) -> None:
    """Lenga contra el resto de lo quemable en el MISMO evento y la MISMA banda."""
    otra = 3 - lenga   # la otra clase de lenga no cuenta como vecina
    t = t[t.clase != otra].assign(es=t.clase == lenga)
    s = t.groupby(["evento", "banda", "es"])[["expuesto_ha", "quemado_ha"]].sum().unstack("es")
    s = s.dropna()
    s = s[(s[("expuesto_ha", True)] >= min_ha) & (s[("expuesto_ha", False)] >= min_ha)]
    if s.empty:
        print(f"{CLASES[lenga]}: sin estratos comparables")
        return
    s = s.reset_index()
    print(f"\n{fuente} · {CLASES[lenga]} contra vecinas, mismo evento y banda "
          f"(estratos con >= {min_ha:.0f} ha de cada lado)")
    rng = np.random.default_rng(0)
    for nombre, sub in [("todas", s), *[(f">= {b}", s[s.banda >= b]) for b in (1000, 1200)],
                        *[(f"{b}-{b + 200}", s[s.banda == b]) for b in (800, 1000, 1200, 1400)]]:
        if sub.empty:
            continue
        def razon(x):
            fl = x[("quemado_ha", True)].sum() / x[("expuesto_ha", True)].sum()
            fv = x[("quemado_ha", False)].sum() / x[("expuesto_ha", False)].sum()
            return fl, fv, fl / fv if fv else np.nan
        fl, fv, r = razon(sub)
        ev = sub.evento.unique()
        boot = [razon(sub[sub.evento.isin(rng.choice(ev, len(ev)))])[2] for _ in range(n_boot)]
        lo, hi = np.nanpercentile(boot, [2.5, 97.5])
        fql = sub[("quemado_ha", True)] / sub[("expuesto_ha", True)]
        fqv = sub[("quemado_ha", False)] / sub[("expuesto_ha", False)]
        print(f"  {nombre:>10}: {len(ev):3d} eventos, {len(sub):3d} estratos · "
              f"fq lenga {fl:.3f} vecinas {fv:.3f} · razón {r:.2f} [IC95 {lo:.2f}-{hi:.2f}] · "
              f"lenga < vecinas en {(fql < fqv).sum()}/{len(sub)}")


if __name__ == "__main__":
    main()
