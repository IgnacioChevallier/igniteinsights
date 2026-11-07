"""Sube y registra el ensamble de un pronóstico corrido en local (skill ensamble-local).

    railway ssh -s api -- 'cd /app && uv run python scripts/ensamble_registrar.py ID' \\
        < data/ensamble-local/ID/ensemble_agreement.json

Lee el contrato por stdin, lo valida y recién entonces lo deja en la salida del pronóstico:
desde ahí lo sirve /simulations/{id}/ensemble-agreement y /operativo/estado marca
`ensamble: true`. El manifiesto queda en `simulation_runs.elmfire_config["ensamble"]`.
"""
import asyncio
import json
import os
import sys
import uuid

from app.db import repository
from app.db.session import async_session_factory
from app.domain.models import Pronostico
from app.operativo import servicio
from app.operativo.ensamble import MIN_MIEMBROS_VALIDOS


def validar(contrato: dict) -> dict:
    """El manifiesto del contrato, si es un acuerdo de ensamble con miembros suficientes."""
    if contrato.get("layer", {}).get("id") != "ensemble_agreement":
        raise ValueError("no es un ensemble_agreement.json (layer.id)")
    meta = contrato.get("metadata", {})
    if meta.get("valid_members", 0) < MIN_MIEMBROS_VALIDOS:
        raise ValueError(f"{meta.get('valid_members')} miembros válidos; "
                         f"mínimo {MIN_MIEMBROS_VALIDOS}")
    if not contrato.get("thresholds"):
        raise ValueError("sin umbrales")
    return meta


async def main(pronostico_id: uuid.UUID, texto: str) -> None:
    try:
        meta = validar(json.loads(texto))
    except (ValueError, AttributeError) as exc:
        sys.exit(f"contrato inválido: {exc}")
    async with async_session_factory() as s:
        p = await s.get(Pronostico, pronostico_id)
        if p is None or p.simulacion_id is None:
            sys.exit(f"no hay pronóstico con P-24 {pronostico_id}")
        destino = servicio.salidas_de(p.id) / "ensemble_agreement.json"
        tmp = destino.with_suffix(".tmp")
        tmp.write_text(texto, encoding="utf-8")
        os.replace(tmp, destino)
        sim = await repository.get_simulation_run(s, p.simulacion_id)
        assert sim is not None   # FK de pronosticos.simulacion_id
        sim.elmfire_config = {**(sim.elmfire_config or {}), "ensamble": meta}
        await s.commit()
    print(f"{p.nombre} {p.pasada:%d-%m %H:%M}: {meta['valid_members']}/"
          f"{meta['expected_members']} miembros, ciclo {meta['weather_cycle']} → {destino}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    asyncio.run(main(uuid.UUID(sys.argv[1]), sys.stdin.read()))
