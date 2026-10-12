"""Año de la última quema por celda en la grilla de la app: Hansen ∪ dNBR ∪ MCD64A1.

Ver docs/resultados/LO-YA-QUEMADO-PROPUESTA.md §1, §4, §5 (paso 2) y §10. Sale con la
codificación de Hansen `lossyear` (0 = sin quema, n = 2000 + n) en
data/raw/cicatrices/anio_quema_<grilla>.tif. **La app no la usa**: el protocolo LYQ-2 no pasó
(§10). El bosque se decide acá por la cobertura de Hansen 2000 y en la regla por el código de
combustible, y las plantaciones posteriores a 2000 quedan en el medio.

- **Hansen GFC `lossyear`** (30 m): pérdida de dosel que reemplaza al rodal, hasta su último año.
- **Máscaras dNBR** de los runs vigentes de ../mask-dataset-gen (20-30 m), con el año de inicio
  del evento. Dentro de lo que cada evento observó mandan sobre MCD64A1 para ese año.
- **MCD64A1** (~463 m, scripts/exportar_mcd64a1.py): relleno.

En bosque (cobertura de Hansen 2000 ≥ 30 %, el umbral por defecto de Global Forest Watch) sólo
Hansen dice si el rodal fue reemplazado, mientras haya publicado ese año: un fuego de superficie
que dejó el bosque en pie no cambia el combustible (Landesmann et al. 2021). Después del último
año de Hansen, cualquier fuente cuenta.

    uv run python scripts/exportar_mcd64a1.py   # (con el venv de ../mask-dataset-gen)
    uv run python scripts/anio_quema.py

Para el benchmark (protocolo LYQ-2) la capa sale sin las máscaras de los incendios de prueba:
sus cicatrices son la referencia de la prueba y no entran como insumo de la calibración; esos
incendios quedan sólo con MCD64A1.

    uv run python scripts/anio_quema.py --sin-prueba
"""
import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

# Las grillas de las preparaciones del benchmark (scripts/perdida_hansen.py): `ext` cubre el AOI
# vigente de la app (settings.aoi_*, borde norte en -41,90) y es la que usa la app.
GRILLAS = {"aoi": Path("data/elmfire/inputs/benchmark-aoi-asp3-v6/dem.tif"),
           "ext": Path("data/elmfire/inputs/benchmark-2026-09-28-asp3-v6/dem.tif")}
HANSEN = Path("data/raw/hansen/Hansen_GFC-2025-v1.13_lossyear_40S_080W.tif")
HANSEN_ULTIMO = 2025
COBERTURA = Path("data/static/canopy/2026-05-24/hansen_treecover2000.tif")
BOSQUE_PCT = 30
MCD64A1 = Path("data/raw/mcd64a1/mcd64a1_anio_quema_aoi.tif")
DATASET = Path("../mask-dataset-gen")
# El run vigente de cada evento (columna "Resultado" de ../mask-dataset-gen/README.md).
RUN_VIGENTE = {"los-alerces-2023": "event-filter-002"}
SALIDA = Path("data/raw/cicatrices")


def a_la_grilla(origen, transform, crs, perfil, remuestreo=Resampling.nearest) -> np.ndarray:
    destino = np.zeros((perfil["height"], perfil["width"]), dtype=origen.dtype)
    reproject(origen, destino, src_transform=transform, src_crs=crs,
              dst_transform=perfil["transform"], dst_crs=perfil["crs"], resampling=remuestreo)
    return destino


def leer(ruta: Path, perfil, remuestreo=Resampling.nearest) -> np.ndarray:
    with rasterio.open(ruta) as src:
        return a_la_grilla(src.read(1), src.transform, src.crs, perfil, remuestreo)


def dnbr(perfil, excluir: set[str]) -> tuple[np.ndarray, np.ndarray, dict]:
    """Año de la quema más reciente según las máscaras, y año observado (dNBR manda ahí)."""
    anio = np.zeros((perfil["height"], perfil["width"]), dtype=np.uint8)
    observado = np.zeros_like(anio)
    eventos = {}
    for config in sorted((DATASET / "config" / "incendios").glob("*.json")):
        evento = json.loads(config.read_text())
        nombre = evento["event_id"]
        if nombre in excluir:
            continue
        a = int(evento["fire_start_date"][:4]) - 2000
        run = DATASET / "dataset" / nombre / "runs" / RUN_VIGENTE.get(nombre, "event-filter-001")
        tiles = sorted((run / "mascaras").glob("*.tif"))
        for tile in tiles:
            with rasterio.open(tile) as src:
                mascara = src.read(1)
                quemado = a_la_grilla(mascara, src.transform, src.crs, perfil,
                                      Resampling.max) > 0
                visto = a_la_grilla(np.ones_like(mascara), src.transform, src.crs, perfil) > 0
            anio[quemado] = np.maximum(anio[quemado], a)
            observado[visto] = np.maximum(observado[visto], a)
        eventos[nombre] = {"run": run.name, "anio": 2000 + a, "tiles": len(tiles)}
    return anio, observado, eventos


def construir(grilla: Path, salida: Path, excluir: set[str]) -> dict:
    with rasterio.open(grilla) as ref:
        perfil = ref.profile | {"dtype": "uint8", "count": 1, "nodata": 0,
                                "compress": "deflate", "predictor": 2}
    hansen = leer(HANSEN, perfil)
    bosque = leer(COBERTURA, perfil, Resampling.average) >= BOSQUE_PCT
    anio_dnbr, observado, eventos = dnbr(perfil, excluir)
    mcd = leer(MCD64A1, perfil)
    mcd[(observado > 0) & (mcd == observado)] = 0   # ese año, ahí, lo dice el dNBR

    otras = np.maximum(anio_dnbr, mcd)
    admitida = ~bosque | (otras > HANSEN_ULTIMO - 2000)
    anio = np.maximum(hansen, np.where(admitida, otras, 0)).astype(np.uint8)

    salida.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(salida, "w", **perfil) as dst:
        dst.write(anio, 1)
    celda_ha = abs(perfil["transform"].a * perfil["transform"].e) / 1e4
    resumen = {
        "grilla": str(grilla),
        "fuentes": {"hansen": HANSEN.name, "hansen_ultimo": HANSEN_ULTIMO,
                    "mcd64a1": MCD64A1.name, "bosque_pct": BOSQUE_PCT, "dnbr": eventos,
                    "dnbr_excluidos": sorted(excluir)},
        "ha_por_anio": {2000 + int(a): round(float((anio == a).sum() * celda_ha))
                        for a in np.unique(anio) if a},
    }
    salida.with_suffix(".json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False))
    return resumen


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--sin-prueba", action="store_true")
    sin_prueba = args.parse_args().sin_prueba
    excluir = set()
    if sin_prueba:
        prueba = json.loads(Path("benchmarks/particion.json").read_text())["prueba"]
        excluir = {c.split("/")[0] for casos in prueba.values() for c in casos}
    for nombre, grilla in GRILLAS.items():
        salida = SALIDA / f"anio_quema_{nombre}{'_sin_prueba' if sin_prueba else ''}.tif"
        print(salida, json.dumps(construir(grilla, salida, excluir)["ha_por_anio"]))
