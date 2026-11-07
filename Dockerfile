# syntax=docker/dockerfile:1.7

FROM python:3.12-slim

# Rasterio, Pyogrio, and ecCodes are locked binary wheels that bundle their core
# geospatial libraries. Rasterio still links to Expat from the OS. Command-line
# GDAL belongs to the separate ELMFIRE runner.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.12 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,id=s/0599a1bb-6b61-4686-bc5e-a71e5e248ce7-/root/.cache/uv,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
# Todo scripts/: los que corren por `railway ssh` (podar_volumen, ensamble_*) llegan sin otra
# línea acá; un script nuevo sólo necesita estar en los watchPatterns de la api para desplegar.
COPY scripts/ ./scripts/
# Casos, recetas y resultados del benchmark de validación: los lee /api/v1/validation.
COPY benchmarks/ ./benchmarks/

RUN mkdir -p /app/data

CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
