# IgniteInsights

Wildfire spread prediction system for Parque Nacional Los Alerces (Patagonia,
Argentina). A FastAPI backend ingests satellite fire detections (FIRMS), weather
(NOAA GFS), topography (Copernicus DEM), and fuel cover (CCS-BAP by default, with
MapBiomas and ESA WorldCover as comparison maps; `settings.fuels_source` picks one), derives
input rasters and a namelist from them, and hands them to **ELMFIRE 2025.0212** — a
fire-spread model that runs as a separate microservice, not in this repo — via
`app/elmfire/runner/client.py`. Results (hourly isochrones, time-of-arrival,
fireline intensity) are served as GeoJSON and shown on a Next.js dashboard. See
`docs/arquitectura.md` for the full pipeline and `docs/elmfire.md` for the
source-data → ELMFIRE-input mapping.

## Commands

- `make check` — full CI-equivalent suite: ruff, mypy, pytest, TypeScript, eslint and
  Playwright. It requires Docker because the end-to-end suite uses PostGIS.
- `make test-unit` — backend unit tests only.
- `make test-e2e` — starts PostGIS, applies migrations and runs the browser suite against
  the stub API.
- `uv run pytest tests/test_namelist_writer.py -k dtdump` — one file / one test.
- `make dev` — PostGIS + API in Docker, Next.js on the host. `make dev-simulation` adds the
  ELMFIRE runner, which docker-compose builds from the sibling repo `../elmfire-runner`;
  without it, anything that actually runs ELMFIRE (`scripts/benchmark.py correr`, real
  simulations) cannot work.
- `npm run typecheck` and `npm run lint` from `frontend/` need no backend. Playwright owns
  the stub API and Next.js processes, but authentication still requires a migrated Postgres;
  use `make test-e2e` from the repository root (details in `frontend/e2e/README.md`).

Documentation and the newer thesis code (`app/validation/`, `scripts/benchmark.py`) are in
Spanish; older application modules may be in English. Match the file or module you are editing.

## Where the project state lives

Read these before assuming something is missing. `docs/resultados/modelo/estado.md` is the
single current status; `docs/resultados/modelo/modelo.md` defines the promoted model;
`docs/resultados/modelo/validacion.md` is the validation method and benchmark;
`docs/resultados/modelo/limites.md` contains the declared limitations; and active
crosswalk material is in `docs/crosswalk.md`. Experimental notes and generated tables live under
`benchmarks/diagnosticos/`, not under `docs/`.

Benchmark vocabulary is strict: a **recipe** configures experimental iterations, an
**iteration** is recipe × case, and a **model** under `benchmarks/modelos/` is an immutable
recipe/case/results snapshot that passed the production gate. Do not call every recipe a model.

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

`docs/elmfire.md` previously drifted out of sync with the real namelist
code — if you ever find another doc disagreeing with `namelist_writer.py`, trust the
code and fix the doc.
