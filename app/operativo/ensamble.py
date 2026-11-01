"""Cálculo operativo opcional del acuerdo meteorológico GEFS.

Congela todos los insumos del pronóstico determinista y cambia únicamente la meteorología
para los 31 miembros. El runner es deliberadamente serial; las descargas se hacen en paralelo.
El artefacto final se escribe junto a la salida determinista, que es donde lo sirve la API.
"""

import asyncio
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path

import rasterio
from rasterio.warp import transform_bounds

from app.elmfire.builder import namelist_writer, weather_builder
from app.elmfire.runner.client import ELMFIRERunnerClient
from app.elmfire.runner.schemas import SimulationRequest
from app.ensemble.agreement import aggregate_burn_agreement
from app.ensemble.sources import (
    GEFS_MEMBERS,
    download_gefs_member,
    inspect_gefs_archive,
)

MIN_MIEMBROS_VALIDOS = 24
ARCHIVO_DESDE_DIAS = 4
# Como servicio.MARGEN_GFS_GRADOS: sin margen, el recorte de GEFS (0,25°) a la caja exacta deja
# afuera parte de la grilla (Patriada 05-01: 1×2 celdas para una caja de 0,25° de alto).
MARGEN_GEFS_GRADOS = 0.5


def _inventario_historico(ciclo: datetime, inicio: datetime) -> tuple[datetime, dict]:
    """Último ciclo archivado completo que ya existía al comienzo del pronóstico."""
    candidato = ciclo
    errores: list[str] = []
    for _ in range(4):
        try:
            prueba = inspect_gefs_archive(candidato, inicio, 24, ["c00", "p30"])
            if datetime.fromisoformat(prueba["cycle_available_at"]) <= inicio:
                completo = inspect_gefs_archive(candidato, inicio, 24, GEFS_MEMBERS)
                return candidato, completo
        except Exception as exc:
            errores.append(f"{candidato.isoformat()}: {exc}")
        candidato -= timedelta(hours=6)
    raise RuntimeError("no hay un ciclo GEFS histórico utilizable: " + "; ".join(errores))


def _descargar(
    ciclo: datetime,
    inicio: datetime,
    caja: tuple[float, float, float, float],
    raiz: Path,
    inventario: dict | None,
) -> tuple[list[str], dict[str, str]]:
    fallos: dict[str, str] = {}

    def uno(miembro: str) -> None:
        download_gefs_member(
            ciclo, miembro, caja, 24, raiz / "fuentes" / miembro,
            forecast_start=inicio, inventory=inventario,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        futuros = {pool.submit(uno, miembro): miembro for miembro in GEFS_MEMBERS}
        for futuro in as_completed(futuros):
            miembro = futuros[futuro]
            try:
                futuro.result()
            except Exception as exc:
                fallos[miembro] = str(exc)
    exitos = [m for m in GEFS_MEMBERS if m not in fallos]
    return exitos, fallos


def _preparar_miembro(base: Path, fuente: Path, destino: Path) -> None:
    if destino.exists():
        shutil.rmtree(destino)
    with rasterio.open(fuente / "u10.tif") as clima, rasterio.open(base / "dem.tif") as dem:
        o, s, e, n = transform_bounds(dem.crs, clima.crs, *dem.bounds)
        c = clima.bounds
        if not (c.left <= o and c.bottom <= s and c.right >= e and c.top >= n):
            # reproject rellenaría lo que falta con el nodata -9999: viento de 27.530 mph y m1 1 %.
            raise RuntimeError(f"GEFS {tuple(c)} no cubre la grilla {(o, s, e, n)}")
    shutil.copytree(base, destino, copy_function=os.link)
    for nombre in ("ws.tif", "wd.tif", "m1.tif", "m10.tif", "m100.tif", "elmfire.data"):
        (destino / nombre).unlink(missing_ok=True)
    weather_builder.derive_wind(
        fuente / "u10.tif", fuente / "v10.tif", destino / "dem.tif", destino
    )
    weather_builder.derive_moisture(
        fuente / "t2m.tif", fuente / "rh.tif", destino / "dem.tif", destino
    )


async def correr_ensamble(
    *,
    ciclo: datetime,
    inicio: datetime,
    tstart_s: float,
    caja: tuple[float, float, float, float],
    insumos_base: Path,
    salidas_base: Path,
    para_runner,
) -> dict:
    """Corre GEFS y devuelve el manifiesto de acuerdo; tolera hasta siete miembros fallidos."""
    raiz = salidas_base / "ensamble"
    raiz.mkdir(parents=True, exist_ok=True)
    inventario = None
    ciclo_gefs = ciclo
    if inicio < datetime.now(UTC) - timedelta(days=ARCHIVO_DESDE_DIAS):
        ciclo_gefs, inventario = await asyncio.to_thread(_inventario_historico, ciclo, inicio)
    m = MARGEN_GEFS_GRADOS
    caja_gefs = (caja[0] - m, caja[1] - m, caja[2] + m, caja[3] + m)
    exitos, fallos = await asyncio.to_thread(
        _descargar, ciclo_gefs, inicio, caja_gefs, raiz, inventario
    )
    if len(exitos) < MIN_MIEMBROS_VALIDOS:
        raise RuntimeError(
            f"GEFS: sólo {len(exitos)} miembros descargados; mínimo {MIN_MIEMBROS_VALIDOS}"
        )

    toa: dict[str, Path] = {}
    cliente = ELMFIRERunnerClient()
    for miembro in exitos:
        entrada = raiz / "insumos" / miembro
        salida = raiz / "corridas" / miembro
        try:
            await asyncio.to_thread(
                _preparar_miembro, insumos_base, raiz / "fuentes" / miembro, entrada
            )
            salida.mkdir(parents=True, exist_ok=True)
            namelist = entrada / "elmfire.data"
            _, dtdump_s, _ = await asyncio.to_thread(
                namelist_writer.write_namelist,
                entrada,
                salida,
                24,
                namelist,
                simulation_tstart_s=tstart_s,
                lh_moisture_pct=30.0,
                lw_moisture_pct=100.0,
            )
            namelist.write_text(
                namelist.read_text(encoding="utf-8")
                .replace(str(entrada), para_runner(entrada))
                .replace(str(salida), para_runner(salida)),
                encoding="utf-8",
            )
            await cliente.run_simulation(
                SimulationRequest(
                    elmfire_data_path=para_runner(namelist),
                    inputs_dir=para_runner(entrada),
                    outputs_dir=para_runner(salida),
                    simulation_hours=24,
                    dtdump_s=dtdump_s,
                ),
                local_inputs_dir=str(entrada),
                local_outputs_dir=str(salida),
            )
            candidatos = sorted(salida.glob("time_of_arrival_*.tif"))
            if not candidatos:
                raise RuntimeError("ELMFIRE no produjo time_of_arrival")
            toa[miembro] = candidatos[-1]
        except Exception as exc:
            fallos[miembro] = str(exc)
        finally:
            shutil.rmtree(entrada, ignore_errors=True)

    return await asyncio.to_thread(
        aggregate_burn_agreement,
        toa,
        salidas_base,
        expected_members=GEFS_MEMBERS,
        min_valid_members=MIN_MIEMBROS_VALIDOS,
        cycle=ciclo_gefs.isoformat(),
        forecast_start=inicio.isoformat(),
        horizon_hours=24,
        failed_members=fallos,
    )
