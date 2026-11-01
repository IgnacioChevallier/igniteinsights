"""Calcula el acuerdo del ensamble GEFS en los pasos clave de la demo de Puerto Patriada.

    uv run python scripts/demo_ensamble.py               # elige los pasos y corre el ensamble
    uv run python scripts/demo_ensamble.py --sin-correr  # sólo imprime la elección

No repite el P-24: reusa los pronósticos demo ya guardados por `scripts/demo_operativo.py` y
corre sólo los 31 miembros GEFS de cada paso elegido (`ensamble.correr_ensamble`, lo mismo que
hace `servicio._correr` con `calcular_ensamble`). El ensamble cuesta ~35 min y 1,4 GiB por
corrida (docs/resultados/ESTADO-RESEARCH.md §6, nota AD), así que no se calcula en todas las
pasadas sino en tres:

- la primera pasada de la demo (2026-01-05 19:20 UTC), donde arranca el recorrido;
- las dos donde el foco más crece en las 24 h de su propio pronóstico determinista: área total
  de fire_size_stats.csv (lo que sirve /simulations/{id}/stats) menos el área sembrada
  (las celdas encendidas de phi.tif, lo observado hasta la pasada).

Corre de a uno (el runner aguanta una corrida por vez) e imprime el tiempo de cada paso.
Reanudable: salta los pasos que ya tienen ensemble_agreement.json. Si los insumos congelados de
un pronóstico ya no están, se regeneran con `servicio.congelar` (misma lógica que la corrida) y
se avisa. Con el modo en demo el cron no corre ELMFIRE, así que no compite con otro P-24.
"""
import argparse
import asyncio
import os
import time
from datetime import timedelta

# Desde el host el runner es localhost (el .env apunta al nombre del servicio en Docker).
os.environ.setdefault("ELMFIRE_RUNNER_URL", "http://localhost:8001")

import rasterio  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db import repository  # noqa: E402
from app.db.session import async_session_factory  # noqa: E402
from app.domain.models import Pronostico  # noqa: E402
from app.elmfire.builder import namelist_writer  # noqa: E402
from app.operativo import servicio  # noqa: E402
from app.operativo.ensamble import correr_ensamble  # noqa: E402
from app.postprocessing.stats_reader import read_fire_size_stats  # noqa: E402
from app.validation.pronostico import LATENCIA_FIRMS_H  # noqa: E402

AC_A_HA = 0.404686
PASOS_POR_CRECIMIENTO = 2
NECESARIOS = (*servicio.ESTATICOS, namelist_writer.FUEL_MODEL_FILE, "phi.tif")


def area_sembrada_ha(phi) -> float:
    """Las celdas encendidas de phi.tif (negativas) en ha; la grilla es UTM, en metros."""
    with rasterio.open(phi) as src:
        return float((src.read(1) < 0).sum()) * abs(src.transform.a * src.transform.e) / 1e4


def elegir(pasadas: list, crecimiento: dict) -> list:
    """La primera pasada más las `PASOS_POR_CRECIMIENTO` de mayor crecimiento, en orden."""
    resto = sorted((p for p in pasadas[1:] if p in crecimiento),
                   key=lambda p: crecimiento[p], reverse=True)
    return [pasadas[0], *sorted(resto[:PASOS_POR_CRECIMIENTO])]


async def regenerar(session, p: Pronostico, desde, caja) -> None:
    """Los insumos congelados de `p`, como los armó `tick`: el mismo incendio (por id) con lo
    visible a `pasada + latencia`."""
    ahora = p.pasada + timedelta(hours=LATENCIA_FIRMS_H, minutes=1)
    detecciones = await servicio.detecciones_visibles(session, ahora, desde)
    activos = servicio.incendios_activos(detecciones, ahora - timedelta(hours=LATENCIA_FIRMS_H))
    inc = next((i for i in activos if i.id == p.incendio_id), None)
    if inc is None or inc.ultima != p.pasada:
        raise RuntimeError(f"no se reconstruye el incendio {p.incendio_id} en {p.pasada}")
    insumos = servicio.insumos_de(p.id)
    insumos.mkdir(parents=True, exist_ok=True)
    await servicio.congelar(session, inc, p.pasada, caja, insumos)
    print(f"  {p.pasada:%d-%m %H:%M}: los insumos congelados no estaban; regenerados en {insumos}",
          flush=True)


