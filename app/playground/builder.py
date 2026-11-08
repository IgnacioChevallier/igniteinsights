"""Builds a synthetic ELMFIRE inputs directory from a Scenario.

Every input is a uniform raster over a square domain — bar the one deliberate exception,
the `lake` terrain, which cuts a non-burnable patch out of the fuel slab. Follows the
shape of ELMFIRE's own
`tutorials/01-constant-wind/01-run.sh`. Nothing here writes the namelist or talks to the
runner: `POST /api/v1/simulations/run` already does both, and it only needs a directory
that exists and contains dem.tif. See docs/arquitectura.md §P2.
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
from app.elmfire.builder.ignition_builder import PHI_IGNITION_FLOOR, PHI_UNBURNED
from app.playground.schemas import Scenario
from app.postprocessing.wind_field import compass_point

logger = logging.getLogger(__name__)

# Written by the builder; everything else the namelist references is uniform.
_FLOAT_RASTERS = ("ws", "wd", "m1", "m10", "m100", "adj")
_INT_RASTERS = ("dem", "slp", "asp", "fbfm40", "cc", "ch", "cbh", "cbd")

# FBFM 98 (NB8, open water) — a real Scott & Burgan non-burnable code, so ELMFIRE treats
# the patch as a barrier without any special-casing on our side.
_WATER_FBFM = 98

# Lake geometry as fractions of the domain span. Fixed rather than exposed as knobs: the
# lake answers a qualitative question ("what does a barrier do to the front?"), and a
# sweepable radius would invite reading a synthetic circle as a real lake. Together they
# keep the patch inside the domain (0.30 + 0.16 < 0.5) and clear of the ignition disc.
_LAKE_RADIUS_FRAC = 0.16
_LAKE_OFFSET_FRAC = 0.30


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
        ("cc", scenario.cc_pct),
        ("ch", round(scenario.ch_m * 10)),
        ("cbh", round(scenario.cbh_m * 10)),
        ("cbd", round(scenario.cbd_kg_m3 * 100)),
    ]:
        rasters.write_uniform_int16(profile, inputs_dir / f"{name}.tif", int(value))

    fbfm = _fbfm_array(scenario, profile)
    # A code absent from the table silently becomes model 256 (NB, unburnable) and the
    # whole synthetic domain stops burning without an error. Same guard as the real path.
    # Checked on the array that is actually written, so the water patch is covered too.
    fuels_builder.assert_codes_are_defined(fbfm)
    rasters.write_int16_array(profile, inputs_dir / "fbfm40.tif", fbfm)

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


def _lake_disc(scenario: Scenario, profile: dict) -> tuple[float, float, float] | None:
    """Centre and radius of the lake in projected metres, or None for a uniform slab.

    The lake is placed in the fire's path, otherwise the barrier is never reached and the
    terrain looks like it does nothing: fire runs downwind, and upslope when there is no
    wind (`aspect_deg` is the DOWNslope azimuth, hence the +180).
    """
    if scenario.terrain != "lake":
        return None

    transform = profile["transform"]
    span = profile["height"] * scenario.cellsize_m
    cx, cy = transform.c + span / 2.0, transform.f - span / 2.0

    if scenario.wind_speed_mph > 0:
        bearing = (scenario.wind_direction_deg + 180.0) % 360.0
    elif scenario.slope_deg > 0:
        bearing = (scenario.aspect_deg + 180.0) % 360.0
    else:
        # ponytail: with no forcing the spread is isotropic, so no direction is better
        # than another. East, arbitrarily and stably.
        bearing = 90.0

    offset = span * _LAKE_OFFSET_FRAC
    rad = math.radians(bearing)
    return cx + math.sin(rad) * offset, cy + math.cos(rad) * offset, span * _LAKE_RADIUS_FRAC


def _fbfm_array(scenario: Scenario, profile: dict) -> np.ndarray:
    """The fuel model grid: one code everywhere, minus the lake if the scenario has one."""
    n = profile["height"]
    fbfm = np.full((n, n), scenario.fbfm40_code, dtype=np.int16)

    disc = _lake_disc(scenario, profile)
    if disc is not None:
        lx, ly, radius = disc
        transform = profile["transform"]
        cell = scenario.cellsize_m
        # Cell centres, so a cell counts as water when its centre is in the disc.
        rows, cols = np.mgrid[0:n, 0:n]
        xs = transform.c + (cols + 0.5) * cell
        ys = transform.f - (rows + 0.5) * cell
        fbfm[np.hypot(xs - lx, ys - ly) <= radius] = _WATER_FBFM

    return fbfm


def _write_phi(scenario: Scenario, profile: dict, output: Path) -> Path:
    """ELMFIRE's ±1 level-set field: a disc at the domain centre at -1, the rest at +1.

    Not a signed distance: ELMFIRE's level set only advances the front at the Rothermel
    rate on its own ±1 convention (see ignition_builder's module docstring).
    """
    n = profile["height"]
    cell = scenario.cellsize_m
    centre = (n - 1) / 2.0
    rows, cols = np.mgrid[0:n, 0:n]
    burning_mask = np.hypot(rows - centre, cols - centre) * cell < scenario.ignition_radius_m
    phi = np.where(burning_mask, PHI_IGNITION_FLOOR, PHI_UNBURNED).astype(np.float32)

    burning = int(burning_mask.sum())
    if burning == 0:
        raise ValueError(
            f"ignition_radius_m={scenario.ignition_radius_m} is smaller than half a cell "
            f"({cell / 2} m): no cell would ignite and the simulation would do nothing."
        )

    out = dict(profile)
    out.update(dtype="float32", count=1, nodata=None)
    with rasterio.open(output, "w", **out) as dst:
        dst.write(phi, 1)
    logger.info("Playground phi: %d burning cells at the domain centre", burning)
    return output


def scenario_map_layers(scenario: Scenario) -> dict:
    """GeoJSON (EPSG:4326) describing what the scenario *is*, for the synthetic map.

    A satellite basemap under a synthetic run is actively misleading: it shows terrain and
    vegetation that the scenario assumes away. These layers draw the scenario's own
    assumptions instead — the fuel slab (with its lake, if it has one), the ignition disc,
    and the two forcing vectors.

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
        "properties": {
            "kind": "domain",
            "color": fuel["color"],
            "label": fuel["label"],
            # Which vegetation texture the map paints the slab with. The server names the
            # fuel family, the client knows how to draw it — the same split as `color`,
            # so a slab can never be drawn as a fuel the run did not use.
            "pattern": f"fuel-{fuel['fuel_type']}",
        },
        "geometry": {"type": "Polygon", "coordinates": [domain_ring]},
    }]

    # Drawn from the same geometry the raster is rasterised from, so the map can never
    # show a lake somewhere the fuel grid does not have one.
    lake = _lake_disc(scenario, profile)
    if lake is not None:
        lx, ly, radius = lake
        features.append({
            "type": "Feature",
            "properties": {
                "kind": "water",
                "label": "lago (FBFM 98 · no combustible)",
                "pattern": "fuel-water",
            },
            "geometry": {"type": "Polygon", "coordinates": [_disc_ring(to_wgs, lx, ly, radius)]},
        })

    # Ignition disc, as a polygon so it keeps its real size when zooming.
    features.append({
        "type": "Feature",
        "properties": {"kind": "ignition"},
        "geometry": {"type": "Polygon",
                     "coordinates": [_disc_ring(to_wgs, cx, cy, scenario.ignition_radius_m)]},
    })

    # Wind is a field, not a symbol: the map animates it as drifting particles the way
    # Windy does, so this feature carries the parameters rather than a drawn arrow.
    # `azimuth_deg` is where the wind blows TO. The raster holds the direction it comes
    # FROM (ELMFIRE adds 180 internally, elmfire_subs.f90:473), so a client drawing along
    # the raster value would send the flow backwards — the classic error.
    if scenario.wind_speed_mph > 0:
        blows_to = (scenario.wind_direction_deg + 180.0) % 360.0
        features.append({
            "type": "Feature",
            "properties": {
                "kind": "wind",
                "speed_mph": scenario.wind_speed_mph,
                "azimuth_deg": round(blows_to, 1),
                "label": (
                    f"viento {scenario.wind_speed_mph:g} mph "
                    f"hacia el {compass_point(blows_to)}"
                ),
            },
            "geometry": {"type": "Point", "coordinates": to_wgs([cx], [cy])[0]},
        })

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


def _disc_ring(to_wgs, cx: float, cy: float, radius: float, steps: int = 48) -> list:
    """A circle as a closed WGS84 ring. Polygons, not point markers, so a disc keeps its
    real size when the map is zoomed."""
    angles = [2 * math.pi * i / steps for i in range(steps + 1)]
    return to_wgs(
        [cx + radius * math.sin(a) for a in angles],
        [cy + radius * math.cos(a) for a in angles],
    )


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
