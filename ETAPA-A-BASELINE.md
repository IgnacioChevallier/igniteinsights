# Etapa A — Baseline honesto y andamiaje de medición

> Estado: **A0-A6 implementados** (2026-09-06), pendiente A7 (congelar el baseline, requiere
> re-ingesta y una corrida completa) · Issues: IGN-21 (parcial), habilita IGN-20 / IGN-22 / IGN-26
> Depende de: nada externo · Bloquea: Etapa B, Etapa C, y toda validación

## Objetivo

Producir un **baseline congelado, reproducible y auditable** del pipeline de combustible
actual (ESA WorldCover → FBFM40), y cerrar los acoplamientos que hoy permiten que un
cambio de crosswalk **no tenga efecto** o **falle en silencio**.

Esta etapa **no mejora la predicción**. La hace *medible*. Es la condición previa para que
la Etapa B pueda afirmar "mejoró" con un número en vez de con una opinión.

El marco de la tesis es comparativo (§12.3 de `docs/historico/SIMULATION_AUDIT.md`): el aporte se demuestra como `IoU(baseline) vs IoU(mapa patagónico)`. Un baseline que se regenera solo, o que
depende de un caché que nadie invalida, **no sirve como término de comparación**.

## Qué NO es esta etapa

- No cambia la fuente de datos de cobertura.
- No introduce modelos de combustible propios.
- No ajusta `ADJ` (IGN-25). Ver §12.3 del audit: **ADJ se toca después de la comparación de combustibles, nunca antes**, o absorbe el error del combustible y anula el resultado.

---



## A0 — Resolver el AOI definitivo (BLOQUEANTE)

El AOI vigente en `app/config.py:30-33` es `west=-72.0, south=-42.9, east=-71.5, north=-42.5`.
El dataset de validación se extiende hasta **lat −42.079**; sólo **70 de 196 tiles** intersectan el AOI (`IGN-26-VALIDACION.md` §12.5, hallazgo 3).

Decisión tomada: **ampliar el AOI al footprint del incendio.**

Por qué va primero y no después: `fbfm40.tif`, `dem.tif`, `slp.tif`, `asp.tif`, el recorte de
WorldCover y todos los cachés de `data/static/` se cortan al AOI. Ampliarlo después de
congelar el baseline invalida el baseline y obliga a rehacer la etapa entera.

**Resuelto** con `../mask-dataset-gen/dataset/metadata.csv` (196 filas, columnas
`tile, lon_min, lat_min, lon_max, lat_max, pct_quemado, fecha_pre, fecha_post, escala_m`):


|                       | Longitud              | Latitud               |
| --------------------- | --------------------- | --------------------- |
| Dataset de validación | −72,014 … **−71,201** | −42,818 … **−42,079** |
| AOI vigente           | −72,0 … −71,5         | −42,9 … −42,5         |
| Faltante              | 0,30° al **este**     | 0,42° al **norte**    |


AOI propuesto, unión con margen de ~2 km para que el frente no toque el borde del dominio:

```
aoi_west  = -72.05
aoi_south = -42.90     # el AOI vigente ya excede el dataset por el sur, se conserva
aoi_east  = -71.15
aoi_north = -42.05
```

**Costo a verificar antes de aceptarlo.** A 30 m y latitud −42,5 (1° lon ≈ 82,1 km, 1° lat ≈ 111,1 km):


|               | Dominio    | Celdas |
| ------------- | ---------- | ------ |
| AOI vigente   | 41 × 44 km | ~2,0 M |
| AOI propuesto | 74 × 94 km | ~7,8 M |


Son **~3,8×** más celdas. Hay que medir el tiempo de corrida de ELMFIRE antes de fijarlo.

### Dos bugs encontrados al ejecutarlo: A0 no era un cambio de config

Ampliar el AOI **no habría tenido ningún efecto**. Dos guardas encadenadas lo impedían, y
ninguna fallaba:

1. `repository.get_or_create_default_aoi` **creaba la geometría una sola vez** y después la
  buscaba por nombre. Editar `aoi_*` no actualizaba la fila: la base conservaba el bbox
   original para siempre mientras los clientes de ingesta calculaban tiles con el nuevo.
2. **Las tres ingestas estáticas** (DEM, WorldCover, Canopy) saltean la descarga con
  `if existing and Path(file_path).exists()`, sin mirar el AOI. Los rásteres viejos,
   recortados al footprint chico, se seguían reutilizando, y todos los derivados heredaban
   la extensión vieja en silencio.
