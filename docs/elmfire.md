# Mapeo de insumos ELMFIRE

## Fuente → insumo ELMFIRE

| Fuente                  | Datos originales            | Derivación                        | Insumo ELMFIRE                          | Módulo                              | Estado  |
|-------------------------|-----------------------------|-----------------------------------|----------------------------------------|-------------------------------------|---------|
| NASA FIRMS VIIRS        | CSV focos → `FireDetection` | margen + SDF (`ignition_builder`) | `PHI_FILENAME` + `ignicion.shp`        | ingestion/satellite/firms + elmfire/builder/ignition_builder | ✅ |
| OpenTopography COP30    | dem_cop30_raw.tif (4326)    | reproyección + recorte | `DEM_FILENAME` → dem.tif              | ingestion/topography/opentopography + elmfire/builder/raster_aligner | ✅ |
| Derivado DEM            | dem.tif                     | gradiente NumPy (`raster_aligner`) | `SLP_FILENAME` → slp.tif              | elmfire/builder/raster_aligner      | ✅ |
| Derivado DEM            | dem.tif                     | gradiente NumPy (`raster_aligner`) | `ASP_FILENAME` → asp.tif              | elmfire/builder/raster_aligner      | ✅ |
| NOAA GFS (Herbie)       | gfs_u10.tif + gfs_v10.tif   | sqrt(u²+v²) / atan2 (weather_builder) | `WS_FILENAME`, `WD_FILENAME`      | elmfire/builder/weather_builder     | ✅ |
| NOAA GFS (Herbie)       | gfs_t2m.tif + gfs_rh.tif   | Nelson 1984 EMC (weather_builder) | `M1_FILENAME`, `M10_FILENAME`, `M100_FILENAME` | elmfire/builder/weather_builder | ✅ |
| ESA WorldCover          | worldcover_raw.tif          | tabla Scott & Burgan (`fuels_builder`) | `FBFM_FILENAME` → fbfm40.tif       | elmfire/builder/fuels_builder    | ✅ |
| Hansen GFC v1.11        | hansen_treecover2000.tif (4326) | reproyección bilineal, % 0–100 sin escalar | `CC_FILENAME` → cc.tif        | ingestion/canopy + elmfire/builder/canopy_builder | ✅ |
| ETH Canopy Height 2020  | eth_canopy_height.tif (4326)    | reproyección bilineal + ×10 (Int16) | `CH_FILENAME` → ch.tif        | ingestion/canopy + elmfire/builder/canopy_builder | ✅ |
| Hansen GFC + ETH Canopy Height | cc.tif + ch.tif (+ fbfm40.tif, Hansen lossyear) | CH × f(CC); CBH por tipo de bosque de literatura y CBD del pino donde hay copa; sin dosel en la pérdida de Hansen anterior al año del incendio (canopy_builder) | `CBH_FILENAME`, `CBD_FILENAME` (y `cc`/`ch` en 0 en la pérdida) | elmfire/builder/canopy_builder | ✅ |
| Hansen GFC v1.13 `lossyear` | Hansen_GFC-2025-v1.13_lossyear_40S_080W.tif (4326) | reproyección por vecino más cercano | sólo para anular el dosel | preparation/service + canopy_builder | ✅ |

## Derivaciones implementadas

### Topografía (`raster_aligner.py`)
- **DEM**: reproyección bilinear EPSG:4326 → EPSG:32719 a 30 m vía rasterio warp.
- **Pendiente:** `arctan(sqrt((dz/dx)² + (dz/dy)²))` en grados, con diferencias centrales NumPy.
- **Orientación:** `90° - atan2(-dz/dy, dz/dx)` en grados desde el norte.
- Los derivados se guardan en `data/static/` y se reutilizan mientras el DEM no cambie.

### Viento (`weather_builder.py`)
- **ws.tif** (mph, Float32, **multibanda — una banda por hora de pronóstico**):
  `sqrt(u10² + v10²) × f_20ft × 2.23694`, donde `f_20ft ≈ 0.870` convierte el viento
  GFS de 10 m al viento a **20 pies (6.096 m)** que ELMFIRE espera, vía perfil
  logarítmico `ln(z/z0)/ln(z_ref/z0)` con `z0 = 0.22 m` (`wind_height_factor()`).
- **wd.tif** (grados desde N, convención meteorológica de procedencia, Float32
  multibanda): `atan2(-u10, -v10)` — la conversión de altura sólo escala la magnitud.

### Humedad de combustible (`weather_builder.py`)
Modelo Nelson (1984) para contenido de humedad de equilibrio (EMC) a partir de temperatura
(Kelvin → Fahrenheit) y humedad relativa (%). Float32, **multibanda**:
- `m1.tif` ≈ EMC
- `m10.tif` ≈ EMC + 2%
- `m100.tif` ≈ EMC + 5%

⚠️ Los incrementos +2/+5 no tienen base física: las clases de retardo se amortiguan hacia
una media móvil, no son un incremento fijo del equilibrio instantáneo. Corregirlo requiere
historial de secado (varios días de GFS previos) que la ingesta no conserva hoy.

