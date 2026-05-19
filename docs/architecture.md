# Architecture

## Objetivo del sistema

IgniteInsights es un pipeline de predicción de incendios forestales para el Parque Nacional Los Alerces (Patagonia). Integra datos satelitales de focos activos, modelos meteorológicos, topografía y cobertura de combustibles para alimentar simulaciones de propagación con el modelo ELMFIRE. Los resultados se exponen como isócronas GeoJSON a través de una API REST y un dashboard web.

## Pipeline de datos

```
1. Detección     satellite/firms        → FireDetection (PostGIS Point)
2. Enriquecimiento
                 topography/            → dem.tif, slp.tif, asp.tif
                 meteorology/gfs/       → ws.tif, wd.tif, m1.tif, m10.tif, m100.tif
                 fuels/worldcover/      → fbfm40.tif
                 canopy/gedi/           → cc.tif, ch.tif, cbh.tif, cbd.tif
3. Construcción  elmfire/builder/       → elmfire.data + rasters alineados
4. Simulación    elmfire/runner/        → HTTP POST al microservicio elmfire-runner
5. Visualización postprocessing/        → GeoJSON isócronas servidas por la API
```

## Separación arquitectural central

El sistema tiene dos responsabilidades desacopladas que deben mantenerse separadas:

```
┌─────────────────────────────────────────────────────┐
│  igniteinsights-api  (este repositorio)             │
│                                                     │
│  1. Pipeline de datos                               │
│     satellite/ → topography/ → meteorology/         │
│     fuels/ → canopy/ → elmfire/builder/             │
│                                                     │
│  2. FastAPI backend                                 │
│     Expone endpoints de focos, predicciones,        │
│     estado de ingestas y resultados al frontend     │
│                                                     │
│  3. Frontend Next.js                                │
│     Dashboard de visualización en frontend/         │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP POST /simulate
                      ▼
┌─────────────────────────────────────────────────────┐
│  elmfire-runner  (microservicio separado)           │
│                                                     │
│  Recibe: paths a GeoTIFFs + elmfire.data            │
│  Ejecuta: elmfire_2025.0212 < elmfire.data          │
│  Devuelve: paths a salidas (isocronas, TOA, etc.)   │
└─────────────────────────────────────────────────────┘
```

Ambos servicios comparten un volumen Docker en `/app/data/elmfire/`. El microservicio ELMFIRE es un ejecutable Linux compilado desde `lautenberger/elmfire` (branch `2025.0212`) y no forma parte de este repositorio; el cliente HTTP que lo consume sí.

## Estructura del repositorio

```
igniteinsights/
│
├── app/
│   ├── main.py                   # FastAPI app, routers, lifespan
│   ├── config.py                 # Pydantic Settings desde env vars
│   ├── dependencies.py           # Dependencias comunes (DB session, etc.)
│   │
│   ├── api/v1/
│   │   ├── router.py             # Agrega todos los sub-routers
│   │   ├── fires.py              # GET /fires/active
│   │   ├── ingestion.py          # POST /ingestion/{source}/run, GET /ingestion/runs/{id}
│   │   └── simulations.py        # POST /simulations/run, GET /simulations/{id}
│   │
│   ├── ingestion/
│   │   ├── satellite/firms/      # NASA FIRMS VIIRS NOAA-20 NRT ✅
│   │   ├── topography/           # Copernicus GLO-30 DEM ✅
│   │   │   └── opentopography/
│   │   ├── meteorology/gfs/      # NOAA GFS 0.25° vía Herbie ✅
│   │   ├── fuels/worldcover/     # ESA WorldCover 10 m ✅
│   │   └── canopy/gedi/          # GEDI L2B + ETH Canopy Height (Sprint 4)
│   │
│   ├── elmfire/
│   │   ├── builder/              # raster_aligner, namelist_writer, ignition_builder
│   │   └── runner/               # Cliente HTTP al microservicio elmfire-runner
│   │
│   ├── postprocessing/           # Shapefile → GeoJSON
│   ├── domain/                   # SQLAlchemy ORM + Pydantic schemas de respuesta
│   └── db/                       # Engine AsyncPG, session factory, repository CRUD
│
├── frontend/                     # Dashboard Next.js (puerto 3000)
├── alembic/                      # Migraciones de base de datos
├── data/                         # Datos en runtime (gitignoreado)
│   ├── raw/{source}/{YYYY-MM-DD}/
│   ├── processed/{aoi_id}/
│   ├── elmfire/{inputs,outputs}/{run_id}/
│   └── static/                   # DEM, fbfm40 (estáticos, una sola descarga)
└── docs/
```