3. `.env` **pisa los defaults de** `config.py`**.** Descubierto al correr la sonda de la Etapa B:
  `Settings` carga `env_file = ".env"`, y el AOI realmente en uso era
   `-71.917 / -42.821 / -71.359 / -42.500` — **más chico todavía** que el default del código
   que el audit citaba. Editar `config.py` no cambia nada en esta máquina ni en Railway.

Es la misma familia de fallo que los cachés de `fbfm40` y de topografía, un nivel más
arriba: un artefacto rancio servido porque la guarda no sabe qué significa "es el mismo".

Arreglo de raíz aplicado:

- `get_or_create_default_aoi` **sigue a la configuración**: si la geometría almacenada
difiere de la configurada, la actualiza y lo registra con un warning.
- `app/ingestion/coverage.py` — `covers_aoi(path)` lee la extensión **del archivo**, no de
`RasterAsset.bbox` (la columna la puebla cada ingesta por separado, y este chequeo existe
justamente porque la contabilidad y la realidad se habían separado). Las tres guardas
ahora saltean sólo si el ráster existente cubre el AOI configurado.

Pasos:

1. Actualizar `aoi_west/south/east/north` en **los tres lugares**: `app/config.py`
  (default), `.env` (lo que realmente se usa) y `.env.example` (lo versionado, para que
   la intención quede en el repo). **Hecho.** Cualquier despliegue con su propio entorno
   —Railway— necesita la misma actualización.
2. Re-ingerir DEM, WorldCover y Canopy con el AOI nuevo (`POST /api/v1/ingestion/run` con
  `include_dem`, `include_worldcover`, `include_canopy` en `true`).
3. Medir el tiempo de corrida de ELMFIRE sobre el dominio ampliado. Si resulta
  prohibitivo, **documentarlo antes de recortar** — recortar el dominio por costo es una
   decisión de tesis que hay que declarar, no un ajuste de ingeniería.

Criterio de salida: el 100 % de los tiles del dataset de validación cae dentro del AOI, o
está documentado por escrito qué fracción queda afuera y por qué.

---



## A1 — Invalidación de caché para `fbfm40.tif`

Problema raíz: `app/preparation/service.py:88-95` decide regenerar con `if not fbfm_cached.exists()`.
Cualquier cambio en `WORLDCOVER_TO_FBFM40` es un no-op mientras exista
`data/static/fbfm40.tif`. Es exactamente el fallo que ya ocurrió con la topografía
(`docs/historico/SIMULATION_AUDIT.md` §7.4, ítem 14).

**El patrón ya existe en el repo**: `app/elmfire/builder/raster_aligner.py` tiene
`DERIVATION_VERSION`, `_CACHE_KEY_FILE = ".topo_cache_key.json"` y `_cache_key()`. No se
inventa nada nuevo, se replica.

Pasos:

1. Agregar `DERIVATION_VERSION` a `fuels_builder.py`, con un comentario que obligue a
  incrementarlo ante **cualquier** cambio del crosswalk, del nodata o del dtype.
2. La clave de caché debe incluir: `DERIVATION_VERSION`, el hash del diccionario de
  crosswalk vigente, el identificador de la fuente de cobertura, la ruta y mtime del
   raster crudo, y el CRS/resolución/extensión de la grilla de referencia.
3. Escribir `.fbfm40_cache_key.json` junto al `.tif` y comparar antes de reutilizar.
4. Log explícito de *cache hit* y de *cache stale* con la clave vieja y la nueva, igual que
  hace `raster_aligner`.

Criterio de salida: un test que modifica una entrada del crosswalk y verifica que el
`.tif` se regenera con el valor nuevo sin borrar nada a mano.

---



## A2 — Emitir siempre nuestra propia tabla de combustibles

Problema raíz (verificado en el fuente de ELMFIRE 2025.0212, `build/source/elmfire_init.f90`,
`READ_FUEL_MODEL_TABLE_ROTHERMEL`): si un código presente en `fbfm40.tif` **no existe** en la
tabla de combustibles, ELMFIRE lo resuelve al modelo **256 (**`NB`**)** — carga `0.0001`,
profundidad `0.01` — es decir, **no combustible**. Sin error, sin warning, sin traza.

Hoy dependemos de que ELMFIRE escriba su tabla por defecto (`FUEL_MODEL_FILE = 'null'` hace
que la genere él). Eso deja el conjunto de códigos válidos **implícito** y hace que el
criterio de aceptación de IGN-21 ("todos los píxeles con un código FBFM40 válido") sea
inverificable: "válido" no es "está entre 91 y 204", es "está en la tabla que ELMFIRE va a
cargar".

