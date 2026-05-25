# Data Sources

## NASA FIRMS — VIIRS NOAA-20 NRT


| Field       | Value                                                                                          |
| ----------- | ---------------------------------------------------------------------------------------------- |
| URL         | `https://firms.modaps.eosdis.nasa.gov/api/`                                                    |
| Endpoint    | `GET /area/csv/{MAP_KEY}/VIIRS_NOAA20_NRT/{bbox}/{day_range}`                                  |
| Auth        | MAP_KEY in URL path. Register free at firms.modaps.eosdis.nasa.gov/api/map_key/                |
| Response    | CSV: latitude, longitude, bright_ti4, frp, confidence, acq_date, acq_time, satellite, daynight |
| Rate limit  | 5,000 transactions / 10 minutes                                                                |
| NRT latency | ~3 hours after satellite pass                                                                  |
| Confidence  | Use `n` (nominal) and `h` (high) only — discard `l` (low)                                      |
| Update freq | Every orbit (~12h for NOAA-20)                                                                 |


```bash
curl "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{KEY}/VIIRS_NOAA20_NRT/-72,-42.9,-71.5,-42.5/1"
```

## OpenTopography — Copernicus GLO-30


| Field       | Value                                                                              |
| ----------- | ---------------------------------------------------------------------------------- |
| URL         | `https://portal.opentopography.org/API/globaldem`                                  |
| Params      | `demtype=COP30`, `south`, `north`, `west`, `east`, `outputFormat=GTiff`, `API_Key` |
| Auth        | API Key in query string. Register free at portal.opentopography.org                |
| Response    | GeoTIFF binary (direct download)                                                   |
| Output file | `data/static/opentopography/{YYYY-MM-DD}/dem_cop30_raw.tif`                        |
| CRS         | EPSG:4326 — reprojected to EPSG:32719 by `raster_aligner.reproject_and_derive_topo()` |
| Resolution  | ~30 m (1 arc-second)                                                               |
| Static data | Terrain does not change — excluded from `/ingestion/run` by default (`include_dem: false`). Pass `true` to refresh. |


```bash
curl -o dem_raw.tif "https://portal.opentopography.org/API/globaldem?demtype=COP30&south=-42.9&north=-42.5&west=-72&east=-71.5&outputFormat=GTiff&API_Key={KEY}"
# Verify: gdalinfo dem_raw.tif
```

## NOAA GFS — Global Forecast System 0.25°

| Field        | Value                                                                                     |
| ------------ | ----------------------------------------------------------------------------------------- |
| Access       | NOMADS HTTPS + public S3 (`noaa-gfs-bdp-pds`), via `herbie-data` library                 |
| Product      | `pgrb2.0p25` — 0.25° (~28 km) global grid, forecast hour `f000`                          |
| Cycle        | 00z / 06z / 12z / 18z UTC — module resolves most-recent available cycle automatically    |
| Variables    | U-wind 10 m (`UGRD`), V-wind 10 m (`VGRD`), Temperature 2 m (`TMP`), RH 2 m (`RH`)      |
| Output files | `data/raw/gfs/{YYYY-MM-DD}/{cycle}_{var}.tif` — one GeoTIFF per variable                 |
| Asset types  | `gfs_u10`, `gfs_v10`, `gfs_t2m`, `gfs_rh`                                                |
| CRS          | EPSG:4326 (native GFS grid, clipped to AOI bbox)                                         |
| Auth         | None — public NOMADS/S3                                                                   |
| Downstream   | `ws.tif`/`wd.tif` via `weather_builder.derive_wind()`; `m1/m10/m100.tif` via `weather_builder.derive_moisture()` (Nelson 1984 EMC) |

```bash
# Trigger ingestion
curl -X POST http://localhost:8000/api/v1/ingestion/gfs/run

# Check result
curl http://localhost:8000/api/v1/ingestion/runs/{run_id}
```

**Cycle resolution logic:** tries cycles 18z → 12z → 06z → 00z for today, then yesterday, until a published cycle is found on NOMADS. GFS data is typically available ~4 hours after cycle time.

## ESA WorldCover — 10 m Land Cover v2.0

