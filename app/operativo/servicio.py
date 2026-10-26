"""Pronóstico operativo: de las detecciones FIRMS a una ventana P-24 por incendio.

Es el mismo camino para el modo en vivo (el cron llama a `tick` cada 30 min) y para la
demostración (`scripts/demo_operativo.py` recorre las pasadas de un incendio pasado con el reloj
congelado). Lo que ve el cliente depende sólo del reloj: una pasada existe recién cuando FIRMS
la publicó (`LATENCIA_FIRMS_H`), y su clima es el ciclo GFS que ya estaba publicado entonces
(`pronostico.ciclo_disponible`), no los análisis posteriores que usa el benchmark (hindcast).

La física es la de modelo-v0 (receta lw-100-obs-001, docs/resultados/MODELO-V0.md): los
estáticos de la preparación de la app (CCS-BAP, dosel por combustible, quemas previas al año),
LH 30 % / LW 100 %, y la semilla de cada ventana es todo lo que VIIRS vio del incendio hasta la
pasada, con la misma reconstrucción que la semilla del benchmark (`build_ignition_layer`).

Lo que difiere del benchmark, a propósito: el dominio es una caja alrededor de las detecciones
(los casos tienen una caja puesta a mano sobre la cicatriz final, que en vivo no existe) y la
ventana 0 arranca en la primera pasada que ve el foco, no en una ignición tomada de la prensa.
docs/dashboard-producto.md tiene el diseño completo.
"""
import asyncio
import hashlib
import logging
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import rasterio
from geoalchemy2.shape import from_shape
from pyproj import Transformer
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds
from shapely.geometry import box
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import resolve_data_path, settings
from app.db import repository
from app.domain.models import Operativo, Pronostico
from app.elmfire.builder import fuels_builder, ignition_builder, namelist_writer, weather_builder
from app.elmfire.runner.client import ELMFIRERunnerClient
from app.elmfire.runner.schemas import SimulationRequest
from app.ingestion.meteorology.gfs.client import GFSClient
from app.ingestion.meteorology.gfs.schemas import GFSCycleInfo
from app.ingestion.satellite.firms.service import run_firms_ingestion
from app.postprocessing.wind_field import WIND_FIELD_FILENAME, write_wind_field
from app.preparation.service import run_preparation
from app.validation.pronostico import LATENCIA_FIRMS_H, bandas_necesarias, ciclo_disponible

logger = logging.getLogger(__name__)

RADIO_GRUPO_M = 3000.0        # filtro_conexo_m de los casos pronostico-v7
ACTIVO_H = 24                 # un incendio sin detecciones en 24 h deja de estar activo
VENTANA_GRUPO_H = 24          # no unir focos cercanos separados por más de un día
HISTORIA_DIAS = 7             # lo observado antes de eso no siembra la ventana
MARGEN_CAJA_M = 15000.0       # caja = detecciones + margen; una ventana de 24 h cabe adentro
HORAS = 24                    # el horizonte de P-24
MARGEN_GFS_GRADOS = 0.5       # como el benchmark: celdas de sobra para interpolar al borde
LH_PCT, LW_PCT = 30.0, 100.0  # humedad viva de modelo-v0 (HUMEDAD_VIVA_BASE + lw-100-001)
ESTATICOS = ("dem.tif", "slp.tif", "asp.tif", "adj.tif", "fbfm40.tif",
             "cc.tif", "ch.tif", "cbh.tif", "cbd.tif")
# Horas UTC típicas de las pasadas VIIRS sobre el AOI (histograma de FIRMS SP 2024-2026: dos
# racimos, 04-07 y 18-20 UTC). Sólo para decirle al cliente cuándo esperar la próxima.
PASADAS_TIPICAS_UTC = (5.5, 19.0)

# Para el nombre automático: "Cerca de <la más cercana a la primera detección>".
LOCALIDADES = (
    ("El Bolsón", -41.964, -71.535), ("Las Golondrinas", -42.008, -71.522),
    ("Lago Puelo", -42.064, -71.603), ("El Hoyo", -42.064, -71.520),
    ("Puerto Patriada", -42.148, -71.535), ("Epuyén", -42.231, -71.368),
    ("Cholila", -42.513, -71.444), ("Villa Lago Rivadavia", -42.596, -71.665),
    ("Villa Futalaufquen", -42.900, -71.600), ("Esquel", -42.911, -71.319),
    ("Trevelin", -43.090, -71.463),
)


