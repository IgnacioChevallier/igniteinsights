"""Recortar las bandas de meteorología que la corrida no va a leer.

ELMFIRE lee la banda n como el clima en `n × DT_METEOROLOGY`, con el tiempo absoluto (la banda 0
es T = 0, no TSTART), así que una corrida que termina en TSTOP sólo necesita
`floor(TSTOP / DT) + 1` bandas desde la 0, y `NUM_METEOROLOGY_TIMES` tiene que decir cuántas
quedan: si declara más, ELMFIRE salta el caso sin quemar nada. La ingesta baja
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

    return math.floor(valor("SIMULATION_TSTOP") / valor("DT_METEOROLOGY")) + 1


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
            texto = f.read_text().replace(args.base.name, destino.name)
            (destino / f.name).write_text(re.sub(
                r"(NUM_METEOROLOGY_TIMES\s+=\s+)\d+",
                lambda m: m.group(1) + str(min(n, int(m.group(0).split("=")[1]))), texto))
        else:
            (destino / f.name).hardlink_to(f)
    print(f"Listo: {destino}")


if __name__ == "__main__":
    main()