| Field        | Value                                                                                              |
| ------------ | -------------------------------------------------------------------------------------------------- |
| URL          | `https://esa-worldcover.s3.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif` |
| Access       | Public S3 — Cloud-Optimized GeoTIFF (COG); only the bbox window is fetched                        |
| Version      | v2.0 (2021)                                                                                        |
| Resolution   | 10 m                                                                                               |
| Tile grid    | 3° × 3° tiles named `{N\|S}{lat:02d}{E\|W}{lon:03d}` (lower-left corner, floored to 3°)           |
| AOI tiles    | S45W072 (single tile for Los Alerces bbox)                                                         |
| Output file  | `data/static/worldcover/{YYYY-MM-DD}/esa_worldcover_v200_10m.tif`                                  |
| Asset type   | `worldcover_raw`                                                                                   |
| CRS          | EPSG:4326 (native)                                                                                 |
| Auth         | None — public S3                                                                                   |
| Static data  | Land cover does not change between runs — excluded from `/ingestion/run` by default (`include_worldcover: false`). Pass `true` to refresh. |
| Downstream   | Crosswalk to FBFM40 via `fuels_builder.worldcover_to_fbfm40()` — result cached in `data/static/fbfm40.tif` |

```bash
# Trigger ingestion (idempotent)
curl -X POST http://localhost:8000/api/v1/ingestion/worldcover/run
```

**Tile selection:** the client computes which 3°×3° tiles intersect the configured AOI bbox, opens each as a COG via rasterio (reads only the relevant window — no full-tile download), merges if >1 tile, and writes a single clipped GeoTIFF with embedded provenance tags (`source`, `version`, `acquisition_year`, `source_tiles`).

## Hansen Global Forest Change v1.11 — treecover2000

| Field        | Value                                                                                             |
| ------------ | ------------------------------------------------------------------------------------------------- |
| URL          | `https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/Hansen_GFC-2023-v1.11_treecover2000_{lat}_{lon}.tif` |
| Access       | Public GCS — Cloud-Optimized GeoTIFF; downloaded with httpx, then windowed with rasterio         |
| Tile grid    | 10°×10° tiles named by NW (upper-left) corner: `{N\|S}{lat:02d}_{E\|W}{lon:03d}`                |
| AOI tile     | 40S\_080W (covers lat -40→-50, lon -70→-80)                                                      |
| Output file  | `data/static/canopy/{YYYY-MM-DD}/hansen_treecover2000.tif`                                       |
| Asset type   | `canopy_cc`                                                                                       |
| Units        | Percent 0–100 → converted to fraction 0–1 by `canopy_builder.reproject_canopy(scale_factor=0.01)` |
| Resolution   | 30 m                                                                                              |
| CRS          | EPSG:4326 (native)                                                                                |
| Auth         | None — public GCS                                                                                 |
| Static data  | Excluded from `/ingestion/run` by default (`include_canopy: false`). Pass `true` to download.    |
| Downstream   | `cc.tif` via `canopy_builder.reproject_canopy()`                                                 |

## ETH Global Canopy Height 2020 — Lang et al.

| Field        | Value                                                                                             |
| ------------ | ------------------------------------------------------------------------------------------------- |
| URL          | `https://libdrive.ethz.ch/index.php/s/cO8or7iOe5dT2Rt/download?path=%2F3deg_cogs%2FETH_GlobalCanopyHeight_10m_2020_{tile}_Map.tif` |
| Access       | Public libdrive — COG; downloaded with httpx, windowed with rasterio                             |
| Tile grid    | 3°×3° tiles named by SW (lower-left) corner: `{N\|S}{lat:02d}{E\|W}{lon:03d}` (same as WorldCover) |
| AOI tile     | S45W072                                                                                           |
| Output file  | `data/static/canopy/{YYYY-MM-DD}/eth_canopy_height.tif`                                          |
| Asset type   | `canopy_ch`                                                                                       |
| Units        | Metres (float32)                                                                                  |
| Resolution   | 10 m → reprojected to 30 m by `canopy_builder.reproject_canopy()`                               |
| CRS          | EPSG:4326 (native)                                                                                |
| Auth         | None — public                                                                                     |
| Static data  | Excluded from `/ingestion/run` by default (`include_canopy: false`). Pass `true` to download.    |
| Downstream   | `ch.tif` via `canopy_builder.reproject_canopy()`                                                 |

## Canopy Base Height + Bulk Density (derived, no download)

| Layer   | Source                | Derivation                                                   |
| ------- | --------------------- | ------------------------------------------------------------ |
| `cbh.tif` | `fbfm40.tif`        | Lookup table `_FBFM40_CBH` — Scott & Reinhardt (2005)        |
| `cbd.tif` | `fbfm40.tif`        | Lookup table `_FBFM40_CBD` — Scott & Reinhardt (2005)        |

No additional download is required. Both are derived in the preparation step via `canopy_builder.derive_cbh_cbd()` from the `fbfm40.tif` already present in the ELMFIRE inputs folder.


