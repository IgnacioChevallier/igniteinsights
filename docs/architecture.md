# Architecture

## Pipeline layers

```
1. Detection     satellite/firms        → FireDetection (PostGIS Point)
2. Enrichment    topography/            → dem.tif, slp.tif, asp.tif
                 meteorology/           → ws.tif, wd.tif, m1.tif...
                 fuels/                 → fbfm40.tif
                 canopy/                → cc.tif, ch.tif, cbh.tif, cbd.tif
3. Construction  elmfire/builder/       → elmfire.data + aligned rasters
4. Simulation    elmfire/runner/        → HTTP POST to elmfire-runner microservice
5. Visualization postprocessing/        → GeoJSON isochrones served via API
```

## Service boundary

```
ignisight-api  ──HTTP POST /simulate──▶  elmfire-runner (separate process)
               ◀─────────── result ──────
```

Both services share a Docker volume at `/app/data/elmfire/`.

## CRS strategy

- Ingestion & storage: EPSG:4326 (WGS84) — PostGIS geometries, API responses
- Processing: EPSG:32719 (UTM Zone 19S) — all rasters for ELMFIRE must use this CRS
- Resolution: 30 m (Copernicus GLO-30 native resolution)

## Key design decisions

- **uv** over Poetry: faster resolution, zero external dependencies, PEP 517 compliant.
- **asyncpg + SQLAlchemy async**: non-blocking DB access for FastAPI.
- **GeoAlchemy2**: PostGIS geometry columns with type-safe Python ORM.
- **Layered ingestion** (client → normalizer → service): any data source can be swapped
  by modifying only `client.py` and `normalizer.py` without touching the API.