Decisión: **emitir nuestro propio** `fuel_models.csv` **desde la Etapa A**, aunque sea idéntico
a la tabla por defecto de ELMFIRE. Con eso el conjunto de códigos válidos pasa a ser un
artefacto nuestro, versionado y testeable — y la Etapa C queda cableada sin trabajo extra.

Formato verificado del CSV (una fila por modelo, sin encabezado):

```
num, shortname, dynamic, w0_1h, w0_10h, w0_100h, w0_liveherb, w0_livewoody,
     sav_1h, sav_liveherb, sav_livewoody, depth_ft, mex_dead_pct, hoc_btu_lb
```

- Cargas en **lb/ft²** (`t/ac × 0,0459137`). Verificación: TL3 = 0,50 t/ac → `0.02296`.
- `dynamic` es `.TRUE.` / `.FALSE.` (transferencia de carga herbácea viva a muerta).
- `depth_ft` en pies, `mex_dead_pct` en porcentaje entero, `hoc_btu_lb` en BTU/lb.
- Constantes internas de ELMFIRE, no configurables por fila: SAV 10 h = 109, SAV 100 h = 30,
densidad de partícula = 32 lb/ft³, contenido mineral total = 0,055, efectivo = 0,01.
- El índice admite **0–303**, de modo que hay espacio libre por encima de 256 para modelos
propios (relevante para la Etapa C).

Pasos:

1. Crear el CSV en el repo como dato versionado (no generado), con las filas de los 13
  originales + SB40 + `256,NB`, copiadas del fuente de ELMFIRE.
2. Agregar `FUEL_MODEL_FILE` y `MISCELLANEOUS_INPUTS_DIRECTORY` al bloque `&MISCELLANEOUS`
  de `app/elmfire/builder/namelist_writer.py:191-194` (hoy sólo escribe `PATH_TO_GDAL` y
   `SCRATCH`).
3. Copiar el CSV al directorio de inputs en `app/preparation/service.py`, junto a los `.tif`.

**Verificado (no hay riesgo de transporte):** los inputs no se suben al microservicio, se
comparten por **volumen Docker**. `app/elmfire/runner/client.py` envía la *ruta*
(`inputs_dir`) y `../elmfire-runner/app/runner.py` ejecuta ELMFIRE con `cwd=inputs_dir`. No
hay filtrado por extensión ni paso de transferencia: cualquier archivo escrito en el
directorio de inputs queda visible para ELMFIRE.

**Trampa verificada en el namelist:** el default de `MISCELLANEOUS_INPUTS_DIRECTORY` es
`'null'`. La sustitución por `FUELS_AND_TOPOGRAPHY_DIRECTORY` ocurre únicamente dentro de
`WRITE_FUEL_MODEL_TABLE`, que **sólo se ejecuta cuando** `FUEL_MODEL_FILE` **vale** `'null'`. Es
decir: al fijar `FUEL_MODEL_FILE` hay que fijar **también**
`MISCELLANEOUS_INPUTS_DIRECTORY`, o ELMFIRE buscará `null/fuel_models.csv` y abortar con
*"Problem opening fuel model table file"*. Falla ruidosa, pero es un `STOP` que hay que
anticipar.

Criterio de salida: una corrida de ELMFIRE consume nuestro CSV (comprobable porque el
archivo no es sobrescrito por ELMFIRE) y produce el mismo resultado que antes.

---



## A3 — Validar que todo código emitido existe en la tabla

Con A2 en su lugar, el criterio de aceptación de IGN-21 pasa a ser verificable de verdad.

Pasos:

1. Función que parsea el `fuel_models.csv` vigente y devuelve el conjunto de códigos.
2. En `fuels_builder`, tras escribir el raster: calcular los valores únicos presentes y
  **levantar excepción** si alguno no está en ese conjunto. Falla ruidosa, no warning —
   un código huérfano convierte silenciosamente parte del parque en incombustible, y eso
   invalida la corrida entera.
3. Test que emite deliberadamente un código inexistente y verifica que rompe.
4. Test que verifica que los códigos del crosswalk vigente están todos en la tabla.

Criterio de salida: es imposible producir un `fbfm40.tif` con un código que ELMFIRE vaya a
degradar a `NB` sin que el pipeline se detenga.

---



## A4 — `cbh` / `cbd` desde datos reales de dosel

