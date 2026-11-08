"""Re-arma una preparación de la app anterior a la auditoría física con las correcciones de
los hallazgos 1–5 (docs/resultados/modelo/auditoria.md), para re-medir los experimentos
del documento de combustibles (§7.4) sobre los mismos insumos.

Toma el directorio de una corrida vieja (p. ej. `cmp_b5_ccsbap`) y escribe otro nuevo, sin
tocar el viejo:
- `phi.tif` en ±1 con la misma semilla (`phi <= 0`; hallazgo 2);
- `wd.tif` por el camino corto (`wd_for_elmfire`; hallazgo 3);
- el dosel re-derivado con `canopy_builder` (hallazgo 4);
- `elmfire.data` de `write_namelist`, con el TSTART, el TSTOP y la humedad viva del namelist
  viejo: escribe `NUM_METEOROLOGY_TIMES` (hallazgo 1) y rellena el clima al este (hallazgo 5).
El resto, hardlinks. `--clima-desde` toma el clima de otra preparación de la misma grilla (el de
`cmp_aoi_*` se había recortado mal a 13 bandas); `--bandas` se queda con las primeras N.

    uv run python scripts/corregir_preparacion_legado.py --desde cmp_b5_ccsbap \\
        --salida auditoria_b5
"""
import argparse
import os
import re
import shutil
from pathlib import Path

import numpy as np
import rasterio

from app.elmfire.builder import canopy_builder, ignition_builder, namelist_writer
from app.elmfire.builder.weather_builder import wd_for_elmfire

INPUTS, OUTPUTS = Path("data/elmfire/inputs"), Path("data/elmfire/outputs")
CONTENEDOR = Path("/app")   # el runner monta ./data en /app/data
CLIMA = tuple(f"{n}.tif" for n in namelist_writer.WEATHER_RASTERS)
REHECHOS = ("phi.tif", "wd.tif", "cc.tif", "cbh.tif", "cbd.tif", "elmfire.data")


def _escribir_bandas(origen: Path, destino: Path, bandas: int | None, transformar=None) -> None:
    with rasterio.open(origen) as src:
        datos = src.read(list(range(1, (bandas or src.count) + 1)))
        perfil = src.profile | {"count": datos.shape[0], "compress": "deflate", "predictor": 3}
    with rasterio.open(destino, "w", **perfil) as dst:
        dst.write(transformar(datos) if transformar else datos)


def _namelist(texto: str, clave: str) -> float:
    return float(re.search(rf"{clave}\s*=\s*([\d.]+)", texto).group(1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", required=True, help="corrida vieja bajo data/elmfire/inputs")
    ap.add_argument("--salida", required=True)
    ap.add_argument("--clima-desde", default=None)
    ap.add_argument("--bandas", type=int, default=None)
    args = ap.parse_args()
    desde, salida = INPUTS / args.desde, INPUTS / args.salida
    clima = INPUTS / (args.clima_desde or args.desde)
    salida.mkdir(parents=True)   # nueva: las corridas viejas son la evidencia del documento

    for ruta in sorted(desde.iterdir()):
        if ruta.is_file() and ruta.name not in REHECHOS + CLIMA:
            os.link(ruta, salida / ruta.name)
    for nombre in CLIMA:
        if nombre == "wd.tif":
            _escribir_bandas(clima / nombre, salida / nombre, args.bandas, wd_for_elmfire)
        elif args.bandas:
            _escribir_bandas(clima / nombre, salida / nombre, args.bandas)
        else:
            os.link(clima / nombre, salida / nombre)

    with rasterio.open(desde / "phi.tif") as src:
        semilla = src.read(1) <= 0
    ignition_builder.build_ignition_from_mask(semilla, salida / "dem.tif", salida)
    assert np.array_equal(semilla, rasterio.open(salida / "phi.tif").read(1) < 0)

    shutil.copyfile(desde / "cc.tif", salida / "cc.tif")
    canopy_builder.derive_cbh_cbd(salida / "cc.tif", salida / "ch.tif", salida / "cbh.tif",
                                  salida / "cbd.tif")

    viejo = (desde / "elmfire.data").read_text()
    tstart, tstop = _namelist(viejo, "SIMULATION_TSTART"), _namelist(viejo, "SIMULATION_TSTOP")
    salidas = OUTPUTS / args.salida
    salidas.mkdir(parents=True, exist_ok=True)
    namelist_writer.write_namelist(
        salida.resolve(), salidas.resolve(), simulation_hours=round((tstop - tstart) / 3600),
        output_path=salida / "elmfire.data", simulation_tstart_s=tstart,
        lh_moisture_pct=_namelist(viejo, "LH_MOISTURE_CONTENT"),
        lw_moisture_pct=_namelist(viejo, "LW_MOISTURE_CONTENT"))
    texto = (salida / "elmfire.data").read_text()
    for ruta in (salida, salidas):
        texto = texto.replace(str(ruta.resolve()), str(CONTENEDOR / ruta))
    (salida / "elmfire.data").write_text(texto)
    print(f"{salida}: TSTART {tstart:.0f} s, TSTOP {tstop:.0f} s, semilla "
          f"{semilla.sum() * 0.09:,.0f} ha")


if __name__ == "__main__":
    main()
