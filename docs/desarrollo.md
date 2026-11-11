# Desarrollo local

## Requisitos

- Docker Desktop, para PostGIS y servicios en contenedores.
- Python 3.12 y `uv`.
- Node.js y npm.
- GDAL, requerido por Rasterio.

## Configuración

```bash
cp .env.example .env
```

Variables principales:

| Variable | Uso |
|---|---|
| `FIRMS_MAP_KEY` | detecciones NASA FIRMS |
| `OPENTOPOGRAPHY_API_KEY` | descarga del DEM |
| `DATABASE_URL` | PostgreSQL/PostGIS |
| `ELMFIRE_RUNNER_URL` | ejecutor ELMFIRE opcional |

## Entorno completo con Docker

```bash
docker compose build
docker compose up -d db api frontend
docker compose exec api uv run alembic upgrade head
```

La interfaz queda en <http://localhost:3000> y la API en <http://localhost:8000>.

ELMFIRE vive en un repositorio separado. Para incluirlo:

```bash
docker compose --profile simulation up -d elmfire-runner
```

## Desarrollo con recarga automática

La opción recomendada en macOS ejecuta PostGIS y FastAPI en Docker y Next.js en el host:

```bash
cp frontend/.env.local.example frontend/.env.local
npm --prefix frontend install
make dev
```

`make dev` no inicia ELMFIRE. Usar `make dev-simulation` cuando sea necesario ejecutar una
simulación real.

## API local sin contenedor

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

PostgreSQL/PostGIS debe seguir disponible y `DATABASE_URL` debe apuntar a esa instancia.

## Cuándo reconstruir

| Cambio | Acción |
|---|---|
| Python en `app/` | ninguna con recarga automática |
| interfaz en `frontend/` | ninguna con recarga automática |
| `pyproject.toml` o `uv.lock` | reconstruir `api` |
| `frontend/package*.json` | ejecutar `npm install` o reconstruir `frontend` |
| Dockerfile | reconstruir sólo el servicio afectado |
| repositorio ELMFIRE | reconstruir `elmfire-runner` |

## Pruebas

```bash
make test-unit     # pruebas unitarias del servidor
make test-e2e      # flujo completo desde la interfaz
make check         # validaciones equivalentes a CI
```

Desde `frontend/`:

```bash
npm run typecheck
npm run lint
```

## Migraciones

```bash
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "descripcion"
```

Revisar siempre la migración generada antes de aplicarla.

## Operaciones frecuentes

```bash
# Ingesta completa
curl -X POST http://localhost:8000/api/v1/ingestion/run \
  -H 'Content-Type: application/json' \
  -d '{}'

# Estado de los servicios
docker compose ps
docker compose logs -f api
```

Las simulaciones end-to-end se prueban mediante la interfaz. Los endpoints individuales se usan
únicamente para desarrollo y diagnóstico.

## Problemas comunes

- **PostGIS todavía no está listo:** esperar unos segundos y volver a ejecutar la migración.
- **GDAL o Rasterio no pueden abrir un archivo:** comprobar instalación y compatibilidad de
  versiones.
- **FIRMS devuelve un CSV vacío:** puede no haber incendios activos; ampliar la ventana temporal.
- **Falta la extensión PostGIS:** ejecutar `alembic upgrade head`.

