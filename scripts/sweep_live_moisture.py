"""B5 paso 4 — cuánto mueve el resultado el escalar de humedad del combustible vivo.

`LH_MOISTURE_CONTENT` y `LW_MOISTURE_CONTENT` están fijados en 60 % sin criterio. Con el
baseline eso era inocuo, porque TL3 no tiene carga viva; con el mapa de CCS-BAP, los
modelos SH, GS y TU son mayoría y el escalar pasa a ser driver de primer orden.

No tenemos todavía el valor medido (Bianchi & Defossé 2015), pero sí podemos medir la
sensibilidad, que es lo que decide si un escalar global alcanza o hace falta un ráster.

    uv run python scripts/sweep_live_moisture.py
    uv run python scripts/sweep_live_moisture.py --base data/elmfire/inputs/auditoria_b5 \\
        --sufijo _v5
"""
import argparse
import json
import re
import shutil
import urllib.request
from pathlib import Path

import numpy as np
import rasterio

BASE = Path("data/elmfire/inputs/cmp_ccsbap")
INPUTS, OUTPUTS = Path("data/elmfire/inputs"), Path("data/elmfire/outputs")
VALORES = [30.0, 60.0, 90.0, 120.0]
CELL_HA = 0.09


def correr(valor: float, base: Path = BASE, sufijo: str = "") -> dict:
    nombre = f"lfmc{sufijo}_{int(valor)}"
    inputs, outputs = INPUTS / nombre, OUTPUTS / nombre
    shutil.rmtree(inputs, ignore_errors=True)
    inputs.mkdir(parents=True)
    outputs.mkdir(parents=True, exist_ok=True)
    for f in base.iterdir():
        (inputs / f.name).unlink(missing_ok=True)
        if f.name == "elmfire.data":
            continue
        try:
            (inputs / f.name).hardlink_to(f)
        except OSError:
            shutil.copy2(f, inputs / f.name)

    texto = (base / "elmfire.data").read_text()
    for clave in ("LH_MOISTURE_CONTENT", "LW_MOISTURE_CONTENT"):
        texto = re.sub(rf"{clave}\s+=\s+[\d.]+", f"{clave}             = {valor}", texto)
    texto = texto.replace(f"inputs/{base.name}/", f"inputs/{nombre}/").replace(
        f"outputs/{base.name}/", f"outputs/{nombre}/")
    (inputs / "elmfire.data").write_text(texto)

    cuerpo = json.dumps({
        "elmfire_data_path": f"/app/data/elmfire/inputs/{nombre}/elmfire.data",
        "inputs_dir": f"/app/data/elmfire/inputs/{nombre}",
        "outputs_dir": f"/app/data/elmfire/outputs/{nombre}",
        "simulation_hours": 12, "dtdump_s": 3600.0,
    }).encode()
    req = urllib.request.Request("http://localhost:8001/simulate", data=cuerpo,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5400) as r:
        json.load(r)

    toa = sorted(outputs.glob("time_of_arrival*.tif"))
    with rasterio.open(toa[-1]) as src:
        arrival = src.read(1)
    with rasterio.open(inputs / "phi.tif") as src:
        phi = src.read(1)
    anillo = (arrival > 0) & ~(phi <= 0)
    fli = 0.0
    flin = sorted(outputs.glob("flin*.tif"))
    if flin:
        with rasterio.open(flin[-1]) as src:
            v = src.read(1)
        vals = v[anillo & (v > 0)]
        fli = float(np.median(vals)) if vals.size else 0.0
    return {"lfmc": valor, "anillo_ha": anillo.sum() * CELL_HA, "fli": fli}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, default=BASE)
    ap.add_argument("--sufijo", default="")
    args = ap.parse_args()
    print(f"Mapa: CCS-BAP · 12 h · todo igual salvo LH/LW · base {args.base}\n")
    resultados = [correr(v, args.base, args.sufijo) for v in VALORES]
    base = next(r["anillo_ha"] for r in resultados if r["lfmc"] == 60.0)
    print(f"{'LH/LW %':>9s}{'anillo (ha)':>14s}{'vs 60 %':>10s}{'FLI mediana':>14s}")
    for r in resultados:
        delta = "—" if r["lfmc"] == 60.0 else f"{100 * (r['anillo_ha'] - base) / base:+.0f}%"
        print(f"{r['lfmc']:9.0f}{r['anillo_ha']:14,.0f}{delta:>10s}{r['fli']:14,.0f}")


if __name__ == "__main__":
    main()
