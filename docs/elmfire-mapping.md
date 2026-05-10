# ELMFIRE Input Mapping

## Source → ELMFIRE input table

| Source                  | Raw data           | Normalized          | ELMFIRE input                      | Module                     | Sprint  |
|-------------------------|--------------------|---------------------|------------------------------------|----------------------------|---------|
| NASA FIRMS VIIRS        | CSV focos          | FireDetection (PostGIS) | `phi.tif` / `ignicion.shp`    | satellite/firms + elmfire/builder/ignition_builder | Actual + sig. |
| OpenTopography COP30    | dem_raw.tif (4326) | dem.tif (32719, 30m) | `DEM_FILENAME`                    | topography/opentopography  | Actual  |
| Derivado DEM            | —                  | slp.tif             | `SLP_FILENAME`                     | elmfire/builder/raster_aligner | Siguiente |
| Derivado DEM            | —                  | asp.tif             | `ASP_FILENAME`                     | elmfire/builder/raster_aligner | Siguiente |
| NOAA GFS (Herbie)       | GRIB2/xarray       | ws.tif, wd.tif      | `WS_FILENAME`, `WD_FILENAME`       | meteorology/gfs            | Siguiente |
| ERA5-Land / GFS         | T2m, RH2m          | m1.tif, m10.tif, m100.tif | `M1_FILENAME`, etc.         | meteorology/gfs            | Siguiente |
| ESA WorldCover (GEE)    | GeoTIFF 11-class   | fbfm40.tif          | `FBFM_FILENAME`                    | fuels/worldcover           | Hito 4  |
| GEDI L2B (GEE)          | NetCDF frac.cover  | cc.tif              | `CC_FILENAME`                      | canopy/gedi                | Hito 4  |
| ETH Canopy Height (GEE) | GeoTIFF altura     | ch.tif              | `CH_FILENAME`                      | canopy/gedi                | Hito 4  |
| Tabla empírica + fbfm40 | —                  | cbh.tif, cbd.tif    | `CBH_FILENAME`, `CBD_FILENAME`     | canopy/gedi                | Hito 4  |
| Constante estacional    | —                  | config              | `LH_MOISTURE_CONTENT = 30.0`       | elmfire/builder/namelist_writer | Siguiente |

## Raster alignment constraint

All ELMFIRE input rasters **must** share:
- CRS: `EPSG:32719` (UTM Zone 19S)
- Resolution: `30 m`
- Extent: exact same bounding box

`elmfire/builder/raster_aligner.py` enforces alignment using `gdalwarp` before any simulation.

## elmfire.data structure (partial)

```fortran
&INPUTS
  DEM_FILENAME        = '/data/elmfire/inputs/{run_id}/dem.tif'
  SLP_FILENAME        = '/data/elmfire/inputs/{run_id}/slp.tif'
  ASP_FILENAME        = '/data/elmfire/inputs/{run_id}/asp.tif'
  FBFM_FILENAME       = '/data/elmfire/inputs/{run_id}/fbfm40.tif'
  CC_FILENAME         = '/data/elmfire/inputs/{run_id}/cc.tif'
  CH_FILENAME         = '/data/elmfire/inputs/{run_id}/ch.tif'
  CBH_FILENAME        = '/data/elmfire/inputs/{run_id}/cbh.tif'
  CBD_FILENAME        = '/data/elmfire/inputs/{run_id}/cbd.tif'
  WS_FILENAME         = '/data/elmfire/inputs/{run_id}/ws.tif'
  WD_FILENAME         = '/data/elmfire/inputs/{run_id}/wd.tif'
  M1_FILENAME         = '/data/elmfire/inputs/{run_id}/m1.tif'
  M10_FILENAME        = '/data/elmfire/inputs/{run_id}/m10.tif'
  M100_FILENAME       = '/data/elmfire/inputs/{run_id}/m100.tif'
  LH_MOISTURE_CONTENT = 30.0
  LW_MOISTURE_CONTENT = 60.0
  PHI_FILENAME        = '/data/elmfire/inputs/{run_id}/phi.tif'
/
```
