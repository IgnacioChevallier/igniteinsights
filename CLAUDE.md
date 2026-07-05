# IgniteInsights

Wildfire spread prediction system for Parque Nacional Los Alerces (Patagonia,
Argentina). A FastAPI backend ingests satellite fire detections (FIRMS), weather
(NOAA GFS), topography (Copernicus DEM), and fuel cover (ESA WorldCover), derives
input rasters and a namelist from them, and hands them to **ELMFIRE 2025.0212** — a
fire-spread model that runs as a separate microservice, not in this repo — via
`app/elmfire/runner/client.py`. Results (hourly isochrones, time-of-arrival,
fireline intensity) are served as GeoJSON and shown on a Next.js dashboard. See
`docs/architecture.md` for the full pipeline and `docs/elmfire-mapping.md` for the
source-data → ELMFIRE-input mapping.

## Working with ELMFIRE inputs

`app/elmfire/builder/*.py` (especially `namelist_writer.py`) generates ELMFIRE's
raster inputs and `elmfire.data` namelist — this is a strict external interface, not
internal application code. **Do not invent, rename, or guess ELMFIRE namelist
keywords, raster filenames, or unit scalings.** Before touching anything under
`app/elmfire/`:

1. Read the current code (`namelist_writer.py`, the relevant `builder/*.py`) — it is
   the ground truth for what this repo emits today.
2. Check the `elmfire` skill (`.claude/skills/elmfire/`) for known conventions and
   gotchas (e.g. Int16 canopy rasters use LANDFIRE's ×10/×100 unit scaling; raster
   filenames are extensionless basenames in the namelist).
3. For anything not covered by the above, check upstream ELMFIRE source
   (`github.com/lautenberger/elmfire`, pinned branch `2025.0212`) rather than
   guessing.

`docs/elmfire-mapping.md` previously drifted out of sync with the real namelist
code — if you ever find another doc disagreeing with `namelist_writer.py`, trust the
code and fix the doc.
