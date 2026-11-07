"""Corre en local el ensamble GEFS de un pronóstico exportado de Railway (skill ensamble-local).

    uv run python scripts/ensamble_local.py paquete.json

Desde la raíz del checkout que tiene `data/` (el runner de `make dev-simulation` monta ./data en
/app/data). Rehace los insumos congelados que no son clima — estáticos de
data/operativo/estaticos/<año>/ recortados a la caja, la tabla de combustibles — más la
semilla `phi.tif` del paquete, y llama a `correr_ensamble` (31 miembros, ~35 min, uno por vez).
Deja `ensemble_agreement.json` en data/ensamble-local/<id>/ y borra las corridas de los miembros.
Reanudable: si el acuerdo ya está, no corre nada.
"""
import argparse
import asyncio
import base64
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# Desde el host el runner es localhost (el .env apunta al nombre del servicio en Docker).
os.environ.setdefault("ELMFIRE_RUNNER_URL", "http://localhost:8001")

import rasterio  # noqa: E402

from app.config import resolve_data_path, settings  # noqa: E402
from app.elmfire.builder import fuels_builder, namelist_writer  # noqa: E402
from app.operativo import servicio  # noqa: E402
from app.operativo.ensamble import correr_ensamble  # noqa: E402


def misma_grilla(a: Path, b: Path) -> None:
    """Los estáticos locales tienen que caer en la grilla de la semilla de Railway: otra fuente
    de combustibles u otro año darían un ensamble sobre otro dominio."""
    with rasterio.open(a) as x, rasterio.open(b) as y:
        if (x.crs, x.transform, x.shape) != (y.crs, y.transform, y.shape):
            raise ValueError(f"{a.name} {x.shape} {x.transform} no coincide con "
                             f"{b.name} {y.shape} {y.transform}")


def armar(paq: dict, insumos: Path) -> None:
    base = resolve_data_path(settings.data_dir) / "operativo" / "estaticos" / paq["pasada"][:4]
    faltan = [n for n in servicio.ESTATICOS if not (base / n).exists()]
    if faltan:
        sys.exit(f"faltan {faltan} en {base}: correr una vez el pronóstico demo en local")
    insumos.mkdir(parents=True, exist_ok=True)
    caja = tuple(paq["caja"])
    for nombre in servicio.ESTATICOS:
        servicio._recortar(base / nombre, caja, insumos / nombre)
    shutil.copy2(fuels_builder.FUEL_MODEL_TABLE, insumos / namelist_writer.FUEL_MODEL_FILE)
    (insumos / "phi.tif").write_bytes(base64.b64decode(paq["phi_b64"]))
    misma_grilla(insumos / "dem.tif", insumos / "phi.tif")


async def main(ruta: Path) -> None:
    paq = json.loads(ruta.read_text(encoding="utf-8"))
    salidas = resolve_data_path(settings.data_dir) / "ensamble-local" / paq["id"]
    acuerdo = salidas / "ensemble_agreement.json"
    if not acuerdo.is_file():
        armar(paq, salidas / "insumos")
        print(f"{paq['nombre']} {paq['pasada']}: ensamble GEFS (~35 min)…", flush=True)
        reloj = time.monotonic()
        meta = await correr_ensamble(
            ciclo=datetime.fromisoformat(paq["ciclo_gfs"]),
            inicio=datetime.fromisoformat(paq["t0"]), tstart_s=paq["tstart_s"],
            caja=tuple(paq["caja"]), insumos_base=salidas / "insumos", salidas_base=salidas,
            para_runner=servicio._para_runner,
        )
        shutil.rmtree(salidas / "ensamble", ignore_errors=True)   # ~1,7 GB de corridas
        print(f"{meta['effective_denominator']}/{meta['expected_member_count']} miembros "
              f"válidos en {(time.monotonic() - reloj) / 60:.0f} min", flush=True)
    print(f"subir con:\n  railway ssh -s api -- 'cd /app && uv run python "
          f"scripts/ensamble_registrar.py {paq['id']}' < {acuerdo}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paquete", type=Path, help="la salida de scripts/ensamble_exportar.py")
    asyncio.run(main(ap.parse_args().paquete))
