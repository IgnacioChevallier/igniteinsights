# ELMFIRE Input Mapping

## Source → ELMFIRE input table

| Source                  | Raw data                    | Derivación                        | ELMFIRE input                          | Módulo                              | Estado  |
|-------------------------|-----------------------------|-----------------------------------|----------------------------------------|-------------------------------------|---------|
| NASA FIRMS VIIRS        | CSV focos → FireDetection DB | buffer + SDF (ignition_builder)   | `PHI_FILENAME` + `ignicion.shp`        | ingestion/satellite/firms + elmfire/builder/ignition_builder | ✅ |
| OpenTopography COP30    | dem_cop30_raw.tif (4326)    | reproject + clip (raster_aligner) | `DEM_FILENAME` → dem.tif              | ingestion/topography/opentopography + elmfire/builder/raster_aligner | ✅ |
| Derivado DEM            | dem.tif                     | gradient numpy (raster_aligner)   | `SLP_FILENAME` → slp.tif              | elmfire/builder/raster_aligner      | ✅ |
| Derivado DEM            | dem.tif                     | gradient numpy (raster_aligner)   | `ASP_FILENAME` → asp.tif              | elmfire/builder/raster_aligner      | ✅ |
| NOAA GFS (Herbie)       | gfs_u10.tif + gfs_v10.tif   | sqrt(u²+v²) / atan2 (weather_builder) | `WS_FILENAME`, `WD_FILENAME`      | elmfire/builder/weather_builder     | ✅ |
| NOAA GFS (Herbie)       | gfs_t2m.tif + gfs_rh.tif   | Nelson 1984 EMC (weather_builder) | `M1_FILENAME`, `M10_FILENAME`, `M100_FILENAME` | elmfire/builder/weather_builder | ✅ |
| ESA WorldCover          | worldcover_raw.tif          | crosswalk Scott & Burgan (fuels_builder) | `FBFM_FILENAME` → fbfm40.tif       | elmfire/builder/fuels_builder    | ✅ |
| Hansen GFC v1.11        | hansen_treecover2000.tif (4326) | scale ×0.01 + reproject (canopy_builder) | `CC_FILENAME` → cc.tif        | ingestion/canopy + elmfire/builder/canopy_builder | ✅ |
| ETH Canopy Height 2020  | eth_canopy_height.tif (4326)    | reproject bilinear (canopy_builder)      | `CH_FILENAME` → ch.tif        | ingestion/canopy + elmfire/builder/canopy_builder | ✅ |
| Scott & Reinhardt (2005) | fbfm40.tif                     | lookup table (canopy_builder)            | `CBH_FILENAME`, `CBD_FILENAME` | elmfire/builder/canopy_builder                   | ✅ |

## Derivaciones implementadas

### Topografía (`raster_aligner.py`)
- **DEM**: reproyección bilinear EPSG:4326 → EPSG:32719 a 30 m vía rasterio warp.
- **Slope**: `arctan(sqrt((dz/dx)² + (dz/dy)²))` en grados, con diferencias centrales numpy.
- **Aspect**: `90° - atan2(-dz/dy, dz/dx)` en grados desde el norte (0=N, 90=E), convención brújula.
- Los derivados se cachean en `data/static/` y se reutilizan mientras el DEM no cambie.

### Viento (`weather_builder.py`)
- **ws.tif** (km/h): `sqrt(u10² + v10²) × 3.6`
- **wd.tif** (grados desde N, convención meteorológica de procedencia): `atan2(-u10, -v10)`

### Humedad de combustible (`weather_builder.py`)
Modelo Nelson (1984) para equilibrium moisture content (EMC) a partir de temperatura (Kelvin → Fahrenheit) y humedad relativa (%):
- `m1.tif` ≈ EMC
- `m10.tif` ≈ EMC + 2%
- `m100.tif` ≈ EMC + 5%

### Combustibles (`fuels_builder.py`)
Crosswalk WorldCover v2.0 → Scott & Burgan FBFM40 para Patagonia:

| WorldCover clase | Descripción        | FBFM40 |
|------------------|--------------------|--------|
| 10               | Tree cover         | 183 (TL3) |
| 20               | Shrubland          | 145 (SH5) |
| 30               | Grassland          | 102 (GR2) |
| 40               | Cropland           | 101 (GR1) |
| 50               | Built-up           | 91 (NB1)  |
| 60               | Bare/sparse veg    | 93 (NB3)  |
| 80               | Permanent water    | 98 (NB8)  |
| 90               | Herbaceous wetland | 103 (GR3) |

### Cobertura de canopy (`canopy_builder.py`)
- **cc.tif** (fracción 0–1): `reproject_canopy(hansen_treecover2000.tif, scale_factor=0.01)` — bilinear, EPSG:32719 30 m.
- **ch.tif** (metros): `reproject_canopy(eth_canopy_height.tif)` — bilinear, EPSG:32719 30 m.
- **cbh.tif** (metros) + **cbd.tif** (kg/m³): `derive_cbh_cbd(fbfm40.tif)` — lookup table Scott & Reinhardt (2005) por código FBFM40.

