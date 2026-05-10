# Sistema de Predicción de Incendios Forestales en la Patagonia

**Proyecto:** IgniteInsights — Pipeline ELMFIRE + VIIRS + GFS + Copernicus DEM  
**Alumnos:** Ignacio Chevallier Boutell & Manuel Salas Seeber  
**Fecha:** Mayo 2026  
**Director:** Gastón Gadea

---

## 1. Objetivo del repositorio

### MVP inmediato (Sprint actual — Hito 3, deadline 01/07/2026)

El objetivo de este sprint es construir la base del backend FastAPI con los primeros dos módulos de ingesta operativos:

1. **NASA FIRMS / VIIRS NOAA-20 NRT** — focos activos filtrados al bounding box de Los Alerces (`west=-72, south=-42.9, east=-71.5, north=-42.5`), normalizados y persistidos.
2. **DEM Copernicus GLO-30 vía OpenTopography** — descargado en crudo y con metadata registrada en base de datos, dejando preparada la derivación de `slp.tif` y `asp.tif`.

Al cerrar este sprint se debe poder ejecutar ELMFIRE con datos reales, lo que requiere también que la arquitectura anticipe el resto del pipeline de enriquecimiento de datos.

### Alcance futuro (fuera de este sprint)

- Ingesta de GFS vía Herbie (`ws.tif`, `wd.tif`, `m1.tif`, `m10.tif`, `m100.tif`)
- Clasificación de combustibles desde ESA WorldCover + Sentinel-2 via GEE (`fbfm40.tif`)
- Parámetros de dosel desde GEDI L2B y ETH Canopy Height (`cc.tif`, `ch.tif`, `cbh.tif`, `cbd.tif`)
- Constructor de insumos ELMFIRE (`elmfire.data` generado programáticamente)
- Cliente HTTP al microservicio ELMFIRE (separado de este repositorio)
- Post-procesamiento de salidas ELMFIRE a GeoJSON
- Frontend Next.js + Mapbox GL JS
- Automatización con cron / Airflow

---

## 2. Separación arquitectural central

El sistema tiene dos responsabilidades claramente diferenciadas que **deben mantenerse desacopladas desde el inicio**:

```
┌─────────────────────────────────────────────────────┐
│  ESTE REPOSITORIO: igniteinsights-api                    │
│                                                     │
│  1. Pipeline de datos                               │
│     satellite/ → topography/ → meteorology/         │
│     fuels/ → canopy/ → elmfire_builder/             │
│                                                     │
│  2. FastAPI backend                                 │
│     Expone endpoints de focos, predicciones,        │
│     estado de ingestas y resultados al frontend     │
└─────────────────┬───────────────────────────────────┘
                  │ HTTP POST /simulate
                  ▼
┌─────────────────────────────────────────────────────┐
│  MICROSERVICIO SEPARADO: elmfire-runner             │
│                                                     │
│  Recibe: paths a GeoTIFFs + elmfire.data            │
│  Ejecuta: elmfire_2025.0212 < elmfire.data          │
│  Devuelve: paths a salidas (isocronas, TOA, etc.)   │
└─────────────────────────────────────────────────────┘
```

El microservicio ELMFIRE es un ejecutable Linux compilado desde el repositorio oficial (`lautenberger/elmfire`, branch `2025.0212`). Este plan **no incluye** la implementación de ese microservicio, pero el cliente HTTP que lo consume sí forma parte de este repositorio.

---

## 3. Estructura del repositorio

