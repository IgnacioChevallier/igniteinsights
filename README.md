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

- [Swagger UI](https://igniteinsights.up.railway.app/docs)


| Method | Path                               | Descripción                                       |
| ------ | ---------------------------------- | ------------------------------------------------- |
| `GET`  | `/health`                          | Healthcheck + estado de la DB                     |
| `GET`  | `/api/v1/dashboard/summary`        | Resumen de runs, raster assets y archivos ELMFIRE |
| `GET`  | `/api/v1/fires/active`             | Focos activos (GeoJSON)                           |
| `POST` | `/api/v1/ingestion/firms/run`      | Ingesta NASA FIRMS VIIRS                          |
| `POST` | `/api/v1/ingestion/dem/run`        | Descarga DEM Copernicus GLO-30                    |
| `POST` | `/api/v1/ingestion/gfs/run`        | Ingesta pronóstico NOAA GFS                       |
| `POST` | `/api/v1/ingestion/worldcover/run` | Ingesta ESA WorldCover 10 m                       |
| `POST` | `/api/v1/ingestion/run`            | Ejecutar varias fuentes simultáneamente           |
| `GET`  | `/api/v1/ingestion/runs/{id}`      | Estado de un run de ingesta                       |


## Documentación

- [Arquitectura](docs/architecture.md)
- [Fuentes de datos](docs/data-sources.md)
- [Mapeo a ELMFIRE](docs/elmfire-mapping.md)
- [Desarrollo local](docs/local-development.md)

