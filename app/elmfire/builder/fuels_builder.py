"""
Derives fbfm40.tif (Scott & Burgan 40 fuel models) from ESA WorldCover land cover.

WorldCover v2.0 classes (2021) → FBFM40 crosswalk for Patagonian forest (Los Alerces).
Output is matched to the reference grid (EPSG:32719, 30 m) and cached in data/static/ —
see `_cache_key`. Bump `DERIVATION_VERSION` on ANY change to how fbfm40.tif is produced,
or the cache will keep serving the old raster and the change will appear to work while
doing nothing.
"""
import hashlib
import json
import logging
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

logger = logging.getLogger(__name__)

# WorldCover class → Scott & Burgan FBFM40 model number
# Reference: Scott & Burgan (2005), Gen. Tech. Rep. RMRS-GTR-153
WORLDCOVER_TO_FBFM40: dict[int, int] = {
    10: 183,   # Tree cover         → TL3 Tall pine needles/cones
    20: 145,   # Shrubland          → SH5 High load dry shrub
    30: 102,   # Grassland          → GR2 Low load dry grass
    40: 101,   # Cropland           → GR1 Short sparse dry grass
    50: 91,    # Built-up           → NB1 Urban/suburban
    60: 93,    # Bare/sparse veg    → NB3 Agricultural/bare
    70: 93,    # Snow and ice       → NB3
    80: 98,    # Permanent water    → NB8 Open water
    90: 103,   # Herbaceous wetland → GR3 Low load very coarse humid
    95: 183,   # Mangroves          → TL3
    100: 101,  # Moss and lichen    → GR1
}
_NODATA_FBFM40 = 99   # NB9 Barrens (unburnable placeholder)

# Bump on ANY change to the crosswalk semantics, the aggregation rule, the nodata value or
# the output dtype. Without this the `.exists()` check served the raster on disk forever:
# a crosswalk edit was a silent no-op until someone deleted data/static/fbfm40.tif by hand.
# Same failure that hit dem/slp/asp — see raster_aligner.DERIVATION_VERSION.
DERIVATION_VERSION = 1
_CACHE_KEY_FILE = ".fbfm40_cache_key.json"

# Identity of the land-cover source this crosswalk is written against. Part of the cache
# key so that switching sources can never reuse a raster built from the previous one.
WORLDCOVER_SOURCE_ID = "esa_worldcover_v200_2021"

# The fuel model table ELMFIRE will actually load (see namelist_writer.FUEL_MODEL_FILE).
# This file — not the 90-204 numeric range — is what "a valid FBFM40 code" means: ELMFIRE
# resolves any code missing from the table to model 256 (NB), load 0.0001, depth 0.01, i.e.
# unburnable, with no error and no log line. A stray code silently turns part of the park
# non-flammable, which invalidates the whole run.
FUEL_MODEL_TABLE = Path(__file__).resolve().parent.parent / "fuel_models.csv"

# Display metadata for the fuels map view (GET /api/v1/fuels/map). Kept here so the
# crosswalk above and what the dashboard legend claims cannot drift apart.
WORLDCOVER_LABELS: dict[int, str] = {
    10: "Cobertura arbórea",
    20: "Arbustal",
    30: "Pastizal",
    40: "Cultivos",
    50: "Área construida",
    60: "Suelo desnudo / vegetación rala",
    70: "Nieve y hielo",
    80: "Agua permanente",
    90: "Humedal herbáceo",
    95: "Manglar",
    100: "Musgo y liquen",
}

# FBFM40 code → (etiqueta, color hex). Colors are land-cover semantic (verde bosque,
# oliva arbustal, ocre pastizal, gris urbano, azul agua), not a categorical ramp.
FBFM40_DISPLAY: dict[int, tuple[str, str]] = {
    183: ("TL3 · hojarasca de conífera alta", "#1b5e20"),
    145: ("SH5 · arbustal denso seco", "#7a8b3a"),
    103: ("GR3 · pastizal húmedo grueso", "#8fbc6d"),
    102: ("GR2 · pastizal seco carga baja", "#d9c27a"),
    101: ("GR1 · pastizal ralo", "#ece1b4"),
    91: ("NB1 · urbano", "#9e9e9e"),
    93: ("NB3 · suelo desnudo / agrícola", "#c9bfae"),
    98: ("NB8 · agua", "#4a80c0"),
    99: ("NB9 · estéril (sin clase)", "#e6e6e6"),
}


