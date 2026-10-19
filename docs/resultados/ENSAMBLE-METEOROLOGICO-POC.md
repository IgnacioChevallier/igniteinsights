# POC de ensamble meteorológico GEFS para ELMFIRE

> Corte: 2026-10-17. Estado: **smoke ELMFIRE y 23/23 backtests contemporáneos de calibración
> completados y consolidados** (`ENSAMBLE-BACKTESTS-CONSOLIDADO.md`). El producto se interpreta
> exclusivamente como “fracción de miembros GEFS que quemaron este píxel bajo las
> incertidumbres consideradas”. No es una probabilidad calibrada.

## 1. Veredicto

**Adoptar con limitaciones como capa de acuerdo entre simulaciones; no adoptar como mejora
predictiva.** Se evaluó con 23 reinicios P-24 de calibración de cuatro incendios, 31/31 miembros
cada uno. Las tres preguntas se responden por separado (§8, “Consolidado de 23 reinicios”):

1. **Infraestructura: válida.** 23/23 casos pasaron la integridad. No hubo sustituciones ni fallos
   científicos, todos los ciclos estaban publicados antes del reinicio y los artefactos son
   trazables por hash. Cada caso tarda cerca de 1 h de reloj en serie y retiene ~1,6 GiB. Es
   viable fuera de línea, pero no en latencia operativa sin paralelizar.
2. **Comunicación de sensibilidad: útil, con una limitación explícita.** Las bandas nunca fueron
   vacías ni uniformes. Sin embargo, la diferencia entre ≥0,10 y ≥0,80 es sólo el 4–14 % del área
   de c00 y queda crecimiento observado fuera de ≥0,10. La capa muestra sensibilidad
   meteorológica, no una envolvente de dónde puede llegar el fuego, y la leyenda lo dice.
3. **Mejora predictiva consistente: no.** En medianas por incendio, ≥0,80 mejora IoU en 2/4
   incendios a 12 h y en 3/4 a 24 h, por ≤0,003, y empeora en Puerto Patriada. ≥0,50 es
   equivalente a c00. ≥0,10 gana recall en 4/4 incendios a costa de IoU y área.

Se mantienen los roles congelados: ≥0,50 escenario central, ≥0,80 alto acuerdo y ≥0,10
propagación posible. ≥0,80 no se promueve.

El experimento no modifica `modelo-v0`, `lw-100-001`, combustible, dosel, supresión,
pavesas ni copa. SMN WRF queda etiquetado como escenario regional independiente y nunca entra al
denominador GEFS.

## 2. Fuentes, disponibilidad y licencias verificadas

### GEFS

