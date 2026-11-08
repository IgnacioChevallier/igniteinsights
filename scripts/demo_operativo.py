"""Precalcula la demostración del producto: lo que habría visto el panel en un incendio pasado.

    uv run python scripts/demo_operativo.py 2026-01-05 2026-01-09

Ingiere FIRMS de esos días y recorre cada pasada VIIRS con el reloj en `pasada + latencia`,
llamando al mismo `servicio.tick` que el cron del modo en vivo (docs/producto.md §2C).
Al final deja el modo en demo con el reloj en el primer pronóstico. Reanudable: un tick no repite
una pasada ya pronosticada. Corre desde el host contra el runner de docker-compose; el runner
aguanta una corrida por vez, así que no lanzarlo con otra cola de ELMFIRE en curso.
"""
import argparse
import asyncio
import os
from datetime import UTC, date, datetime, timedelta

# Desde el host el runner es localhost (el .env apunta al nombre del servicio en Docker).
os.environ.setdefault("ELMFIRE_RUNNER_URL", "http://localhost:8001")

import pandas as pd  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db import repository  # noqa: E402
from app.db.session import async_session_factory  # noqa: E402
from app.domain.models import Pronostico  # noqa: E402
from app.ingestion.satellite.firms.service import run_firms_ingestion  # noqa: E402
from app.operativo import servicio  # noqa: E402
from app.validation import pronostico  # noqa: E402

INICIO_DEMO = datetime(2026, 1, 5, 19, 20, tzinfo=UTC)


async def main(desde: date, hasta: date) -> None:
    async with async_session_factory() as session:
        op = await servicio.leer_operativo(session)
        op.demo_desde = INICIO_DEMO   # antes de los ticks: tick y estado lo leen de acá
        await session.commit()
        dia = desde - timedelta(days=1)   # lo de la víspera también siembra
        while dia <= hasta:
            dias = min(5, (hasta - dia).days + 1)
            await run_firms_ingestion(session, day_range=dias, start_date=dia)
            dia += timedelta(days=dias)

        aoi = await repository.get_or_create_default_aoi(session)
        inicio = datetime.combine(desde, datetime.min.time(), tzinfo=UTC)
        fin = datetime.combine(hasta + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
        features = await repository.get_active_fires(session, since=inicio, aoi_id=aoi.id,
                                                     until=fin)
        tiempos = pd.Series(pd.to_datetime([f["properties"]["acq_datetime"] for f in features],
                                           utc=True))
        pasadas = [
            t.to_pydatetime() for t in pronostico.pasadas(tiempos)
            if t.to_pydatetime() >= INICIO_DEMO
        ]
        print(f"{len(features)} detecciones, {len(pasadas)} pasadas", flush=True)
        for pasada in pasadas:
            ahora = pasada + timedelta(hours=pronostico.LATENCIA_FIRMS_H, minutes=1)
            hechos = await servicio.tick(
                session,
                ahora,
                modo="demo",
                ingerir=False,
            )
            for h in hechos:
                print(f"  {pasada:%d-%m %H:%M} {h['nombre']}: {h['estado']}"
                      + (f" ({h['error']})" if h["error"] else ""), flush=True)

        primero = (await session.execute(
            select(Pronostico.disponible).where(Pronostico.modo == "demo",
                                                Pronostico.estado == "listo",
                                                Pronostico.nombre.like(
                                                    "Cerca de Puerto Patriada ·%"
                                                ))
            .order_by(Pronostico.disponible).limit(1))).scalar_one_or_none()

        # Ids estables: en cada reloj de la demo, `estado` tiene que encontrar los pronósticos que
        # acaban de quedar disponibles; si no, el panel queda en "se está calculando" (74c27d3).
        guardados = (await session.execute(select(Pronostico).where(
            Pronostico.modo == "demo", Pronostico.estado == "listo"))).scalars().all()
        relojes = sorted({p.disponible for p in guardados})
        perdidos = []
        op.modo = "demo"
        for reloj in relojes:
            op.reloj = reloj
            vistos = {i["pronostico"]["id"] for i in (await servicio.estado(session))["incendios"]
                      if i["pronostico"]}
            perdidos += [p for p in guardados if p.disponible == reloj and str(p.id) not in vistos]
        print(f"ids: estado encuentra {len(guardados) - len(perdidos)}/{len(guardados)} "
              f"pronósticos en {len(relojes)} relojes")
        for p in perdidos:
            print(f"  NO encontrado: {p.nombre} {p.pasada:%d-%m %H:%M} ({p.incendio_id})")

        op.modo, op.reloj = "demo", primero
        await session.commit()
        print(f"modo demo, reloj en {primero}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("desde", type=date.fromisoformat)
    ap.add_argument("hasta", type=date.fromisoformat)
    a = ap.parse_args()
    asyncio.run(main(a.desde, a.hasta))
