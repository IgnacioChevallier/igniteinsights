"""El paquete de un pronóstico para correr su ensamble GEFS en local (skill ensamble-local).

    railway ssh -s api -- 'cd /app && uv run python scripts/ensamble_exportar.py' > paquete.json
    railway ssh -s api -- 'cd /app && uv run python scripts/ensamble_exportar.py --id ID' > …

Por defecto, el último pronóstico vivo `listo`; con `--id`, cualquiera (también uno demo). El
JSON lleva los metadatos de la ventana y, en base64, los insumos congelados que no son clima
tal como los arma `servicio.congelar`: los estáticos de esta base recortados a la caja, la
tabla de combustibles y `phi.tif` (la semilla). Así el ensamble local no depende de que los
estáticos de la computadora estén al día (unos 20 MB).
"""
import argparse
import asyncio
import base64
import json
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

from sqlalchemy import select

from app.db import repository
from app.db.session import async_session_factory
from app.domain.models import Pronostico
from app.elmfire.builder import fuels_builder, namelist_writer
from app.operativo import servicio


def paquete(p: Pronostico, caja: list[float], insumos: Path) -> dict:
    t0 = p.pasada.replace(minute=0, second=0, microsecond=0)
    return {
        "id": str(p.id), "simulacion_id": str(p.simulacion_id), "nombre": p.nombre,
        "modo": p.modo, "pasada": p.pasada.isoformat(),
        "ciclo_gfs": p.ciclo_gfs.isoformat() if p.ciclo_gfs else None,
        "caja": list(caja), "t0": t0.isoformat(), "tstart_s": (p.pasada - t0).total_seconds(),
        "insumos_b64": {f.name: base64.b64encode(f.read_bytes()).decode()
                        for f in sorted(insumos.iterdir())},
    }


async def main(pronostico_id: uuid.UUID | None) -> None:
    async with async_session_factory() as s:
        if pronostico_id:
            p = await s.get(Pronostico, pronostico_id)
        else:
            p = (await s.execute(
                select(Pronostico).where(Pronostico.modo == "vivo", Pronostico.estado == "listo")
                .order_by(Pronostico.pasada.desc()).limit(1))).scalar_one_or_none()
        if p is None:
            sys.exit("no hay pronóstico " + (str(pronostico_id) if pronostico_id
                                             else "vivo listo: pasar --id (p. ej. uno demo)"))
        if p.estado != "listo" or p.simulacion_id is None:
            sys.exit(f"el pronóstico {p.id} está {p.estado}: no tiene P-24 que ensamblar")
        sim = await repository.get_simulation_run(s, p.simulacion_id)
        assert sim is not None   # FK de pronosticos.simulacion_id
        caja = (sim.elmfire_config or {})["operativo"]["caja"]
        base = await servicio.estaticos(s, p.pasada.year)
    phi = servicio.insumos_de(p.id) / "phi.tif"
    if not phi.is_file():
        sys.exit(f"{phi} no está (podado antes de que podar conservara phi.tif)")
    with tempfile.TemporaryDirectory() as tmp:
        insumos = Path(tmp)
        for nombre in servicio.ESTATICOS:
            servicio._recortar(base / nombre, tuple(caja), insumos / nombre)
        shutil.copy2(fuels_builder.FUEL_MODEL_TABLE, insumos / namelist_writer.FUEL_MODEL_FILE)
        shutil.copy2(phi, insumos / "phi.tif")
        print(json.dumps(paquete(p, caja, insumos)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--id", type=uuid.UUID, help="pronóstico (por defecto el último vivo listo)")
    asyncio.run(main(ap.parse_args().id))
