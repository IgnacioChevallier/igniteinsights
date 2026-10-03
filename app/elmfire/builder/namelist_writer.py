"""
Writes elmfire.data (Fortran namelist) consumed by the ELMFIRE runner.

The namelist tells ELMFIRE where to find each input raster and where to write
outputs. All paths must be accessible to the elmfire-runner container via the
shared data volume.
"""
import logging
import math
import re
from pathlib import Path

import numpy as np
import rasterio

logger = logging.getLogger(__name__)

DEFAULT_DTDUMP_S = 3600.0
# Weather rasters whose band count is the forecast time series. At absolute time T ELMFIRE
# interpolates between bands floor(T / DT_METEOROLOGY) and the next (0-based), so band n is
# the weather at n × DT_METEOROLOGY — T is absolute, band 0 is T = 0, not TSTART
# (elmfire_level_set.f90: ITLO_METEOROLOGY = 1 + FLOOR(T / DT_METEOROLOGY)).
#
# It only does so if &MONTE_CARLO NUM_METEOROLOGY_TIMES says how many bands there are: the
# default is 1, and with 1 ELMFIRE clamps the band index to 1 and holds the FIRST band for
# the whole run, silently (elmfire_namelists.f90 READ_MONTE_CARLO; the vendor transient
# tutorials 02/03 set it to 8). Until 2026-09-29 this repo never wrote it, so every run used
# the weather of its first hour throughout (AUDITORIA-FISICA.md, hallazgo 1).
WEATHER_RASTERS = ("ws", "wd", "m1", "m10", "m100")
REQUIRED_NAMELISTS = (
    "INPUTS",
    "COMPUTATIONAL_DOMAIN",
    "TIME_CONTROL",
    "SIMULATOR",
    "OUTPUTS",
)


# Fuel model table shipped with this repo (app/elmfire/fuel_models.csv), copied into the
# inputs directory by the preparation step. ELMFIRE writes its own default table ONLY when
# FUEL_MODEL_FILE is left at 'null'; naming it here makes the set of valid FBFM codes an
# artefact we version and test against, instead of an implicit property of the solver.
#
# Gotcha: MISCELLANEOUS_INPUTS_DIRECTORY defaults to 'null' and is only substituted with
# FUELS_AND_TOPOGRAPHY_DIRECTORY inside WRITE_FUEL_MODEL_TABLE — which runs only when
# FUEL_MODEL_FILE == 'null'. Setting one without the other makes ELMFIRE look for
# 'null/fuel_models.csv' and abort. Both are written together, always.
FUEL_MODEL_FILE = "fuel_models.csv"

# Live fuel moisture, percent. ELMFIRE defaults both to 60.0; written explicitly so the
# value is a recorded decision rather than an inherited default. Inert while the crosswalk
# only emits models with no live load (TL/NB), a first-order driver as soon as it emits
# SH/GS/TU. ELMFIRE takes a single scalar for the whole domain — there is no live-moisture
# raster — so any value is an area-weighted mean and the weighting has to be justified.
# docs/historico/ETAPA-B-INSUMO-PATAGONICO.md §B5: source is Bianchi & Defossé (2015),
# LFMC by species for Andean Patagonia.
# ELMFIRE enciende el fuego de copas si el namelist OMITE CROWN_FIRE_MODEL
# (.claude/skills/elmfire/references/namelist-reference.md: &SIMULATOR, 0 = off,
# cualquier valor > 0 = on). Estaba activo por omisión, no por decisión. Se escribe
# explícito con el valor que ya se venía usando: activado.
DEFAULT_CROWN_FIRE_MODEL = 1