```
igniteinsights-api/
│
├── app/
│   ├── main.py                   # FastAPI app, routers, lifespan
│   ├── config.py                 # Pydantic Settings desde env vars
│   ├── dependencies.py           # Dependencias comunes (DB session, etc.)
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── router.py         # Agrega todos los sub-routers
│   │       ├── fires.py          # GET /fires/active
│   │       ├── ingestion.py      # POST /ingestion/{source}/run, GET /ingestion/runs/{id}
│   │       └── simulations.py    # POST /simulations/run, GET /simulations/{id}
│   │
│   ├── ingestion/                # Módulos de ingesta por familia de datos
│   │   ├── satellite/
│   │   │   └── firms/
│   │   │       ├── client.py         # Llamada HTTP a la API de FIRMS
│   │   │       ├── schemas.py        # Pydantic: FIRMSResponse, FireDetectionRaw
│   │   │       ├── normalizer.py     # Raw → FireDetection (modelo interno)
│   │   │       ├── service.py        # Orquesta: fetch → normalize → persist
│   │   │       └── errors.py         # FIRMSClientError, FIRMSAuthError, etc.
│   │   │
│   │   ├── topography/
│   │   │   └── opentopography/
│   │   │       ├── client.py         # Descarga DEM vía OpenTopography API
│   │   │       ├── schemas.py        # DEMDownloadRequest, DEMMetadata
│   │   │       ├── service.py        # Descarga, guarda en filesystem, registra metadata
│   │   │       └── errors.py
│   │   │
│   │   ├── meteorology/              # Sprint siguiente: GFS vía Herbie
│   │   │   └── gfs/                  # (estructura preparada, no implementada)
│   │   │
│   │   ├── fuels/                    # Sprint siguiente: ESA WorldCover / Sentinel-2 GEE
│   │   │   └── worldcover/           # (estructura preparada, no implementada)
│   │   │
│   │   └── canopy/                   # Sprint siguiente: GEDI L2B + ETH Canopy Height
│   │       └── gedi/                 # (estructura preparada, no implementada)
│   │
│   ├── elmfire/
│   │   ├── builder/
│   │   │   ├── raster_aligner.py     # Reproyecta/recorta todos los rasters al mismo grid
│   │   │   ├── namelist_writer.py    # Genera elmfire.data programáticamente
│   │   │   └── ignition_builder.py   # Construye phi.tif / ignicion.shp desde FIRMS
│   │   │
│   │   └── runner/
│   │       ├── client.py             # HTTP client al microservicio elmfire-runner
│   │       ├── schemas.py            # SimulationRequest, SimulationResult
│   │       └── errors.py
│   │
│   ├── postprocessing/
│   │   └── isochrone_converter.py    # Shapefile → GeoJSON para la API
│   │
│   ├── domain/
│   │   ├── models.py                 # SQLAlchemy ORM models
│   │   └── schemas.py                # Pydantic schemas de respuesta API
│   │
│   └── db/
│       ├── session.py                # Engine AsyncPG + session factory
│       └── repository.py            # CRUD genérico y consultas espaciales
│
├── alembic/
│   ├── env.py
│   └── versions/
│
├── data/                             # No versionar (en .gitignore)
│   ├── raw/
│   │   ├── firms/{YYYY-MM-DD}/
│   │   └── opentopography/{YYYY-MM-DD}/
│   ├── processed/
│   │   └── {aoi_id}/
│   ├── elmfire/
│   │   ├── inputs/
│   │   └── outputs/
│   └── static/                       # DEM, fbfm40 (estáticos, descargar 1 sola vez)
│
├── docs/
│   ├── architecture.md
│   ├── data-sources.md
│   ├── elmfire-mapping.md
│   └── local-development.md
│
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## 4. Patrón de modularización por fuente de datos

Cada fuente de datos sigue el mismo patrón de capas:

```
client.py
  └── Responsabilidad: SOLO llamadas HTTP externas. Sin lógica de negocio.
      Maneja timeouts, retries y errores HTTP.
      Devuelve datos crudos (dict, bytes, DataFrame).

schemas.py
  └── Responsabilidad: Tipado de entrada/salida con Pydantic.
      Dos grupos: modelos del proveedor externo (raw) y modelos internos del dominio.

normalizer.py
  └── Responsabilidad: Transforma datos del proveedor al modelo interno.
      Aquí vive el mapping de campos, conversión de unidades y filtros de calidad.
      (Ej: filtrar confidence == 'l' en FIRMS, convertir m/s a nudos en GFS)

service.py
  └── Responsabilidad: Orquesta el flujo completo para una ingesta.
      Llama a client → normalizer → repository → filesystem.
      Es el único punto de entrada desde los endpoints FastAPI.

errors.py
  └── Responsabilidad: Excepciones específicas del proveedor.
      Permite que el endpoint maneje errores de forma específica.
```

**Principio clave:** FastAPI nunca llama directamente a `client.py`. Solo llama a `service.py`. Esto permite reemplazar cualquier proveedor externo (ej: cambiar OpenTopography por NASA EarthData) modificando solo `client.py` y `normalizer.py`.

---

## 5. Configuración del proyecto

### Gestión de dependencias: `uv`

Se elige `uv` sobre Poetry porque tiene instalación sin dependencias externas, resolución de dependencias significativamente más rápida, y es compatible con `pyproject.toml` estándar (PEP 517/621). Para un proyecto de tesis con iteraciones frecuentes, el tiempo de `uv sync` es materialmente menor al de `poetry install`.

```toml
# pyproject.toml
[project]
name = "igniteinsights-api"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    # Web
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",

    # HTTP client
    "httpx>=0.27",

    # GIS / Raster
    "rasterio>=1.3",
    "geopandas>=1.0",
    "shapely>=2.0",
    # GDAL: instalar via apt/conda antes de pip. Ver docs/local-development.md

    # Data
    "pandas>=2.2",
    "numpy>=1.26",

    # DB
    "sqlalchemy[asyncio]>=2.0",
    "geoalchemy2>=0.15",
    "asyncpg>=0.29",
    "alembic>=1.13",

    # Dev/ops
    "python-dotenv>=1.0",
]

[tool.uv]
dev-dependencies = [
    "ruff>=0.4",
    "mypy>=1.10",
]

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "UP"]

[tool.mypy]
python_version = "3.12"
strict = false
ignore_missing_imports = true
```

### Variables de entorno (`.env.example`)

```bash
# APIs externas
FIRMS_MAP_KEY=                       # firms.modaps.eosdis.nasa.gov/api/map_key/
OPENTOPOGRAPHY_API_KEY=              # portal.opentopography.org