@dataclass
class Deteccion:
    lon: float
    lat: float
    t: datetime


@dataclass
class Incendio:
    id: str
    nombre: str
    detecciones: list[Deteccion]

    @property
    def primera(self) -> datetime:
        return min(d.t for d in self.detecciones)

    @property
    def ultima(self) -> datetime:
        return max(d.t for d in self.detecciones)

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        lons = [d.lon for d in self.detecciones]
        lats = [d.lat for d in self.detecciones]
        return min(lons), min(lats), max(lons), max(lats)


def _a_utm() -> Transformer:
    return Transformer.from_crs("EPSG:4326", settings.aoi_crs_processing, always_xy=True)


def agrupar(detecciones: list[Deteccion], radio_m: float = RADIO_GRUPO_M) -> list[list[Deteccion]]:
    """Componentes conexas a menos de `radio_m` y 24 h (enlace simple). Una grilla de
    celdas de `radio_m` deja comparar cada punto sólo con sus vecinas: Patriada tiene ~10⁴
    detecciones por semana y la matriz completa no entra en memoria."""
    if not detecciones:
        return []
    xs, ys = _a_utm().transform([d.lon for d in detecciones], [d.lat for d in detecciones])
    padre = list(range(len(detecciones)))

    def raiz(i: int) -> int:
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    celdas: dict[tuple[int, int], list[int]] = {}
    for i, (x, y) in enumerate(zip(xs, ys)):
        celdas.setdefault((int(x // radio_m), int(y // radio_m)), []).append(i)
    r2 = radio_m * radio_m
    for (cx, cy), miembros in celdas.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in celdas.get((cx + dx, cy + dy), ()):
                    for i in miembros:
                        separacion_h = abs((detecciones[i].t - detecciones[j].t).total_seconds())
                        if (i < j and separacion_h <= VENTANA_GRUPO_H * 3600
                                and (xs[i] - xs[j]) ** 2 + (ys[i] - ys[j]) ** 2 <= r2):
                            padre[raiz(i)] = raiz(j)
    grupos: dict[int, list[Deteccion]] = {}
    for i, d in enumerate(detecciones):
        grupos.setdefault(raiz(i), []).append(d)
    return list(grupos.values())


def nombrar(primera: Deteccion) -> str:
    """'Cerca de Puerto Patriada · desde 05-01': estable entre pasadas porque sale de la primera
    detección. La identidad no depende de este rótulo: la da `identificar`."""
    localidad = min(LOCALIDADES, key=lambda loc: (loc[1] - primera.lat) ** 2
                    + ((loc[2] - primera.lon) * 0.73) ** 2)[0]   # cos(43°) para la longitud
    return f"Cerca de {localidad} · desde {primera.t:%d-%m}"


def identificar(primera: Deteccion) -> str:
    """ID compacto y determinista a partir de la primera observación del grupo."""
    clave = f"{primera.t.astimezone(UTC).isoformat()}|{primera.lon:.5f}|{primera.lat:.5f}"
    return f"f-{hashlib.sha256(clave.encode()).hexdigest()[:12]}"


def incendios_activos(detecciones: list[Deteccion], hasta: datetime) -> list[Incendio]:
    """Los grupos con alguna detección en las últimas `ACTIVO_H` horas, del más reciente al más
    viejo. Cualquier detección de confianza nominal o alta abre uno (el normalizador de FIRMS
    ya descartó las de confianza baja)."""
    activos = []
    for grupo in agrupar(detecciones):
        if max(d.t for d in grupo) >= hasta - timedelta(hours=ACTIVO_H):
            primera = min(grupo, key=lambda d: d.t)
            activos.append(Incendio(identificar(primera), nombrar(primera), grupo))
    return sorted(activos, key=lambda i: i.ultima, reverse=True)


def proxima_pasada(t: datetime) -> datetime:
    """La próxima hora típica de pasada después de `t` (aproximada: ±1-2 h)."""
    dia = t.replace(hour=0, minute=0, second=0, microsecond=0)
    candidatas = [dia + timedelta(days=k, hours=h) for k in (0, 1) for h in PASADAS_TIPICAS_UTC]
    return min(c for c in candidatas if c > t)


async def leer_operativo(session: AsyncSession) -> Operativo:
    op = await session.get(Operativo, 1)
    if op is None:   # la migración la crea; esto cubre una base armada con create_all
        op = Operativo(id=1, modo="demo")
        session.add(op)
        await session.flush()
    return op


def ahora_de(op: Operativo) -> datetime:
    """El "ahora" que ve el cliente: el reloj congelado de la demo, o el de verdad."""
    if op.modo == "demo" and op.reloj is not None:
        return op.reloj
    return datetime.now(UTC)


async def detecciones_visibles(session: AsyncSession, ahora: datetime) -> list[Deteccion]:
    """Lo que FIRMS ya había publicado a las `ahora`: adquiridas hasta `ahora - latencia`."""
    hasta = ahora - timedelta(hours=LATENCIA_FIRMS_H)
    aoi = await repository.get_or_create_default_aoi(session)
    features = await repository.get_active_fires(
        session, since=hasta - timedelta(days=HISTORIA_DIAS), aoi_id=aoi.id,
        until=hasta + timedelta(microseconds=1),
    )
    return [Deteccion(f["properties"]["longitude"], f["properties"]["latitude"],
                      datetime.fromisoformat(f["properties"]["acq_datetime"]))
            for f in features]


async def estado(session: AsyncSession) -> dict:
    """Todo lo que necesita la vista del cliente en un solo pedido."""
    op = await leer_operativo(session)
    ahora = ahora_de(op)
    hasta = ahora - timedelta(hours=LATENCIA_FIRMS_H)
    detecciones = await detecciones_visibles(session, ahora)
    incendios = incendios_activos(detecciones, hasta)
    filas = (await session.execute(
        select(Pronostico).where(Pronostico.modo == op.modo, Pronostico.disponible <= ahora)
        .order_by(Pronostico.pasada.desc())
    )).scalars().all()
    ultimo: dict[str, Pronostico] = {}
    listo: dict[str, Pronostico] = {}
    for f in filas:   # última actualización y último producto válido de cada incendio
        ultimo.setdefault(f.incendio_id, f)
        if f.estado == "listo":
            listo.setdefault(f.incendio_id, f)
    recientes = [d for d in detecciones if d.t >= hasta - timedelta(hours=ACTIVO_H)]
    return {
        "modo": op.modo,
        "ahora": ahora.isoformat(),
        "latencia_firms_h": LATENCIA_FIRMS_H,
        "calcular_ensamble": op.calcular_ensamble,
        "ultima_pasada": max((d.t.isoformat() for d in detecciones), default=None),
        "proxima_pasada_estimada": proxima_pasada(ahora).isoformat(),
        "horizonte_h": HORAS,
        "incendios": [
            _incendio_json(i, listo.get(i.id), ultimo.get(i.id)) for i in incendios
        ],
        "detecciones": {
            "type": "FeatureCollection",
            "features": [{"type": "Feature",
                          "geometry": {"type": "Point", "coordinates": [d.lon, d.lat]},
                          "properties": {"acq_datetime": d.t.isoformat()}}
                         for d in recientes],
        },
    }


def _incendio_json(inc: Incendio, p: Pronostico | None,
                   actualizacion: Pronostico | None) -> dict:
    return {
        "id": inc.id,
        "nombre": inc.nombre,
        "primera_deteccion": inc.primera.isoformat(),
        "ultima_deteccion": inc.ultima.isoformat(),
        "detecciones": len(inc.detecciones),
        "bbox": inc.bbox,
        "pronostico": None if p is None else {
            "id": str(p.id),
            "simulacion_id": str(p.simulacion_id) if p.simulacion_id else None,
            "pasada": p.pasada.isoformat(),
            "disponible": p.disponible.isoformat(),
            "ciclo_gfs": p.ciclo_gfs.isoformat() if p.ciclo_gfs else None,
        },
        "actualizacion": None if actualizacion is None else {
            "estado": actualizacion.estado,
            "pasada": actualizacion.pasada.isoformat(),
            "error": actualizacion.error,
        },
    }


async def pasadas_demo(session: AsyncSession, direccion: int) -> datetime | None:
    """El `disponible` del pronóstico demo siguiente (1) o anterior (-1) al reloj."""
    op = await leer_operativo(session)
    ahora = ahora_de(op)
    q = select(Pronostico.disponible).where(Pronostico.modo == "demo",
                                             Pronostico.estado == "listo")
    if direccion > 0:
        q = q.where(Pronostico.disponible > ahora).order_by(Pronostico.disponible)
    else:
        q = q.where(Pronostico.disponible < ahora).order_by(Pronostico.disponible.desc())
    return (await session.execute(q.limit(1))).scalar_one_or_none()


# ── la corrida ────────────────────────────────────────────────────────────────

async def tick(session: AsyncSession, ahora: datetime | None = None, modo: str = "vivo",
               ingerir: bool = True, solo_localidad: str | None = None,
               detecciones_desde: datetime | None = None) -> list[dict]:
    """Un paso del ciclo: (FIRMS) → incendios activos → una ventana por pasada nueva. Corre de a
    una ventana: el runner aguanta una sola corrida a la vez."""
    ahora = ahora or datetime.now(UTC)
    if ingerir:
        await run_firms_ingestion(session, day_range=2)
    hasta = ahora - timedelta(hours=LATENCIA_FIRMS_H)
    hechos = []
    operativo = await leer_operativo(session)
    detecciones = await detecciones_visibles(session, ahora)
    if detecciones_desde is not None:
        detecciones = [d for d in detecciones if d.t >= detecciones_desde]
    for inc in incendios_activos(detecciones, hasta):
        if solo_localidad and f"Cerca de {solo_localidad} ·" not in inc.nombre:
            continue
        previo = (await session.execute(select(Pronostico).where(
            Pronostico.modo == modo, Pronostico.incendio_id == inc.id,
            Pronostico.pasada == inc.ultima))).scalar_one_or_none()
        if previo is not None and previo.estado != "fallido":
            continue
        if previo is not None:   # un GFS caído o un runner ocupado: se reintenta en este tick
            await session.delete(previo)
            await session.commit()
        p = await correr(session, inc, modo, calcular_ensamble=operativo.calcular_ensamble)
        hechos.append({"incendio_id": p.incendio_id, "nombre": p.nombre,
                       "pasada": p.pasada.isoformat(), "estado": p.estado, "error": p.error})
    return hechos


async def correr(session: AsyncSession, inc: Incendio, modo: str,
                 calcular_ensamble: bool = False) -> Pronostico:
    """Arma y corre la ventana de 24 h que arranca en la última pasada de `inc`."""
    pasada = inc.ultima
    t0 = pasada.replace(minute=0, second=0, microsecond=0)
    tstart_s = (pasada - t0).total_seconds()
    ciclo = ciclo_disponible(pasada)
    p = Pronostico(modo=modo, incendio_id=inc.id, nombre=inc.nombre, pasada=pasada,
                   disponible=pasada + timedelta(hours=LATENCIA_FIRMS_H), ciclo_gfs=ciclo,
                   estado="corriendo")
    session.add(p)
    await session.commit()
    try:
        await _correr(session, inc, p, t0, tstart_s, ciclo, calcular_ensamble)
        p.estado = "listo"
    except Exception as exc:   # el tick sigue con los demás incendios; el error queda guardado
        logger.exception("pronóstico %s %s falló", inc.nombre, pasada)
        p.estado, p.error = "fallido", str(exc)
    await session.commit()
    return p


async def _correr(session: AsyncSession, inc: Incendio, p: Pronostico, t0: datetime,
                  tstart_s: float, ciclo: datetime, calcular_ensamble: bool) -> None:
    caja = _caja(inc)
    p.caja = from_shape(box(*caja), srid=4326)
    insumos = resolve_data_path(settings.elmfire_inputs_dir) / f"operativo-{p.id}"
    salidas = resolve_data_path(settings.elmfire_outputs_dir) / f"operativo-{p.id}"
    shutil.rmtree(insumos, ignore_errors=True)
    insumos.mkdir(parents=True)
    salidas.mkdir(parents=True, exist_ok=True)

    base = await estaticos(session, p.pasada.year)
    for nombre in ESTATICOS:
        await asyncio.to_thread(_recortar, base / nombre, caja, insumos / nombre)
    shutil.copy2(fuels_builder.FUEL_MODEL_TABLE, insumos / namelist_writer.FUEL_MODEL_FILE)

    bandas = bandas_necesarias(HORAS, tstart_s)
    await asyncio.to_thread(_clima, ciclo, t0, bandas, caja, insumos)

    sembradas = [(d.lon, d.lat) for d in inc.detecciones if d.t <= p.pasada]
    await asyncio.to_thread(ignition_builder.build_ignition_layer, sembradas,
                            insumos / "dem.tif", insumos)

    elmfire_data = insumos / "elmfire.data"
    _, dtdump_s, avisos = await asyncio.to_thread(
        namelist_writer.write_namelist, insumos, salidas, HORAS, elmfire_data,
        simulation_tstart_s=tstart_s, lh_moisture_pct=LH_PCT, lw_moisture_pct=LW_PCT,
    )
    # El namelist lleva rutas absolutas y el runner monta ./data en /app/data.
    elmfire_data.write_text(elmfire_data.read_text()
                            .replace(str(insumos), _para_runner(insumos))
                            .replace(str(salidas), _para_runner(salidas)))

    aoi = await repository.get_or_create_default_aoi(session)
    config = {"inputs_dir": str(insumos), "warnings": avisos,
              "operativo": {"pronostico_id": str(p.id), "nombre": p.nombre,
                            "ciclo_gfs": ciclo.isoformat(), "caja": caja}}
    sim = await repository.create_simulation_run(
        session, aoi.id, horizon_hours=HORAS, ignition_datetime=p.pasada, elmfire_config=config)
    p.simulacion_id = sim.id
    await session.commit()

    try:
        resultado = await ELMFIRERunnerClient().run_simulation(
            SimulationRequest(elmfire_data_path=_para_runner(elmfire_data),
                              inputs_dir=_para_runner(insumos), outputs_dir=_para_runner(salidas),
                              simulation_hours=HORAS, dtdump_s=dtdump_s),
            local_inputs_dir=str(insumos), local_outputs_dir=str(salidas),
        )
    except Exception as exc:
        await repository.update_simulation_run(
            session, sim.id, status="failed", output_dir=str(salidas),
            elmfire_config=config, error_message=str(exc),
        )
        raise
    await repository.update_simulation_run(session, sim.id, status="success",
                                           output_dir=str(salidas), elmfire_config=config)
    if resultado.outputs.isochrones_shp:
        await repository.create_simulation_output(session, sim.id, "isochrones",
                                                  file_path=resultado.outputs.isochrones_shp)
    if resultado.outputs.time_of_arrival_tif:
        await repository.create_simulation_output(
            session, sim.id, "time_of_arrival", file_path=resultado.outputs.time_of_arrival_tif)
    if calcular_ensamble:
        from app.operativo.ensamble import correr_ensamble

        try:
            config["ensamble"] = await correr_ensamble(
                ciclo=ciclo,
                inicio=t0,
                tstart_s=tstart_s,
                caja=caja,
                insumos_base=insumos,
                salidas_base=salidas,
                para_runner=_para_runner,
            )
        except Exception as exc:
            logger.exception("ensamble %s %s falló; se conserva P-24", inc.nombre, p.pasada)
            config["ensamble"] = {"estado": "fallido", "error": str(exc)}
        await repository.update_simulation_run(
            session, sim.id, status="success", output_dir=str(salidas), elmfire_config=config
        )


def _caja(inc: Incendio) -> tuple[float, float, float, float]:
    """Las detecciones más `MARGEN_CAJA_M`, recortadas al AOI, en grados."""
    a_utm = _a_utm()
    oeste, sur, este, norte = inc.bbox
    x0, y0 = a_utm.transform(oeste, sur)
    x1, y1 = a_utm.transform(este, norte)
    caja = transform_bounds(settings.aoi_crs_processing, "EPSG:4326",
                            x0 - MARGEN_CAJA_M, y0 - MARGEN_CAJA_M,
                            x1 + MARGEN_CAJA_M, y1 + MARGEN_CAJA_M)
    return (max(caja[0], settings.aoi_west), max(caja[1], settings.aoi_south),
            min(caja[2], settings.aoi_east), min(caja[3], settings.aoi_north))


def _recortar(origen: Path, caja: tuple[float, float, float, float], destino: Path) -> None:
    """Como benchmark._recortar: una ventana de la grilla del AOI, sin remuestrear."""
    with rasterio.open(origen) as src:
        izq, abajo, der, arriba = transform_bounds("EPSG:4326", src.crs, *caja)
        w = from_bounds(izq, abajo, der, arriba, src.transform).round_offsets().round_lengths()
        w = w.intersection(Window(0, 0, src.width, src.height))
        if w.width < 10 or w.height < 10:   # el DEM crudo no llega a todo el AOI configurado
            raise ValueError(f"la caja {caja} cae fuera de los estáticos preparados")
        datos = src.read(window=w)
        perfil = src.profile.copy()
        for clave in ("blockxsize", "blockysize", "tiled"):
            perfil.pop(clave, None)
        perfil.update(height=int(w.height), width=int(w.width), transform=src.window_transform(w))
    with rasterio.open(destino, "w", **perfil) as dst:
        dst.write(datos)


def _clima(ciclo: datetime, t0: datetime, bandas: int, caja: tuple[float, float, float, float],
           insumos: Path) -> None:
    """ws/wd/m1/m10/m100 con `bandas` horas desde `t0` del ciclo `ciclo` (la banda 0 es `t0`,
    como en las ventanas del benchmark), más el campo de viento que dibuja el mapa."""
    desfase = int((t0 - ciclo).total_seconds() // 3600)
    m = MARGEN_GFS_GRADOS
    info = GFSCycleInfo(date=ciclo.date().isoformat(), cycle_hour=ciclo.hour)
    with tempfile.TemporaryDirectory() as tmp:
        crudo = Path(tmp)
        # Las cuatro variables en paralelo: cada una son ~26 pedidos HTTP en serie y bajarlas de
        # a una era la mayor parte de los ~5 min de una ventana.
        with ThreadPoolExecutor(4) as pool:
            list(pool.map(lambda var: GFSClient().download_variable(
                info, var, caja[0] - m, caja[1] - m, caja[2] + m, caja[3] + m,
                crudo / f"{var}.tif", forecast_hours=list(range(desfase, desfase + bandas))),
                ("u10", "v10", "t2m", "rh")))
        ws, wd = weather_builder.derive_wind(crudo / "u10.tif", crudo / "v10.tif",
                                             insumos / "dem.tif", insumos)
        weather_builder.derive_moisture(crudo / "t2m.tif", crudo / "rh.tif",
                                        insumos / "dem.tif", insumos)
    write_wind_field(ws, wd, insumos / WIND_FIELD_FILENAME, forecast_start=t0,
                     forecast_cycle=f"{ciclo:%Y%m%d%H}")


async def estaticos(session: AsyncSession, anio: int) -> Path:
    """Los estáticos del AOI para incendios de `anio` (las quemas previas reasignan combustible y
    dosel según el año), preparados una vez y reutilizados."""
    destino = resolve_data_path(settings.data_dir) / "operativo" / "estaticos" / str(anio)
    if all((destino / n).exists() for n in ESTATICOS):
        return destino
    prep = await run_preparation(session, fires_until=datetime(anio, 7, 1, tzinfo=UTC),
                                 only_static=True)
    faltan = [n for n in ESTATICOS if n not in prep["generated"]]
    if faltan:
        raise RuntimeError(f"la preparación de los estáticos de {anio} no generó {faltan}: "
                           f"{prep['warnings']}")
    destino.mkdir(parents=True, exist_ok=True)
    for n in ESTATICOS:
        shutil.copy2(Path(prep["inputs_dir"]) / n, destino / n)
    return destino


def _para_runner(ruta: Path) -> str:
    """La ruta que ve el runner. En docker-compose es la misma (/app/data); desde el host
    (desarrollo, scripts) ./data se monta en /app/data."""
    datos = Path("data").resolve()
    relativa = os.path.relpath(ruta.resolve(), datos)
    return str(ruta) if relativa.startswith("..") else f"/app/data/{relativa}"
