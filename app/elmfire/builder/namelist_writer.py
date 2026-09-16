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

import rasterio

logger = logging.getLogger(__name__)

DEFAULT_DTDUMP_S = 3600.0
# Weather rasters whose band count is the forecast time series. ELMFIRE reads band n as
# the weather at TSTART + n × DT_METEOROLOGY and interpolates between bands.
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
# ETAPA-B-INSUMO-PATAGONICO.md §B5: source is Bianchi & Defossé (2015), LFMC by species for
# Andean Patagonia.
# ELMFIRE enciende el fuego de copas si el namelist OMITE CROWN_FIRE_MODEL
# (.claude/skills/elmfire/references/namelist-reference.md: &SIMULATOR, 0 = off,
# cualquier valor > 0 = on). Estaba activo por omisión, no por decisión. Se escribe
# explícito con el valor que ya se venía usando: activado.
DEFAULT_CROWN_FIRE_MODEL = 1

DEFAULT_LH_MOISTURE_PCT = 60.0
DEFAULT_LW_MOISTURE_PCT = 60.0


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

    ELMFIRE indexes weather bands by `TSTART + n × DT_METEOROLOGY`. A raster with fewer
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
        simulation_tstart_s: absolute simulation start time in seconds. Non-zero anchors
            the run to the wall clock: ELMFIRE reads weather band n at
            TSTART + n × DT_METEOROLOGY, so this is what puts the fire at the right point
            of the diurnal cycle.
        simulator_mode: ELMFIRE mode; 1 is transient fire-spread simulation
        crown_fire_model: 0 disables crown fire; any value > 0 enables it. Written
            explicitly because ELMFIRE enables it when the keyword is absent.

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
"""
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