# Credenciales pendientes (sprints futuros)
# GEE_SERVICE_ACCOUNT_JSON=          # Google Earth Engine
# CDS_API_KEY=                       # Copernicus CDS (ERA5 para humedad)

# Base de datos
DATABASE_URL=postgresql+asyncpg://igniteinsights:igniteinsights@localhost:5432/igniteinsights

# Microservicio ELMFIRE
ELMFIRE_RUNNER_URL=http://elmfire-runner:8001  # URL del microservicio separado
ELMFIRE_RUNNER_TIMEOUT=300                     # segundos (simulación puede tardar ~3 min)

# Filesystem
DATA_DIR=/app/data
RAW_DATA_DIR=/app/data/raw
PROCESSED_DATA_DIR=/app/data/processed
ELMFIRE_INPUTS_DIR=/app/data/elmfire/inputs
ELMFIRE_OUTPUTS_DIR=/app/data/elmfire/outputs

# App
APP_ENV=development   # development | production
LOG_LEVEL=INFO

# Área de interés: Parque Nacional Los Alerces
AOI_WEST=-72.0
AOI_SOUTH=-42.9
AOI_EAST=-71.5
AOI_NORTH=-42.5
AOI_CRS_PROCESSING=EPSG:32719         # UTM Zona 19S — para procesamiento interno
AOI_CRS_OUTPUT=EPSG:4326              # WGS84 — para la API y el frontend
```

---

## 6. Diseño de dominio

### Entidades conceptuales y mapping a PostgreSQL/PostGIS

`**AreaOfInterest**` — Zona geográfica de interés definida como polígono.

```sql
CREATE TABLE areas_of_interest (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    geom        GEOMETRY(Polygon, 4326) NOT NULL,  -- PostGIS
    crs_processing TEXT NOT NULL,   -- 'EPSG:32719'
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

`**DataSource**` — Registro de cada proveedor de datos externo.

```sql
CREATE TABLE data_sources (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT UNIQUE NOT NULL,  -- 'firms_viirs_noaa20', 'opentopography_cop30'
    category    TEXT NOT NULL,         -- 'satellite', 'topography', 'meteorology', etc.
    base_url    TEXT,
    is_active   BOOLEAN DEFAULT TRUE
);
```

`**IngestionRun**` — Registro de cada ejecución de una ingesta.

```sql
CREATE TABLE ingestion_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_source_id  UUID REFERENCES data_sources(id),
    aoi_id          UUID REFERENCES areas_of_interest(id),
    status          TEXT NOT NULL,       -- 'pending', 'running', 'success', 'failed'
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    error_message   TEXT,
    metadata        JSONB                -- params de la corrida, counts, etc.
);
```

`**FireDetection**` — Foco de calor detectado por VIIRS.

```sql
CREATE TABLE fire_detections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingestion_run_id UUID REFERENCES ingestion_runs(id),
    geom            GEOMETRY(Point, 4326) NOT NULL,  -- PostGIS Point
    bright_ti4      FLOAT,
    frp             FLOAT,              -- Fire Radiative Power (MW)
    confidence      TEXT,              -- 'l', 'n', 'h'
    acq_datetime    TIMESTAMPTZ NOT NULL,
    satellite       TEXT,              -- 'N' = NOAA-20
    daynight        TEXT               -- 'D' = Day, 'N' = Night
);

CREATE INDEX idx_fire_detections_geom ON fire_detections USING GIST(geom);
CREATE INDEX idx_fire_detections_acq ON fire_detections(acq_datetime);
```

`**RasterAsset**` — Metadata de un archivo raster descargado o generado.

```sql
CREATE TABLE raster_assets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingestion_run_id UUID REFERENCES ingestion_runs(id),
    asset_type      TEXT NOT NULL,     -- 'dem_raw', 'dem_processed', 'slp', 'asp', etc.
    file_path       TEXT NOT NULL,     -- path absoluto en el filesystem
    crs             TEXT,              -- 'EPSG:4326', 'EPSG:32719'
    resolution_m    FLOAT,             -- 30.0
    bbox            GEOMETRY(Polygon, 4326),  -- extensión del raster
    band_count      INT,
    dtype           TEXT,              -- 'float32', 'int16'
    file_size_bytes BIGINT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    metadata        JSONB
);
```

`**SimulationRun**` — Ejecución de ELMFIRE vía el microservicio.

```sql
CREATE TABLE simulation_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aoi_id          UUID REFERENCES areas_of_interest(id),
    status          TEXT NOT NULL,      -- 'pending', 'running', 'success', 'failed'
    horizon_hours   INT NOT NULL,       -- 1, 2, 3
    ignition_datetime TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    elmfire_config  JSONB,              -- copia del elmfire.data generado
    output_dir      TEXT,              -- path al directorio de outputs
    error_message   TEXT
);
```

`**SimulationOutput**` — Salida procesada de una simulación (isocrona como GeoJSON).

```sql
CREATE TABLE simulation_outputs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_id   UUID REFERENCES simulation_runs(id),
    output_type     TEXT NOT NULL,     -- 'isochrone_1h', 'isochrone_2h', 'toa', etc.
    geom            GEOMETRY(MultiPolygon, 4326),  -- para isocronas vectoriales
    file_path       TEXT,              -- para rasters (TOA, flame length)
    valid_at        TIMESTAMPTZ,       -- timestamp al que corresponde la predicción
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## 7. Endpoints FastAPI

### Diseño de respuesta estándar

```python
# Todas las respuestas siguen este envelope
{
    "status": "success" | "error",
    "data": { ... } | null,
    "error": { "code": "...", "message": "..." } | null,
    "meta": { "request_id": "...", "timestamp": "..." }
}
```

### Endpoints del sprint actual


| Método | Path                              | Descripción                            | Sync/Async       |
| ------ | --------------------------------- | -------------------------------------- | ---------------- |
| `GET`  | `/health`                         | Healthcheck + estado de DB             | Sync             |
| `GET`  | `/api/v1/fires/active`            | Focos activos (últimas 24h) en GeoJSON | Async DB         |
| `POST` | `/api/v1/ingestion/firms/run`     | Dispara ingesta FIRMS                  | Background task* |
| `POST` | `/api/v1/ingestion/dem/run`       | Dispara descarga DEM                   | Background task* |
| `GET`  | `/api/v1/ingestion/runs/{run_id}` | Estado de una ingesta                  | Async DB         |


*Para desarrollo se ejecutan de forma síncrona. Marcar como TODO para migrar a Celery/ARQ en producción.

### Endpoints preparados (sprints futuros, rutas ya definidas)


| Método | Path                         | Descripción                             |
| ------ | ---------------------------- | --------------------------------------- |
| `POST` | `/api/v1/ingestion/gfs/run`  | Ingesta meteorológica GFS               |
| `POST` | `/api/v1/simulations/run`    | Dispara simulación ELMFIRE completa     |
| `GET`  | `/api/v1/simulations/{id}`   | Estado y resultado de una simulación    |
| `GET`  | `/api/v1/predictions/latest` | Última predicción disponible en GeoJSON |


---

## 8. Validación de APIs externas

### API authenticity checklist

#### NASA FIRMS — VIIRS NOAA-20 NRT


| Campo             | Valor verificado                                                                                                                                |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| URL oficial       | `https://firms.modaps.eosdis.nasa.gov/api/`                                                                                                     |
| Endpoint          | `GET https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_NOAA20_NRT/{bbox}/{day_range}`                                           |
| Parámetros        | `bbox` = `west,south,east,north` (lon/lat WGS84); `day_range` = `1` a `10`                                                                      |
| Autenticación     | MAP_KEY en la URL (no header). Registro gratuito en `firms.modaps.eosdis.nasa.gov/api/map_key/`                                                 |
| Formato respuesta | CSV con columnas: `latitude, longitude, bright_ti4, scan, track, acq_date, acq_time, satellite, confidence, version, bright_ti5, frp, daynight` |
| Rate limit        | 5.000 transacciones / 10 minutos                                                                                                                |
| Confianza         | Filtrar `confidence in ('n', 'h')` — descartar `'l'` (low)                                                                                      |
| Latencia NRT      | ~3 horas desde el paso del satélite                                                                                                             |
| Request mínimo    | `curl "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{KEY}/VIIRS_NOAA20_NRT/-72,-42.9,-71.5,-42.5/1"`                                       |


**Nota sobre bbox en FIRMS:** el orden es `west,south,east,north` (lon_min, lat_min, lon_max, lat_max), consistente con valores negativos para el hemisferio sur.

#### OpenTopography — Copernicus GLO-30


| Campo             | Valor verificado                                                                                                                                                   |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| URL oficial       | `https://portal.opentopography.org/`                                                                                                                               |
| Endpoint          | `GET https://portal.opentopography.org/API/globaldem`                                                                                                              |
| Parámetros        | `demtype=COP30`, `south`, `north`, `west`, `east` (en grados decimales WGS84), `outputFormat=GTiff`, `API_Key`                                                     |
| Autenticación     | API Key en query string. Registro gratuito en `portal.opentopography.org`                                                                                          |
| Formato respuesta | GeoTIFF binario (descarga directa)                                                                                                                                 |
| CRS de entrega    | EPSG:4326 (WGS84) — **se debe reproyectar a EPSG:32719 para procesamiento**                                                                                        |
| Resolución        | 30 m (~1 arc-second)                                                                                                                                               |
| Sin API key       | Limitado a 500 MB/día                                                                                                                                              |
| Request mínimo    | `curl -o dem_raw.tif "https://portal.opentopography.org/API/globaldem?demtype=COP30&south=-42.9&north=-42.5&west=-72&east=-71.5&outputFormat=GTiff&API_Key={KEY}"` |


#### Microservicio ELMFIRE — PENDING VERIFICATION

El contrato del microservicio ELMFIRE-runner debe definirse. Como punto de partida se propone:

```
POST http://elmfire-runner:8001/simulate
Content-Type: application/json

{
    "elmfire_data_path": "/data/elmfire/inputs/{run_id}/elmfire.data",
    "inputs_dir": "/data/elmfire/inputs/{run_id}/",
    "outputs_dir": "/data/elmfire/outputs/{run_id}/",
    "simulation_hours": 3
}

Response 200:
{
    "status": "success",
    "run_id": "...",
    "outputs": {
        "isochrones_shp": "/data/elmfire/outputs/{run_id}/hourly_isochrones.shp",
        "time_of_arrival_tif": "/data/elmfire/outputs/{run_id}/toa_*.tif",
        "flame_length_tifs": [...]
    }
}
```

**PENDING VERIFICATION:** validar que los paths sean compartidos entre ambos microservicios vía volumen Docker montado, o definir un mecanismo alternativo (objeto storage, SFTP, etc.).

---

## 9. Mapeado fuente externa → ELMFIRE

Esta tabla es la guía principal para entender qué módulo de ingesta produce qué input de ELMFIRE:


| Fuente externa          | Dato crudo                        | Dato normalizado                     | Input ELMFIRE                                              | Módulo                                                 | Sprint        |
| ----------------------- | --------------------------------- | ------------------------------------ | ---------------------------------------------------------- | ------------------------------------------------------ | ------------- |
| NASA FIRMS VIIRS        | CSV de focos                      | `FireDetection` (Point PostGIS)      | `phi.tif` / `ignicion.shp`                                 | `satellite/firms` + `elmfire/builder/ignition_builder` | Actual + sig. |
| OpenTopography COP30    | `dem_raw.tif` (EPSG:4326)         | `dem.tif` (EPSG:32719, 30m)          | `DEM_FILENAME`                                             | `topography/opentopography`                            | Actual        |
| Derivado de DEM         | —                                 | `slp.tif` (gdaldem slope)            | `SLP_FILENAME`                                             | `elmfire/builder/raster_aligner`                       | Siguiente     |
| Derivado de DEM         | —                                 | `asp.tif` (gdaldem aspect)           | `ASP_FILENAME`                                             | `elmfire/builder/raster_aligner`                       | Siguiente     |
| NOAA GFS (Herbie)       | GRIB2 / xarray                    | `ws.tif`, `wd.tif` (multi-banda, 1h) | `WS_FILENAME`, `WD_FILENAME`                               | `meteorology/gfs`                                      | Siguiente     |
| ERA5-Land / GFS         | T2m, RH2m                         | `m1.tif`, `m10.tif`, `m100.tif`      | `M1_FILENAME`, etc.                                        | `meteorology/gfs`                                      | Siguiente     |
| ESA WorldCover (GEE)    | GeoTIFF clasificado (11 clases)   | `fbfm40.tif` (crosswalk)             | `FBFM_FILENAME`                                            | `fuels/worldcover`                                     | Hito 4        |
| Derivado de fbfm40      | —                                 | `adj.tif` (factores empíricos)       | `ADJ_FILENAME`                                             | `fuels/worldcover`                                     | Hito 4        |
| GEDI L2B (GEE)          | NetCDF/GeoTIFF fracción cobertura | `cc.tif` (%, int16)                  | `CC_FILENAME`                                              | `canopy/gedi`                                          | Hito 4        |
| ETH Canopy Height (GEE) | GeoTIFF altura m                  | `ch.tif` (float32)                   | `CH_FILENAME`                                              | `canopy/gedi`                                          | Hito 4        |
| Tabla empírica + fbfm40 | —                                 | `cbh.tif`, `cbd.tif` (float32)       | `CBH_FILENAME`, `CBD_FILENAME`                             | `canopy/gedi`                                          | Hito 4        |
| Constante estacional    | —                                 | Config en `elmfire.data`             | `LH_MOISTURE_CONTENT = 30.0`, `LW_MOISTURE_CONTENT = 60.0` | `elmfire/builder/namelist_writer`                      | Siguiente     |


**Restricción ELMFIRE confirmada:** todos los rasters deben compartir CRS (`EPSG:32719`), resolución (30 m), y extensión exacta. El módulo `elmfire/builder/raster_aligner.py` es responsable de garantizar esta alineación usando `gdalwarp` antes de cualquier simulación.

---

## 10. Estrategia de persistencia

### Filesystem

```
data/
├── raw/
│   ├── firms/
│   │   └── 2026-05-10/
│   │       └── viirs_noaa20_nrt_los_alerces.csv    # CSV crudo de la API
│   └── opentopography/
│       └── 2026-05-10/
│           └── dem_cop30_raw.tif                   # GeoTIFF sin procesar, EPSG:4326
│
├── static/                                          # Datos estáticos (1 sola descarga)
│   ├── dem_cop30_los_alerces.tif                   # DEM base reproyectado
│   ├── slp_los_alerces.tif
│   ├── asp_los_alerces.tif
│   └── fbfm40_los_alerces.tif                      # Hito 4
│
├── processed/
│   └── {aoi_id}/
│       └── {date}/
│           ├── ws.tif                               # multi-banda
│           ├── wd.tif
│           └── m1.tif
│
└── elmfire/
    ├── inputs/
    │   └── {run_id}/
    │       ├── elmfire.data                         # namelist generado
    │       ├── dem.tif → symlink o copia
    │       ├── ws.tif, wd.tif, m1.tif, ...
    │       └── ignicion.shp
    └── outputs/
        └── {run_id}/
            ├── hourly_isochrones.shp
            ├── toa_0000001_*.tif
            └── flin_0000001_*.tif
```

**¿Qué va a la base de datos?** Metadata y datos vectoriales/puntuales: `FireDetection` (geometrías PostGIS), `IngestionRun`, `RasterAsset` (metadata + path del archivo), `SimulationOutput` (isocronas como geometrías PostGIS).

**¿Qué queda solo en filesystem?** Los rasters en sí (GeoTIFF). Son archivos binarios grandes que no van a DB.

### `.gitignore`

```gitignore
# Datos — nunca versionar
data/
*.tif
*.shp
*.dbf
*.shx
*.prj
*.csv

# Credenciales
.env
*.env

# Python
__pycache__/
*.pyc
.venv/
dist/

# IDE
.vscode/
.idea/

# Alembic no versionados
alembic/versions/*.py  # sí versionar, sólo excluir si se prefiere

# Logs
*.log
```

---

## 11. Implementación paso a paso

### Commit 1 — Scaffold FastAPI

**Objetivo:** app FastAPI mínima que responde `/health`  
**Archivos a crear:** `app/main.py`, `app/config.py`, `pyproject.toml`, `.env.example`  
**Criterio de aceptación:** `uvicorn app.main:app --reload` levanta y `GET /health` devuelve `{"status": "ok"}`

```python
# app/config.py (snippet mínimo)
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "development"
    firms_map_key: str
    opentopography_api_key: str
    database_url: str
    elmfire_runner_url: str = "http://localhost:8001"
    data_dir: str = "/app/data"
    aoi_west: float = -72.0
    aoi_south: float = -42.9
    aoi_east: float = -71.5
    aoi_north: float = -42.5

    class Config:
        env_file = ".env"

settings = Settings()
```

---

### Commit 2 — Docker Compose + PostGIS

**Objetivo:** levantar API + PostgreSQL/PostGIS con un solo comando  
**Archivos a crear:** `Dockerfile`, `docker-compose.yml`  
**Criterio de aceptación:** `docker compose up` levanta ambos servicios, API conecta a DB

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data
    env_file: .env
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: igniteinsights
      POSTGRES_USER: igniteinsights
      POSTGRES_PASSWORD: igniteinsights
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U igniteinsights"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

```dockerfile
# Dockerfile
FROM python:3.12-slim

# GDAL: instalar antes que rasterio
RUN apt-get update && apt-get install -y \
    gdal-bin libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

ENV GDAL_VERSION=3.6
RUN pip install GDAL==$(gdal-config --version)

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml .
RUN uv sync --no-dev

COPY . .
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Commit 3 — Modelos SQLAlchemy + migraciones Alembic iniciales

**Objetivo:** tablas `areas_of_interest`, `data_sources`, `ingestion_runs`, `fire_detections`, `raster_assets` creadas en DB  
**Archivos a crear:** `app/domain/models.py`, `app/db/session.py`, `alembic/env.py`, primera migración  
**Criterio de aceptación:** `alembic upgrade head` ejecuta sin errores, tablas visibles en psql

---

### Commit 4 — Cliente FIRMS

**Objetivo:** `firms/client.py` descarga CSV de la API de FIRMS para el bbox de Los Alerces  
**Archivos a crear:** `app/ingestion/satellite/firms/client.py`, `schemas.py`, `errors.py`  
**Criterio de aceptación:**

```python
# Script de prueba manual
from app.ingestion.satellite.firms.client import FIRMSClient
client = FIRMSClient()
df = client.fetch_active_fires(west=-72, south=-42.9, east=-71.5, north=-42.5, day_range=1)
assert not df.empty
assert "latitude" in df.columns
```

**Snippet clave en `client.py`:**

```python
import httpx
import pandas as pd
from io import StringIO
from app.config import settings
from .errors import FIRMSClientError, FIRMSAuthError

FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

class FIRMSClient:
    def __init__(self):
        self._timeout = httpx.Timeout(30.0)

    def fetch_active_fires(
        self, west: float, south: float, east: float, north: float, day_range: int = 1
    ) -> pd.DataFrame:
        bbox = f"{west},{south},{east},{north}"
        url = f"{FIRMS_BASE_URL}/{settings.firms_map_key}/VIIRS_NOAA20_NRT/{bbox}/{day_range}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url)
                if response.status_code == 401:
                    raise FIRMSAuthError("MAP_KEY inválida o expirada")
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise FIRMSClientError(f"Error HTTP al consultar FIRMS: {e}") from e
        
        if "No data" in response.text or not response.text.strip():
            return pd.DataFrame()  # Sin focos en el área/período
        
        return pd.read_csv(StringIO(response.text))
```

---

### Commit 5 — Normalizador y servicio FIRMS

**Objetivo:** `normalizer.py` convierte CSV a lista de `FireDetection`, `service.py` orquesta y persiste  
**Archivos a crear:** `app/ingestion/satellite/firms/normalizer.py`, `service.py`  
**Criterio de aceptación:** `POST /api/v1/ingestion/firms/run` devuelve `run_id` y registra focos en DB

**Snippet clave en `normalizer.py`:**

```python
import pandas as pd
from datetime import datetime, timezone
from shapely.geometry import Point
from .schemas import FireDetectionNormalized

# Niveles de confianza aceptados (excluir 'l' = low)
ACCEPTED_CONFIDENCE = {"n", "h"}

def normalize_firms_response(df: pd.DataFrame) -> list[FireDetectionNormalized]:
    if df.empty:
        return []
    
    filtered = df[df["confidence"].isin(ACCEPTED_CONFIDENCE)].copy()
    detections = []
    for _, row in filtered.iterrows():
        acq_dt = datetime.strptime(
            f"{row['acq_date']} {str(row['acq_time']).zfill(4)}",
            "%Y-%m-%d %H%M"
        ).replace(tzinfo=timezone.utc)
        detections.append(FireDetectionNormalized(
            geom=Point(row["longitude"], row["latitude"]),
            bright_ti4=float(row["bright_ti4"]),
            frp=float(row["frp"]),
            confidence=str(row["confidence"]),
            acq_datetime=acq_dt,
            satellite=str(row["satellite"]),
            daynight=str(row["daynight"]),
        ))
    return detections
```

---

### Commit 6 — Cliente OpenTopography + descarga DEM

**Objetivo:** `opentopography/client.py` descarga el GeoTIFF crudo y lo guarda en filesystem  
**Archivos a crear:** `app/ingestion/topography/opentopography/client.py`, `schemas.py`, `service.py`, `errors.py`  
**Criterio de aceptación:** `POST /api/v1/ingestion/dem/run` descarga `dem_cop30_raw.tif` y registra `RasterAsset` en DB

**Nota importante sobre el DEM:** el DEM de Los Alerces es un dato **estático** (el terreno no cambia). En producción, la descarga se hace una única vez y el archivo se reutiliza indefinidamente. El endpoint permite re-descargar, pero el servicio debe verificar si ya existe antes de volver a descargar.

```python
# Snippet de verificación de idempotencia en service.py
async def download_dem_if_needed(aoi_id: str, bbox: BoundingBox) -> RasterAsset:
    existing = await repository.find_raster_asset(
        aoi_id=aoi_id, asset_type="dem_raw"
    )
    if existing and Path(existing.file_path).exists():
        logger.info(f"DEM ya existe en {existing.file_path}, omitiendo descarga")
        return existing
    return await _download_and_register(aoi_id, bbox)
```

---

### Commit 7 — Estructura del módulo `elmfire/`

**Objetivo:** dejar preparada la estructura de `elmfire/builder/` y `elmfire/runner/`  
**Archivos a crear:** módulos vacíos con docstrings que explican responsabilidad de cada uno  
**Criterio de aceptación:** imports sin errores, estructura clara para el siguiente sprint

**Snippet del cliente ELMFIRE en `runner/client.py`:**

```python
# elmfire/runner/client.py
import httpx
from app.config import settings
from .schemas import SimulationRequest, SimulationResult
from .errors import ELMFIRERunnerError

class ELMFIRERunnerClient:
    """
    Cliente HTTP al microservicio elmfire-runner.
    El microservicio ELMFIRE es un proceso separado que ejecuta
    elmfire_2025.0212 < elmfire.data y devuelve los paths a los outputs.
    """
    def __init__(self):
        self._base_url = settings.elmfire_runner_url
        self._timeout = httpx.Timeout(settings.elmfire_runner_timeout)
    
    async def run_simulation(self, request: SimulationRequest) -> SimulationResult:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/simulate",
                    json=request.model_dump()
                )
                response.raise_for_status()
                return SimulationResult(**response.json())
            except httpx.HTTPError as e:
                raise ELMFIRERunnerError(f"Error comunicando con elmfire-runner: {e}") from e
