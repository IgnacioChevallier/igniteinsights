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
    """Reclassify WorldCover to FBFM40 on the reference grid — the baseline map.

    Delegates to `raster_to_fbfm40`: two copies of the same reclassification would drift,
    and the aggregation rule is a declared model assumption (ETAPA-A §A5), not an
    implementation detail to be maintained twice. Kept as a named entry point because
    WorldCover is the frozen baseline the thesis compares against.
    """
    return raster_to_fbfm40(
        worldcover_path,
        reference_path,
        output_path,
        WORLDCOVER_TO_FBFM40,
        WORLDCOVER_SOURCE_ID,
    )


def _cache_key(
    source_path: Path,
    reference_path: Path,
    source_id: str,
    crosswalk: dict[int, int] | dict[str, int],
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


# ---------------------------------------------------------------------------
# MapBiomas Argentina Colección 2 → FBFM40 (docs/crosswalk/IGN-20-CROSSWALK.md §5)
# ---------------------------------------------------------------------------
MAPBIOMAS_SOURCE_ID = "mapbiomas_argentina_col2_2024"

MAPBIOMAS_TO_FBFM40: dict[int, int] = {
    3: 165,    # Bosques cerrados                 → TU5
    4: 163,    # Bosques abiertos                 → TU3
    6: 162,    # Bosques inundables               → TU2
    66: 149,   # Arbustales cerrados              → SH9
    77: 144,   # Arbustales abiertos              → SH4
    63: 123,   # Mosaicos de arbustos y herbáceas → GS3
    12: 103,   # Herbáceas                        → GR3
    11: 105,   # Herbáceas inundables (mallines)  → GR5
    73: 99,    # Turberas                         → NB9, fuera de alcance (§6.6)
    9: 188,    # Silvicultura                     → TL8
    15: 102,   # Pasturas                         → GR2
    18: 101,   # Agricultura                      → GR1
    19: 101,   # Cultivos temporarios             → GR1
    36: 101,   # Cultivos perennes                → GR1
    21: 101,   # Mosaico de usos                  → GR1
    24: 91,    # Áreas urbanas                    → NB1
    25: 99,    # Otras áreas no vegetadas         → NB9
    33: 98,    # Ríos, lagunas, lagos             → NB8
    34: 92,    # Hielo y nieve permanente         → NB2
    # 0 (sin dato, lado chileno) y 27 (no observado) quedan deliberadamente fuera:
    # son hueco, y el hueco se rellena con la fuente global (§7.5, opción 1).
}

# ---------------------------------------------------------------------------
# CCS-BAP (CIEFAP/MAyDS) → FBFM40 — ver docs/crosswalk/IGN-20B-FINAL-CROSSWALK-CCSBAP.md
#
# Clave: el par (Ley_N1, Ley_N2). Ley_N2 sola es ambigua — "Le" existe como bosque
# (TF) y como lenga achaparrada (OFL), y esa distinción estructural es justamente la
# que separa un modelo de hojarasca de uno de matorral.
# ---------------------------------------------------------------------------
CCSBAP_SOURCE_ID = "ccsbap_ciefap_2017_chubut_n3"

CCSBAP_TO_FBFM40: dict[tuple[str, str], int] = {
    # --- Tierras Forestales: bosque ---
    ("TF", "Le"): 186,    # Lenga           → TL6 hojarasca latifoliada moderada
    ("TF", "Ñi"): 163,    # Ñire            → TU3 hojarasca con pasto y arbustos
    ("TF", "Co"): 165,    # Coihue          → TU5 hojarasca alta con sotobosque de caña
    ("TF", "Ci"): 165,    # Ciprés          → TU5 conífera con sotobosque arbustivo
    ("TF", "Al"): 185,    # Alerce          → TL5 hojarasca de conífera carga alta
    ("TF", "Mx"): 165,    # Mixtos          → TU5
    ("TF", "Ma"): 182,    # Maitén          → TL2 hojarasca latifoliada carga baja
    ("TF", "Rd"): 182,    # Radal           → TL2
    ("TF", "Mr"): 182,    # Mirtáceas       → TL2
    ("TF", "Cg"): 185,    # Ciprés guaitecas→ TL5
    # --- Otras Formaciones Leñosas: matorral y bosque achaparrado ---
    ("OFL", "Ñi"): 148,      # Ñire bajo       → SH8  (PT-37 modelo A1)
    ("OFL", "Le"): 148,      # Lenga achaparrada→ SH8
    ("OFL", "Arbu Na"): 144, # Arbustal nativo → SH4  (PT-37 modelo A3)
    ("OFL", "MMx"): 144,     # Matorral mixto  → SH4
    ("OFL", "Ci"): 144,      # Ciprés abierto/juvenil → SH4
    ("OFL", "Co"): 144,      # Coihue juvenil  → SH4
    ("OFL", "Ch"): 144,      # Chacay          → SH4
    ("OFL", "Rd"): 144,      # Radal juvenil   → SH4
    ("OFL", "Mr"): 144,      # Mirtáceas bajas → SH4
    ("OFL", "Ma"): 144,      # Maitén bajo     → SH4
    ("OFL", "Cg"): 144,      # Ciprés guaitecas juvenil → SH4
    # --- Otras Tierras ---
    # Estepa → GR2 (docs/crosswalk/DECISIONES-MODELO-V0 loop L; antes GR3,
    # 1.138 m/h a 10 mph, precisión 0,12 en calibración) y sobre el límite del bosque → NB9
    # (CCSBAP_SOBRE_LIMITE_BOSQUE).
    ("OT", "Herb-Subarb"): 102,   # Estepa      → GR2 (ver override Estepa Arb/Pradera)
    ("OT", "Erial"): 99,          # Erial       → NB9
    ("OT", "Humedales"): 105,     # Mallín      → GR5 (ver override Turbera)
    ("OT", "Agua"): 98,           # Agua        → NB8
    ("OT", "Hie-Nie"): 92,        # Hielo/nieve → NB2
    # Remanente de disturbio reciente → SH3
    # (docs/crosswalk/DECISIONES-MODELO-V0 §4, loop L): el GS3 de la PT-37 (A2, ñire a
    # 2 años) describe los primeros 2-5 años; con mapas de 2013/2017 y fuegos
    # de 2015-2026 el remanente tiene 6-15 años, matorral rebrotante leñoso (Tiribelli et al.
    # 2018; Blackhall et al. 2017).
    ("OT", "Rem Dist Rec"): 143,
    ("OT", "Exot-Artif"): 101,    # Exóticas/artificial → GR1 (ver overrides)
}

# Clases de nivel 3 cuyo comportamiento del fuego NO es el de su nivel 2. Sin estos, la
# turbera heredaría el modelo del mallín y una forestación de pino heredaría el de un
# cultivo. Cada una está justificada en docs/crosswalk/IGN-20B-FINAL-CROSSWALK-CCSBAP.md §5.
CCSBAP_N3_OVERRIDES: dict[str, int] = {
    "Turbera": 99,       # NB9 — combustión latente, fuera del alcance de Rothermel
    "Cg Juv-Tur": 99,    # ciprés de las guaitecas sobre turbera → ídem
    "Caña": 149,         # caña colihue → SH9, carga muy alta, lecho profundo
    "Estepa Arb": 123,   # estepa arbustiva → GS3 (PT-37 modelos A4 y A5)
    "Pradera": 105,      # pradera húmeda → GR5
    "Forest": 188,       # forestación de coníferas exóticas → TL8
    "Arles Ex": 182,     # arboledas exóticas latifoliadas → TL2
    "Arbu Ex": 144,      # arbustal exótico → SH4
    "Pastura": 102,      # pastura implantada → GR2
    "Infraest": 91,      # infraestructura → NB1
}


# Clases de nivel 3 que sobre una altura (m, del DEM de referencia) cambian de modelo: CCS-BAP
# llama "Estepa" también a la vegetación altoandina rala entre roca y nieve, por encima del
# límite del bosque (docs/resultados/AUDITORIA-FISICA.md loop K;
# docs/crosswalk/DECISIONES-MODELO-V0 loop L: +0,009 en calibración,
# Alerces 2024 0,562 → 0,614).
CCSBAP_SOBRE_LIMITE_BOSQUE: dict[str, tuple[float, int]] = {"Estepa": (1300.0, 99)}

# Año que observa cada mapa de cobertura: las quemas posteriores no están en él.
COVER_MAP_YEAR: dict[str, int] = {"ccsbap": 2017, "mapbiomas": 2024, "worldcover": 2021}

# Lo ya quemado que el mapa no vio (docs/resultados/LO-YA-QUEMADO-PROPUESTA.md §4 y §11), por
# edad de la quema: (desde, hasta, modelo, sólo bosque TL/TU). 1-5 años: rebrote ralo con
# entreparches amplios (PT-37 A2; Landesmann et al. 2021); las cicatrices de 1-5 años casi no
# vuelven a arder y frenan al fuego en el borde (MCD64A1, §10.3). 6-15: el bosque es matorral
# rebrotante, más inflamable (Paritsis et al. 2015; §10.3), como el remanente de CCS-BAP
# (DECISIONES-MODELO-V0 §4). Más viejo: el mapa, como LANDFIRE FDist.
FUEL_BY_BURN_AGE: list[tuple[int, int, int, bool]] = [
    (1, 5, 101, False),   # GR1
    (6, 15, 143, True),   # SH3
]
# Último año de Hansen GFC lossyear en settings.hansen_lossyear_path (v1.13 = GFC-2025).
HANSEN_LAST_YEAR = 2025


def last_burn_before(burn_bits: np.ndarray, year: int) -> np.ndarray:
    """Last burn year before `year` (lossyear encoding) from a uint32 mask where bit i is a
    burn in 2001 + i (scripts/anio_quema.py). Keeping every year, not only the last, is what
    stops a fire's own scar from hiding the earlier burns of those cells."""
    out = np.zeros(burn_bits.shape, dtype=np.uint8)
    for y in range(2001, min(year, 2033)):
        out[((burn_bits >> (y - 2001)) & 1) == 1] = y - 2000
    return out


def reassign_burns_by_age(
    fbfm40: np.ndarray, burn_year: np.ndarray, simulation_year: int, map_year: int,
    other_burn_bits: np.ndarray | None = None,
) -> np.ndarray:
    """Fuel of the burns the cover map never saw, by burn age (FUEL_BY_BURN_AGE).

    `burn_year` is Hansen GFC `lossyear` (0 = none, n = 2000 + n); `other_burn_bits` is what
    other sources saw burn, every year (dNBR, MCD64A1: last_burn_before). A forest
    cell (TL/TU in this map) only takes another source's burn after HANSEN_LAST_YEAR: until
    then only Hansen says the stand was replaced, and a burn that left it standing does not
    change the fuel (Landesmann et al. 2021). Other cells take the latest of both.

    Burns the map already saw are left alone: a burnt forest the map still calls forest most
    likely burnt at low severity. Never a burn of the simulation year itself, which can be the
    fire being simulated. Non-burnable codes (NB) never change.
    """
    burnable = (fbfm40 >= 101) & (fbfm40 <= 204)   # GR to SB; NB is 91-99 and 256
    forest = ((fbfm40 >= 161) & (fbfm40 <= 165)) | ((fbfm40 >= 181) & (fbfm40 <= 189))
    # A burn of the simulation year (maybe the fire itself) never counts, nor hides older ones.
    burn_year = np.where(2000 + burn_year.astype(np.int32) < simulation_year, burn_year, 0)
    if other_burn_bits is not None:
        other_burn_year = last_burn_before(other_burn_bits, simulation_year)
        unpublished = other_burn_year > HANSEN_LAST_YEAR - 2000
        latest = np.maximum(burn_year, other_burn_year)
        burn_year = np.where(forest & ~unpublished, burn_year, latest)
    year = 2000 + burn_year.astype(np.int32)
    age = np.where(burn_year > 0, simulation_year - year, 0)
    unseen = (burn_year > 0) & (year > map_year)
    out = fbfm40.copy()
    for low, high, code, forest_only in FUEL_BY_BURN_AGE:
        band = unseen & (age >= low) & (age <= high)
        out[band & (forest if forest_only else burnable)] = code
    assert_codes_are_defined(out)
    return out


def reassign_burns_in_raster(
    fbfm40_path: Path, lossyear_path: Path, simulation_year: int, map_year: int,
    other_burns_path: Path | None = None,
) -> float:
    """reassign_burns_by_age on an fbfm40.tif in place (same grid as the burn rasters).
    Returns the hectares that changed."""
    with rasterio.open(fbfm40_path) as src:
        fbfm40, profile = src.read(1), src.profile
        cell_ha = abs(src.res[0] * src.res[1]) / 1e4
    with rasterio.open(lossyear_path) as src:
        burn_year = np.clip(src.read(1), 0, None)   # reproject_canopy writes nodata -9999
    other = None
    if other_burns_path is not None:   # uint32 bit mask: nearest onto the fuel grid, no int16
        with rasterio.open(other_burns_path) as src:
            other = np.zeros(fbfm40.shape, dtype=np.uint32)
            reproject(src.read(1), other, src_transform=src.transform, src_crs=src.crs,
                      dst_transform=profile["transform"], dst_crs=profile["crs"],
                      resampling=Resampling.nearest)
    out = reassign_burns_by_age(fbfm40, burn_year, simulation_year, map_year, other)
    with rasterio.open(fbfm40_path, "w", **profile) as dst:
        dst.write(out, 1)
    hectares = float((out != fbfm40).sum() * cell_ha)
    logger.info("Burns after %d reassigned by age: %.0f ha", map_year, hectares)
    return hectares


def ccsbap_fuel_code(ley_n1: str, ley_n2: str, ley_n3: str) -> int:
    """Fuel model for one CCS-BAP polygon. Raises if the legend class is unknown —
    silence here would map a real class to unburnable without anyone noticing."""
    if ley_n3 in CCSBAP_N3_OVERRIDES:
        return CCSBAP_N3_OVERRIDES[ley_n3]
    try:
        return CCSBAP_TO_FBFM40[(ley_n1, ley_n2)]
    except KeyError:
        raise ValueError(
            f"CCS-BAP class ({ley_n1}, {ley_n2}, {ley_n3}) has no fuel model. "
            f"Add it to CCSBAP_TO_FBFM40 or CCSBAP_N3_OVERRIDES."
        ) from None


def _fill_gaps(
    fbfm40: "np.ndarray", gap_mask: "np.ndarray", fill_path: Path | None
) -> "np.ndarray":
    """Resolve pixels the source has no class for.

    Both Argentine products (MapBiomas, CCS-BAP) stop at the international border, and the
    gap sits on the **west edge of the domain** — an artificially unburnable border stops
    the front by construction and biases any validation (IGN-20 §7.5). Option 1 of that
    section: fill from the global product. Same rule for every source, or the comparison
    measures the fill rule instead of the map.
    """
    if not gap_mask.any():
        return fbfm40
    if fill_path is None:
        logger.warning("%d gap pixels left as NB9 — no fill raster given", int(gap_mask.sum()))
        fbfm40[gap_mask] = _NODATA_FBFM40
        return fbfm40
    with rasterio.open(fill_path) as src:
        fill = src.read(1)
    if fill.shape != fbfm40.shape:
        raise ValueError(f"fill raster {fill_path.name} is {fill.shape}, grid is {fbfm40.shape}")
    fbfm40[gap_mask] = fill[gap_mask]
    logger.info(
        "Filled %d gap pixels (%.2f%%) from %s",
        int(gap_mask.sum()), 100 * gap_mask.mean(), fill_path.name,
    )
    return fbfm40


def raster_to_fbfm40(
    source_path: Path,
    reference_path: Path,
    output_path: Path,
    crosswalk: dict[int, int],
    source_id: str,
    fill_path: Path | None = None,
) -> Path:
    """Reclassify any raster land-cover source to FBFM40 on the reference grid.

    Source-neutral version of `worldcover_to_fbfm40`: same majority aggregation (A5) and
    same cache semantics, with the crosswalk and the source identity passed in so several
    products can coexist (ETAPA-B §B3). Classes absent from `crosswalk` are treated as
    gap, not as unburnable — see `_fill_gaps`.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    key = _cache_key(source_path, reference_path, source_id, crosswalk)
    key_path = output_path.parent / f".{output_path.stem}_cache_key.json"
    if output_path.exists() and key_path.exists():
        try:
            if json.loads(key_path.read_text()) == key:
                logger.info("FBFM40 cache hit at %s — skipping", output_path)
                return output_path
        except (OSError, ValueError):
            pass

    with rasterio.open(reference_path) as ref:
        dst_transform, dst_crs = ref.transform, ref.crs
        dst_shape = (ref.height, ref.width)
        profile = ref.meta.copy()

    with rasterio.open(source_path) as src:
        raw = np.empty(dst_shape, dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=raw,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.mode,
        )

    classes = np.round(raw).astype(np.int32)
    fbfm40 = np.zeros(dst_shape, dtype=np.int16)
    for cover_class, fuel_model in crosswalk.items():
        fbfm40[classes == cover_class] = fuel_model
    fbfm40 = _fill_gaps(fbfm40, fbfm40 == 0, fill_path)

    assert_codes_are_defined(fbfm40)
    profile.update(dtype="int16", count=1, nodata=_NODATA_FBFM40)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(fbfm40, 1)
    key_path.write_text(json.dumps(key, sort_keys=True))
    _log_distribution(output_path, fbfm40)
    return output_path


def ccsbap_to_fbfm40(
    shapefile_path: Path,
    reference_path: Path,
    output_path: Path,
    fill_path: Path | None = None,
    subpixel: int = 3,
) -> Path:
    """Rasterize the CCS-BAP vector cover to FBFM40 on the reference grid.

    CCS-BAP is vector (1 ha minimum mapping unit) while the grid is 30 m, so "majority
    class" has to be built rather than resampled: the layer is burned at `subpixel`×
    finer resolution (10 m by default, 9 sub-cells per output pixel) and each output pixel
    takes the class covering most of its sub-cells. Same aggregation rule as every other
    source (ETAPA-A §A5), so the comparison is not measuring resampling differences.

    Reprojection happens before rasterizing: polygon areas are computed on the projected
    grid, never in degrees.
    """
    import geopandas as gpd
    from rasterio.features import rasterize

    output_path.parent.mkdir(parents=True, exist_ok=True)
    key = _cache_key(
        shapefile_path, reference_path, CCSBAP_SOURCE_ID,
        {f"{a}|{b}": v for (a, b), v in CCSBAP_TO_FBFM40.items()} | CCSBAP_N3_OVERRIDES
        | {f"{k}>={h}": v for k, (h, v) in CCSBAP_SOBRE_LIMITE_BOSQUE.items()},
    )
    key_path = output_path.parent / f".{output_path.stem}_cache_key.json"
    if output_path.exists() and key_path.exists():
        try:
            if json.loads(key_path.read_text()) == key:
                logger.info("FBFM40 cache hit at %s — skipping", output_path)
                return output_path
        except (OSError, ValueError):
            pass

    with rasterio.open(reference_path) as ref:
        dst_crs, dst_transform = ref.crs, ref.transform
        height, width, bounds = ref.height, ref.width, ref.bounds
        profile = ref.meta.copy()

    gdf = gpd.read_file(shapefile_path, bbox=gpd.GeoSeries([_box(bounds)], crs=dst_crs))
    if gdf.empty:
        raise ValueError(f"{shapefile_path.name} has no polygons over the reference grid")
    gdf = gdf.to_crs(dst_crs)
    gdf["fuel"] = [
        ccsbap_fuel_code(a, b, c)
        for a, b, c in zip(gdf["Ley_N1"], gdf["Ley_N2"], gdf["Ley_N3"])
    ]
    # Las clases con cambio por altura se queman con un código propio (negativo, fuera de la
    # tabla) y se resuelven después de la moda, con la altura de cada celda.
    altura_clases = {n3: -(i + 1) for i, n3 in enumerate(CCSBAP_SOBRE_LIMITE_BOSQUE)}
    gdf.loc[gdf["Ley_N3"].isin(altura_clases), "fuel"] = gdf["Ley_N3"].map(altura_clases)

    fine_transform = dst_transform * rasterio.Affine.scale(1 / subpixel, 1 / subpixel)
    fine = rasterize(
        ((geom, code) for geom, code in zip(gdf.geometry, gdf["fuel"])),
        out_shape=(height * subpixel, width * subpixel),
        transform=fine_transform,
        fill=0,
        dtype="int16",
        all_touched=False,
    )

    blocks = fine.reshape(height, subpixel, width, subpixel)
    fbfm40 = np.zeros((height, width), dtype=np.int16)
    best = np.zeros((height, width), dtype=np.int8)
    for code in np.unique(fine):
        if code == 0:
            continue
        count = (blocks == code).sum(axis=(1, 3)).astype(np.int8)
        wins = count > best
        best[wins], fbfm40[wins] = count[wins], code

    if altura_clases:
        with rasterio.open(reference_path) as ref:
            altura = ref.read(1)
        for n3, provisorio in altura_clases.items():
            umbral, sobre = CCSBAP_SOBRE_LIMITE_BOSQUE[n3]
            clase = fbfm40 == provisorio
            debajo = next(ccsbap_fuel_code(a, b, c) for a, b, c in
                          zip(gdf["Ley_N1"], gdf["Ley_N2"], gdf["Ley_N3"]) if c == n3)
            fbfm40[clase] = np.where(altura[clase] >= umbral, sobre, debajo)

    fbfm40 = _fill_gaps(fbfm40, fbfm40 == 0, fill_path)
    assert_codes_are_defined(fbfm40)
    profile.update(dtype="int16", count=1, nodata=_NODATA_FBFM40)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(fbfm40, 1)
    key_path.write_text(json.dumps(key, sort_keys=True))
    _log_distribution(output_path, fbfm40)
    return output_path


def _box(bounds) -> "object":
    from shapely.geometry import box
    return box(*bounds)


def _log_distribution(output_path: Path, fbfm40: "np.ndarray") -> None:
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


# ---------------------------------------------------------------------------
# Selección de fuente (ETAPA-B §B3)
# ---------------------------------------------------------------------------
SOURCE_LABELS: dict[str, str] = {
    "worldcover": "ESA WorldCover v200 (2021)",
    "mapbiomas": "MapBiomas Argentina Colección 2 (2024)",
    "ccsbap": "CCS-BAP · CIEFAP/MAyDS (2017)",
}

MAPBIOMAS_LABELS: dict[int, str] = {
    3: "Bosques cerrados", 4: "Bosques abiertos", 6: "Bosques inundables",
    66: "Arbustales cerrados", 77: "Arbustales abiertos",
    63: "Mosaicos de arbustos y herbáceas", 12: "Herbáceas",
    11: "Herbáceas inundables (mallines)", 73: "Turberas", 9: "Silvicultura",
    15: "Pasturas", 18: "Agricultura", 19: "Cultivos temporarios",
    36: "Cultivos perennes", 21: "Mosaico de usos", 24: "Áreas urbanas",
    25: "Otras áreas no vegetadas", 33: "Ríos, lagunas y lagos",
    34: "Hielo y nieve permanente",
}

CCSBAP_LABELS: dict[tuple[str, str], str] = {
    ("TF", "Le"): "Bosque de lenga", ("TF", "Ñi"): "Bosque de ñire",
    ("TF", "Co"): "Bosque de coihue", ("TF", "Ci"): "Bosque de ciprés",
    ("TF", "Al"): "Bosque de alerce", ("TF", "Mx"): "Bosque mixto",
    ("TF", "Ma"): "Bosque de maitén", ("TF", "Rd"): "Bosque de radal",
    ("TF", "Mr"): "Bosque de mirtáceas", ("TF", "Cg"): "Bosque de ciprés de las guaitecas",
    ("OFL", "Le"): "Lenga achaparrada", ("OFL", "Ñi"): "Ñire bajo",
    ("OFL", "Arbu Na"): "Arbustal nativo", ("OFL", "MMx"): "Matorral mixto",
    ("OFL", "Ci"): "Ciprés abierto o juvenil", ("OFL", "Co"): "Coihue juvenil",
    ("OFL", "Ch"): "Chacay", ("OFL", "Rd"): "Radal juvenil",
    ("OFL", "Mr"): "Mirtáceas bajas", ("OFL", "Ma"): "Maitén bajo",
    ("OFL", "Cg"): "Ciprés de las guaitecas juvenil",
    ("OT", "Herb-Subarb"): "Estepa y herbáceas", ("OT", "Erial"): "Erial",
    ("OT", "Humedales"): "Humedales", ("OT", "Agua"): "Agua",
    ("OT", "Hie-Nie"): "Hielo y nieve", ("OT", "Exot-Artif"): "Exóticas y artificial",
    ("OT", "Rem Dist Rec"): "Remanente de disturbio reciente",
}

CCSBAP_N3_LABELS: dict[str, str] = {
    "Turbera": "Turbera", "Cg Juv-Tur": "Guaitecas sobre turbera",
    "Caña": "Caña colihue", "Estepa Arb": "Estepa arbustiva", "Pradera": "Pradera",
    "Forest": "Forestación exótica", "Arles Ex": "Arboledas exóticas",
    "Arbu Ex": "Arbustal exótico", "Pastura": "Pastura implantada",
    "Infraest": "Infraestructura",
}


def build_fbfm40(
    source: str,
    source_path: Path,
    reference_path: Path,
    output_path: Path,
    fill_path: Path | None = None,
) -> Path:
    """Build fbfm40.tif from whichever cover source is configured.

    One entry point per source instead of a hardwired call, so the thesis can regenerate
    any of the three maps without editing code (ETAPA-B §B3). The source identity is part
    of the cache key, so switching sources regenerates rather than serving the old raster.
    """
    if source == "ccsbap":
        return ccsbap_to_fbfm40(source_path, reference_path, output_path, fill_path)
    if source == "mapbiomas":
        return raster_to_fbfm40(
            source_path, reference_path, output_path,
            MAPBIOMAS_TO_FBFM40, MAPBIOMAS_SOURCE_ID, fill_path,
        )
    if source == "worldcover":
        return raster_to_fbfm40(
            source_path, reference_path, output_path,
            WORLDCOVER_TO_FBFM40, WORLDCOVER_SOURCE_ID, fill_path,
        )
    raise ValueError(
        f"Unknown fuels source {source!r}; expected one of {sorted(SOURCE_LABELS)}"
    )


def source_classes_by_fuel_model(source: str) -> dict[int, list[str]]:
    """Which cover classes feed each fuel model, for the map legend.

    Lives next to the crosswalks so the dashboard can never claim a provenance the
    raster does not have.
    """
    out: dict[int, list[str]] = {}
    if source == "ccsbap":
        pairs = [(CCSBAP_LABELS.get(k, f"{k[0]} {k[1]}"), v) for k, v in CCSBAP_TO_FBFM40.items()]
        pairs += [(CCSBAP_N3_LABELS.get(k, k), v) for k, v in CCSBAP_N3_OVERRIDES.items()]
    elif source == "mapbiomas":
        pairs = [(MAPBIOMAS_LABELS.get(k, str(k)), v) for k, v in MAPBIOMAS_TO_FBFM40.items()]
    elif source == "worldcover":
        pairs = [(WORLDCOVER_LABELS.get(k, str(k)), v) for k, v in WORLDCOVER_TO_FBFM40.items()]
    else:
        raise ValueError(f"Unknown fuels source {source!r}")

    for label, code in pairs:
        out.setdefault(code, [])
        if label not in out[code]:
            out[code].append(label)
    return out
