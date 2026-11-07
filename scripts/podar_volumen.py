"""Poda única del volumen de Railway: lo que `servicio.podar` ya hace con cada pronóstico nuevo,
aplicado a los que se corrieron antes, más las carpetas de simulaciones que ninguna fila usa.

    railway ssh -s api -- 'cd /app && uv run python scripts/podar_volumen.py'            # lista
    railway ssh -s api -- 'cd /app && uv run python scripts/podar_volumen.py --aplicar'  # borra

No toca los pronósticos que están corriendo ni las carpetas que una simulación de la base
referencia (salvo lo que `podar` saca de las operativas: el producto queda).
"""
import argparse
import asyncio
import shutil
from pathlib import Path

from sqlalchemy import select

from app.config import resolve_data_path, settings
from app.db.session import async_session_factory
from app.domain.models import Pronostico, SimulationRun
from app.operativo.servicio import INSUMOS_QUE_QUEDAN


def a_borrar(insumos: Path, salidas: Path, referenciadas: set[str],
             corriendo: set[str]) -> list[Path]:
    """Lo que sobra: en cada carpeta operativa que no está corriendo, lo que `podar` borraría;
    las carpetas no operativas que ninguna simulación referencia, enteras."""
    sobra: list[Path] = []
    for raiz in (insumos, salidas):
        for d in sorted(p for p in raiz.iterdir() if p.is_dir()):
            if d.name.startswith("operativo-"):
                if d.name.removeprefix("operativo-") in corriendo:
                    continue
                if raiz == salidas:
                    sobra += [d / "ensamble"] if (d / "ensamble").exists() else []
                else:
                    sobra += [f for f in d.iterdir() if not f.name.startswith(INSUMOS_QUE_QUEDAN)]
            elif str(d) not in referenciadas:
                sobra.append(d)
    return sobra


def _tamano(p: Path) -> int:
    return p.stat().st_size if p.is_file() else sum(
        f.stat().st_size for f in p.rglob("*") if f.is_file())


async def main(aplicar: bool) -> None:
    insumos = resolve_data_path(settings.elmfire_inputs_dir)
    salidas = resolve_data_path(settings.elmfire_outputs_dir)
    async with async_session_factory() as s:
        corriendo = {str(i) for i in (await s.execute(
            select(Pronostico.id).where(Pronostico.estado == "corriendo"))).scalars()}
        referenciadas: set[str] = set()
        for config, output_dir in (await s.execute(
                select(SimulationRun.elmfire_config, SimulationRun.output_dir))).all():
            for ruta in ((config or {}).get("inputs_dir"), output_dir):
                if ruta:
                    referenciadas.add(str(resolve_data_path(ruta)))
    sobra = a_borrar(insumos, salidas, referenciadas, corriendo)
    total = 0
    for p in sobra:
        n = _tamano(p)
        total += n
        print(f"{n / 1e9:7.2f} GB  {p}")
        if aplicar:
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    print(f"{'Borrado' if aplicar else 'Se borraría'}: {total / 1e9:.1f} GB en {len(sobra)} rutas")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--aplicar", action="store_true", help="borrar (si no, sólo lista)")
    asyncio.run(main(parser.parse_args().aplicar))