```

---

### Commit 8 — Endpoints FastAPI completos del sprint

**Objetivo:** routers `ingestion.py` y `fires.py` funcionales, con manejo de errores consistente  
**Archivos a crear/modificar:** `app/api/v1/ingestion.py`, `app/api/v1/fires.py`, `app/api/v1/router.py`  
**Criterio de aceptación:** todos los endpoints del sprint responden con el formato de respuesta estándar

---

### Commit 9 — CI GitHub Actions

**Objetivo:** pipeline de CI mínimo  
**Archivos a crear:** `.github/workflows/ci.yml`

```yaml
name: CI
on: [push, pull_request]

jobs:
  lint-and-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --no-dev
      - run: uv run ruff check app/
      - run: uv run mypy app/ --ignore-missing-imports
```

---

## 12. Calidad de código

### Principios aplicados en todo el proyecto

- **Type hints obligatorios:** todo `def` y `async def` tiene anotaciones de retorno e inputs.
- **Pydantic v2 models:** schemas de validación en todas las capas que cruzan datos externos.
- **Logging estructurado:** usar `structlog` o el `logging` estándar con formato JSON en producción. Nunca `print()`.
- **Sin credenciales en código:** siempre desde `settings.variable`. Cualquier hardcode es un bug.
- **Idempotencia de ingestas:** re-ejecutar la misma ingesta no debe crear duplicados. Verificar por `(aoi_id, date, source)` antes de insertar.
- **Retries y timeouts explícitos:** todos los `httpx.Client` declaran `timeout=`. Para reintentos automáticos usar `tenacity` si se agrega como dependencia.
- **Errores explícitos:** cada módulo tiene su propio `errors.py`. Los endpoints capturan excepciones específicas y devuelven HTTP apropiado (400, 404, 502, 503).
- **Separación de capas:** FastAPI → `service.py` → `client.py` + `repository.py`. Nunca saltar capas.

---

## 13. Riesgos del sprint y mitigaciones


| Riesgo                                                               | Severidad | Mitigación                                                                                                                                                           |
| -------------------------------------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MAP_KEY de FIRMS inválida o no registrada                            | ALTO      | Registrar en `firms.modaps.eosdis.nasa.gov/api/map_key/` antes de empezar. La key se genera instantáneamente con email.                                              |
| Sin focos activos en Los Alerces en el día actual                    | MEDIO     | Usar `day_range=7` para los primeros tests o probar con bbox de Patagonia amplio (`-75,-56,-62,-38`).                                                                |
| DEM descargado con CRS incorrecto o vacío                            | MEDIO     | Verificar con `gdalinfo dem_raw.tif` después de la descarga. El CRS debe ser EPSG:4326 y el bbox debe contener Los Alerces.                                          |
| GDAL/rasterio incompatibilidad en instalación                        | ALTO      | Usar la imagen Docker base `postgis/postgis` para desarrollo local. Para rasterio instalar GDAL primero via apt, luego `pip install GDAL==$(gdal-config --version)`. |
| Descarga del DEM de toda Patagonia (bbox grande) es pesada (~500 MB) | BAJO      | Para el sprint solo descargar el bbox acotado de Los Alerces (`-72,-42.9,-71.5,-42.5`). Extender luego.                                                              |
| Path compartido entre API y microservicio ELMFIRE                    | MEDIO     | Definir y documentar el volumen Docker compartido antes de implementar el cliente. El path debe ser consistente en ambos servicios.                                  |


---

## 14. Checklist de aceptación del sprint

```
[ ] Repositorio inicializado con estructura completa
[ ] FastAPI levanta localmente con uvicorn
[ ] Configuración 100% desde variables de entorno (sin hardcode)
[ ] docker compose up levanta API + PostGIS sin errores
[ ] alembic upgrade head crea todas las tablas correctamente
[ ] GET /health responde 200 con estado de DB
[ ] POST /api/v1/ingestion/firms/run descarga CSV de FIRMS para Los Alerces
[ ] Los focos FIRMS se filtran por confidence 'n' y 'h'
[ ] Los focos normalizados se insertan como Points en PostGIS
[ ] GET /api/v1/fires/active devuelve focos en GeoJSON válido
[ ] POST /api/v1/ingestion/dem/run descarga DEM Copernicus GLO-30 para Los Alerces
[ ] El GeoTIFF descargado existe en data/raw/opentopography/{date}/
[ ] La metadata del raster se registra en tabla raster_assets
[ ] La ingesta es idempotente: re-ejecutar no crea duplicados ni re-descarga si ya existe
[ ] Módulos elmfire/builder/ y elmfire/runner/ tienen estructura y docstrings claros
[ ] .github/workflows/ci.yml ejecuta ruff y mypy sin errores
[ ] .gitignore excluye todos los datos (*.tif, *.csv, data/)
[ ] docs/data-sources.md documenta los endpoints verificados
[ ] docs/local-development.md documenta los pasos para levantar el entorno desde cero
```

---

## 15. Documentación del repositorio

### `README.md` — secciones mínimas

- Descripción del proyecto y objetivo
- Diagrama de arquitectura (texto o imagen)
- Requisitos previos (Docker, uv, credenciales necesarias)
- Quickstart: `cp .env.example .env && docker compose up`
- Links a docs/ para detalle

### `docs/architecture.md`

- Las 5 capas del pipeline (detección → enriquecimiento → construcción → simulación → visualización)
- Diagrama de separación entre `igniteinsights-api` y `elmfire-runner`
- Decisiones de arquitectura y su justificación (CRS EPSG:32719, resolución 30m, etc.)

### `docs/data-sources.md`

- Tabla de fuentes de datos (de la Sección 9 de este documento)
- Endpoints verificados, credenciales necesarias y cómo obtenerlas
- Frecuencia de actualización de cada capa

### `docs/elmfire-mapping.md`

- Tabla fuente externa → input ELMFIRE (de la Sección 9)
- Restricciones de alineación raster (CRS, resolución, extensión)
- Estructura del `elmfire.data` generado programáticamente

### `docs/local-development.md`

- Instalación de GDAL en Ubuntu/macOS
- Cómo obtener cada API key
- Comandos de desarrollo frecuentes
- Troubleshooting de problemas comunes (GDAL, asyncpg, PostGIS)

