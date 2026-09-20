"""Builds a synthetic ELMFIRE inputs directory from a Scenario.

Every input is a uniform raster over a square domain, following the shape of ELMFIRE's own
`tutorials/01-constant-wind/01-run.sh`. Nothing here writes the namelist or talks to the
runner: `POST /api/v1/simulations/run` already does both, and it only needs a directory
that exists and contains dem.tif. See PLAYGROUND-SENSIBILIDAD.md §P2.
"""
import logging
import math
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


def scenario_map_layers(scenario: Scenario) -> dict:
    """GeoJSON (EPSG:4326) describing what the scenario *is*, for the synthetic map.

    A satellite basemap under a synthetic run is actively misleading: it shows terrain and
    vegetation that the scenario assumes away. These layers draw the scenario's own
    assumptions instead — a uniform slab of one fuel model, the ignition disc, and the two
    forcing vectors.

    Built here, next to the grid, so the UTM→4326 conversion has exactly one home.
    """
    profile = _grid_profile(scenario)
    transform = profile["transform"]
    n = profile["height"]
    x0, y0 = transform.c, transform.f                 # north-west corner
    span = n * scenario.cellsize_m
    x1, y1 = x0 + span, y0 - span                     # south-east corner
    cx, cy = x0 + span / 2.0, y0 - span / 2.0
    crs = profile["crs"]

    def to_wgs(xs: list[float], ys: list[float]) -> list[list[float]]:
        lons, lats = warp_transform(crs, "EPSG:4326", xs, ys)
        return [[lon, lat] for lon, lat in zip(lons, lats)]

    domain_ring = to_wgs([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0])

    fuel = fuels_builder.fuel_model_info(scenario.fbfm40_code)
    features: list[dict] = [{
        "type": "Feature",
        # The colour travels with the geometry so the map can paint it straight from the
        # feature, and so it can never disagree with the model the run actually used.
        "properties": {"kind": "domain", "color": fuel["color"], "label": fuel["label"]},
        "geometry": {"type": "Polygon", "coordinates": [domain_ring]},
    }]

    # Ignition disc, as a polygon so it keeps its real size when zooming.
    steps = 48
    angles = [2 * math.pi * i / steps for i in range(steps + 1)]
    features.append({
        "type": "Feature",
        "properties": {"kind": "ignition"},
        "geometry": {"type": "Polygon", "coordinates": [to_wgs(
            [cx + scenario.ignition_radius_m * math.sin(a) for a in angles],
            [cy + scenario.ignition_radius_m * math.cos(a) for a in angles],
        )]},
    })

    # Wind: drawn pointing where it blows TO. The raster holds the direction it comes
    # FROM (ELMFIRE adds 180 internally, elmfire_subs.f90:473), so an arrow drawn along
    # the raster value would point backwards — the classic error.
    if scenario.wind_speed_mph > 0:
        features.append(_arrow(
            to_wgs, cx - span * 0.34, cy + span * 0.30,
            azimuth_deg=(scenario.wind_direction_deg + 180.0) % 360.0,
            length_m=span * (0.06 + 0.10 * min(scenario.wind_speed_mph / 40.0, 1.0)),
            kind="wind",
            label=f"viento {scenario.wind_speed_mph:g} mph",
        ))

    # Slope: drawn pointing downslope, which is what aspect_deg means. Fire runs the
    # other way, upslope.
    if scenario.slope_deg > 0:
        features.append(_arrow(
            to_wgs, cx - span * 0.34, cy - span * 0.30,
            azimuth_deg=float(scenario.aspect_deg),
            length_m=span * (0.06 + 0.10 * min(scenario.slope_deg / 45.0, 1.0)),
            kind="slope",
            label=f"pendiente {scenario.slope_deg}° (flecha = cuesta abajo)",
        ))

    return {"type": "FeatureCollection", "features": features}


def _arrow(to_wgs, x: float, y: float, azimuth_deg: float, length_m: float,
           kind: str, label: str) -> dict:
    """Shaft plus two barbs, as one MultiLineString in projected metres."""
    rad = math.radians(azimuth_deg)
    dx, dy = math.sin(rad), math.cos(rad)
    tip_x, tip_y = x + dx * length_m, y + dy * length_m
    barb = length_m * 0.28

    lines = [to_wgs([x, tip_x], [y, tip_y])]
    for offset in (140.0, -140.0):
        b = math.radians(azimuth_deg + offset)
        lines.append(to_wgs(
            [tip_x, tip_x + math.sin(b) * barb], [tip_y, tip_y + math.cos(b) * barb]
        ))
    return {
        "type": "Feature",
        "properties": {"kind": kind, "label": label, "azimuth_deg": round(azimuth_deg, 1)},
        "geometry": {"type": "MultiLineString", "coordinates": lines},
    }
