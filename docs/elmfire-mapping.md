# ELMFIRE Input Mapping

## Source → ELMFIRE input table

| Source                  | Raw data                    | Derivación                        | ELMFIRE input                          | Módulo                              | Estado  |
|-------------------------|-----------------------------|-----------------------------------|----------------------------------------|-------------------------------------|---------|
| NASA FIRMS VIIRS        | CSV focos → FireDetection DB | buffer + SDF (ignition_builder)   | `PHI_FILENAME` + `ignicion.shp`        | ingestion/satellite/firms + elmfire/builder/ignition_builder | ✅ |
| OpenTopography COP30    | dem_cop30_raw.tif (4326)    | reproject + clip (raster_aligner) | `DEM_FILENAME` → dem.tif              | ingestion/topography/opentopography + elmfire/builder/raster_aligner | ✅ |
| Derivado DEM            | dem.tif                     | gradient numpy (raster_aligner)   | `SLOPE_FILENAME` → slp.tif            | elmfire/builder/raster_aligner      | ✅ |
| Derivado DEM            | dem.tif                     | gradient numpy (raster_aligner)   | `ASPECT_FILENAME` → asp.tif           | elmfire/builder/raster_aligner      | ✅ |
| NOAA GFS (Herbie)       | gfs_u10.tif + gfs_v10.tif   | sqrt(u²+v²) / atan2 (weather_builder) | `WS_FILENAME`, `WD_FILENAME`      | elmfire/builder/weather_builder     | ✅ |
| NOAA GFS (Herbie)       | gfs_t2m.tif + gfs_rh.tif   | Nelson 1984 EMC (weather_builder) | `M1_FILENAME`, `M10_FILENAME`, `M100_FILENAME` | elmfire/builder/weather_builder | ✅ |
| ESA WorldCover          | worldcover_raw.tif          | crosswalk Scott & Burgan (fuels_builder) | `FUEL_MODEL_FILENAME` → fbfm40.tif | elmfire/builder/fuels_builder    | ✅ |
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

### Ignición (`ignition_builder.py`)
1. Buffer shapely de 90 m sobre cada punto FIRMS (proyectados a EPSG:32719).
2. Rasterizar polígono de ignición al grid de referencia.
3. Función de distancia con signo L1 (4-pass sweep, numpy): `phi < 0` dentro del perímetro, `phi > 0` fuera.

## Raster alignment constraint

Todos los rasters de entrada a ELMFIRE deben compartir:
- CRS: `EPSG:32719` (UTM Zone 19S)
- Resolution: `30 m`
- Extent: bbox exacto del AOI

`raster_aligner.align_raster()` y las funciones de weather/fuels builder usan `rasterio.warp.reproject` para garantizar este alineamiento.

## elmfire.data — formato generado por `namelist_writer.py`

```fortran
&INPUTS
  FUELS_AND_TOPOGRAPHY_DIRECTORY = '/app/data/elmfire/inputs/{prep_id}/'
  WEATHER_DIRECTORY               = '/app/data/elmfire/inputs/{prep_id}/'
  DEM_FILENAME                    = 'dem.tif'
  SLOPE_FILENAME                  = 'slp.tif'
  ASPECT_FILENAME                 = 'asp.tif'
  FUEL_MODEL_FILENAME             = 'fbfm40.tif'
  CC_FILENAME                     = 'cc.tif'
  CH_FILENAME                     = 'ch.tif'
  CBH_FILENAME                    = 'cbh.tif'
  CBD_FILENAME                    = 'cbd.tif'
  WS_FILENAME                     = 'ws.tif'
  WD_FILENAME                     = 'wd.tif'
  M1_FILENAME                     = 'm1.tif'
  M10_FILENAME                    = 'm10.tif'
  M100_FILENAME                   = 'm100.tif'
  PHI_FILENAME                    = 'phi.tif'
  IGNITION_RADIUS                 = 45.0
  A_SRS                           = 'EPSG:32719'
  XLLCORNER                       = {utm_west}
  YLLCORNER                       = {utm_south}
  XURCORNER                       = {utm_east}
  YURCORNER                       = {utm_north}
  CELLSIZE                        = 30.0
/

&OUTPUTS
  DTDUMP                          = 3600.0
  DUMP_NEWBURNS_ONLY              = F
  OUTPUTS_DIRECTORY               = '/app/data/elmfire/outputs/{sim_id}/'
  CHECK_OUTPUTS_DIRECTORY_EXISTS  = F
  CONVERT_TO_GEOTIFF              = T
  CONVERT_TIMINGS                 = T
  SAVE_ISOCHRONES                 = T
/

&TIME_CONTROL
  SIMULATION_DT                   = 30.0
  SIMULATION_DTMAX                = 300.0
  PRINT_SIMULATION_CLOCK          = T
  SIMULATION_TSTOP                = 43200.0    ! horizon_hours × 3600
/

&MISCELLANEOUS
  PATH_TO_GDAL                    = '/usr/bin/'
  SCRATCH_PATH                    = '/tmp/'
/
```

El dominio (XLLCORNER, YLLCORNER, XURCORNER, YURCORNER, CELLSIZE) se lee automáticamente de `dem.tif` al escribir el namelist. `SIMULATION_TSTOP` se calcula como `horizon_hours × 3600` desde el parámetro de `POST /simulations/run`.
