# IgniteInsights

**Alumnos:** Ignacio Chevallier Boutell & Manuel Salas Seeber  
**Universidad Austral — Tesis 2026**  
**Director:** Gastón Gadea

## Qué es

IgniteInsights es un sistema de predicción de propagación de incendios forestales para el Parque Nacional Los Alerces (Patagonia Argentina). Automatiza la descarga y procesamiento de cuatro familias de datos geoespaciales —focos activos VIIRS, pronóstico meteorológico GFS, topografía Copernicus DEM y cobertura de combustibles ESA WorldCover— y los integra como insumos del modelo de simulación ELMFIRE. Los resultados (isócronas de propagación horaria, frente de llamas, tiempo de llegada) se exponen como GeoJSON a través de una API REST y se visualizan en un dashboard web.

El sistema está diseñado para correr sobre los datos reales del parque con una latencia de ingesta de pocas horas respecto al ciclo GFS más reciente.

## Stack


| Capa                | Tecnología                               |
| ------------------- | ---------------------------------------- |
| Backend API         | FastAPI + Python 3.12                    |
| Base de datos       | PostgreSQL 16 + PostGIS 3.4              |
| ORM                 | SQLAlchemy async + GeoAlchemy2           |
| Ingesta geoespacial | rasterio, herbie-data, xarray, rioxarray |
| Frontend            | Next.js 15 + Tailwind CSS                |
| Simulación          | ELMFIRE (microservicio separado)         |
| Infraestructura     | Docker Compose                           |


## Quickstart

```bash
cp .env.example .env
# Completar FIRMS_MAP_KEY y OPENTOPOGRAPHY_API_KEY en .env

docker compose up --build
# API  → http://localhost:8000
# Docs → http://localhost:8000/docs
# Dashboard → http://localhost:3000

# Primera vez: correr migraciones
docker compose exec api uv run alembic upgrade head
```

## Desarrollo local del frontend

Para iterar sobre el dashboard sin reconstruir la imagen Docker:

```bash
cd frontend
cp .env.local.example .env.local   # API_BASE_URL=http://localhost:8000
npm install
npm run dev
# Dashboard → http://localhost:3000
```

## Endpoints

- [Swagger UI](https://igniteinsights-api.up.railway.app/docs)


| Method | Path                               | Descripción                                                                    |
| ------ | ---------------------------------- | ------------------------------------------------------------------------------ |
| `GET`  | `/health`                          | Healthcheck + estado de la DB                                                  |
| `GET`  | `/api/v1/dashboard/summary`        | Resumen de runs, raster assets y archivos ELMFIRE                              |
| `GET`  | `/api/v1/fires/active`             | Focos activos (GeoJSON)                                                        |
| `POST` | `/api/v1/ingestion/firms/run`      | Ingesta NASA FIRMS VIIRS                                                       |
| `POST` | `/api/v1/ingestion/dem/run`        | Descarga DEM Copernicus GLO-30                                                 |
| `POST` | `/api/v1/ingestion/gfs/run`        | Ingesta pronóstico NOAA GFS                                                    |
| `POST` | `/api/v1/ingestion/worldcover/run` | Ingesta ESA WorldCover 10 m                                                    |
| `POST` | `/api/v1/ingestion/run`            | Ejecutar varias fuentes + preparación ELMFIRE automática (endpoint principal)  |
| `GET`  | `/api/v1/ingestion/runs/{id}`      | Estado de un run de ingesta                                                    |
| `POST` | `/api/v1/simulations/run`          | Lanzar simulación ELMFIRE desde una carpeta de inputs preparada                |
| `GET`  | `/api/v1/simulations/{id}`         | Estado de una simulación                                                       |


## Ejecución end-to-end: ingesta → construcción → simulación ELMFIRE

Flujo reproducible completo, desde datos reales hasta salidas de ELMFIRE
(`time_of_arrival_*.tif`, `flin_*.tif`, `vs_*.tif`, `hourly_isochrones.shp`).

```bash
# 1. Ingesta + preparación automática de inputs ELMFIRE (FIRMS, DEM, GFS, WorldCover)
curl -s -X POST http://localhost:8000/api/v1/ingestion/run \
  -H 'Content-Type: application/json' \
  -d '{"include_firms": true, "include_dem": true, "include_gfs": true, "include_worldcover": true}' \
  | jq .
# → capturar .data.preparation.inputs_dir de la respuesta

# 2. Simulación ELMFIRE (usar un horizonte realista — ver nota abajo sobre DTDUMP)
curl -s -X POST http://localhost:8000/api/v1/simulations/run \
  -H 'Content-Type: application/json' \
  -d '{"inputs_dir": "<inputs_dir del paso 1>", "horizon_hours": 12}' \
  | jq .
# → capturar .data.simulation_id

# 3. Poll de estado
curl -s http://localhost:8000/api/v1/simulations/<simulation_id> | jq .

# 4. Verificar salidas en disco
ls -la data/elmfire/outputs/<simulation_id>/
# esperado: time_of_arrival_*.tif, flin_*.tif, vs_*.tif, hourly_isochrones.shp(+.dbf/.shx/.prj), fire_size_stats.csv

# 5. Verificar registro en base de datos
docker compose exec db psql -U igniteinsights -d igniteinsights \
  -c "SELECT id, status, output_dir, error_message, horizon_hours, finished_at FROM simulation_runs WHERE id = '<simulation_id>';"
```

**Nota sobre `horizon_hours`:** el intervalo de dump (`DTDUMP`, 3600s por defecto) debe
ser estrictamente menor que `SIMULATION_TSTOP` (`horizon_hours × 3600`) para que ELMFIRE
llegue a escribir al menos un raster/isócrona — `namelist_writer.resolve_dtdump_s()`
ajusta esto automáticamente, pero un `horizon_hours=1` (igual al DTDUMP por defecto) es
un caso límite pensado solo para smoke tests, no para una corrida real. Para el incendio
histórico de Los Alerces usar un horizonte que cubra la duración real del evento.

**Isócronas:** no son un flag nativo de ELMFIRE — se generan como post-procesamiento
(`gdal_contour` sobre `time_of_arrival_*.tif`) en `elmfire-runner/app/runner.py` después
de que ELMFIRE termina exitosamente. Ver [Mapeo a ELMFIRE](docs/elmfire-mapping.md).

## Documentación

- [Arquitectura](docs/architecture.md)
- [Fuentes de datos](docs/data-sources.md)
- [Mapeo a ELMFIRE](docs/elmfire-mapping.md)
- [Desarrollo local](docs/local-development.md)

