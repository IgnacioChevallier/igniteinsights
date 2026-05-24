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


def write_namelist(
    inputs_dir: Path,
    outputs_dir: Path,
    simulation_hours: int,
    output_path: Path,
    dt_s: float = 30.0,
    dtmax_s: float = 300.0,
    dtdump_s: float = 3600.0,
) -> Path:
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
        Path to the written namelist.
    """
    tstop_s = simulation_hours * 3600.0
    inputs_str = str(inputs_dir).rstrip("/") + "/"
    outputs_str = str(outputs_dir).rstrip("/") + "/"

    dem_path = inputs_dir / "dem.tif"
    utm_east, utm_west, utm_south, utm_north, cell_size = _read_domain(dem_path)

    namelist = f"""\
&INPUTS
  FUELS_AND_TOPOGRAPHY_DIRECTORY = '{inputs_str}'
  WEATHER_DIRECTORY               = '{inputs_str}'
  DEM_FILENAME                    = 'dem.tif'
  SLOPE_FILENAME                  = 'slp.tif'
  ASPECT_FILENAME                 = 'asp.tif'
  FUEL_MODEL_FILENAME             = 'fbfm40.tif'
  CC_FILENAME                     = 'cc.tif'
  CH_FILENAME                     = 'ch.tif'
  CBH_FILENAME                    = 'cbh.tif'
  CBD_FILENAME                    = 'cbd.tif'
  WS_FILENAME                     = 'ws.tif'
  WD_FILENAME                     = 'wd.tif'
  M1_FILENAME                     = 'm1.tif'
  M10_FILENAME                    = 'm10.tif'
  M100_FILENAME                   = 'm100.tif'
  PHI_FILENAME                    = 'phi.tif'
  IGNITION_RADIUS                 = {cell_size * 1.5:.1f}
  A_SRS                           = 'EPSG:32719'
  XLLCORNER                       = {utm_west:.2f}
  YLLCORNER                       = {utm_south:.2f}
  XURCORNER                       = {utm_east:.2f}
  YURCORNER                       = {utm_north:.2f}
  CELLSIZE                        = {cell_size:.1f}
/

&OUTPUTS
  DTDUMP                          = {dtdump_s:.1f}
  DUMP_NEWBURNS_ONLY              = F
  OUTPUTS_DIRECTORY               = '{outputs_str}'
  CHECK_OUTPUTS_DIRECTORY_EXISTS  = F
  CONVERT_TO_GEOTIFF              = T
  CONVERT_TIMINGS                 = T
  SAVE_ISOCHRONES                 = T
/

&TIME_CONTROL
  SIMULATION_DT                   = {dt_s:.1f}
  SIMULATION_DTMAX                = {dtmax_s:.1f}
  PRINT_SIMULATION_CLOCK          = T
  SIMULATION_TSTOP                = {tstop_s:.1f}
/

&MISCELLANEOUS
  PATH_TO_GDAL                    = '/usr/bin/'
  SCRATCH_PATH                    = '/tmp/'
/
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(namelist)
    logger.info(
        "Namelist written to %s (%.0f h, %.0f s timestep)", output_path, simulation_hours, dt_s
    )
    return output_path


def _read_domain(dem_path: Path) -> tuple[float, float, float, float, float]:
    """Return (east, west, south, north, cell_size) from a UTM raster."""
    if not dem_path.exists():
        raise FileNotFoundError(f"DEM not found at {dem_path} — run ingestion first")
    with rasterio.open(dem_path) as ds:
        b = ds.bounds
        cell_size = abs(ds.transform.a)
    return b.right, b.left, b.bottom, b.top, cell_size