# Pavesas (&SPOTTING, elmfire_spotting.f90). Apagadas por defecto en ELMFIRE y acá. Los
# valores son los de la plantilla de hindcast del proveedor
# (/opt/elmfire/runs/hindcasts/templates/hindcast/elmfire.data), con un detalle: ELMFIRE
# sortea cada parámetro entre su _MIN/_LO y su _MAX/_HI en SET_SPOTTING_PARAMETERS, también en
# una corrida única (elmfire.f90, con la semilla fija SEED = 2024), así que acá _MIN = _MAX =
# el centro del rango de la plantilla y el valor queda declarado, no sorteado.
SPOTTING_HINDCAST: dict[str, float | bool | str] = {
    "ENABLE_SPOTTING": True,
    "ENABLE_SURFACE_FIRE_SPOTTING": True,
    "CRITICAL_SPOTTING_FIRELINE_INTENSITY": 1000.0,
    "SPOTTING_DISTRIBUTION_TYPE": "LOGNORMAL",
    "MEAN_SPOTTING_DIST": 10.0,
    "NORMALIZED_SPOTTING_DIST_VARIANCE": 425.0,
    "SPOT_WS_EXP": 0.55,
    "SPOT_FLIN_EXP": 0.3,
    "NEMBERS_MIN": 1.0,
    "NEMBERS_MAX": 1.0,
    "GLOBAL_SURFACE_FIRE_SPOTTING_PERCENT": 0.065,
    "CROWN_FIRE_SPOTTING_PERCENT": 0.65,
    "PIGN": 100.0,
}
# Cada parámetro sorteado y los nombres de sus extremos en el fuente.
_SPOTTING_RANGOS = {
    "MEAN_SPOTTING_DIST": ("MEAN_SPOTTING_DIST_MIN", "MEAN_SPOTTING_DIST_MAX"),
    "NORMALIZED_SPOTTING_DIST_VARIANCE": ("NORMALIZED_SPOTTING_DIST_VARIANCE_MIN",
                                          "NORMALIZED_SPOTTING_DIST_VARIANCE_MAX"),
    "SPOT_WS_EXP": ("SPOT_WS_EXP_LO", "SPOT_WS_EXP_HI"),
    "SPOT_FLIN_EXP": ("SPOT_FLIN_EXP_LO", "SPOT_FLIN_EXP_HI"),
    "NEMBERS_MAX": ("NEMBERS_MAX_LO", "NEMBERS_MAX_HI"),
    "GLOBAL_SURFACE_FIRE_SPOTTING_PERCENT": ("GLOBAL_SURFACE_FIRE_SPOTTING_PERCENT_MIN",
                                             "GLOBAL_SURFACE_FIRE_SPOTTING_PERCENT_MAX"),
    "CROWN_FIRE_SPOTTING_PERCENT": ("CROWN_FIRE_SPOTTING_PERCENT_MIN",
                                    "CROWN_FIRE_SPOTTING_PERCENT_MAX"),
    "PIGN": ("PIGN_MIN", "PIGN_MAX"),
}
_SPOTTING_FIJOS = {"ENABLE_SPOTTING", "ENABLE_SURFACE_FIRE_SPOTTING",
                   "CRITICAL_SPOTTING_FIRELINE_INTENSITY", "SPOTTING_DISTRIBUTION_TYPE",
                   "NEMBERS_MIN"}


def spotting_group(cambios: dict | None) -> str:
    """El grupo &SPOTTING: la plantilla de hindcast con `cambios` encima (mismas claves)."""
    if cambios is None:
        return ""
    desconocidas = set(cambios) - set(SPOTTING_HINDCAST)
    if desconocidas:
        raise ValueError(f"keywords de &SPOTTING no soportados: {sorted(desconocidas)}")
    valores = SPOTTING_HINDCAST | cambios

    def fortran(v: float | bool | str) -> str:
        if isinstance(v, bool):
            return ".TRUE." if v else ".FALSE."
        if isinstance(v, str):
            return f"'{v}'"
        if isinstance(v, int):   # NEMBERS_*: enteros en el fuente, un real no se lee
            return str(v)
        return f"{float(v)}"

    lineas = []
    for clave, v in valores.items():
        if clave in _SPOTTING_RANGOS:
            nombres = (clave, *_SPOTTING_RANGOS[clave]) if clave != "NEMBERS_MAX" else \
                _SPOTTING_RANGOS[clave]
            if clave == "NEMBERS_MAX":
                v = int(v)
            lineas += [f"  {n:<42s}= {fortran(v)}" for n in nombres]
        elif clave in _SPOTTING_FIJOS:
            lineas.append(f"  {clave:<42s}= {fortran(int(v) if clave == 'NEMBERS_MIN' else v)}")
    return "\n&SPOTTING\n" + "\n".join(lineas) + "\n/\n"

