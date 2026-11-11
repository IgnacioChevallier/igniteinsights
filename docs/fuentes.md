# Fuentes de datos

## FIRMS — detecciones de incendios

| Campo | Valor |
|---|---|
| Proveedor | NASA FIRMS, VIIRS NOAA-20 |
| Acceso | `GET /area/csv/{MAP_KEY}/VIIRS_NOAA20_NRT/{bbox}/{day_range}` |
| Formato | CSV con posición, fecha, confianza, FRP y satélite |
| Filtro | confianza nominal (`n`) o alta (`h`) |
| Frecuencia | cada órbita, aproximadamente 12 h |
| Credencial | `FIRMS_MAP_KEY` |

La ingesta histórica combina las fuentes SP y NRT y elimina detecciones NRT ya cubiertas por SP.

## Copernicus DEM GLO-30

| Campo | Valor |
|---|---|
| Proveedor | OpenTopography |
| Resolución | 30 m |
| Formato | GeoTIFF |
| Salida | `data/static/opentopography/{YYYY-MM-DD}/dem_cop30_raw.tif` |
| Credencial | `OPENTOPOGRAPHY_API_KEY` |

El terreno se considera estático y sólo se actualiza cuando se solicita explícitamente.

## NOAA GFS 0,25°

| Campo | Valor |
|---|---|
| Producto | `pgrb2.0p25` |
| Ciclos | 00, 06, 12 y 18 UTC |
| Variables | viento a 10 m, temperatura y humedad relativa a 2 m |
| Acceso | NOMADS y espejos públicos AWS/GCS mediante `herbie-data` |
| Archivo histórico | desde 2021-01-01 |
| Salida | `data/raw/gfs/{YYYY-MM-DD}/{cycle}_{var}.tif` |
| Credenciales | no requiere |

`GFSClient.resolve_cycle()` elige el último ciclo publicado anterior al instante solicitado. La
preparación filtra por `valid_time`, no por la fecha de inserción, para que una ingesta actual no
reemplace silenciosamente el clima de una reproducción histórica.

```bash
curl -X POST http://localhost:8000/api/v1/ingestion/gfs/run \
  -H 'Content-Type: application/json' \
  -d '{"target_date":"2026-01-05"}'
```

## CCS-BAP

Clasificación regional de tipos forestales y cobertura del suelo provista por CIEFAP. La capa
2017 es la fuente principal de combustible superficial. La tabla de conversión está en
[`crosswalk.md`](crosswalk.md).

## ESA WorldCover

| Campo | Valor |
|---|---|
| Producto | WorldCover v2.0, año 2021 |
| Resolución | 10 m |
| Acceso | GeoTIFF optimizado para nube desde S3 público |
| Tesela del AOI | `S45W072` |
| Salida | `data/static/worldcover/{YYYY-MM-DD}/esa_worldcover_v200_10m.tif` |

Se usa como comparador y para rellenar el sector chileno no cubierto por CCS-BAP.

## MapBiomas Argentina

Producto anual de cobertura utilizado como comparador temporal. Para cada incendio se selecciona
el último año publicado anterior al evento, evitando fuga temporal.

## Dosel

### Hansen Global Forest Change

- `treecover2000`: cobertura de dosel del año 2000.
- `lossyear` v1.13: año de pérdida forestal entre 2001 y 2025.
- Acceso: GeoTIFF optimizado para nube en Google Cloud Storage.

### ETH Global Canopy Height

- Altura global del dosel para 2020.
- Acceso público mediante `libdrive`.
- Se recorta y reproyecta al AOI durante la preparación.

### Capas derivadas

| Capa | Derivación |
|---|---|
| `cc.tif` | cobertura Hansen reproyectada |
| `ch.tif` | altura ETH reproyectada |
| `cbh.tif` | altura de base de copa según tipo de bosque y altura disponible |
| `cbd.tif` | densidad aparente de copa derivada de cobertura y altura |

Cuando Hansen registra pérdida anterior al incendio, la preparación anula el dosel. Las reglas y
sus límites están documentados en [`crosswalk.md`](crosswalk.md).

## Áreas quemadas

La preparación combina Hansen `lossyear`, cicatrices dNBR y MCD64A1 para actualizar combustibles
posteriores al mapa base. La regla adoptada está en
[`resultados/pronostico/areas-quemadas.md`](resultados/pronostico/areas-quemadas.md).

## Licencias y atribución

La aplicación muestra proveedor, fecha y vigencia de cada fuente. Los términos específicos deben
verificarse en la publicación original; esta documentación no redistribuye datos de terceros.