### Ignición (`ignition_builder.py` + `perimeter_reconstruction.py`)
1. Reconstrucción de perímetro por evento (`perimeter_reconstruction.reconstruct_burn_polygon`,
   puntos FIRMS proyectados a EPSG:32719): dedup (~10 m) → clustering single-linkage
   (eps 1500 m) → concave hull por cluster (ratio 0.4) con padding de 187.5 m
   (media huella VIIRS); clusters de <4 puntos quedan como buffers de 375 m por punto
   (spot fires).
2. Rasterizar el (Multi)Polygon de ignición al grid de referencia.
3. Función de distancia con signo L1 (4-pass sweep, numpy): `phi < 0` dentro del perímetro, `phi > 0` fuera (clamp interior a -1.0 por el reset `PHI0 < -1.1` de ELMFIRE).

## Raster alignment constraint

Todos los rasters de entrada a ELMFIRE deben compartir:
- CRS: `EPSG:32719` (UTM Zone 19S)
- Resolution: `30 m`
- Extent: bbox exacto del AOI

`raster_aligner.align_raster()` y las funciones de weather/fuels builder usan `rasterio.warp.reproject` para garantizar este alineamiento.

## elmfire.data — formato generado por `namelist_writer.py`

> Este bloque se transcribe directamente de `write_namelist()` en
> `app/elmfire/builder/namelist_writer.py`. Para gotchas de interfaz (unidades,
> convenciones de nombres, diferencias con el mode `MODE=2`, etc.) ver
> `.claude/skills/elmfire/references/`.

```fortran
&INPUTS
  FUELS_AND_TOPOGRAPHY_DIRECTORY = '/app/data/elmfire/inputs/{prep_id}/'
  WEATHER_DIRECTORY               = '/app/data/elmfire/inputs/{prep_id}/'
  DEM_FILENAME                    = 'dem'
  SLP_FILENAME                    = 'slp'
  ASP_FILENAME                    = 'asp'
  FBFM_FILENAME                   = 'fbfm40'
  CC_FILENAME                     = 'cc'
  CH_FILENAME                     = 'ch'
  CBH_FILENAME                    = 'cbh'
  CBD_FILENAME                    = 'cbd'
  WS_FILENAME                     = 'ws'
  WD_FILENAME                     = 'wd'
  M1_FILENAME                     = 'm1'
  M10_FILENAME                    = 'm10'
  M100_FILENAME                   = 'm100'
  ADJ_FILENAME                    = 'adj'
  PHI_FILENAME                    = 'phi'
  DT_METEOROLOGY                  = 3600.0
/

&COMPUTATIONAL_DOMAIN
  A_SRS                           = 'EPSG:32719'
  COMPUTATIONAL_DOMAIN_XLLCORNER  = {utm_west}
  COMPUTATIONAL_DOMAIN_YLLCORNER  = {utm_south}
  COMPUTATIONAL_DOMAIN_CELLSIZE   = {cell_size}
/

&OUTPUTS
  DTDUMP                          = 3600.0    ! clamped to tstop_s/2 if >= tstop_s, see resolve_dtdump_s()
  OUTPUTS_DIRECTORY               = '/app/data/elmfire/outputs/{sim_id}/'
  CONVERT_TO_GEOTIFF              = T
  DUMP_TIME_OF_ARRIVAL            = T
  DUMP_FLIN                       = T
  DUMP_SPREAD_RATE                = T
/

&TIME_CONTROL
  SIMULATION_TSTART               = 0.0
  SIMULATION_DT                   = 30.0
  SIMULATION_DTMAX                = 300.0
  SIMULATION_TSTOP                = 43200.0    ! horizon_hours × 3600
/

&SIMULATOR
  MODE                            = 1
/

&MISCELLANEOUS
  PATH_TO_GDAL                    = '/usr/bin/'
  SCRATCH                         = '/tmp/'
/
```

Los nombres de raster son **basenames sin extensión** (`'dem'`, no `'dem.tif'`) —
ELMFIRE agrega `.tif` internamente; los archivos en disco sí son `.tif`. El dominio
(XLLCORNER, YLLCORNER, CELLSIZE — sin esquina superior derecha, ELMFIRE la deriva del
raster) y el CRS (`A_SRS`) se leen automáticamente de `dem.tif` al escribir el namelist.
`SIMULATION_TSTOP` se calcula como `SIMULATION_TSTART + horizon_hours × 3600` desde el
parámetro de `POST /simulations/run`; el modo 1 configura una simulación transitoria.

**Isócronas:** no existe ningún flag `SAVE_ISOCHRONES`/`DUMP_ISOCHRONE_SHAPEFILES` en
ELMFIRE (no aparece en ninguna parte de su código fuente,
github.com/lautenberger/elmfire). Los shapefiles de isócronas se generan como
**post-procesamiento externo** — `elmfire-runner/app/runner.py` ejecuta
`gdal_contour -i <DTDUMP> time_of_arrival_*.tif hourly_isochrones.shp` después de que
ELMFIRE termina exitosamente. Nombres reales de salida: `time_of_arrival_*.tif` (no
`toa_*.tif`), `flin_*.tif`, `vs_*.tif` (spread rate, no `spread_rate_*.tif`).