- Inventario operativo oficial: control `c00` y 30 perturbados `p01`–`p30`; ciclos 00, 06, 12 y
  18 UTC. El producto selectivo `pgrb2s.0p25` tiene resolución 0,25°, pasos cada 3 h y llega a
  240 h. El inventario de f003 confirma TMP y RH a 2 m, UGRD y VGRD a 10 m, y APCP. Fuente:
  [NCEP GEFS Product Inventory](https://www.nco.ncep.noaa.gov/pmb/products/gens/).
- NOMADS permite filtrar por variable, nivel y bounding box. El adaptador usa el endpoint vigente
  `filter_gefs_atmos_0p25s.pl`; no descarga el globo completo.
- La ventana de NOMADS es operativa y corta (el índice observado el 2026-10-12 mostraba cuatro
  días). NOAA también publica GEFS en `s3://noaa-gefs-pds`, pero NCEI advierte que NODD es
  distribución y no un archivo oficial. Para backtests hay que congelar por hash los archivos
  usados y comprobar el número de miembros y la versión disponibles para la fecha. Fuentes:
  [NOAA GEFS en AWS](https://registry.opendata.aws/noaa-gefs/) y
  [NCEI GEFS](https://www.ncei.noaa.gov/products/weather-climate-models/global-ensemble-forecast).
- Licencia: datos NOAA/NODD abiertos al público; NOAA solicita atribución y prohíbe implicar
  endoso o presentar datos modificados como originales sin alterar.

### SMN WRF

- WRF 4.0 determinista, 4 km, Lambert conforme, horario y hasta 72 h. Variables: `T2` en °C,
  `HR2` en %, `magViento10` en m/s, `dirViento10` en grados y `PP` horario en mm. Fuentes:
  [documentación general](https://odp-aws-smn.github.io/documentation_wrf_det/Informacion_general/),
  [formato y variables](https://odp-aws-smn.github.io/documentation_wrf_det/Formato_de_datos/).
- Estructura pública: `DATA/WRF/DET/YYYY/MM/DD/HH/WRFDETAR_01H_YYYYMMDD_HH_FFF.nc` en
  `s3://smn-ar-wrf`. La documentación enumera ciclos 00/06/12/18; la ficha de AWS dice 00/12.
  La POC exige un ciclo explícito y falla si no existe, en vez de resolver esa discrepancia con
  una sustitución silenciosa. Fuentes: [estructura](https://odp-aws-smn.github.io/documentation_wrf_det/Estructura_de_datos/)
  y [acceso](https://odp-aws-smn.github.io/documentation_wrf_det/Acceso_a_los_datos/).
- Licencia: Creative Commons Atribución 2.5 Argentina, según la
  [ficha oficial en AWS](https://registry.opendata.aws/smn-ar-wrf-dataset/).

## 3. Diseño y ciclo completo

```text
GEFS f000,f003,… (31 miembros) ─┐
                                ├─ recorte fuente al AOI
SMN WRF f000,f001,… (separado) ─┘
      → U/V 10 m, T 2 m [K], RH 2 m [%]
      → interpolación horaria (GEFS: U/V/T/RH; nunca grados)
      → reproyección bilinear a la grilla congelada de la preparación
      → ws 20 ft [mph], wd meteorológica, m1/m10/m100 [%]
      → copia por hardlink de combustibles/dosel/topografía/phi congelados
      → namelist de modelo-v0, una ejecución por miembro
      → TOA > 0 por miembro
      → suma binaria / miembros exitosos
      → burn_agreement.tif + máscaras y GeoJSON ≥0,10/≥0,50/≥0,80
      → ensemble_agreement.json (contrato autocontenido para el frontend)
```

La precipitación se descarga sólo si se incorpora después una humedad con historia. La cadena
vigente `derive_moisture` usa T/RH instantáneas y, por lo tanto, esta POC no usa APCP. Esto
preserva exactamente la convención de `modelo-v0`; no introduce una humedad nueva.

### Transformaciones

1. GEFS se descarga cada 3 h y se interpola por **horas válidas UTC absolutas**. El inicio de
   simulación es explícito y puede caer entre pasos; no se redondea al ciclo ni a la hora. U y V
   se interpolan antes de calcular velocidad/dirección. T permanece en Kelvin
   (`GRIB_NORMALIZE_UNITS=NO`) y RH en %.
2. SMN publica magnitud/dirección: se convierten primero a U/V; T pasa de °C a K. El recorte se
   hace como ventana rectangular sobre la grilla Lambert nativa.
3. `weather_builder` reproyecta al DEM congelado, convierte viento de 10 m a 20 ft con el factor
   logarítmico vigente (~0,87), pasa m/s a mph, calcula dirección meteorológica y EMC Nelson.
4. Antes de reproyectar, la CLI verifica que el clima cubra por completo la grilla destino. Todos
   los miembros deben compartir CRS, transform, forma y nodata al agregarse.

## 4. Trazabilidad y fallos

Cada miembro conserva `manifest.json` con ciclo, disponibilidad del ciclo, `forecast_start`, hora
del perímetro, offset, horas fuente, horas válidas fuente y de cada banda, miembro, bbox, URL
exacta, rango de bytes, ETag, ruta, SHA-256 y transformaciones. Faltantes de variable, miembro,
hora o cobertura abortan. La CLI no reemplaza un perturbado por control ni por otro ciclo.

El agregador registra miembros esperados, exitosos, fallidos y `effective_denominator`. El valor
de cada píxel es `miembros_exitosos_que_quemaron / miembros_exitosos`. Por defecto exige 24 de 31
miembros (77 %); el umbral es explícito por CLI y debe ser ratificado como decisión de producto.
Con menos miembros no escribe mapa.

### Integración visual preparada

El agregador también escribe `ensemble_agreement.json`, contrato versionado para una futura capa
del sidebar derecho llamada **“Acuerdo del ensamble”**. La salida incluye los polígonos de los
tres umbrales, colores de presentación y los campos `valid_members`, `expected_members`,
`weather_cycle`, `forecast_start`, `horizon_hours`, `generated_at` y `forecast_valid_at`. Este
último es `forecast_start + horizon`, nunca `cycle + horizon`. La leyenda contractual es
exactamente **“acuerdo entre simulaciones”**: el producto no se presenta como probabilidad.

El contrato declara `default_visible: false`. Desde el 2026-10-17 la capa está conectada en
`MapPanel` como checkbox del sidebar derecho:

- arranca apagada y carga `GET /api/v1/simulations/{id}/ensemble-agreement` sólo al activarse;
- es mutuamente excluyente con “Tiempo de llegada” e “Intensidad del frente de fuego”;
- se dibuja debajo de las isócronas sin modificarlas;
- avisa sin romper el mapa cuando el artefacto falta o está incompleto.

Apagada, no agrega fuentes ni capas a MapLibre. La leyenda muestra miembros válidos/esperados,
ciclo, inicio, horizonte, vigencia y timestamp. También aclara que no es probabilidad calibrada,
que es propagación potencial sin supresión y que el incendio real puede extenderse fuera de
≥ 0,10. La cubre `frontend/e2e/ensemble-agreement.spec.ts`.

## 5. Evidencia obtenida

Smoke de datos del ciclo `2026101200`, control, AOI `[-72,25, -44, -70, -41,75]`, horizonte 3 h:

- NOMADS devolvió f000 y f003 filtrados (2,2 KiB en total para el AOI pequeño), ambos con SHA-256.
- Se generaron cuatro bandas horarias. Las medias cambiaron entre bandas: T2 281,03 → 279,67 K;
  U10 0,71 → 0,95 m/s; V10 −2,00 → −1,26 m/s; RH 79,98 → 86,94 %.
- Sobre `benchmark-2026-09-28-asp3-v5/dem.tif`, ELMFIRE recibiría ws 2,77 → 3,49 mph y m1
  20,77 → 22,95 %. Esto prueba que las bandas no quedaron congeladas y que las transformaciones
  son físicamente plausibles para ese recorte.
- Una hora de SMN WRF ocupó 31,1 MB antes del recorte. El adaptador leyó la grilla Lambert real y
  produjo un recorte de 66 × 50: T2 media 281,72 K, RH 85,23 %, U10 1,13 m/s y V10 −0,36 m/s.
  El manifiesto declara `included_in_gefs_denominator: false`.

### Caso P-24 congelado

- Caso: `epuyen-2025/pronostico-v6`, ventana 1, derivado de
  `epuyen-2025/calibracion-v6`; la partición lo ubica en calibración, no en prueba.
- Perímetro observado acumulado: VIIRS SNPP SP + NOAA-20 SP hasta
  **2025-01-15 18:33 UTC**. No se usó la ignición original ni una semilla oráculo.
- Preparación: `benchmark-aoi-asp3-v6`, `modelo-v0`, receta `lw-100-001`; grilla
  EPSG:32719 de 1.480 × 1.333 celdas a 30 m.
- Paquete: `data/ensemble-poc/base-p24-modelo-v0-inputs` (38 MB), con DEM, pendiente,
  aspecto, `fbfm40` CCS-BAP 2017 anterior al fuego, dosel, `adj`, `phi` y
  `fuel_models.csv`. `base-package.json` registra procedencia y SHA-256 de cada archivo.
- Meteorología: GEFS `2026101200`, AOI `[-71,90, -42,70, -70,90, -41,80]`, 24 h. Como
  ciclo y perímetro no son contemporáneos, la clasificación es **smoke no puntuable**.

### Gate de cinco miembros

c00+p01–p04 terminaron sin fallos. Los hashes de `ws`, `wd` y `m1` fueron distintos en los cinco
miembros; cada serie tuvo 25 bandas. Las áreas quemadas quedaron entre 1.145,07 y 1.225,17 ha y
los IoU de geometría entre pares entre 0,847 y 0,953. El acuerdo tomó los seis valores posibles
0/0,2/0,4/0,6/0,8/1, por lo que no fue vacío ni uniforme. Ese gate habilitó la corrida completa.

### Ensamble de 31 miembros

- **Completitud:** 31 descargados, preparados y ejecutados; `effective_denominator=31`, sin
  miembros fallidos o sustituidos. Los 31 hashes de `ws`, `wd` y `m1` son únicos.
- **TOA:** todos EPSG:32719, 1.480 × 1.333, transform y nodata idénticos, y todos no vacíos.
- **Área:** mínimo 1.065,42 ha (p05), máximo 1.297,98 ha (p17), media 1.195,14 ha y mediana
  1.183,41 ha. Las 31 geometrías binarias tienen hashes distintos.
- **Geometría:** IoU entre los 465 pares: mínimo 0,820, mediana 0,917 y máximo 0,972.
- **Acuerdo:** aparecen todas las fracciones 0/31–31/31; el ráster no es vacío ni uniforme.
- **Tiempo:** 1.056,6 s acumulados de solver en ejecución serial (17,6 min); mediana 19,2 s,
  media 34,1 s y rango 16,0–207,2 s. El máximo incluye el arranque frío c00.
- **Almacenamiento:** 8,5 GB para el ciclo completo, de los cuales ~8,84 GB decimales son las
  cinco series meteorológicas ELMFIRE; las salidas del solver ocupan 32,7 MB y el producto de
  acuerdo 852 KB. CPU/RSS del solver remoto siguen sin estar expuestos.

Comparación del control c00 (1.172,34 ha) con los contornos:

| Contorno | Área | IoU con c00 | Sólo c00 | Sólo contorno |
|---|---:|---:|---:|---:|
| ≥0,10 | 1.311,93 ha | 0,893 | 0,18 ha | 139,77 ha |
| ≥0,50 | 1.191,06 ha | 0,960 | 15,03 ha | 33,75 ha |
| ≥0,80 | 1.126,44 ha | 0,948 | 53,91 ha | 8,01 ha |

Los números completos, hashes, pares y gates están en
`data/ensemble-poc/2026101200/ensemble31-analysis.json`. En esa etapa de smoke no se hizo un
backtest ni se fabricó una sustitución histórica; el backtest posterior está en §8.

## 6. Reproducción exacta

Construir el paquete P-24 elegido desde el almacén inmutable:

```bash
uv run python scripts/weather_ensemble_poc.py build-base \
  --case epuyen-2025/pronostico-v6 --window 1 \
  --output data/ensemble-poc/base-p24-modelo-v0-inputs
```

Descargar los 31 miembros, 24 h:

```bash
export UV_CACHE_DIR=/tmp/igniteinsights-uv-cache
uv run python scripts/weather_ensemble_poc.py download-gefs \
  --cycle 2026101200 --forecast-start 2026-10-12T00:00:00+00:00 \
  --bbox -71.90 -42.70 -70.90 -41.80 \
  --horizon 24 --member-limit 31 --output data/ensemble-poc/2026101200/gefs
```

Preparar inputs sin modificar la preparación congelada (repetir por miembro):

```bash
uv run python scripts/weather_ensemble_poc.py materialize \
  --source data/ensemble-poc/2026101200/gefs/c00 \
  --frozen-inputs data/ensemble-poc/base-p24-modelo-v0-inputs \
  --output data/ensemble-poc/2026101200/inputs/c00
```

Ejecutar ELMFIRE 2025.0212 mediante el runner configurado:

```bash
uv run python scripts/weather_ensemble_poc.py run \
  --inputs data/ensemble-poc/2026101200/inputs/c00 \
  --outputs data/ensemble-poc/2026101200/runs/c00 --horizon 24
```

Lote completo, una vez armado `base-p24-modelo-v0-inputs`:

```bash
for member in c00 $(seq -f 'p%02g' 1 30); do
  uv run python scripts/weather_ensemble_poc.py materialize \
    --source "data/ensemble-poc/2026101200/gefs/${member}" \
    --frozen-inputs data/ensemble-poc/base-p24-modelo-v0-inputs \
    --output "data/ensemble-poc/2026101200/inputs/${member}"
  uv run python scripts/weather_ensemble_poc.py run \
    --inputs "data/ensemble-poc/2026101200/inputs/${member}" \
    --outputs "data/ensemble-poc/2026101200/runs/${member}" --horizon 24
done
```

El directorio congelado es el reinicio VIIRS explícito descrito arriba, no el directorio base del
benchmark ni la ignición original. `build-base` rechaza ventana 0 y casos fuera de calibración o
pertenecientes a prueba. `materialize` valida el contrato, enlaza estáticos, elimina sólo los cinco
rásters meteorológicos en la copia y los regenera; además registra hashes de estáticos y clima. `run`
deja `run-metrics.json` con pared, CPU/RSS del cliente y almacenamiento;
el runner actual no expone CPU/RSS remotos, limitación que debe resolverse antes del ensayo de
costo.

SMN WRF, siempre por separado:

```bash
uv run python scripts/weather_ensemble_poc.py download-smn \
  --cycle 2026101200 --bbox -72.25 -44 -70 -41.75 \
  --horizon 24 --output data/ensemble-poc/2026101200/smn-wrf
uv run python scripts/weather_ensemble_poc.py materialize \
  --source data/ensemble-poc/2026101200/smn-wrf \
  --frozen-inputs data/ensemble-poc/base-p24-modelo-v0-inputs \
  --output data/ensemble-poc/2026101200/inputs/smn-wrf
```

Agregar sólo GEFS (ajustar `--toa-name` al nombre real del runner):

```bash
uv run python scripts/weather_ensemble_poc.py aggregate \
  --runs data/ensemble-poc/2026101200/runs \
  --toa-pattern 'time_of_arrival_*.tif' --expected-members 31 --min-valid-members 24 \
  --cycle-label 2026101200 --forecast-start 2026-10-12T00:00:00+00:00 --horizon 24 \
  --output data/ensemble-poc/2026101200/agreement-31
```

Reproducir todos los gates y la comparación con c00:

```bash
uv run python scripts/weather_ensemble_poc.py evaluate-smoke \
  --sources data/ensemble-poc/2026101200/gefs \
  --inputs data/ensemble-poc/2026101200/inputs \
  --runs data/ensemble-poc/2026101200/runs \
  --agreement data/ensemble-poc/2026101200/agreement-31 \
  --expected-members 31 --scale-members 31 \
  --output data/ensemble-poc/2026101200/ensemble31-analysis.json
```

## 7. Pruebas automatizadas

`tests/test_weather_ensemble_poc.py` cubre:

- U/V ↔ velocidad/dirección y m/s → viento ELMFIRE;
- interpolación vectorial a través de 0°/360°;
- orden cronológico y rechazo de extrapolación;
- selección control + perturbados y URL con filtro de variables/AOI;
- acuerdo sintético, denominador efectivo y umbral mínimo;
- grilla, CRS, transform y nodata;
- máscaras/GeoJSON 0,10, 0,50 y 0,80;
- contrato frontend, visibilidad inicial desactivada, metadatos y copy de leyenda;
- reproducibilidad byte a byte del GeoTIFF de acuerdo.

Comando validado:

```bash
uv run pytest -q tests/test_weather_ensemble_poc.py tests/test_weather_multiband.py \
  tests/test_wind_bands.py tests/test_namelist_writer.py
```

Resultado final: 204 tests y 3 subtests pasaron; Ruff pasó sobre `app`, `scripts` y `tests`, y
mypy pasó sobre los seis archivos modificados. El mypy global expuso 43 errores preexistentes en
seis scripts ajenos a esta POC y no se usó para ampliar alcance. El build Next/TypeScript pasó sin
errores y ESLint conservó sólo dos warnings preexistentes sobre `<img>`.

### Reproducción del backtest contemporáneo

```bash
BACKTEST_ROOT=data/ensemble-poc/backtest-epuyen-20250115T1833Z-gefs-2025011512
uv run python scripts/weather_ensemble_poc.py inventory-gefs \
  --cycle 2025011512 --forecast-start 2025-01-15T18:33:00+00:00 \
  --horizon 24 --member-limit 31 --output "$BACKTEST_ROOT/archive-inventory.json"
uv run python scripts/weather_ensemble_poc.py download-gefs \
  --cycle 2025011512 --forecast-start 2025-01-15T18:33:00+00:00 \
  --bbox -72 -44 -70 -42 --horizon 24 --member-limit 31 \
  --inventory "$BACKTEST_ROOT/archive-inventory.json" --output "$BACKTEST_ROOT/sources"
```

Después de materializar y ejecutar cada miembro, los dos cortes se agregan sin volver a correr el
solver:

```bash
for H in 12 24; do
  uv run python scripts/weather_ensemble_poc.py aggregate \
    --runs "$BACKTEST_ROOT/runs" --expected-members 31 --min-valid-members 31 \
    --cycle-label 2025011512 --forecast-start 2025-01-15T18:33:00+00:00 \
    --horizon "$H" --output "$BACKTEST_ROOT/agreement/h$(printf '%02d' "$H")"
done
uv run python scripts/weather_ensemble_poc.py evaluate-backtest \
  --base-inputs "$BACKTEST_ROOT/base-p24-modelo-v0-inputs" --runs "$BACKTEST_ROOT/runs" \
  --agreement-root "$BACKTEST_ROOT/agreement" \
  --output "$BACKTEST_ROOT/backtest-metrics.json"
```

`aggregate` considera llegada sólo si `0 < TOA <= horizon × 3600`; esto evita incluir el pequeño
paso numérico posterior al límite que puede aparecer en el ráster final de 24 h.

## 8. Protocolo de evaluación

### Smoke operacional completado

Los cinco pasos previstos se completaron en orden. El gate de cinco pasó antes de iniciar los 26
miembros restantes; el de 31 también pasó. Los archivos `smoke5-analysis.json` y
`ensemble31-analysis.json` preservan la evaluación automática.

### Backtest contemporáneo: selección y eje temporal

Se eligió antes de puntuar `epuyen-2025/pronostico-v6`, ventana 1, reinicio VIIRS P-24 de
calibración (no prueba) a **2025-01-15 18:33 UTC**. El último ciclo nominal anterior fue GEFS
`2025011512`. El inventario exhaustivo confirmó 31 miembros y las cuatro variables en los diez
plazos necesarios; el último índice requerido se publicó a **16:01:15 UTC**, 2 h 31 min 45 s
antes del reinicio. Por eso el ciclo 12Z estaba efectivamente disponible y no fue necesario
retroceder a 06Z.

- Offset inicio−ciclo: 6 h 33 min = 6,55 h.
- Horas fuente: f006, f009, …, f033; válidas desde 18:00 UTC del 15 hasta 21:00 UTC del 16.
- Bandas: 25 instantes 18:33, 19:33, …, 18:33 UTC del día siguiente.
- Validez de 12 h: 2025-01-16 06:33 UTC; validez de 24 h: 2025-01-16 18:33 UTC.
- Umbrales declarados antes del resultado: 0,10; 0,50; 0,80. No hubo selección posterior.

El paquete trazable vive en
`data/ensemble-poc/backtest-epuyen-20250115T1833Z-gefs-2025011512`. El manifiesto base conserva
los hashes de preparación v6, perímetro y referencias; `archive-inventory.json` conserva las 310
entradas miembro×plazo y su disponibilidad; cada fuente recortada y cada clima ELMFIRE tienen
SHA-256. `modelo-v0`, `lw-100-001`, parámetros, combustibles y dosel permanecieron congelados.

### Resultado real

Los gates pasaron: 31/31 miembros exitosos, 31 hashes distintos de `ws`, `wd` y `m1`, una sola
grilla EPSG:32719 de 1.480×1.333, 31 geometrías distintas y acuerdo con las 32 fracciones posibles
0/31–31/31. Las áreas finales de miembro fueron 2.102,49–2.396,43 ha (media 2.236,90; mediana
2.231,55) y los 465 IoU entre pares 0,875–0,988 (mediana 0,960).

La puntuación es exclusivamente de crecimiento nuevo respecto de la semilla VIIRS de 1.964,25
ha. La referencia visible contiene 635,94 ha nuevas a 12 h y 771,12 ha a 24 h.

| Horizonte | Producto | Dice | IoU | Sesgo de área | Recall cicatriz |
|---:|---|---:|---:|---:|---:|
| 12 h | c00 | 0,4789 | 0,3148 | 1,344 | 0,5613 |
| 12 h | ≥0,10 | 0,4840 | 0,3192 | 1,445 | 0,5916 |
| 12 h | ≥0,50 | 0,4786 | 0,3146 | 1,340 | 0,5599 |
| 12 h | ≥0,80 | 0,4729 | 0,3097 | 1,289 | 0,5412 |
| 24 h | c00 | 0,5502 | 0,3795 | 2,230 | 0,8884 |
| 24 h | ≥0,10 | 0,5389 | 0,3688 | 2,392 | 0,9139 |
| 24 h | ≥0,50 | 0,5497 | 0,3790 | 2,239 | 0,8902 |
| 24 h | ≥0,80 | 0,5525 | 0,3817 | 2,163 | 0,8737 |

Como envolvente, ≥0,10 cubrió 59,2 % de la cicatriz visible y 38,2 % del soporte VIIRS nuevo a
12 h; a 24 h, 91,4 % y 83,9 %. Predijo 918,72/1.844,37 ha de crecimiento y dejó
542,52/1.139,67 ha adicionales fuera de la referencia a 12/24 h. La zona ≥0,80 es alto acuerdo,
no alta probabilidad; a 24 h fue el único contorno que mejoró marginalmente Dice/IoU y sesgo
respecto de c00.

En integridad, c00 tuvo 2.220,66 ha de llegada en el ráster final. Los contornos de 24 h midieron
2.351,16 ha (≥0,10), 2.227,41 ha (≥0,50) y 2.165,22 ha (≥0,80), con IoU contra c00 0,944,
0,989 y 0,974. El gate de integridad usa el TOA final; la puntuación anterior aplica el corte
temporal exacto y excluye semilla y zonas no observables según P-24.

### Tiempo y almacenamiento

- Tiempo acumulado observado: 19.490 s de pared de cliente. No equivale a CPU de solver porque
  mezcla un tramo con bind mount, cuatro corridas contendiendo por una CPU y la cola local.
- Centinela aislado por transferencia (`p06`): 228 s end-to-end. En el conjunto: mediana 131 s,
  rango 48–1.939 s; los extremos altos son I/O del bind mount y contención, no sólo propagación.
- Volumen actual: 8,9 GiB; fuentes 1,6 GiB, inputs 7,2 GiB, salidas 43 MiB y agregados h12+h24
  1,8 MiB. En bytes decimales, las cinco series meteorológicas suman 7.700.503.416 B y las
  salidas 43.941.636 B.
- Fallos científicos por miembro: cero. Hubo un intento de transporte fallido antes de ELMFIRE y
  cuatro trabajos parciales detenidos al cambiar de estrategia; se movieron fuera del conjunto y
  se repitieron desde cero. Sólo los 31 `run-metrics.json` exitosos entran al denominador.

### Otros reinicios con archivo

El probe `calibration-restart-archive-inventory.json` verificó `c00` y `p30`, las diez horas
fuente y las cuatro variables en cada reinicio P-24 de calibración. Encontró 23/34 reinicios con
archivo: Epuyén 2025 6/6, Los Alerces 2023 3/3, Los Alerces 2024 8/8 y Puerto Patriada 2026
6/6; Cholila 2015 y Los Alerces 2016, 0. Excluido el caso actual quedaban **22 candidatos**, y
los 22 se corrieron (ver abajo). Este probe sólo inventaría: antes de cada corrida se confirmó
31/31.

### Consolidado de 23 reinicios

Del 2026-10-14 al 17 se corrieron con una cola serial reanudable los 22 reinicios adicionales:
Epuyén w2–w6, Los Alerces 2023 w1–w3, Los Alerces 2024 w1–w8 y Puerto Patriada w1–w6. Cada
reinicio usa un único runner y su propio ciclo GEFS, publicado antes de `forecast_start`.
`scripts/run_ensemble_backtest_queue.py` y `scripts/run_ensemble_backtest_case.py` siguen este
orden:

1. inventario 31/31;
2. descarga con reintentos que conservan el ciclo;
3. paquete P-24;
4. materialización y ejecución en streaming por miembro;
5. agregados h12/h24;
6. evaluación;
7. `integrity.json`;
8. retención.

Consolidado: `data/ensemble-poc/calibration-backtests-consolidated.{json,csv}` e informe
`docs/resultados/ENSAMBLE-BACKTESTS-CONSOLIDADO.md`, generados por
`scripts/consolidate_ensemble_backtests.py`.

- **Integridad:** 23/23 `integrity_passed`; además, auditoría uniforme de 14 gates sobre los 23
  (`data/ensemble-poc/calibration-backtests-uniform-integrity-audit.json`). Hubo cero fallos
  científicos. Los dos reintentos transitorios de descarga, el c00 excluido por transporte y el
  c00 interrumpido por concurrencia se repitieron desde cero.
- **Por incendio** (mediana de Δ IoU frente a c00, 12/24 h):

  | Incendio | ≥0,10 | ≥0,50 | ≥0,80 |
  |---|---|---|---|
  | Epuyén | −0,0036/−0,0063 | −0,0004/−0,0004 | +0,0013/+0,0019 |
  | LA 2023 | −0,0019/+0,0012 | +0,0003/+0,0004 | +0,0030/+0,0022 |
  | LA 2024 | −0,0013/−0,0024 | +0,0004/−0,0001 | −0,0004/+0,0017 |
  | Puerto Patriada | −0,0026/−0,0003 | −0,0002/−0,0008 | −0,0008/−0,0030 |

  La mediana del IoU absoluto de c00 por incendio va de 0,08 a 0,35.
- **≥0,10 como envolvente:**
  - suma +0,6 a +2,5 pp de cobertura de cicatriz y +0,3 a +1,9 pp de FIRMS nuevas;
  - lo paga con +10 a +231 ha de FP y +12 a +231 ha de área (medianas por incendio);
  - a 24 h deja fuera medianas de 18 ha (Epuyén) a 685 ha (Puerto Patriada) de crecimiento
    observado.
- **Ancho de banda:** el área de ≥0,10 menos la de ≥0,80 equivale al 4–14 % del área de c00.
- **Costo y almacenamiento:**
  - pared de cliente del solver, mediana de 592 s por caso y 16 s por miembro;
  - cerca de 1 h de reloj por caso con descarga y materialización;
  - 44,7 GiB retenidos en total y ~1,6 GiB por caso, sobre todo rangos GRIB;
  - CPU/RSS remotos no expuestos.

La lectura parcial con 9 casos (≥0,80 mejoraba en 3/3 incendios) no se sostuvo con Puerto
Patriada. El resultado es descriptivo: hay 4 incendios con reinicios correlacionados y no se
calculó significancia.

### Política de retención propuesta

1. Conservar de forma permanente los rangos GRIB fuente, URLs/rangos/ETags/SHA-256, inventario de
   disponibilidad, manifiesto del paquete base, versión de código/solver, agregados de 12/24 h y
   métricas finales.
2. Conservar los TOA por miembro durante la ventana de auditoría; después pasarlos a archivo frío
   o eliminarlos sólo si siguen disponibles la imagen exacta del solver y todos los insumos.
3. Eliminar tras validar hashes las materializaciones reproducibles `u10/v10/t2m/rh`,
   `ws/wd/m1/m10/m100`, copias/hardlinks estáticos por miembro, `flin`, `vs` e isócronas por
   miembro. Son la mayor parte del volumen y no son evidencia primaria.
4. No eliminar manifiestos, logs de fallos, denominadores efectivos ni métricas aunque se borren
   sus cachés. Una limpieza nunca debe convertir un miembro faltante en miembro válido.

## 9. Limitaciones y fallos encontrados

- El endpoint inferido inicialmente sin sufijo `s` devolvió 404; quedó corregido y cubierto por el
  smoke real.
- GDAL convierte Kelvin a Celsius por defecto al leer GRIB. Se desactivó esa normalización para
  preservar la unidad documentada; el smoke detectó el problema antes de una corrida.
- Un AOI fuente que no cubra completamente la grilla destino puede dejar bordes inválidos. La CLI
  ahora falla antes de reproyectar y exige margen.
- SMN entrega un NetCDF completo por hora (~31 MB observado) y S3 no ofrece filtro espacial del
  contenido; se recorta inmediatamente en la grilla nativa, pero la transferencia es mayor que
  GEFS filtrado.
- La dirección SMN se convierte a U/V. GEFS ya entrega U/V. Ninguna ruta interpola grados.
- Las métricas de CPU/RSS del solver remoto no están disponibles en la API actual.
- La primera corrida centinela detectó que la CLI local enviaba una ruta macOS al runner Docker.
  Se corrigió la traducción al volumen `/app/data` antes de ejecutar perturbados. El
  `run-metrics.json` final de c00 corresponde al reintento exitoso; el intento de integración no
  se contó como falla de miembro y no alteró inputs.
- La ruta de transferencia remota confundía el directorio local a empaquetar con el destino
  `/app/data` del runner y tampoco subía el directorio que contiene el namelist. El primer intento
  de `p06` falló antes de ELMFIRE; se corrigió el cliente con rutas local/remota separadas, se
  agregaron tests y `p06` se repitió desde cero. Cuatro trabajos parciales posteriores se
  descartaron al cambiar de cuatro runners contendiendo por una CPU a una cola serial.
- El tiempo local depende fuertemente del transporte: el bind mount macOS produjo hasta 1.939 s,
  mientras la cola por transferencia caliente bajó a decenas/cientos de segundos. No debe usarse
  la suma de pared como CPU facturable sin instrumentar el runner.
- El acuerdo representa incertidumbre meteorológica GEFS condicionada a un modelo de propagación,
  combustible, dosel y perímetro fijos. No incluye supresión ni es una probabilidad calibrada.

## 10. Condiciones de adopción

1. **Cumplida (2026-10-17):** backtest extendido a los 23 reinicios de calibración con archivo,
   sin abrir prueba. No mostró mejora predictiva consistente. Ninguna afirmación de
   superioridad sobre c00 está respaldada, y ≥0,80 no se promueve.
2. Mantener en la leyenda que sólo varía la meteorología y que el incendio puede extenderse fuera
   de ≥0,10. Validarlo con usuarios reales (`PROTOCOLO-EVALUACION-ACUERDO-ENSAMBLE.md`, tarea
   11) antes de usar la capa fuera de la tesis.
3. Mantener el mínimo operativo explícito de 24/31 y mostrar siempre válidos/esperados, ciclo,
   horizonte y timestamp. Nunca sustituir miembros ni ciclos silenciosamente.
4. **Cumplida:** la política de retención se aplicó en los 22 casos nuevos y dejó ~1,6 GiB por
   caso, frente a 8,9 GiB sin retención. El primer backtest conserva sus inputs a propósito.
5. Exponer métricas de CPU/RSS del runner para convertir tiempo y almacenamiento en costo de
   infraestructura real. Sigue pendiente.
6. Mantener `modelo-v0` y `lw-100-001` congelados durante la evaluación. Un backtest puede aceptar
   o rechazar el producto de ensamble, pero no autoriza recalibrar el modelo ni seleccionar
   retrospectivamente miembros.
