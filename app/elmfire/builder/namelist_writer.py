"""
Writes elmfire.data (Fortran namelist) consumed by the ELMFIRE runner.

The namelist tells ELMFIRE where to find each input raster and where to write
outputs. All paths must be accessible to the elmfire-runner container via the
shared data volume.
"""
import logging
from pathlib import Path

import rasterio

logger = logging.getLogger(__name__)

DEFAULT_DTDUMP_S = 3600.0


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


def write_namelist(
    inputs_dir: Path,
    outputs_dir: Path,
    simulation_hours: int,
    output_path: Path,
    dt_s: float = 30.0,
    dtmax_s: float = 300.0,
    dtdump_s: float = DEFAULT_DTDUMP_S,
) -> tuple[Path, float]:
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

    Returns:
        Tuple of (path to the written namelist, resolved dump interval in seconds).
    """
    tstop_s = simulation_hours * 3600.0
    dtdump_s = resolve_dtdump_s(tstop_s, dtdump_s)
    inputs_str = str(inputs_dir).rstrip("/") + "/"
    outputs_str = str(outputs_dir).rstrip("/") + "/"

    dem_path = inputs_dir / "dem.tif"
    utm_west, utm_south, cell_size = _read_domain(dem_path)

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
  DT_METEOROLOGY                  = 3600.0
/

&COMPUTATIONAL_DOMAIN
  A_SRS                           = 'EPSG:32719'
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
  SIMULATION_DT                   = {dt_s:.1f}
  SIMULATION_DTMAX                = {dtmax_s:.1f}
  SIMULATION_TSTOP                = {tstop_s:.1f}
/

&MISCELLANEOUS
  PATH_TO_GDAL                    = '/usr/bin/'
  SCRATCH                         = '/tmp/'
/
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(namelist)
    logger.info(
        "Namelist written to %s (%.0f h, %.0f s timestep)", output_path, simulation_hours, dt_s
    )
    return output_path, dtdump_s


def _read_domain(dem_path: Path) -> tuple[float, float, float]:
    """Return (west, south, cell_size) from a UTM raster."""
    if not dem_path.exists():
        raise FileNotFoundError(f"DEM not found at {dem_path} — run ingestion first")
    with rasterio.open(dem_path) as ds:
        b = ds.bounds
        cell_size = abs(ds.transform.a)
    return b.left, b.bottom, cell_size