# Scott & Burgan (2005) p. 5, Table 1: each fuel type owns a block of model numbers, and
# the authors state the reason plainly — "so that fuel model maps colored by fuel type are
# simple to create". One colour per block covers all 256 codes without inventing anything,
# which is what the synthetic playground map needs for an arbitrary fuel model.
_FUEL_TYPE_BLOCKS: list[tuple[int, int, str, str, str]] = [
    (1, 13, "FBFM13", "#8a6d3b", "13 modelos originales"),
    (90, 99, "NB", "#b8bcc0", "No combustible"),
    (100, 119, "GR", "#d9c27a", "Pastizal"),
    (120, 139, "GS", "#bcae6a", "Pastizal-arbustal"),
    (140, 159, "SH", "#7a8b3a", "Arbustal"),
    (160, 179, "TU", "#4a7a3a", "Bosque con sotobosque"),
    (180, 199, "TL", "#1b5e20", "Hojarasca de bosque"),
    (200, 219, "SB", "#6b4f2a", "Restos de corta / caída"),
]


def fuel_model_info(code: int) -> dict:
    """Identity of a fuel model: short name, fuel type, colour and label.

    The short name comes from the table ELMFIRE will load, so it can never disagree with
    what the simulation actually ran. The colour comes from the fuel type block, which is
    defined for every code — FBFM40_DISPLAY only covers the handful the WorldCover
    crosswalk emits, and the playground can be handed any model in the table.
    """
    fuel_type, color, type_label = "?", "#9e9e9e", "Desconocido"
    for low, high, name, hex_color, label in _FUEL_TYPE_BLOCKS:
        if low <= code <= high:
            fuel_type, color, type_label = name, hex_color, label
            break

    short_name, display_label = str(code), None
    for line in FUEL_MODEL_TABLE.read_text(encoding="utf-8").splitlines():
        if line.strip() and int(line.split(",")[0]) == code:
            short_name = line.split(",")[1]
            break
    if code in FBFM40_DISPLAY:
        display_label = FBFM40_DISPLAY[code][0]

    return {
        "code": code,
        "name": short_name,
        "fuel_type": fuel_type,
        "fuel_type_label": type_label,
        "color": color,
        "label": display_label or f"{short_name} · {type_label}",
    }