**Bandas = serie temporal.** ELMFIRE lee la banda *n* como el clima en `n × DT_METEOROLOGY`
(tiempo absoluto: la banda 0 es T = 0, y `SIMULATION_TSTART` se mide desde ella) e interpola
entre bandas, **siempre que `&MONTE_CARLO NUM_METEOROLOGY_TIMES` declare cuántas hay**: con el
valor por defecto (1) usa la banda 0 toda la corrida (docs/resultados/modelo/auditoria.md, hallazgo 1).
`write_namelist()` lo escribe con las bandas de `ws.tif`. Un ráster de una sola banda
congela el clima durante toda la simulación (sin ciclo diurno).
`namelist_writer.validate_weather_coverage()` falla si las bandas no cubren el horizonte.

### Combustibles (`fuels_builder.py`)
Tabla WorldCover v2.0 → Scott & Burgan FBFM40 para Patagonia:

| WorldCover clase | Descripción        | FBFM40 |
|------------------|--------------------|--------|
| 10               | Cobertura arbórea  | 183 (TL3) |
| 20               | Arbustal           | 145 (SH5) |
| 30               | Pastizal           | 102 (GR2) |
| 40               | Cultivo            | 101 (GR1) |
| 50               | Construido         | 91 (NB1)  |
| 60               | Vegetación rala    | 93 (NB3)  |
| 70               | Nieve y hielo      | 93 (NB3)  |
| 80               | Agua permanente    | 98 (NB8)  |
| 90               | Humedal herbáceo   | 103 (GR3) |
| 95               | Manglar            | 183 (TL3) |
| 100              | Musgo y liquen     | 101 (GR1) |

### Dosel (`canopy_builder.py`)
Codificación Int16 compatible con las convenciones de LANDFIRE:
- **cc.tif** (porcentaje **0–100**, sin escalado): `reproject_canopy(hansen_treecover2000.tif)`
  con `scale_factor=1.0` — bilinear, EPSG:32719 30 m.
- **ch.tif** (**10×metros**): `reproject_canopy(eth_canopy_height.tif, scale_factor=10.0)`.
- **cbh.tif** (**10×metros**) + **cbd.tif** (**100×kg/m³**): `derive_cbh_cbd(cc.tif, ch.tif)` —
  derivación estructural desde cobertura y altura de dosel medidas, con los valores
  pre-escalados a la codificación Int16 de ELMFIRE. Ver `docs/arquitectura.md` §A4.

### Ignición (`ignition_builder.py` + `perimeter_reconstruction.py`)
1. Reconstrucción de perímetro por evento (`perimeter_reconstruction.reconstruct_burn_polygon`,
   puntos FIRMS proyectados a EPSG:32719): eliminación de duplicados (~10 m) → agrupamiento por
   enlace simple (1.500 m) → envolvente cóncava por grupo con margen de 187,5 m. Los grupos de
   menos de cuatro puntos quedan como círculos de 375 m por punto.
2. Rasterizar el polígono de ignición sobre la grilla de referencia.
3. Calcular la distancia con signo L1 mediante un barrido NumPy de cuatro pasadas: `phi < 0`
   dentro del perímetro y `phi > 0` fuera.

## Restricción de alineación de rásteres

Todos los rasters de entrada a ELMFIRE deben compartir:
- CRS: `EPSG:32719` (UTM zona 19S)
- Resolución: `30 m`
- Extensión: caja exacta del AOI

`raster_aligner.align_raster()` y los generadores de meteorología y combustibles usan
`rasterio.warp.reproject` para garantizar este alineamiento.

## elmfire.data — formato generado por `namelist_writer.py`

> Este bloque se transcribe directamente de `write_namelist()` en
> `app/elmfire/builder/namelist_writer.py`. Para particularidades de la interfaz —unidades,
> convenciones de nombres y diferencias con `MODE=2`— consultar
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

Los nombres de ráster son **nombres base sin extensión** (`'dem'`, no `'dem.tif'`) —
ELMFIRE agrega `.tif` internamente; los archivos en disco sí son `.tif`. El dominio
(XLLCORNER, YLLCORNER, CELLSIZE — sin esquina superior derecha, ELMFIRE la deriva del
ráster) y el CRS (`A_SRS`) se leen automáticamente de `dem.tif` al escribir el namelist.
`SIMULATION_TSTOP` se calcula como `SIMULATION_TSTART + horizon_hours × 3600` desde el
parámetro de `POST /simulations/run`; el modo 1 configura una simulación transitoria.

**Isócronas:** no existe ningún flag `SAVE_ISOCHRONES`/`DUMP_ISOCHRONE_SHAPEFILES` en
ELMFIRE (no aparece en ninguna parte de su código fuente,
github.com/lautenberger/elmfire). Los shapefiles de isócronas se generan como
**posprocesamiento externo** — `elmfire-runner/app/runner.py` ejecuta
`gdal_contour -i <DTDUMP> time_of_arrival_*.tif hourly_isochrones.shp` después de que
ELMFIRE termina exitosamente. Nombres reales de salida: `time_of_arrival_*.tif` (no
`toa_*.tif`), `flin_*.tif`, `vs_*.tif` (spread rate, no `spread_rate_*.tif`).