## Patrón de modularización por fuente de datos

Cada fuente de datos sigue el mismo patrón de cuatro capas:

```
client.py
  └── Solo llamadas HTTP/IO externas. Sin lógica de negocio.
      Maneja timeouts y errores HTTP. Devuelve datos crudos.

schemas.py
  └── Tipado Pydantic de entrada/salida.
      Modelos del proveedor externo (raw) y modelos internos del dominio.

normalizer.py  (donde aplique)
  └── Transforma datos del proveedor al modelo interno.
      Mapping de campos, conversión de unidades, filtros de calidad.

service.py
  └── Orquesta el flujo completo: client → normalizer → repository → filesystem.
      Único punto de entrada desde los endpoints FastAPI.
      Registra IngestionRun en DB con estado completed/failed.

errors.py
  └── Excepciones específicas del proveedor.
      Permite que el endpoint maneje errores de forma granular.
```

**Principio clave:** FastAPI nunca llama directamente a `client.py`. Solo llama a `service.py`. Esto permite reemplazar cualquier proveedor externo modificando únicamente `client.py` (y `normalizer.py` si existe) sin tocar la API ni el resto del sistema.

## Estrategia de CRS


| Capa                     | CRS                       | Motivo                                              |
| ------------------------ | ------------------------- | --------------------------------------------------- |
| Ingesta y almacenamiento | EPSG:4326 (WGS84)         | Geometrías PostGIS, respuestas API, fuentes nativas |
| Procesamiento ELMFIRE    | EPSG:32719 (UTM Zone 19S) | ELMFIRE requiere proyección métrica                 |
| Resolución               | 30 m                      | Resolución nativa del DEM Copernicus GLO-30         |


Todos los rasters de entrada a ELMFIRE deben compartir CRS, resolución y extent exactos. `elmfire/builder/raster_aligner.py` enforces este alineamiento vía `gdalwarp`.

## Estrategia de persistencia: Filesystem

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
│   └── fbfm40_los_alerces.tif
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

## Principios aplicados en todo el proyecto

- **Type hints obligatorios:** todo `def` y `async def` tiene anotaciones de retorno e inputs.
- **Pydantic v2 models:** schemas de validación en todas las capas que cruzan datos externos.
- **Logging estructurado:** usar `structlog` o el `logging` estándar con formato JSON en producción. Nunca `print()`.
- **Sin credenciales en código:** siempre desde `settings.variable`. Cualquier hardcode es un bug.
- **Errores explícitos:** cada módulo tiene su propio `errors.py`. Los endpoints capturan excepciones específicas y devuelven HTTP apropiado (400, 404, 502, 503).
- **Separación de capas:** FastAPI → `service.py` → `client.py` + `repository.py`. Nunca saltar capas.
- **uv** sobre Poetry: resolución más rápida, sin dependencias externas, PEP 517.
- **asyncpg + SQLAlchemy async**: acceso no bloqueante a la DB para FastAPI.
- **GeoAlchemy2**: columnas de geometría PostGIS con ORM type-safe en Python.
- **asyncio.to_thread** en servicios de ingesta: las operaciones de descarga (herbie, httpx, rasterio) son síncronas; se corren en un thread pool para no bloquear el event loop y permitir `asyncio.gather` en el endpoint `/ingestion/run`.
- **Ingesta idempotente**: re-ejecutar la misma ingesta no crea duplicados. Para datos estáticos (DEM, WorldCover) se verifica el `RasterAsset` existente antes de descargar.

