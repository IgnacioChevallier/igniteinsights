# IgniteInsights

Wildfire spread prediction system for Parque Nacional Los Alerces (Patagonia,
Argentina). A FastAPI backend ingests satellite fire detections (FIRMS), weather
(NOAA GFS), topography (Copernicus DEM), and fuel cover (ESA WorldCover today;
CCS-BAP and MapBiomas crosswalks exist and are not wired into the pipeline yet), derives
input rasters and a namelist from them, and hands them to **ELMFIRE 2025.0212** — a
fire-spread model that runs as a separate microservice, not in this repo — via
`app/elmfire/runner/client.py`. Results (hourly isochrones, time-of-arrival,
fireline intensity) are served as GeoJSON and shown on a Next.js dashboard. See
`docs/architecture.md` for the full pipeline and `docs/elmfire-mapping.md` for the
source-data → ELMFIRE-input mapping.

## Commands

- `make check` — ruff, mypy, pytest, `tsc` and eslint; exactly what CI runs (~20s). Run it
  before calling a change done.
- `uv run pytest tests/test_namelist_writer.py -k dtdump` — one file / one test.
- `make dev` — PostGIS + API in Docker, Next.js on the host. `make dev-simulation` adds the
  ELMFIRE runner, which docker-compose builds from the sibling repo `../elmfire-runner`;
  without it, anything that actually runs ELMFIRE (`scripts/benchmark.py correr`, real
  simulations) cannot work.
- Frontend checks need no backend: `node e2e/stub-api.mjs &`, `npm run dev &`,
  `npx playwright test` from `frontend/` (details in `frontend/e2e/README.md`).

Language: planning docs (`ESTADO.md`, `IGN-*.md`) and the newer thesis code (`app/validation/`,
`scripts/benchmark.py`) are in Spanish; the rest of `app/`, `docs/` and the frontend are in
English. Match the file or module you are editing.

## Where the project state lives

**`ESTADO.md` is the entry point**: it says what is done, what is pending and where each plan
lives. Read it before assuming something is missing. Live plans sit in the root
(`ETAPA-*.md`, `IGN-*.md`, `PENDING_PARAMETERS.md`); finished or superseded documents are in
`docs/historico/`, and converted source material in `docs/referencias/`. The fuel-model
crosswalk the thesis argues for is `IGN-20B-CROSSWALK-CCSBAP.md`.

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
