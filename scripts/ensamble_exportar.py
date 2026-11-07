"""El paquete de un pronóstico para correr su ensamble GEFS en local (skill ensamble-local).

    railway ssh -s api -- 'cd /app && uv run python scripts/ensamble_exportar.py' > paquete.json
    railway ssh -s api -- 'cd /app && uv run python scripts/ensamble_exportar.py --id ID' > …

Por defecto, el último pronóstico vivo `listo`; con `--id`, cualquiera (también uno demo). El
JSON lleva todo lo que `ensamble_local.py` no puede rehacer en la computadora: los metadatos
de la ventana y `phi.tif` (la semilla, que sale de las detecciones de esta base) en base64.
"""
import argparse
import asyncio
import base64
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import select

from app.db import repository
from app.db.session import async_session_factory
from app.domain.models import Pronostico
from app.operativo import servicio


def paquete(p: Pronostico, caja: list[float], phi: bytes) -> dict:
    t0 = p.pasada.replace(minute=0, second=0, microsecond=0)
    return {
        "id": str(p.id), "simulacion_id": str(p.simulacion_id), "nombre": p.nombre,
        "modo": p.modo, "pasada": p.pasada.isoformat(),
        "ciclo_gfs": p.ciclo_gfs.isoformat() if p.ciclo_gfs else None,
        "caja": list(caja), "t0": t0.isoformat(), "tstart_s": (p.pasada - t0).total_seconds(),
        "phi_b64": base64.b64encode(phi).decode(),
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
    phi = servicio.insumos_de(p.id) / "phi.tif"
    if not phi.is_file():
        sys.exit(f"{phi} no está (podado antes de que podar conservara phi.tif)")
    print(json.dumps(paquete(p, caja, Path(phi).read_bytes())))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--id", type=uuid.UUID, help="pronóstico (por defecto el último vivo listo)")
    asyncio.run(main(ap.parse_args().id))