Problema raíz: `app/elmfire/builder/canopy_builder.py:19-41` deriva altura de base de copa y
densidad aparente de copa desde una tabla indexada por código FBFM que sólo tiene **9
claves**. Cualquier código nuevo produce `-9999` (nodata) en `cbh.tif` y `cbd.tif`, en
silencio. Además es circular: el modelo de combustible *de superficie* no debería determinar
la estructura del dosel.

Decisión: **derivar** `cbh`**/**`cbd` **de los datos de dosel que ya ingerimos**, en vez de
inferirlos del código de combustible. Disponibles hoy (`app/ingestion/canopy/client.py`):


| Asset       | Fuente                                              | Resolución |
| ----------- | --------------------------------------------------- | ---------- |
| `canopy_cc` | Hansen Global Forest Change v1.11 (`treecover2000`) | 30 m       |
| `canopy_ch` | ETH Global Canopy Height 2020 (Lang et al.)         | 10 m       |


Alcance de la fundamentación: **breve**. Nota de método con la referencia canónica
(Cruz, Alexander & Wakimoto 2003, modelos de carga de copa a partir de variables de rodal),
no un capítulo de la tesis. Es infraestructura, no aporte.

Pasos:

1. Reemplazar `derive_cbh_cbd(fbfm40, ...)` por una derivación desde `cc` y `ch`.
2. Conservar el escalado Int16 vigente (`cbh` ×10 m, `cbd` ×100 kg/m³) — es interfaz de
  ELMFIRE, no se toca. Ver `.claude/skills/elmfire/references/interface-gotchas.md`.
3. Definir el comportamiento donde `cc` es bajo o nulo (no hay dosel): `cbh`/`cbd` = 0, no
  nodata.
4. Eliminar `_FBFM40_CBH` y `_FBFM40_CBD`. Que dejen de existir es el arreglo de raíz: no
  se puede olvidar de actualizar una tabla que ya no está.
5. Actualizar `docs/elmfire-mapping.md` y `docs/data-sources.md`, que hoy documentan la
  derivación desde `fbfm40.tif`.

Criterio de salida: `cbh.tif` y `cbd.tif` no dependen de `fbfm40.tif`; agregar un código de
combustible nuevo no puede romperlos.

---



## A5 — Rasterización por clase mayoritaria

Hoy `fuels_builder.worldcover_to_fbfm40()` usa `Resampling.nearest` para bajar de 10 m a
30 m: el píxel toma la clase que caiga en su centro. No es reproducible conceptualmente ni
defendible como criterio, y con CCS-BAP empeora, porque se pasa de **polígonos de 1 ha** a
píxeles de 900 m².

Decisión: **clase mayoritaria por píxel** (la que ocupa más área dentro del píxel de destino).

Justificación a documentar: es el criterio estándar para variables categóricas, es
determinista y no introduce sesgo direccional. Limitación a declarar explícitamente: pierde
corredores de combustible más angostos que 30 m, y en modelado de fuego la **continuidad**
del combustible gobierna la propagación — un corredor de matorral que conecta dos manchones
puede decidir si el fuego cruza. Es un supuesto del modelo, y como tal va enunciado en la
tesis, no escondido en el código.

Pasos:

1. Reemplazar `Resampling.nearest` por `Resampling.mode` en la reproyección, o agregar el
  remuestreo por moda si el orden reproyectar/reclasificar lo requiere.
2. **Reclasificar antes de agregar, no después.** La moda debe calcularse sobre clases de
  cobertura, no sobre códigos FBFM: los códigos FBFM son etiquetas arbitrarias y la moda
   sobre ellos es igualmente válida, pero mezclar los dos órdenes entre fuentes rompe la
   comparabilidad. Fijar el orden y documentarlo.
3. Registrar en el log qué fracción de píxeles tuvo clase mayoritaria ambigua (empate).
4. Test con un raster sintético de clases conocidas que verifica la moda.

Criterio de salida: la regla de agregación está declarada, testeada y es idéntica para todas
las fuentes de cobertura, de modo que la comparación IoU entre mapas no mida diferencias de
remuestreo.

---



## A6 — Humedad de combustible vivo explícita

Hallazgo verificado: ELMFIRE expone `LH_MOISTURE_CONTENT` y `LW_MOISTURE_CONTENT` en el
namelist, ambos con **default 60 %**. Nuestro `namelist_writer.py` no los escribe, así que
hoy aceptamos ese default sin declararlo.

Hoy es inocuo porque TL3 no tiene carga viva. **Deja de serlo en la Etapa B**, en el momento
en que aparezca cualquier modelo con componente vivo (SH, GS, TU). Ahí la humedad del
combustible vivo pasa a ser un driver de primer orden.

Importante: **son escalares globales para todo el dominio, no un raster por especie.** No
existe un `lh.tif`. Cualquier valor elegido es una media espacial y hay que justificar la
ponderación.

Pasos:

1. Escribir ambos parámetros explícitamente en `&INPUTS`, con el valor actual (60) en la
  Etapa A, para que quede registrado que es una decisión y no un default heredado.
2. Exponerlos como configuración, no como literal.
3. Dejar anotado en la Etapa B que el valor definitivo se toma de Bianchi & Defossé (2015),
  que mide LFMC por especie en Patagonia andina, ponderado por área de cada clase.

Criterio de salida: ningún parámetro con influencia física queda implícito en un default del
solver.

---



## A7 — Congelar el baseline

Es el entregable real de la etapa.

Pasos:

1. Corrida completa sobre el AOI definitivo con el crosswalk WorldCover vigente.
2. Archivar: `fbfm40.tif`, todos los inputs, el `elmfire.data`, el `fuel_models.csv` y las
  salidas, bajo un identificador estable de baseline.
3. Registrar las métricas descriptivas que ya calculó el audit, ahora sobre el AOI nuevo:
  distribución de códigos FBFM por área, fracción no combustible, intensidad de línea de
   fuego mediana.
4. Registrar el `IoU` del baseline con el harness B, puntuando **sólo el anillo de
  crecimiento** — nunca la unión con el `phi` inicial (`IGN-26-VALIDACION.md` §12.1: el 84 %
   de lo que la corrida reporta como quemado es la semilla FIRMS, y puntuar la unión daría
   un IoU halagüeño que no mide nada de ELMFIRE).
5. Estratificar por `pct_quemado` (§12.4): los tiles cerca de 0 o 100 son triviales; los
  informativos son los de quema parcial, que contienen el borde real del fuego.

Criterio de salida: existe un número de referencia, reproducible desde el repo, contra el
cual la Etapa B puede compararse.

---



## Riesgos


| Riesgo                                                           | Mitigación                                                                                        |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| El AOI ampliado hace la corrida de ELMFIRE demasiado lenta       | Medir antes de recortar; si hay que recortar, documentarlo como limitación de alcance             |
| `runner/client.py` ~~no transfiere archivos que no sean~~ `.tif` | **Descartado**: los inputs se comparten por volumen Docker y el runner corre con `cwd=inputs_dir` |
| La regeneración de rásteres estáticos con AOI nuevo tarda        | Es de una sola vez; correrla en background                                                        |
| El baseline queda desactualizado si alguien toca el pipeline     | La clave de caché de A1 lo detecta; el baseline archivado es inmutable                            |




## Decisiones registradas


| Decisión                      | Elegida                                          | Motivo                                                      |
| ----------------------------- | ------------------------------------------------ | ----------------------------------------------------------- |
| Alcance del AOI               | Ampliar al footprint del incendio                | Validar sobre 196 tiles en vez de 70                        |
| Fallo por código huérfano     | Excepción, no warning                            | Degrada el parque a incombustible en silencio               |
| `cbh`/`cbd`                   | Desde `cc`/`ch` reales, borrando las tablas FBFM | Elimina la clase de bug en vez de taparla                   |
| Fundamentación de `cbh`/`cbd` | Nota de método, no capítulo                      | Es infraestructura, no aporte de tesis                      |
| Regla de agregación           | Clase mayoritaria                                | Determinista y estándar para categóricas                    |
| Tabla de combustibles         | Propia desde el arranque                         | Hace verificable el criterio de IGN-21 y prepara la Etapa C |




## Fuentes

- ELMFIRE 2025.0212, `build/source/elmfire_init.f90` (`READ_FUEL_MODEL_TABLE_ROTHERMEL`,
`WRITE_FUEL_MODEL_TABLE`) y `build/source/elmfire_namelists.f90` —
[https://github.com/lautenberger/elmfire](https://github.com/lautenberger/elmfire)
- Cruz, M.G.; Alexander, M.E.; Wakimoto, R.H. (2003). *Assessing canopy fuel stratum
characteristics in crown fire prone fuel types of western North America.* IJWF 12:39-50.
- Scott, J.H.; Burgan, R.E. (2005). *Standard Fire Behavior Fuel Models.* RMRS-GTR-153.
- `docs/historico/SIMULATION_AUDIT.md` §1, §7.4 · `IGN-26-VALIDACION.md` §12.1, §12.3, §12.4, §12.5