def worldcover_to_fbfm40(
    worldcover_path: Path,
    reference_path: Path,
    output_path: Path,
) -> Path:
    """Reclassify WorldCover to FBFM40 on the reference grid. Cached; see `_cache_key`.

    Aggregation to the 30 m grid is by **majority class** (`Resampling.mode`): the output
    pixel takes the cover class occupying most of its area. This is a model assumption, not
    an implementation detail — it discards fuel corridors narrower than one pixel, and fuel
    continuity governs spread. Declared in ETAPA-A-BASELINE.md §A5.

    The mode is taken over *cover* classes and the crosswalk applied afterwards, so the
    aggregation is defined on the source legend and stays comparable across sources. GDAL
    does not report how many destination pixels had a tie, so ties are not logged; the
    resulting class histogram is logged instead.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    key = _cache_key(
        worldcover_path, reference_path, WORLDCOVER_SOURCE_ID, WORLDCOVER_TO_FBFM40
    )
    key_path = output_path.parent / _CACHE_KEY_FILE
    cached_key = None
    if key_path.exists():
        try:
            cached_key = json.loads(key_path.read_text())
        except (OSError, ValueError):
            cached_key = None  # unreadable key → treat as a miss and rebuild

    if output_path.exists() and cached_key == key:
        logger.info("FBFM40 cache hit at %s — skipping", output_path)
        return output_path
    if output_path.exists():
        logger.info("FBFM40 cache stale (key %s → %s) — regenerating", cached_key, key)

    with rasterio.open(reference_path) as ref:
        dst_transform = ref.transform
        dst_crs = ref.crs
        dst_shape = (ref.height, ref.width)
        profile = ref.meta.copy()

    with rasterio.open(worldcover_path) as src:
        wc_raw = np.empty(dst_shape, dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=wc_raw,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.mode,  # land-cover: majority class per output pixel
        )

    wc_int = np.round(wc_raw).astype(np.int16)
    fbfm40 = np.full_like(wc_int, _NODATA_FBFM40, dtype=np.int16)
    for wc_class, fuel_model in WORLDCOVER_TO_FBFM40.items():
        fbfm40[wc_int == wc_class] = fuel_model

    # Validate before writing: a raster with an undefined code must never reach disk.
    assert_codes_are_defined(fbfm40)

    profile.update(dtype="int16", count=1, nodata=_NODATA_FBFM40)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(fbfm40, 1)

    key_path.write_text(json.dumps(key, sort_keys=True))

    codes, counts = np.unique(fbfm40, return_counts=True)
    total = int(counts.sum())
    logger.info(
        "FBFM40 raster written to %s — %s",
        output_path,
        ", ".join(
            f"{int(c)}:{n / total:.1%}"
            for c, n in sorted(zip(codes, counts), key=lambda p: -p[1])
        ),
    )
    return output_path


def _cache_key(
    source_path: Path,
    reference_path: Path,
    source_id: str,
    crosswalk: dict[int, int],
) -> dict:
    """Identity of a cached fbfm40 raster: the source raster, which legend it speaks, the
    crosswalk applied to it, the target grid, and the version of this code.

    Source identity uses size + nanosecond mtime rather than a content hash — the raw
    land-cover raster is hundreds of MB and is only ever replaced wholesale by a
    re-download. Same reasoning as raster_aligner._cache_key.
    """
    stat = source_path.stat()
    with rasterio.open(reference_path) as ref:
        grid = {
            "crs": str(ref.crs),
            "transform": [round(v, 6) for v in tuple(ref.transform)[:6]],
            "width": ref.width,
            "height": ref.height,
        }
    crosswalk_repr = json.dumps({str(k): v for k, v in sorted(crosswalk.items())})
    return {
        "version": DERIVATION_VERSION,
        "source_id": source_id,
        "src_name": source_path.name,
        "src_size": stat.st_size,
        "src_mtime_ns": stat.st_mtime_ns,
        "crosswalk_sha256": hashlib.sha256(crosswalk_repr.encode()).hexdigest()[:16],
        "nodata": _NODATA_FBFM40,
        "grid": grid,
    }


def valid_fuel_codes(table_path: Path | None = None) -> set[int]:
    """Model numbers defined in the fuel model table.

    ELMFIRE reads the table with a list-directed READ inside a `DO WHILE (IOS .EQ. 0)`
    loop, so the first unparseable line silently truncates it — the file carries no header
    and no comments, and this parser mirrors that: bare `num,name,...` rows only.
    """
    path = table_path or FUEL_MODEL_TABLE
    return {
        int(line.split(",")[0])
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def assert_codes_are_defined(fbfm40: "np.ndarray", table_path: Path | None = None) -> None:
    """Raise if the raster carries a code ELMFIRE would silently degrade to NB."""
    present = {int(c) for c in np.unique(fbfm40)}
    undefined = sorted(present - valid_fuel_codes(table_path))
    if undefined:
        raise ValueError(
            f"fbfm40 carries codes absent from the fuel model table: {undefined}. "
            f"ELMFIRE would resolve these to model 256 (NB, unburnable) without an error. "
            f"Add them to {(table_path or FUEL_MODEL_TABLE).name} or fix the crosswalk."
        )