# Humedad del combustible vivo, de Bianchi & Defossé (2015), IJWF 24(3):340, que mide LFMC
# en las especies de la Patagonia andina cada 10-15 días durante la temporada de fuego
# (mediados de noviembre a principios de abril), en hojas de la cara norte —la más expuesta
# y por lo tanto la más seca— a 2 m de altura.
#
# LW: ñire, ciprés, laura y radal se mueven entre 110 y 220 % durante la temporada; la caña
# colihue nunca supera 110 %. Bianchi & Defossé ubican en 110 % el UMBRAL por debajo del cual
# ocurren los grandes incendios, así que el día de un gran incendio está por debajo. Se toma
# **100 %**, el valor calibrado contra siete incendios con la interfaz de ELMFIRE corregida
# (AUDITORIA-FISICA.md, loop E: intervalo sin sobre-propagación ~[97; 110] %; hasta el
# 2026-09-30 era 110 %, el borde húmedo). Lenga, coihue y alerce no fueron medidos: heredan el
# valor por analogía con el ñire, y eso se declara.
# LH: no hay medición de herbáceas. 30 % representa el pasto **completamente curado** del
# verano tardío, que es el umbral de transferencia dinámica de Scott & Burgan. Es una
# convención de modelado declarada, no un dato.
#
# El valor anterior (60 % en ambos) no tenía criterio y quedaba por debajo de todo lo medido.
# Su efecto está cuantificado en docs/historico/IGN-20B-FINAL-CROSSWALK-CCSBAP.md §6.3.
DEFAULT_LH_MOISTURE_PCT = 30.0
DEFAULT_LW_MOISTURE_PCT = 100.0


def resolve_dtdump_s(tstop_s: float, dtdump_s: float = DEFAULT_DTDUMP_S) -> float:
    """Clamp dtdump_s so at least one output checkpoint occurs strictly before TSTOP.

    If dtdump_s >= tstop_s, ELMFIRE's only possible dump checkpoint coincides with
    the simulation's final instant, which can result in raster/isochrone outputs
    never being written even though the run completes successfully.
    """
    if dtdump_s >= tstop_s:
        clamped = tstop_s / 2.0
        logger.warning(
            "dtdump_s=%.1f >= tstop_s=%.1f; clamping to %.1f so ELMFIRE dumps at least once "
            "before TSTOP",
            dtdump_s,
            tstop_s,
            clamped,
        )
        return clamped
    return dtdump_s


def validate_weather_coverage(
    inputs_dir: Path, tstop_s: float, dt_meteorology_s: float
) -> list[str]:
    """Fail if the weather rasters do not span the simulation horizon; return warnings.

    ELMFIRE reads band n as the weather at absolute time n × DT_METEOROLOGY. A raster with fewer
    bands than the run needs does not error — it silently holds the last available band,
    which freezes wind and moisture for the remainder of the simulation and removes the
    diurnal cycle that drives fire behaviour. Catch it here instead.

    Single-band rasters are allowed but warned about: they *are* constant weather. The
    returned warnings are surfaced to the dashboard, not just logged — a run whose
    weather never changes looks identical to a good one on the map.
    """
    warnings: list[str] = []
    needed = int(math.floor(tstop_s / dt_meteorology_s)) + 1
    for name in WEATHER_RASTERS:
        path = inputs_dir / f"{name}.tif"
        if not path.exists():
            continue
        with rasterio.open(path) as ds:
            bands = ds.count
        if bands != weather_band_count(inputs_dir):
            # ELMFIRE indexes every weather raster with the same band number.
            raise ValueError(f"{path.name} has {bands} band(s) but ws.tif has "
                             f"{weather_band_count(inputs_dir)}: weather rasters must share "
                             "one time series")
        if bands == 1:
            msg = (
                f"{path.name} tiene una sola banda: el clima permanece constante "
                "durante toda la simulación (sin ciclo diurno — sin pico de viento "
                "de la tarde ni mínimo de humedad). Volvé a correr la ingesta GFS "
                "para obtener bandas horarias."
            )
            logger.warning("%s", msg)
            warnings.append(msg)
        elif bands < needed:
            raise ValueError(
                f"{path.name} has {bands} band(s) but the run needs {needed} "
                f"(TSTOP={tstop_s:.0f}s / DT_METEOROLOGY={dt_meteorology_s:.0f}s). "
                "ELMFIRE would hold the last band and freeze weather mid-run — "
                "shorten horizon_hours or re-ingest GFS with more forecast hours."
            )
    return warnings


