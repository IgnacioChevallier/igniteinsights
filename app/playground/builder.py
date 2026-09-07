"""Builds a synthetic ELMFIRE inputs directory from a Scenario.

Every input is a uniform raster over a square domain, following the shape of ELMFIRE's own
`tutorials/01-constant-wind/01-run.sh`. Nothing here writes the namelist or talks to the
runner: `POST /api/v1/simulations/run` already does both, and it only needs a directory
that exists and contains dem.tif. See PLAYGROUND-SENSIBILIDAD.md §P2.
"""
import logging
import shutil
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform as warp_transform

from app.config import settings
from app.elmfire.builder import fuels_builder, rasters
from app.elmfire.builder.ignition_builder import PHI_IGNITION_FLOOR
from app.playground.schemas import Scenario

logger = logging.getLogger(__name__)

# Written by the builder; everything else the namelist references is uniform.
_FLOAT_RASTERS = ("ws", "wd", "m1", "m10", "m100", "adj")
_INT_RASTERS = ("dem", "slp", "asp", "fbfm40", "cc", "ch", "cbh", "cbd")


def build_scenario_inputs(scenario: Scenario, inputs_dir: Path) -> Path:
    """Write a complete synthetic inputs directory. Returns the directory."""
    inputs_dir.mkdir(parents=True, exist_ok=True)
    profile = _grid_profile(scenario)

    for name, value in [
        ("ws", scenario.wind_speed_mph),
        ("wd", scenario.wind_direction_deg),
        ("m1", scenario.m1_pct),
        ("m10", scenario.m10_pct),
        ("m100", scenario.m100_pct),
        ("adj", scenario.adj),
    ]:
        rasters.write_uniform_float(profile, inputs_dir / f"{name}.tif", value)

    # ELMFIRE's on-disk encoding: ch/cbh are 10×metres, cbd is 100×kg/m³, cc is percent.
    for name, value in [
        ("dem", scenario.elevation_m),
        ("slp", scenario.slope_deg),
        ("asp", scenario.aspect_deg),
        ("fbfm40", scenario.fbfm40_code),
        ("cc", scenario.cc_pct),
        ("ch", round(scenario.ch_m * 10)),
        ("cbh", round(scenario.cbh_m * 10)),
        ("cbd", round(scenario.cbd_kg_m3 * 100)),
    ]:
        rasters.write_uniform_int16(profile, inputs_dir / f"{name}.tif", int(value))

    # A code absent from the table silently becomes model 256 (NB, unburnable) and the
    # whole synthetic domain stops burning without an error. Same guard as the real path.
    fuels_builder.assert_codes_are_defined(
        np.full((1, 1), scenario.fbfm40_code, dtype=np.int16)
    )

    _write_phi(scenario, profile, inputs_dir / "phi.tif")

    shutil.copy2(fuels_builder.FUEL_MODEL_TABLE, inputs_dir / "fuel_models.csv")

    logger.info(
        "Playground inputs at %s — %dx%d cells, fbfm %d, ws %.1f mph from %.0f°",
        inputs_dir, profile["width"], profile["height"],
        scenario.fbfm40_code, scenario.wind_speed_mph, scenario.wind_direction_deg,
    )
    return inputs_dir


def _grid_profile(scenario: Scenario) -> dict:
    """Square domain centred on the AOI centre, in the processing CRS.

    Centring it inside the real AOI is cosmetic — it puts the case somewhere plausible on
    the map instead of at the UTM false origin — but it costs nothing and keeps the CRS
    identical to the production pipeline, so the same code path is exercised.
    """
    crs = settings.aoi_crs_processing
    lon_c = (settings.aoi_west + settings.aoi_east) / 2.0
    lat_c = (settings.aoi_south + settings.aoi_north) / 2.0
    xs, ys = warp_transform("EPSG:4326", crs, [lon_c], [lat_c])

    n = max(2, int(round(scenario.domain_size_m / scenario.cellsize_m)))
    half = n * scenario.cellsize_m / 2.0
    return {
        "driver": "GTiff",
        "height": n,
        "width": n,
        "count": 1,
        "crs": crs,
        "transform": from_origin(xs[0] - half, ys[0] + half, scenario.cellsize_m,
                                 scenario.cellsize_m),
    }


def _write_phi(scenario: Scenario, profile: dict, output: Path) -> Path:
    """Signed distance to a disc at the domain centre: negative inside, positive outside.

    A disc has a closed-form signed distance, so no sweep is needed. The interior is
    floored at PHI_IGNITION_FLOOR because ELMFIRE resets any PHI0 < -1.1 to +1.0
    (unburned) as a nodata guard — without the floor the ignition is erased before the
    simulation starts.
    """
    n = profile["height"]
    cell = scenario.cellsize_m
    centre = (n - 1) / 2.0
    rows, cols = np.mgrid[0:n, 0:n]
    dist_m = np.hypot(rows - centre, cols - centre) * cell

    phi = (dist_m - scenario.ignition_radius_m).astype(np.float32)
    phi = np.where(phi < 0, np.maximum(phi, PHI_IGNITION_FLOOR), phi)

    burning = int((phi < 0).sum())
    if burning == 0:
        raise ValueError(
            f"ignition_radius_m={scenario.ignition_radius_m} is smaller than half a cell "
            f"({cell / 2} m): no cell would ignite and the simulation would do nothing."
        )

    out = dict(profile)
    out.update(dtype="float32", count=1, nodata=None)
    with rasterio.open(output, "w", **out) as dst:
        dst.write(phi.astype(np.float32), 1)
    logger.info("Playground phi: %d burning cells at the domain centre", burning)
    return output
