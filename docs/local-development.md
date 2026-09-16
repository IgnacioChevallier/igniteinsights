# Local Development

## Prerequisites

- Docker Desktop (for PostGIS)
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- GDAL (for rasterio)

## GDAL installation

**macOS (Homebrew):**
```bash
brew install gdal
pip install GDAL=="$(gdal-config --version)"
```

**Ubuntu/Debian:**
```bash
sudo apt-get install gdal-bin libgdal-dev
pip install GDAL=="$(gdal-config --version)"
```

## API keys

| Key | Where to get it |
|-----|----------------|
| `FIRMS_MAP_KEY` | firms.modaps.eosdis.nasa.gov/api/map_key/ — instant, free |
| `OPENTOPOGRAPHY_API_KEY` | portal.opentopography.org — free registration |

## Setup

```bash
git clone <repo>
cd igniteinsights
cp .env.example .env
# Edit .env and fill in FIRMS_MAP_KEY and OPENTOPOGRAPHY_API_KEY

uv sync
```

## Run the complete image-based stack

```bash
docker compose build  # first run, or after dependency/Dockerfile changes
docker compose up     # subsequent starts do not rebuild
# API: http://localhost:8000
# DB: localhost:5432
# Dashboard: http://localhost:3000
```

```bash
# Run migrations (first time)
docker compose exec api uv run alembic upgrade head
```

## Development with hot reload (recommended on macOS)

FastAPI and PostGIS run in Docker while Next.js runs on the host. Python files
under `app/` and frontend source files reload without rebuilding an image.

```bash
cp frontend/.env.local.example frontend/.env.local
npm --prefix frontend install
make dev
```

The regular development command intentionally omits ELMFIRE. Start it only when
working on simulations:

```bash
make dev-simulation
```

For an entirely containerized development environment with frontend hot reload:

```bash
make dev-docker
# Or include ELMFIRE:
make dev-docker-simulation
```

The Docker development override stores Linux `node_modules` and `.next` output
in Docker volumes while bind-mounting frontend source code.

## Run the API locally

```bash
# Start only PostGIS
docker compose up db -d

# Run migrations
uv run alembic upgrade head

# Run API
uv run uvicorn app.main:app --reload
```

## When to rebuild or restart

| Change | Action |
| --- | --- |
| `app/**/*.py` | None in development; Uvicorn reloads |
| Frontend source | None in development; Next.js reloads |
| `pyproject.toml` or `uv.lock` | `docker compose build api && docker compose up -d --no-deps api` |
| `frontend/package*.json` | Run `npm install` for host development, or rebuild only the Docker frontend |
| API/frontend Dockerfile | Rebuild and recreate only that service |
| ELMFIRE source/Dockerfile | Rebuild and recreate only `elmfire-runner` |
| Database migration | Run Alembic; no image rebuild |

Avoid `docker compose up --build` as a daily command because it checks all three
locally built services. Plain `docker compose up -d` reuses existing images.

## Common commands

```bash
# Lint
uv run ruff check app/

# Type check
uv run mypy app/ --ignore-missing-imports

# New migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Full ingestion run (FIRMS + GFS) + automatic preparation of ELMFIRE inputs
curl -X POST http://localhost:8000/api/v1/ingestion/run \
  -H "Content-Type: application/json" \
  -d '{"include_firms": true, "include_gfs": true}'
# Response includes preparation.inputs_dir — use it for /simulations/run

# First-time setup: download static data (DEM + WorldCover)
curl -X POST http://localhost:8000/api/v1/ingestion/run \
  -H "Content-Type: application/json" \
  -d '{"include_dem": true, "include_worldcover": true, "include_firms": true, "include_gfs": true}'

# Run a simulation (use inputs_dir from ingestion response)
curl -X POST http://localhost:8000/api/v1/simulations/run \
  -H "Content-Type: application/json" \
  -d '{"inputs_dir": "/app/data/elmfire/inputs/{prep_id}", "horizon_hours": 12}'

# Poll simulation status
curl http://localhost:8000/api/v1/simulations/{simulation_id}

# Get active fires
curl http://localhost:8000/api/v1/fires/active

# Individual source endpoints (for debugging)
curl -X POST http://localhost:8000/api/v1/ingestion/firms/run
curl -X POST http://localhost:8000/api/v1/ingestion/gfs/run
curl -X POST http://localhost:8000/api/v1/ingestion/dem/run
curl -X POST http://localhost:8000/api/v1/ingestion/worldcover/run
curl -X POST http://localhost:8000/api/v1/ingestion/canopy/run

# First-time setup: download all static data including canopy (downloads ~500 MB Hansen + ETH tiles)
curl -X POST http://localhost:8000/api/v1/ingestion/run \
  -H "Content-Type: application/json" \
  -d '{"include_dem": true, "include_worldcover": true, "include_canopy": true, "include_firms": true, "include_gfs": true}'
```

## Troubleshooting

**`asyncpg.exceptions.InvalidCatalogNameError`** — PostGIS container not ready yet. Wait a few seconds and retry.

**`rasterio._err.CPLE_OpenFailedError`** — GDAL not installed or version mismatch. See GDAL installation above.

**FIRMS returns empty CSV** — No active fires in Los Alerces today. Use `?day_range=7` to extend the window, or test with a broader bbox like `-75,-56,-62,-38` (Patagonia).

**`geoalchemy2` import error** — PostGIS extension not enabled. Run `alembic upgrade head` which issues `CREATE EXTENSION IF NOT EXISTS postgis`.