def weather_band_count(inputs_dir: Path) -> int:
    """Bands in ws.tif — the NUM_METEOROLOGY_TIMES ELMFIRE needs (1 if there is no ws.tif)."""
    path = inputs_dir / "ws.tif"
    if not path.exists():
        return 1
    with rasterio.open(path) as ds:
        return int(ds.count)


def pad_weather_columns(inputs_dir: Path) -> None:
    """Pad the weather rasters east with their last column until NCOLS >= NROWS.

    ELMFIRE 2025.0212 maps each fuel cell to a weather cell in MAP_FINE_TO_COARSE and clamps
    the weather ROW with the weather grid's NCOLS instead of NROWS (elmfire_subs.f90:296-297).
    Rows count from the south (the reader flips them, elmfire_io.f90:1265), so on a
    weather grid taller than wide every fuel row with IY > NCOLS reads weather row NCOLS: the
    northern strip gets the weather of another latitude (AUDITORIA-FISICA.md, hallazgo 5).

    Each raster's shape comes from its own header (READ_BSQ_HDR_HEADER, elmfire_io.f90:1242)
    and the mapping only uses the weather grid's lower-left corner and cell size
    (elmfire_subs.f90:293-297). Adding columns to the east moves neither, so every fuel cell
    keeps its weather cell and the extra columns are never read (ICOL <= the fuel grid's own
    columns). Padding is the whole fix, with no ELMFIRE change and no new keyword.

    Done here because write_namelist is the one step every path runs last before ELMFIRE
    (the API, preparation, the benchmark's cadena._preparar after its knobs, the physics
    bench and the harness scripts), like wd_for_elmfire but without two call sites. It uses
    each raster's own shape, so a weather grid coarser than the fuel grid is padded in its
    own cells. A no-op on grids at least as wide as tall, so re-writing the namelist on the
    same inputs is safe. Band by band, to keep memory at one band of the AOI grid.
    """
    for name in WEATHER_RASTERS:
        path = inputs_dir / f"{name}.tif"
        if not path.exists():
            continue
        with rasterio.open(path) as src:
            if src.width >= src.height:
                continue
            extra = src.height - src.width
            profile = src.profile | {"width": src.height, "compress": "deflate",
                                     "predictor": 3 if src.dtypes[0].startswith("float") else 2}
            # A new file then a rename: inputs can be read-only hardlinks into the benchmark
            # store (cadena), which must never be written through.
            tmp = path.with_name(f".{name}.padded.tif")
            with rasterio.open(tmp, "w", **profile) as dst:
                for band in range(1, src.count + 1):
                    dst.write(np.pad(src.read(band), ((0, 0), (0, extra)), mode="edge"), band)
        tmp.replace(path)
        logger.info("Padded %s east by %d columns (ELMFIRE clamps weather rows by NCOLS)",
                    path.name, extra)


