# ELMFIRE namelist (`elmfire.data`) reference

ELMFIRE reads a Fortran namelist file, passed as its argument (the runner calls
`mpirun -n 1 elmfire_2025.0212 elmfire.data`).
This reference has two parts: what this repo actually writes today (code-verified),
and what exists in the vendor ELMFIRE 2025.0212 docs but isn't used here yet.

## What this repo emits today

Source of truth: `app/elmfire/builder/namelist_writer.py:write_namelist()`. Read that
function directly before changing any of this — the table below is a transcription,
not a substitute.

| Group | Keyword | Notes |
|---|---|---|
| `&INPUTS` | `FUELS_AND_TOPOGRAPHY_DIRECTORY`, `WEATHER_DIRECTORY` | Same directory in this repo (`inputs_dir`) |
| `&INPUTS` | `DEM_FILENAME`, `SLP_FILENAME`, `ASP_FILENAME`, `FBFM_FILENAME`, `CC_FILENAME`, `CH_FILENAME`, `CBH_FILENAME`, `CBD_FILENAME`, `WS_FILENAME`, `WD_FILENAME`, `M1_FILENAME`, `M10_FILENAME`, `M100_FILENAME`, `ADJ_FILENAME`, `PHI_FILENAME` | Values are **extensionless basenames** (`'dem'`, not `'dem.tif'`) — the actual files on disk are `.tif`, ELMFIRE appends the extension itself. This matches the vendor tutorials' convention (`FLOAT_RASTER[1]=ws`). |
| `&INPUTS` | `DT_METEOROLOGY` | Seconds between weather raster bands (`dt_meteorology_s`, default `3600.0`, i.e. hourly); `validate_weather_coverage()` checks the rasters have enough bands for `TSTOP` |
| `&INPUTS` | `LH_MOISTURE_CONTENT`, `LW_MOISTURE_CONTENT` | Live herbaceous / woody moisture, percent, one scalar for the whole domain (`DEFAULT_LH_MOISTURE_PCT`, `DEFAULT_LW_MOISTURE_PCT`; ELMFIRE's own default is 60 for both) |
| `&COMPUTATIONAL_DOMAIN` | `A_SRS`, `COMPUTATIONAL_DOMAIN_XLLCORNER`, `COMPUTATIONAL_DOMAIN_YLLCORNER`, `COMPUTATIONAL_DOMAIN_CELLSIZE` | Corner/cellsize are read from `dem.tif` bounds via `_read_domain()` — only lower-left corner + cellsize, **no** upper-right corner keywords (ELMFIRE derives extent from the raster itself) |
| `&OUTPUTS` | `DTDUMP`, `OUTPUTS_DIRECTORY`, `CONVERT_TO_GEOTIFF`, `DUMP_TIME_OF_ARRIVAL`, `DUMP_FLIN`, `DUMP_SPREAD_RATE` | `DTDUMP` is clamped by `resolve_dtdump_s()` to `tstop_s / 2` if the caller-supplied value would be `>= tstop_s` — see gotcha below |
| `&TIME_CONTROL` | `SIMULATION_TSTART`, `SIMULATION_DT`, `SIMULATION_DTMAX`, `SIMULATION_TSTOP` | `SIMULATION_TSTOP = TSTART + simulation_hours * 3600`. Time is **absolute**: at time T ELMFIRE interpolates bands `floor(T / DT_METEOROLOGY)` and the next (0-based), so band n is the weather at `n × DT_METEOROLOGY` and band 0 is T = 0, not TSTART |
| `&SIMULATOR` | `MODE`, `CROWN_FIRE_MODEL`, `PHIS_ADJ` | `MODE` must be `1` (transient spread; `_validate_parameters()` rejects anything else). `CROWN_FIRE_MODEL`: `0` = off, any value `> 0` = on (only one crown model is implemented); ELMFIRE turns it **on** when the keyword is omitted, so it is written explicitly (`DEFAULT_CROWN_FIRE_MODEL = 1`). `PHIS_ADJ` multiplies the slope contribution and is written only when it differs from its `1.0` default |
| `&MONTE_CARLO` | `NUM_METEOROLOGY_TIMES` | Number of weather bands (`weather_band_count()`, the band count of `ws.tif`). **Required for transient weather**: the default is 1, and with 1 ELMFIRE holds band 0 for the whole run (see `interface-gotchas.md`) |
| `&MISCELLANEOUS` | `PATH_TO_GDAL`, `SCRATCH`, `MISCELLANEOUS_INPUTS_DIRECTORY`, `FUEL_MODEL_FILE` | Keyword is `SCRATCH`, not `SCRATCH_PATH`. `FUEL_MODEL_FILE = 'fuel_models.csv'` and `MISCELLANEOUS_INPUTS_DIRECTORY` are always written together — one without the other makes ELMFIRE look for `null/fuel_models.csv` and abort |

Raster basename vocabulary this repo produces (see `references/interface-gotchas.md`
for units): `dem, slp, asp, fbfm40, cc, ch, cbh, cbd, ws, wd, m1, m10, m100, adj, phi`.

Ignition is handled via `phi.tif` (a signed-distance field written by
`ignition_builder.py`), **not** via `&SIMULATOR` `X_IGN`/`Y_IGN`/`T_IGN` point
ignitions — this repo doesn't use point-source ignition namelist parameters at all
(no `NUM_IGNITIONS`/`X_IGN`/`T_IGN` reference anywhere in `app/`).

## Not used by this repo yet (from vendor tutorials — 2025.0212)

These are real ELMFIRE namelist keywords seen in the official tutorial PDFs, kept
here for when the pipeline grows (e.g. multi-ignition, fire-potential mode). Verify
against upstream source before relying on exact spelling — the tutorials themselves
weren't fully self-consistent (see flag below).

| Group | Keyword | Meaning |
|---|---|---|
| `&SIMULATOR` | `MODE=2` | Landscape-scale fire-potential ("head fire" mode, every pixel burned independently, FlamMap-style); this repo only emits `MODE=1` |
| `&SIMULATOR` | `NUM_IGNITIONS`, `X_IGN(n)`, `Y_IGN(n)`, `T_IGN(n)` | Point ignitions; coordinates are in the raster's projected CRS (UTM meters), not lat/lon; `T_IGN` in seconds |
| `&MONTE_CARLO` | `METEOROLOGY_BAND_START`, `METEOROLOGY_BAND_STOP`, `METEOROLOGY_BAND_SKIP_INTERVAL` | Sweep over weather raster bands, one calc per band (used with `MODE=2`) |
| `&MONTE_CARLO` | ~~`NUM_METEOROLOGY_BANDS`~~ | Resolved against the source (`elmfire_namelists.f90`, `READ_MONTE_CARLO`): the keyword is `NUM_METEOROLOGY_TIMES` (now written by this repo, above); `NUM_METEOROLOGY_BANDS` does not exist. |

`&TIME_CONTROL` is referenced by the vendor docs (as containing timestep/CFL/stop-time
settings) but its full keyword list beyond what's already used in `namelist_writer.py`
was never actually shown in any of the docs we have — treat anything beyond
`SIMULATION_TSTART`/`SIMULATION_DT`/`SIMULATION_DTMAX`/`SIMULATION_TSTOP` as unverified.

Note: MODE=2 namelists drop the `&TIME_CONTROL` group entirely (not applicable to
fire-potential mode) — if this repo ever adds MODE=2 support, `write_namelist()` will
need a real branch for it, not just extra keywords.
