"""B6 — correr el mismo incendio con los tres mapas de combustible.

Toma un directorio de preparación ya armado, le cambia sólo fbfm40.tif y los escalares de
humedad viva, y corre ELMFIRE una vez por mapa. Los rásters pesados se comparten por enlace
duro: son idénticos entre corridas y copiarlos triplicaría 1 GB por nada.

    uv run python scripts/run_three_maps.py --base data/elmfire/inputs/<prep> --sufijo b5
"""
import argparse
import json
import re
import shutil
import urllib.request
from pathlib import Path

from app.elmfire.builder.namelist_writer import (
    DEFAULT_LH_MOISTURE_PCT,
    DEFAULT_LW_MOISTURE_PCT,
)

MAPAS = Path("data/static/fuel_maps")
INPUTS, OUTPUTS = Path("data/elmfire/inputs"), Path("data/elmfire/outputs")


def preparar(base: Path, fuente: str, sufijo: str, lh: float, lw: float, mapas: str) -> str:
    nombre = f"cmp{sufijo}_{fuente}"
    inputs, outputs = INPUTS / nombre, OUTPUTS / nombre
    shutil.rmtree(inputs, ignore_errors=True)
    inputs.mkdir(parents=True)
    outputs.mkdir(parents=True, exist_ok=True)

    for f in base.iterdir():
        if f.name in ("elmfire.data", "fbfm40.tif"):
            continue
        try:
            (inputs / f.name).hardlink_to(f)
        except OSError:
            shutil.copy2(f, inputs / f.name)
    shutil.copy2(mapas.format(fuente=fuente), inputs / "fbfm40.tif")

    texto = (base / "elmfire.data").read_text()
    for clave, valor in (("LH_MOISTURE_CONTENT", lh), ("LW_MOISTURE_CONTENT", lw)):
        texto = re.sub(rf"{clave}\s+=\s+[\d.]+", f"{clave}             = {valor}", texto)
    texto = re.sub(r"inputs/[^/']+/", f"inputs/{nombre}/", texto)
    texto = re.sub(r"outputs/[^/']+/", f"outputs/{nombre}/", texto)
    (inputs / "elmfire.data").write_text(texto)
    return nombre


def correr(nombre: str) -> None:
    cuerpo = json.dumps({
        "elmfire_data_path": f"/app/data/elmfire/inputs/{nombre}/elmfire.data",
        "inputs_dir": f"/app/data/elmfire/inputs/{nombre}",
        "outputs_dir": f"/app/data/elmfire/outputs/{nombre}",
        "simulation_hours": 12, "dtdump_s": 3600.0,
    }).encode()
    req = urllib.request.Request("http://localhost:8001/simulate", data=cuerpo,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=7200) as r:
        json.load(r)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--sufijo", default="")
    ap.add_argument("--lh", type=float, default=DEFAULT_LH_MOISTURE_PCT)
    ap.add_argument("--lw", type=float, default=DEFAULT_LW_MOISTURE_PCT)
    # Los mapas de data/static/fuel_maps se regeneraron sobre la caja del benchmark: para
    # re-correr una comparación vieja, sus propios fbfm40
    # (p. ej. data/elmfire/inputs/cmp_b5_{fuente}/fbfm40.tif).
    ap.add_argument("--mapas", default=str(MAPAS / "fbfm40_{fuente}.tif"))
    args = ap.parse_args()

    print(f"Base: {args.base} · LH {args.lh} % · LW {args.lw} %")
    for fuente in ("worldcover", "mapbiomas", "ccsbap"):
        nombre = preparar(args.base, fuente, args.sufijo, args.lh, args.lw, args.mapas)
        print(f"  corriendo {nombre} …", flush=True)
        correr(nombre)
        print(f"  listo {nombre}", flush=True)
    fuentes = ("worldcover", "mapbiomas", "ccsbap")
    etiquetas = " ".join(f"{args.sufijo.lstrip('_')}_{f}" if args.sufijo else f for f in fuentes)
    print(f"\nComparar con: uv run python scripts/compare_fuel_map_runs.py --runs {etiquetas}")


if __name__ == "__main__":
    main()