def write_namelist(
    inputs_dir: Path,
    outputs_dir: Path,
    simulation_hours: int,
    output_path: Path,
    dt_s: float = 30.0,
    dtmax_s: float = 300.0,
    dtdump_s: float = DEFAULT_DTDUMP_S,
    dt_meteorology_s: float = 3600.0,
    simulation_tstart_s: float = 0.0,
    simulator_mode: int = 1,
    crown_fire_model: int = DEFAULT_CROWN_FIRE_MODEL,
    lh_moisture_pct: float = DEFAULT_LH_MOISTURE_PCT,
    lw_moisture_pct: float = DEFAULT_LW_MOISTURE_PCT,
    spotting: dict | None = None,
) -> tuple[Path, float, list[str]]:
    """
    Write elmfire.data to output_path.

    Args:
        inputs_dir: directory containing the ELMFIRE raster inputs
        outputs_dir: directory where ELMFIRE will write its outputs
        simulation_hours: length of simulation
        output_path: destination path for the namelist file
        dt_s: minimum timestep in seconds
        dtmax_s: maximum timestep in seconds
        dtdump_s: output dump interval in seconds
        dt_meteorology_s: interval between weather-raster bands in seconds
        simulation_tstart_s: absolute simulation start time in seconds, measured from
            weather band 0. Non-zero anchors the run to the wall clock: ELMFIRE reads band
            n as the weather at T = n × DT_METEOROLOGY (T absolute), so a run starting at
            TSTART begins on band floor(TSTART / DT_METEOROLOGY).
        simulator_mode: ELMFIRE mode; 1 is transient fire-spread simulation
        crown_fire_model: 0 disables crown fire; any value > 0 enables it. Written
            explicitly because ELMFIRE enables it when the keyword is absent.
        spotting: None leaves &SPOTTING out (spotting off, ELMFIRE's default); a dict writes
            SPOTTING_HINDCAST with those keys overridden ({} = the vendor hindcast values).

    Returns:
        Tuple of (namelist path, resolved dump interval in seconds, weather warnings).
    """
    _validate_parameters(
        simulation_hours,
        dt_s,
        dtmax_s,
        dtdump_s,
        dt_meteorology_s,
        simulation_tstart_s,
        simulator_mode,
        crown_fire_model,
    )
    duration_s = simulation_hours * 3600.0
    tstop_s = simulation_tstart_s + duration_s
    dtdump_s = resolve_dtdump_s(duration_s, dtdump_s)
    inputs_str = _fortran_path(inputs_dir)
    outputs_str = _fortran_path(outputs_dir)

    weather_warnings = validate_weather_coverage(inputs_dir, tstop_s, dt_meteorology_s)
    pad_weather_columns(inputs_dir)

    dem_path = inputs_dir / "dem.tif"
    utm_west, utm_south, cell_size = _read_domain(dem_path)
    a_srs = _read_srs(dem_path)

    namelist = f"""\
&INPUTS
  FUELS_AND_TOPOGRAPHY_DIRECTORY = '{inputs_str}'
  WEATHER_DIRECTORY               = '{inputs_str}'
  DEM_FILENAME                    = 'dem'
  SLP_FILENAME                    = 'slp'
  ASP_FILENAME                    = 'asp'
  FBFM_FILENAME                   = 'fbfm40'
  CC_FILENAME                     = 'cc'
  CH_FILENAME                     = 'ch'
  CBH_FILENAME                    = 'cbh'
  CBD_FILENAME                    = 'cbd'
  WS_FILENAME                     = 'ws'
  WD_FILENAME                     = 'wd'
  M1_FILENAME                     = 'm1'
  M10_FILENAME                    = 'm10'
  M100_FILENAME                   = 'm100'
  ADJ_FILENAME                    = 'adj'
  PHI_FILENAME                    = 'phi'
  DT_METEOROLOGY                  = {dt_meteorology_s:.1f}
  LH_MOISTURE_CONTENT             = {lh_moisture_pct:.1f}
  LW_MOISTURE_CONTENT             = {lw_moisture_pct:.1f}
/

&COMPUTATIONAL_DOMAIN
  A_SRS                           = '{a_srs}'
  COMPUTATIONAL_DOMAIN_XLLCORNER  = {utm_west:.2f}
  COMPUTATIONAL_DOMAIN_YLLCORNER  = {utm_south:.2f}
  COMPUTATIONAL_DOMAIN_CELLSIZE   = {cell_size:.1f}
/

&OUTPUTS
  DTDUMP                          = {dtdump_s:.1f}
  OUTPUTS_DIRECTORY               = '{outputs_str}'
  CONVERT_TO_GEOTIFF              = T
  DUMP_TIME_OF_ARRIVAL            = T
  DUMP_FLIN                       = T
  DUMP_SPREAD_RATE                = T
/

&TIME_CONTROL
  SIMULATION_TSTART               = {simulation_tstart_s:.1f}
  SIMULATION_DT                   = {dt_s:.1f}
  SIMULATION_DTMAX                = {dtmax_s:.1f}
  SIMULATION_TSTOP                = {tstop_s:.1f}
/

&SIMULATOR
  MODE                            = {simulator_mode}
  CROWN_FIRE_MODEL                = {crown_fire_model}
/

&MISCELLANEOUS
  PATH_TO_GDAL                    = '/usr/bin/'
  SCRATCH                         = '/tmp/'
  MISCELLANEOUS_INPUTS_DIRECTORY  = '{inputs_str}'
  FUEL_MODEL_FILE                 = '{FUEL_MODEL_FILE}'
/

&MONTE_CARLO
  NUM_METEOROLOGY_TIMES           = {weather_band_count(inputs_dir)}
/
{spotting_group(spotting)}"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    validate_namelist(namelist)
    output_path.write_text(namelist, encoding="utf-8", newline="\n")
    logger.info(
        "Namelist written to %s (%.0f h, %.0f s timestep)", output_path, simulation_hours, dt_s
    )
    return output_path, dtdump_s, weather_warnings


def _read_domain(dem_path: Path) -> tuple[float, float, float]:
    """Return (west, south, cell_size) from a UTM raster."""
    if not dem_path.exists():
        raise FileNotFoundError(f"DEM not found at {dem_path} — run ingestion first")
    with rasterio.open(dem_path) as ds:
        b = ds.bounds
        cell_size = abs(ds.transform.a)
    return b.left, b.bottom, cell_size


def _read_srs(dem_path: Path) -> str:
    """Return the DEM CRS in the format ELMFIRE expects for A_SRS."""
    with rasterio.open(dem_path) as ds:
        if ds.crs is None:
            raise ValueError(f"DEM at {dem_path} has no CRS")
        return ds.crs.to_string()


def validate_namelist(namelist: str) -> None:
    """Perform structural validation before handing a namelist to ELMFIRE.

    This is deliberately a small syntax check rather than a replacement for the
    ELMFIRE parser: it catches malformed group delimiters and empty assignments
    while keeping the generated file entirely standard Fortran namelist text.
    """
    groups = re.findall(r"(?ms)^&([A-Z_]+)\s*\n(.*?)(?=^/\s*$)^/\s*$", namelist)
    found = tuple(name for name, _ in groups)
    missing = set(REQUIRED_NAMELISTS) - set(found)
    if missing:
        raise ValueError(f"Missing required namelist group(s): {', '.join(sorted(missing))}")
    if len(found) != len(set(found)):
        raise ValueError("A namelist group was declared more than once")
    if re.search(r"(?m)^\s*[A-Z][A-Z0-9_]*(?:\([0-9]+\))?\s*=\s*(?:!.*)?$", namelist):
        raise ValueError("Namelist contains an empty assignment")


def _validate_parameters(
    simulation_hours: int,
    dt_s: float,
    dtmax_s: float,
    dtdump_s: float,
    dt_meteorology_s: float,
    simulation_tstart_s: float,
    simulator_mode: int,
    crown_fire_model: int,
) -> None:
    values = {
        "simulation_hours": simulation_hours,
        "dt_s": dt_s,
        "dtmax_s": dtmax_s,
        "dtdump_s": dtdump_s,
        "dt_meteorology_s": dt_meteorology_s,
        "simulation_tstart_s": simulation_tstart_s,
        "crown_fire_model": crown_fire_model,
    }
    invalid = [name for name, value in values.items() if not math.isfinite(value) or value < 0]
    if invalid:
        raise ValueError(f"Parameters must be finite and non-negative: {', '.join(invalid)}")
    if simulation_hours <= 0 or dt_s <= 0 or dtmax_s <= 0 or dtdump_s <= 0 or dt_meteorology_s <= 0:
        raise ValueError("Simulation duration and timestep intervals must be greater than zero")
    if dt_s > dtmax_s:
        raise ValueError("dt_s must not exceed dtmax_s")
    if simulator_mode != 1:
        raise ValueError("Only transient ELMFIRE simulator MODE=1 is supported")


def _fortran_path(path: Path) -> str:
    """Make a directory path safe for a single-quoted Fortran namelist value."""
    return str(path).replace("\\", "/").rstrip("/").replace("'", "''") + "/"
