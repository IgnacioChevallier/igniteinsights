"""Años con quema según otras fuentes además de Hansen: dNBR ∪ MCD64A1.

Ver docs/resultados/LO-YA-QUEMADO-PROPUESTA.md §5 (paso 2), §10 y §11. Sale en
data/raw/cicatrices/otras_quemas_<grilla>.tif como máscara de bits uint32: el bit i es una quema
en el año 2001 + i (fuels_builder.last_burn_before). Todos los años y no sólo el último: al simular
un incendio, su propia cicatriz (y las de su temporada) no puede tapar las quemas anteriores de
esas celdas.
La app la lee de `settings.otras_quemas_path` (grilla `ext`) junto con Hansen, y
`fuels_builder.reassign_burns_by_age` decide con el mapa de combustible cuál cuenta: en bosque,
sólo Hansen mientras haya publicado ese año. El dosel sigue saliendo de Hansen solo.

- **Máscaras dNBR** de los runs vigentes de ../mask-dataset-gen (20-30 m), con el año de inicio
  del evento. Dentro de lo que cada evento observó mandan sobre MCD64A1 para ese año.
- **MCD64A1** (~463 m, scripts/exportar_mcd64a1.py): el resto.

    ../mask-dataset-gen/.venv/bin/python scripts/exportar_mcd64a1.py
    uv run python scripts/anio_quema.py

Para el benchmark (protocolo LYQ-3) la capa sale sin las máscaras de los incendios de prueba:
sus cicatrices son la referencia de la prueba y no entran como insumo de la calibración; esos
incendios quedan sólo con MCD64A1.

    uv run python scripts/anio_quema.py --sin-prueba

La versión de LYQ-2 (commit 8ddff5a) escribía una sola capa con el último año de Hansen ∪ dNBR ∪
MCD64A1, y decidía el bosque por la cobertura de Hansen 2000 (§10.2).
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
MCD64A1 = Path("data/raw/mcd64a1/mcd64a1_anios_aoi.tif")   # banda i = año 2001 + i
DATASET = Path("../mask-dataset-gen")
# El run vigente de cada evento (columna "Resultado" de ../mask-dataset-gen/README.md).
RUN_VIGENTE = {"los-alerces-2023": "event-filter-002"}
SALIDA = Path("data/raw/cicatrices")


def a_la_grilla(origen, transform, crs, perfil, remuestreo=Resampling.nearest) -> np.ndarray:
    destino = np.zeros((perfil["height"], perfil["width"]), dtype=origen.dtype)
    reproject(origen, destino, src_transform=transform, src_crs=crs,
              dst_transform=perfil["transform"], dst_crs=perfil["crs"], resampling=remuestreo)
    return destino


def dnbr(perfil, excluir: set[str]) -> tuple[np.ndarray, dict[int, np.ndarray], dict]:
    """Bits de las quemas de las máscaras, y lo que observó cada año (ahí el dNBR manda)."""
    bits = np.zeros((perfil["height"], perfil["width"]), dtype=np.uint32)
    observado: dict[int, np.ndarray] = {}
    eventos = {}
    for config in sorted((DATASET / "config" / "incendios").glob("*.json")):
        evento = json.loads(config.read_text())
        nombre = evento["event_id"]
        if nombre in excluir:
            continue
        anio = int(evento["fire_start_date"][:4])
        run = DATASET / "dataset" / nombre / "runs" / RUN_VIGENTE.get(nombre, "event-filter-001")
        visto = observado.setdefault(anio, np.zeros(bits.shape, bool))
        tiles = sorted((run / "mascaras").glob("*.tif"))
        for tile in tiles:
            with rasterio.open(tile) as src:
                mascara = src.read(1)
                quemado = a_la_grilla(mascara, src.transform, src.crs, perfil,
                                      Resampling.max) > 0
                visto |= a_la_grilla(np.ones_like(mascara), src.transform, src.crs, perfil) > 0
            bits[quemado] |= np.uint32(1 << (anio - 2001))
        eventos[nombre] = {"run": run.name, "anio": anio, "tiles": len(tiles)}
    return bits, observado, eventos


def construir(grilla: Path, salida: Path, excluir: set[str]) -> dict:
    with rasterio.open(grilla) as ref:
        perfil = ref.profile | {"dtype": "uint32", "count": 1, "nodata": None,
                                "compress": "deflate", "predictor": 2}
    bits, observado, eventos = dnbr(perfil, excluir)
    with rasterio.open(MCD64A1) as src:
        for i in range(src.count):
            anio = 2001 + i
            mcd = a_la_grilla(src.read(i + 1), src.transform, src.crs, perfil) > 0
            if anio in observado:
                mcd &= ~observado[anio]   # ese año, ahí, lo dice el dNBR
            bits[mcd] |= np.uint32(1 << i)

    salida.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(salida, "w", **perfil) as dst:
        dst.write(bits, 1)
    celda_ha = abs(perfil["transform"].a * perfil["transform"].e) / 1e4
    resumen = {
        "grilla": str(grilla),
        "codificacion": "uint32, bit i = quema en el año 2001 + i",
        "fuentes": {"mcd64a1": MCD64A1.name, "dnbr": eventos, "dnbr_excluidos": sorted(excluir)},
        "ha_por_anio": {2001 + i: round(float(((bits >> i) & 1).sum() * celda_ha))
                        for i in range(32) if ((bits >> i) & 1).any()},
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
        salida = SALIDA / f"otras_quemas_{nombre}{'_sin_prueba' if sin_prueba else ''}.tif"
        print(salida, json.dumps(construir(grilla, salida, excluir)["ha_por_anio"]))
