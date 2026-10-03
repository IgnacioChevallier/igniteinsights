"""Variantes del crosswalk CCS-BAP → FBFM40 sobre los mapas del benchmark v5.

Reetiqueta clases de CCS-BAP (N1|N2 o N1|N2|N3, opcionalmente sólo sobre una altura) en los
tres mapas que usan los paquetes v5, sin rehacer la agregación: cambia sólo las celdas cuyo
centro cae en un polígono de la clase y cuyo código es el que el crosswalk vigente le da a
esa clase (los bordes donde la moda eligió otra clase quedan como estaban). Así una variante
difiere del mapa base exactamente en lo declarado. Los mapas salen en la grilla de cada
preparación y entran a un protocolo `-v5x*` con el empaquetador `ampliar_mapas`, como fuente
`ccsbap-<nombre>` (DECISIONES-DIRECTOR.md).

    uv run python scripts/variante_crosswalk.py l1 '[{"clase": "OFL|Le", "a": 143}]'

"El código del crosswalk vigente" es el de este checkout: las variantes del loop L (x1-x3) se
armaron con el crosswalk anterior a su adopción (Estepa → GR3, remanente → GS3), que desde los
protocolos -v6 ya trae esos cambios.
"""
import argparse
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize

from app.elmfire.builder import fuels_builder as fb

SHP = {2013: Path("datasets/CH_2013_Ver20190521_Subido202000316/cob_2013_N3_aok_CH.shp"),
       2017: Path("datasets/CH_2017_Ver20190521_Subido202000316/cob_2017_N3_aok_CH.shp")}
# (mapa base, año, dem de su grilla, sufijo) — los que referencian los paquetes v5.
EXT = Path("data/elmfire/inputs/benchmark-2026-09-28-asp3-v5")
BASES = [(Path("data/static/fuel_maps/fbfm40_ccsbap.tif"), 2017,
          Path("data/elmfire/inputs/benchmark-aoi-asp3-v5/dem.tif"), "aoi"),
         (EXT / "fbfm40_ccsbap2013.tif", 2013, EXT / "dem.tif", "ext"),
         (EXT / "fbfm40_ccsbap2017.tif", 2017, EXT / "dem.tif", "ext")]
SALIDA = Path("data/static/fuel_maps/variantes")


def aplicar(fuel: np.ndarray, clases: np.ndarray, viejo: np.ndarray, dem: np.ndarray,
            cambio: dict) -> np.ndarray:
    """`clases`: True donde el centro de la celda cae en un polígono de la clase; `viejo`: el
    código que el crosswalk vigente le da a ese polígono."""
    m = clases & (fuel == viejo)
    if "altura_min" in cambio:
        m &= dem >= cambio["altura_min"]
    if "altura_max" in cambio:
        m &= dem < cambio["altura_max"]
    return np.where(m, cambio["a"], fuel).astype(fuel.dtype)


def construir(nombre: str, cambios: list[dict]) -> list[Path]:
    salidas = []
    gdfs = {a: gpd.read_file(p) for a, p in SHP.items()}
    for base, anio, dem_path, sufijo in BASES:
        with rasterio.open(base) as src:
            fuel, perfil = src.read(1), src.profile
        with rasterio.open(dem_path) as src:
            dem = src.read(1)
            if (src.shape, src.transform) != (fuel.shape, perfil["transform"]):
                raise ValueError(f"{dem_path} no está en la grilla de {base}")
        g = gdfs[anio].to_crs(perfil["crs"])
        g["clave"] = g.Ley_N1 + "|" + g.Ley_N2 + "|" + g.Ley_N3
        g["codigo"] = [fb.ccsbap_fuel_code(a, b, c)
                       for a, b, c in zip(g.Ley_N1, g.Ley_N2, g.Ley_N3)]
        for cambio in cambios:
            sel = g[g.clave.str.startswith(cambio["clase"] + "|") | (g.clave == cambio["clase"])]
            if sel.empty:
                continue
            viejo = rasterize(zip(sel.geometry, sel.codigo), out_shape=fuel.shape,
                              transform=perfil["transform"], fill=0, dtype="int32")
            fuel = aplicar(fuel, viejo > 0, viejo, dem, cambio)
        destino = SALIDA / nombre / f"fbfm40_ccsbap{anio}_{sufijo}.tif"
        destino.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(destino, "w", **(perfil | {"compress": "deflate"})) as dst:
            dst.write(fuel, 1)
        with rasterio.open(base) as src:
            n = int((src.read(1) != fuel).sum())
        print(f"{destino}: {n} celdas cambiadas")
        salidas.append(destino)
    (SALIDA / nombre / "cambios.json").write_text(json.dumps(cambios, indent=2, ensure_ascii=False))
    return salidas


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("nombre")
    ap.add_argument("cambios", help='JSON: [{"clase": "OFL|Le", "a": 143, "altura_min": 1300}]')
    args = ap.parse_args()
    construir(args.nombre, json.loads(args.cambios))
