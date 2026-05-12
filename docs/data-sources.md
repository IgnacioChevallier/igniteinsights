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
| CRS         | EPSG:4326 — reproject to EPSG:32719 for ELMFIRE processing                         |
| Resolution  | ~30 m (1 arc-second)                                                               |
| Static data | Terrain does not change — download once, reuse indefinitely                        |


```bash
curl -o dem_raw.tif "https://portal.opentopography.org/API/globaldem?demtype=COP30&south=-42.9&north=-42.5&west=-72&east=-71.5&outputFormat=GTiff&API_Key={KEY}"
# Verify: gdalinfo dem_raw.tif
```

## Future sources (sprints 2+)


| Source               | Data                  | Sprint           |
| -------------------- | --------------------- | ---------------- |
| NOAA GFS (Herbie)    | ws, wd, m1, m10, m100 | Hito 3 siguiente |
| ESA WorldCover (GEE) | fbfm40                | Hito 4           |
| GEDI L2B + ETH (GEE) | cc, ch, cbh, cbd      | Hito 4           |


