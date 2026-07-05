# ELMFIRE namelist (`elmfire.data`) reference

ELMFIRE reads a Fortran namelist file (invoked as `elmfire_2025.0212 < elmfire.data`).
This reference has two parts: what this repo actually writes today (code-verified),
and what exists in the vendor ELMFIRE 2025.0212 docs but isn't used here yet.

## What this repo emits today

Source of truth: `app/elmfire/builder/namelist_writer.py:write_namelist()`. Read that
function directly before changing any of this — the table below is a transcription,
not a substitute.

| Group | Keyword | Notes |
|---|---|---|
| `&INPUTS` | `FUELS_AND_TOPOGRAPHY_DIRECTORY`, `WEATHER_DIRECTORY` | Same directory in this repo (`inputs_dir`) |
| `&INPUTS` | `DEM_FILENAME`, `SLP_FILENAME`, `ASP_FILENAME`, `FBFM_FILENAME`, `CC_FILENAME`, `CH_FILENAME`, `CBH_FILENAME`, `CBD_FILENAME`, `WS_FILENAME`, `WD_FILENAME`, `M1_FILENAME`, `M10_FILENAME`, `M100_FILENAME`, `ADJ_FILENAME`, `PHI_FILENAME` | Values are **extensionless basenames** (`'dem'`, not `'dem.tif'`) — the actual files on disk are `.tif`, ELMFIRE appends the extension itself. This matches the vendor tutorials' convention (`FLOAT_RASTER[1]=ws`), not the `.tif`-suffixed style previously (incorrectly) shown in `docs/elmfire-mapping.md`. |
| `&INPUTS` | `DT_METEOROLOGY` | Seconds between weather raster bands (currently hardcoded `3600.0`, i.e. hourly) |
| `&COMPUTATIONAL_DOMAIN` | `A_SRS`, `COMPUTATIONAL_DOMAIN_XLLCORNER`, `COMPUTATIONAL_DOMAIN_YLLCORNER`, `COMPUTATIONAL_DOMAIN_CELLSIZE` | Corner/cellsize are read from `dem.tif` bounds via `_read_domain()` — only lower-left corner + cellsize, **no** upper-right corner keywords (ELMFIRE derives extent from the raster itself) |
| `&OUTPUTS` | `DTDUMP`, `OUTPUTS_DIRECTORY`, `CONVERT_TO_GEOTIFF`, `DUMP_TIME_OF_ARRIVAL`, `DUMP_FLIN`, `DUMP_SPREAD_RATE` | `DTDUMP` is clamped by `resolve_dtdump_s()` to `tstop_s / 2` if the caller-supplied value would be `>= tstop_s` — see gotcha below |
| `&TIME_CONTROL` | `SIMULATION_DT`, `SIMULATION_DTMAX`, `SIMULATION_TSTOP` | `SIMULATION_TSTOP = simulation_hours * 3600` |
| `&MISCELLANEOUS` | `PATH_TO_GDAL`, `SCRATCH` | Keyword is `SCRATCH`, not `SCRATCH_PATH` |

Raster basename vocabulary this repo produces (see `references/interface-gotchas.md`
for units): `dem, slp, asp, fbfm40, cc, ch, cbh, cbd, ws, wd, m1, m10, m100, adj, phi`.

Ignition is handled via `phi.tif` (a signed-distance field written by
`ignition_builder.py`), **not** via `&SIMULATOR` `X_IGN`/`Y_IGN`/`T_IGN` point
ignitions — this repo doesn't use point-source ignition namelist parameters at all
today (confirmed: no `NUM_IGNITIONS`/`X_IGN`/`MODE` reference anywhere in `app/`).

## Not used by this repo yet (from vendor tutorials — 2025.0212)

These are real ELMFIRE namelist keywords seen in the official tutorial PDFs, kept
here for when the pipeline grows (e.g. multi-ignition, fire-potential mode). Verify
against upstream source before relying on exact spelling — the tutorials themselves
weren't fully self-consistent (see flag below).

| Group | Keyword | Meaning |
|---|---|---|
| `&SIMULATOR` | `MODE` | `1` = transient point-ignition fire spread (default); `2` = landscape-scale fire-potential ("head fire" mode, every pixel burned independently, FlamMap-style) |
| `&SIMULATOR` | `NUM_IGNITIONS`, `X_IGN(n)`, `Y_IGN(n)`, `T_IGN(n)` | Point ignitions; coordinates are in the raster's projected CRS (UTM meters), not lat/lon; `T_IGN` in seconds |
| `&SIMULATOR` | `CROWN_FIRE_MODEL` | `0` = off, any value `> 0` = on (only one crown fire model implemented — effectively boolean). **On by default** in ELMFIRE if omitted. |
| `&MONTE_CARLO` | `METEOROLOGY_BAND_START`, `METEOROLOGY_BAND_STOP`, `METEOROLOGY_BAND_SKIP_INTERVAL` | Sweep over weather raster bands, one calc per band (used with `MODE=2`) |
| `&MONTE_CARLO` | ⚠️ `NUM_METEOROLOGY_TIMES` vs `NUM_METEOROLOGY_BANDS` | **Unresolved discrepancy in the vendor docs themselves**: Tutorial 02 prose refers to `NUM_METEOROLOGY_BANDS`, but the namelist code snippet in the same tutorial uses `NUM_METEOROLOGY_TIMES`. Do not pick one without checking upstream ELMFIRE source first. |

`&TIME_CONTROL` is referenced by the vendor docs (as containing timestep/CFL/stop-time
settings) but its full keyword list beyond what's already used in `namelist_writer.py`
was never actually shown in any of the docs we have — treat anything beyond
`SIMULATION_DT`/`SIMULATION_DTMAX`/`SIMULATION_TSTOP` as unverified.

Note: MODE=2 namelists drop the `&TIME_CONTROL` group entirely (not applicable to
fire-potential mode) — if this repo ever adds MODE=2 support, `write_namelist()` will
need a real branch for it, not just extra keywords.
