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

## Run with Docker (recommended)

```bash
docker compose up
# API: http://localhost:8000
# DB: localhost:5432
```

```bash
# Run migrations (first time)
uv run alembic upgrade head
```

## Run locally (without Docker DB)

```bash
# Start only PostGIS
docker compose up db -d

# Run API
uv run uvicorn app.main:app --reload
```

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

# Test FIRMS endpoint
curl -X POST http://localhost:8000/api/v1/ingestion/firms/run

# Test DEM endpoint
curl -X POST http://localhost:8000/api/v1/ingestion/dem/run

# Get active fires
curl http://localhost:8000/api/v1/fires/active
```

## Troubleshooting

**`asyncpg.exceptions.InvalidCatalogNameError`** — PostGIS container not ready yet. Wait a few seconds and retry.

**`rasterio._err.CPLE_OpenFailedError`** — GDAL not installed or version mismatch. See GDAL installation above.

**FIRMS returns empty CSV** — No active fires in Los Alerces today. Use `?day_range=7` to extend the window, or test with a broader bbox like `-75,-56,-62,-38` (Patagonia).

**`geoalchemy2` import error** — PostGIS extension not enabled. Run `alembic upgrade head` which issues `CREATE EXTENSION IF NOT EXISTS postgis`.