async def main(correr: bool) -> None:
    async with async_session_factory() as session:
        op = await servicio.leer_operativo(session)
        filas = (await session.execute(
            select(Pronostico).where(Pronostico.modo == "demo", Pronostico.estado == "listo",
                                     Pronostico.nombre.like("Cerca de Puerto Patriada ·%"))
            .order_by(Pronostico.pasada))).scalars().all()
        if not filas:
            raise SystemExit("no hay pronósticos demo de Puerto Patriada: correr antes "
                             "scripts/demo_operativo.py")
        por_pasada = {p.pasada: p for p in filas}
        configs = {}
        crecimiento = {}
        print("pasada UTC     total 24 h   sembrada   crecimiento", flush=True)
        for p in filas:
            sim = await repository.get_simulation_run(session, p.simulacion_id)
            configs[p.pasada] = (sim, dict(sim.elmfire_config or {}))
            caja = tuple(configs[p.pasada][1]["operativo"]["caja"])
            if not all((servicio.insumos_de(p.id) / n).exists() for n in NECESARIOS):
                await regenerar(session, p, servicio.desde_de(op, "demo"), caja)
            stats = read_fire_size_stats(servicio.salidas_de(p.id) / "fire_size_stats.csv")
            if not stats or stats[0].get("total_fire_area_ac") is None:
                print(f"{p.pasada:%d-%m %H:%M}    sin fire_size_stats.csv; no compite", flush=True)
                continue
            total = stats[0]["total_fire_area_ac"] * AC_A_HA
            sembrada = area_sembrada_ha(servicio.insumos_de(p.id) / "phi.tif")
            crecimiento[p.pasada] = total - sembrada
            print(f"{p.pasada:%d-%m %H:%M}    {total:9.0f} ha {sembrada:7.0f} ha "
                  f"{crecimiento[p.pasada]:+10.0f} ha", flush=True)

        elegidas = elegir(list(por_pasada), crecimiento)
        print(f"\nelegidas: {elegidas[0]:%d-%m %H:%M} (primera pasada, arranque de la demo)",
              flush=True)
        for t in elegidas[1:]:
            print(f"          {t:%d-%m %H:%M} (crece {crecimiento[t]:+.0f} ha en 24 h)", flush=True)
        if not correr:
            return

        for t in elegidas:
            p = por_pasada[t]
            sim, config = configs[t]
            salidas = servicio.salidas_de(p.id)
            if (salidas / "ensemble_agreement.json").is_file():
                print(f"{t:%d-%m %H:%M}: ya tiene ensamble, se salta", flush=True)
                continue
            print(f"{t:%d-%m %H:%M}: ensamble GEFS (~35 min)…", flush=True)
            t0 = p.pasada.replace(minute=0, second=0, microsecond=0)
            reloj = time.monotonic()
            try:
                config["ensamble"] = await correr_ensamble(
                    ciclo=p.ciclo_gfs, inicio=t0, tstart_s=(p.pasada - t0).total_seconds(),
                    caja=tuple(config["operativo"]["caja"]), insumos_base=servicio.insumos_de(p.id),
                    salidas_base=salidas, para_runner=servicio._para_runner,
                )
                resultado = (f"{config['ensamble']['effective_denominator']}/"
                             f"{config['ensamble']['expected_member_count']} miembros válidos")
            except Exception as exc:   # como _correr: el P-24 queda y el error se guarda
                config["ensamble"] = {"estado": "fallido", "error": str(exc)}
                resultado = f"falló: {exc}"
            await repository.update_simulation_run(session, sim.id, status="success",
                                                   output_dir=str(salidas), elmfire_config=config)
            print(f"{t:%d-%m %H:%M}: {resultado} en {(time.monotonic() - reloj) / 60:.0f} min",
                  flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sin-correr", action="store_true", help="sólo imprimir la elección")
    asyncio.run(main(not ap.parse_args().sin_correr))
