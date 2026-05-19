FROM python:3.12-slim

# GDAL must be installed before rasterio
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libeccodes-dev \
    && rm -rf /var/lib/apt/lists/*

# GDAL already installed as system package; no need for wheel

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml .
RUN uv sync --no-dev

COPY . .

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
