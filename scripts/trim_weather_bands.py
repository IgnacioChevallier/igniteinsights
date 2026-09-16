"""Recortar las bandas de meteorología que la corrida no va a leer.

ELMFIRE lee la banda n como el clima en `TSTART + n × DT_METEOROLOGY`, así que una corrida
que termina en TSTOP sólo necesita `ceil((TSTOP - TSTART) / DT) + 1` bandas. La ingesta baja
24 h de pronóstico por defecto, y sobre el AOI completo (8,3 M celdas) esas bandas de más son
unos 2 GB de RAM que hacen que el OOM killer mate la simulación.

Deja un directorio de preparación equivalente, con los rásters de clima recortados y el
resto enlazado en duro.

    uv run python scripts/trim_weather_bands.py --base data/elmfire/inputs/<prep>
"""
import argparse
import math
import re
import shutil
from pathlib import Path

import rasterio

CLIMA = ("ws.tif", "wd.tif", "m1.tif", "m10.tif", "m100.tif")


def bandas_necesarias(namelist: Path) -> int:
    texto = namelist.read_text()

    def valor(clave: str) -> float:
        return float(re.search(rf"{clave}\s+=\s+([\d.]+)", texto).group(1))

    span = valor("SIMULATION_TSTOP") - valor("SIMULATION_TSTART")
    return math.ceil(span / valor("DT_METEOROLOGY")) + 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    destino = args.out or args.base.parent / f"{args.base.name}_trim"

    n = bandas_necesarias(args.base / "elmfire.data")
    shutil.rmtree(destino, ignore_errors=True)
    destino.mkdir(parents=True)
    print(f"Bandas necesarias: {n}")

    for f in sorted(args.base.iterdir()):
        if f.name in CLIMA:
            with rasterio.open(f) as src:
                if src.count <= n:
                    (destino / f.name).hardlink_to(f)
                    continue
                perfil = src.profile | {"count": n}
                with rasterio.open(destino / f.name, "w", **perfil) as dst:
                    for banda in range(1, n + 1):
                        dst.write(src.read(banda), banda)
            print(f"  {f.name}: recortado a {n} bandas")
        elif f.name == "elmfire.data":
            (destino / f.name).write_text(
                f.read_text().replace(args.base.name, destino.name)
            )
        else:
            (destino / f.name).hardlink_to(f)
    print(f"Listo: {destino}")


if __name__ == "__main__":
    main()
