# Tarea E: auditoría de la cadena de insumos contra lo que ELMFIRE espera

Sólo lectura y análisis offline. ELMFIRE 2025.0212 (Fortran en `scratchpad/upstream/elmfire/build/source/`,
citado como `f90:línea`). Scripts de apoyo y números crudos en
`/private/tmp/claude-501/-Users-ichevallier-Projects-university-tesis-igniteinsights/550f7315-60bc-43cc-824e-2a1c8674fa42/scratchpad/E/`.
Datos usados: paquetes `epuyen-2025/calibracion-v6`, `epuyen-2025/cadena-96h-interior-retardo`
y `los-alerces-2016/calibracion-era5-v6` (objetos por sha en `data/benchmark/objetos/`), la caché
GFS de `data/benchmark/cache/gfs/` y los GRIB de `data/ensemble-poc/backtest-epuyen-2025-w02-gefs-2025011600/`.
Referencia de ROS: la Rothermel independiente de `scripts/pruebas_fisicas.py` (±2 % de ELMFIRE según
AUDITORIA-FISICA §3), a LH 30 %, LW 100 %, 7 mph a 20 pies, m1/m10/m100 = 7/9/12 %, sin pendiente.

Lo cerrado no se re-audita (ADJ, LW, dt, z0 0,22, CBH/CBD, orientación, Hansen, ERA5×1,3,
WindNinja, humedad en altura, viento de valle). Sólo aparece si traje un número nuevo.

## 1. Bug posible

### B1. `CROWN_RATIO` queda en el default de ELMFIRE (1,0 = abrigo máximo del dosel) — evidencia fuerte, sin decidir

- **Qué hace el repo.** `namelist_writer.py:372-434` no escribe `CROWN_RATIO`. Sólo se menciona en un
  docstring (`app/validation/copa.py:49`, "CROWN_RATIO = 1") y en `pruebas_fisicas.py:82`. Ningún `.md`
  del repo lo discute (grep sin resultados).
- **Qué hace ELMFIRE.** Default 1,0 (`elmfire_namelists.f90:595`), grupo `&SIMULATOR` (`:580`). Entra en
  la fracción de copa `F = 0,3333·CC·CROWN_RATIO` (`elmfire_init.f90:561`, `:620`) y de ahí en el
  WAF bajo dosel de Albini y Baughman, `WAF ∝ 1/√F` (`elmfire_init.f90:555-567`, `:615-622`). La
  plantilla de riesgo del propio proveedor lo fija en 0,3
  (`upstream/elmfire/runs/risk/template/empty_run/elmfire.data.all:73`); las de hindcast y forecast lo dejan
  en el default.
- **Por qué importa.** CR = 1 supone una copa que cubre el árbol de punta a pie: es el techo del abrigo,
  no un valor de rodal. El WAF sale 1,4× mayor con CR 0,5 y 1,8× con CR 0,3 (CC ≥ 40 %), y entre 1,6× y 2,2×
  con CC 20 %. Es la misma vía que el diagnóstico `dosel-coherente` (AUDITORIA-FISICA, WAF 0,08 contra
  0,46) tocó por otro lado.
- **Magnitud.** Con las celdas reales del paquete (`scratchpad/E/crown_ratio.py`):

  | Paquete | Celdas con dosel | ROS(CR 0,5)/ROS(CR 1) | ROS(CR 0,3)/ROS(CR 1) |
  |---|---|---|---|
  | Epuyén 2025, GR/GS/SH con dosel (20 % de lo quemable, mediana CC 44 %, CH 13,7 m) | 340.533 | 1,32 | 1,65 |
  | Epuyén 2025, TU/TL (21 %, CC 86 %, CH 18,7 m) | 353.752 | 1,19 | 1,40 |
  | Alerces 2016, GR/GS/SH con dosel (36 %) | 97.454 | 1,32 | 1,66 |
  | Alerces 2016, TU/TL (47 %) | 126.710 | 1,20 | 1,41 |

  Entre el 41 % y el 83 % de lo quemable está bajo dosel. Hacia el mismo lado que el viento ×1,3 que
  ya se midió y no se adoptó (viento ×1,6 "apenas mueve" Epuyén en el histórico), pero este entra sólo bajo
  dosel, donde el modelo es más lento que el fuego real (límites: día 1 explosivo, Alerces 2015).
- **Cómo verificarlo.** (1) Banco físico: `pruebas_fisicas.py dosel` con `CROWN_RATIO = 0.3` y `0.5` a
  mano en el namelist (el banco ya compara contra Albini y Baughman con CR 1). (2) Una receta nueva que
  agregue `CROWN_RATIO` a `&SIMULATOR` (hoy `write_namelist` no tiene el kwarg) sobre calibración v6. Ojo:
  LW 100 % se calibró con CR 1, así que el óptimo se mueve; es una decisión de insumo, no un barrido.
- **Veredicto.** Bug posible por omisión: es el mismo patrón que `CROWN_FIRE_MODEL` (default silencioso que
  luego se escribió explícito). No se ve en las 5 correcciones ni en los barridos de receta.

### B2. Latente, sin efecto medible hoy: vecinas del nodata del DEM quedan con pendiente NaN → int16

- `raster_aligner.py:174-190`: `np.gradient` con NaN deja NaN también en las celdas válidas vecinas del
  nodata; `np.round(nan).astype(np.int16)` es indefinido (0 en este Mac ARM, −32768 en x86).
  Medido: Epuyén 346 celdas válidas con gradiente NaN, hoy valen `slp = 0`. ELMFIRE acota
  `NINT(slp)` entre 0 y 90 (`elmfire_subs.f90:1075`), pero el `asp` pasa por `MIN(MAX(NINT(asp),0),360)`
  (`elmfire_level_set.f90:1692`), así que −32768 también quedaría acotado. Efecto: 346 celdas del borde
  norte. Se anota sólo porque la salida dependería de la arquitectura de quien prepara.

### B3. `cbh` de la tabla por tipo de bosque puede quedar por encima de `ch`

- `canopy_builder.py` pisa CBH con `CBH_BY_FUEL_MODEL_M` (TL6 6 m, TL5 4 m) sin acotar por CH. Medido:
  1.031 celdas (0,05 %) en Epuyén y 1.034 en Alerces 2016 con `cbh ≥ ch` y `cbd > 0`. ELMFIRE hace
  `CBD·MAX(CH−CBH,0)` (`elmfire_spread_rate.f90:165`) → carga de copa 0 en esas celdas; efecto despreciable.
  Además hay 4.369 celdas (0,2 %) con CH < 5 m y CBD > 0,3 kg/m³ (máximo 0,95), fuera del rango de la
  literatura para cualquier conífera. Cae dentro de lo cerrado (CBH/CBD) y de `copas-off`.

## 2. Aproximación documentada

Formato: qué hace el código; qué espera ELMFIRE; dónde está documentado; magnitud.

### Meteorología

- **Viento 10 m → 20 pies, aplicado una sola vez y en mph.** `weather_builder.py:51` (z0 0,22),
  `:81` (`× wind_height_factor() × MS_TO_MPH`). ELMFIRE lee `ws` como viento a 20 pies en mph:
  `C%WSMF = WS20_NOW · WAF · 5280/60` (`elmfire_subs.f90:429`, `:496`, `:552`); `WS_AT_10M` (un 0,87 fijo,
  `elmfire_io.f90:178`, default falso `elmfire_namelists.f90:162`) no se usa, así que no hay doble
  conversión. Factor del repo 0,870 = el 0,87 del proveedor (`elmfire_spread_rate.f90:140`). Las perillas
  del benchmark (`z0_desde_dosel`, `viento_atlas`) vuelven a 10 m antes de reconvertir, no apilan
  (`cadena.py` ~l. 240, `factor_rugosidad`). Documentado: `weather_builder.py:40-51`, PENDING_PARAMETERS §1 y §2.
  Sensibilidad: z0 de 0,03 a 1,0 m mueve el factor de 0,915 a 0,785 (+5 % / −10 % de viento → +6 % / −13 % de ROS).
- **Exponente real de ROS contra viento.** Sin el techo de Rothermel el exponente local
  `d ln ROS / d ln ws` es 0,9–1,4 (GR2 1,31, SH4 1,28, SH8 1,13, TU5 0,94, TL3 0,94–1,14, a 7–14 mph),
  no 1,5–2: la parte `1+φw` está amortiguada por φs, la carga y el WAF. Un viento ×0,87 baja el ROS
  12–16 %, ×1,3 lo sube 29–42 %, ×0,6 lo baja 35–47 %.
- **Sesgo de viento contra estaciones.** El GFS da 0,50–0,87× la estación y ERA5 0,40–0,70×
  (AUDITORIA-FISICA §3, "Dirección del viento…"). Con el exponente de arriba, si la estación fuera la verdad,
  el ROS sub-propagaría 20–55 %. Documentado y probado: ERA5×1,3 no adoptado, WindNinja, viento ×1,3/×1,6
  (recetas `viento-*`, `lw100-diurno-*`); PENDING_PARAMETERS §2 "Viento de superficie".
- **Interpolación espacial.** GFS 0,25° ≈ 21 km. `_read_aligned` (`weather_builder.py:275-310`) reproyecta
  u/v (nunca grados) con `Resampling.bilinear` a la grilla de 30 m, así que el clima ya viene en la grilla
  del combustible y el `MAP_FINE_TO_COARSE` de ELMFIRE (vecino más cercano, `elmfire_subs.f90:296-297`)
  es identidad. El AOI de Epuyén (40 × 44 km) cae en unas 2 × 2 celdas GFS (caché 7 × 7 con margen
  `MARGEN_GFS_GRADOS = 0,5`, `benchmark.py:185`): el "campo" de viento es una rampa suave, sin
  canalización de valle. Documentado: AUDITORIA-FISICA loop M, RIESGOS_Y_SUPOSICIONES §3,
  DIA-1-PROPUESTA §5.1.
- **Interpolación temporal.** `DT_METEOROLOGY = 3600`, bandas horarias, lineal en ELMFIRE
  (`elmfire_level_set.f90:516-520`); `wd` por el camino corto (`wd_for_elmfire`, hallazgo 3);
  `NUM_METEOROLOGY_TIMES` se escribe (hallazgo 1). Análisis encadenados f000–f005
  (`gfs/client.py` `download_analysis_series`): saltos de 0,15 m/s extra en el cambio de ciclo (0,59 contra
  0,43 m/s de salto vectorial horario en Epuyén; 0,63 contra 0,45 en Alerces 2023): ~5 % del viento medio,
  ignorable.
- **Ráfagas.** No se usa ninguna (no hay variable `GUST` en `gfs/client.py:19-24`; ni `WIND_FLUCTUATIONS`
  de ELMFIRE, que el proveedor activa en su plantilla de riesgo con intensidad 0,1). Estimación: con ROS ∝
  ws^1,2 y una variabilidad sub-horaria del 30 % de la media, E[ws^n]/E[ws]^n ≈ 1+n(n−1)σ²/2 → +1–2 %;
  con n=2 y 30 %, +9 %. La señal grande es la del día explosivo (ERA5 con ráfaga 4,4–4,7× la media en Epuyén
  el 15-ene-2025), documentada como opción 4 no adoptada en DIA-1-PROPUESTA §5.2 y como límite "Las Golondrinas"
  en PENDING_PARAMETERS §3.
- **Análisis (benchmark) contra pronóstico (app).** El benchmark y P-24 corren con el análisis encadenado
  (`IGN-26-VALIDACION.md:103`, caso `pronostico-v6`: "gfs-analisis-encadenado"); la app corre con un
  único ciclo, f000–f024, de hasta 4+6 h de antigüedad (`gfs/client.py:30-60`, `config.py:27`). Indicativo:
  en la ventana w02 de Epuyén (16-ene-2025) el control GEFS (pronóstico de 3 a 30 h) da 1,22× la rapidez
  media del análisis GFS (rango 1,03–1,33) con rumbos a ≤9° (`gefs_vs_analisis.py`): ±20 % de viento ≈
  ±20–25 % de ROS por un cambio de producto y de plazo. No se midió cuánto pierde el Dice P-24 con
  pronóstico; los backtests GEFS (ENSAMBLE-BACKTESTS-CONSOLIDADO) no incluyen la corrida "análisis" de
  referencia en el mismo reinicio.
- **Convergencia de meridianos (rumbo de la UTM).** `u/v` del GFS son este/norte verdaderos; los rásteres
  están en UTM 19S (meridiano central −69°) y ELMFIRE usa el norte de la malla (`GRID_DECLINATION = 0`,
  `ROTATE_WD = .FALSE.`, `elmfire_namelists.f90:125,148`). En Epuyén la convergencia es ≈ 1,6° y en Alerces ≈ 2,0°.
  Nunca se discutió (grep sin resultados). Efecto: rumbo de propagación corrido ~2°, ≈ 35 m por km
  recorrido; muy por debajo del desvío de dirección contra estaciones (−14° a +30°). No justifica una receta.

### SMN WRF 4 km

- **Existe, pero sólo como prototipo de ensamble, nunca como meteorología principal.**
  Ingesta: `app/ensemble/sources.py:374-452` (`smn_object_url`, `download_smn_wrf`, bucket
  `smn-ar-wrf.s3-us-west-2.amazonaws.com`) y `scripts/weather_ensemble_poc.py:747-748`
  (`download-smn`). Está sin versionar (`git status`: `app/ensemble/` y `scripts/weather_ensemble_poc.py`
  sin seguimiento). No hay ingesta SMN en `app/ingestion/` ni en la preparación (`app/preparation/service.py`
  sólo busca `gfs_u10/v10/t2m/rh`).
- Estado: ENSAMBLE-METEOROLOGICO-POC.md l.30 ("escenario regional independiente… nunca entra al
  denominador GEFS"), l.52-60 (formato), l.145 (una hora, 31,1 MB, recorte 66 × 50), l.503; y
  DECISIONES-TESIS-TRANSPARENCIA-INCERTIDUMBRE.md l.97 y 5.2.
  No hay corridas de ELMFIRE con SMN: `data/ensemble-poc/2026101200/` no tiene `smn-wrf` ni insumos SMN, y
  ningún informe de backtest lo menciona. P-24 nunca lo usó (usa GFS/ERA5, `pronostico.py`, casos `pronostico-v6`).
  Los dos únicos otros rastros son RIESGOS_Y_SUPOSICIONES l.244 (pedido de estaciones del SMN) y una cita de
  WRF-SFIRE en DIA-1-PROPUESTA l.143.
- Pendiente de verificar si algún día se usa: la dirección `dirViento10` de WRF podría ser relativa a la
  malla Lambert y no al norte verdadero (el adaptador la convierte a u/v sin rotarla). El error sería de
  unos pocos grados.

### Humedad

- **m1 = EMC de Nelson instantáneo con T y HR a 2 m del GFS, sin retardo, sin sol/sombra/pendiente.**
  `weather_builder.py:134-155` y `:220-232` (coeficientes de Nelson 1984, T en °F); m10 = EMC+2, m100 = EMC+5,
  recortados a [1, 40]; LH 30 %, LW 100 % constantes (`namelist_writer.py:182-183`). ELMFIRE los espera en
  porcentaje (`DEAD_MC_IN_PERCENT`/`LIVE_MC_IN_PERCENT` = .TRUE., `elmfire_io.f90:185-195`), e interpola
  linealmente entre bandas (`elmfire_subs.f90:439-451`). Documentado: `weather_builder.py:149-153` (nota
  `ponytail`), `humedad.py:1-14`, PENDING_PARAMETERS §2, `docs/elmfire.md:42`, HUMEDAD-ALTURA-PROPUESTA
  (cerrado como límite), RESULTADOS-CSS-BAP H3 y §880 (`fosberg-001`/`altura-001`: ±0,01 de Dice; estaciones dan m1
  5,9–6,6 % en las tardes de fuego, GFS 5,5–9,1 %).
- **Error del EMC instantáneo frente a un modelo con retardo de 1 h** (`humedad_retardo.py`, paquete
  `epuyen-2025/cadena-96h-interior-retardo`, `m1.tif` contra `m1_retardo.tif`, media espacial por hora; UTC−3 = hora local):

  | Hora local (ART) | m1 instantáneo | m1 con retardo | Dif. |
  |---|---|---|---|
  | 12 (ventana 0, h1) | 12,0 % | 14,4 % | +2,4 |
  | 13 | 8,2 | 10,6 | +2,3 |
  | 14 | 7,1 | 8,4 | +1,3 |
  | 15 | 6,9 | 7,4 | +0,6 |
  | 16–18 (pico de propagación) | 6,7–6,8 | 6,8–7,0 | +0,1 a +0,3 |
  | 19–20 | 7,2–8,4 | 7,1–7,9 | −0,2 a −0,4 |
  | 21–23 (noche) | 12,4–19,8 | 11,0–18,2 | −1,4 a −2,0 |

  En el pico de la tarde el instantáneo es 0,0–0,3 pp más seco que el rezagado (ventana 1: 0,0–0,3 pp): a lo
  sumo +1–2 % de ROS. El error está a media mañana (hasta 2,4 pp demasiado seco, ROS +4–13 % en SH8, TU y TL; en SH4,
  ver abajo) y a la noche (−1,4 a −2 pp: demasiado húmedo, −3–10 %). Cancela en el día; coincide con el
  histórico ("el modelo de retardo no es la palanca", RESULTADOS.md §8). Para m10/m100 la diferencia es
  grande (m10 instantáneo+2 = 8,7 % a las 17 ART contra 12,7 % con retardo; m100 11,7 contra 10,3) pero sólo
  pesa en SH4 (abajo).
- **SH4 está cerca del precipicio de extinción viva con LW 100 %** (`sh4.py`, `sens.py`). Es el combustible
  más común del mapa (24 % de lo quemable en Epuyén, 28 % en Alerces 2016) y el de CCS-BAP arbustal nativo.
  A 7 mph y m1 = 7 %: ROS 5,9 m/min con LW 80 %, 4,6 con 90, 3,0 con 100, 1,5 con 110 y 1,4 con 120.
  A LW 100 %: m1 6 → 7 → 9 % (con m10/m100 acompañando) da 3,8 → 3,0 → 1,5 m/min; m1 +1 pp solo da −25 %; m10 +4 pp con m1 fijo da −41 %. Con GR2,
  SH3, SH8, TU3/TU5 y TL3/TL6 el ROS cambia 2–6 % por pp de m1 y ≤4 % por +4 pp de m10. Esto explica por
  qué LW calibra de forma tan aguda (intervalo sin sobre-propagación [97; 110] %, loop E) y que cada error de
  ±1 pp de m1 en SH4 valga ±25 % de ROS: más que cualquier error de viento de ±15 %. Lo documentado
  ("m10/m100 insensibles", RESULTADOS-CSS-BAP §880) es verdad para el conjunto, pero no para SH4: mérito de
  una nota, no de una receta (el modelo-v0 no se reabre por esto).

### Combustibles y dosel

- **Tabla.** CCS-BAP → FBFM40: `fuels_builder.py:256-318` (`CCSBAP_TO_FBFM40`, `CCSBAP_N3_OVERRIDES`,
  `CCSBAP_SOBRE_LIMITE_BOSQUE` l.320); MapBiomas l.223, WorldCover l.24. Documento: `docs/crosswalk.md`
  y DECISIONES-MODELO-V0. Es el aporte de la tesis y el sesgo TL3 es el baseline: no se discute.
  `fuel_models.csv` del repo = la tabla de ELMFIRE (`elmfire_init.f90:671-721`): diff limpio salvo NB91–99 extras
  y un GR2 duplicado en el fuente de ELMFIRE (l.681-682); ningún código del paquete fuera de la tabla.
- **Resolución y rasterizado.** Vector de 1 ha → moda sobre 3 × 3 subpíxeles de 10 m (`ccsbap_to_fbfm40`, l.512-585);
  mapas ráster por `Resampling.mode`. Documentado: ETAPA-A §A5 (citado en el docstring).
- **Unidades del dosel.** `cc` % entero 0–100, `ch` 10×m, `cbh` 10×m, `cbd` 100×kg/m³, Int16 con nodata −9999
  (`canopy_builder.py:67-125` y `:127-225`; `preparation/service.py` multiplica `ch` por 10). ELMFIRE los reescala con los
  defaults `CC_IN_PERCENT`, `CH_TIMES_10`, `CBH_TIMES_10`, `CBD_TIMES_100` (= .TRUE., `elmfire_namelists.f90:112-118`;
  `elmfire_io.f90:278-308`, el nodata se salta con `.NE. NODATA_VALUE`). Confirmado también en AUDITORIA-FISICA
  §3 y en el paquete: `cc` 0–100, `ch` máx. 481 (48,1 m), `cbh` máx. 200, `cbd` máx. 98.
  El nodata `ch/cbh/cbd` (9,5 % de Epuyén, 8,9 % de Alerces) se solapa con `cc = 0`: 0 celdas con `cc > 0` y `ch` nodata,
  0 celdas quemables con `cc ≥ 15` e `ICH = 0` (WAF 0, hallazgo 4 cerrado), sin `ch < 2 m` con `cc > 0`.
  `CBD` nodata (< 1e-3) deja la celda sin fuego de copas (`elmfire_spread_rate.f90:161`).
- **Dosel sobre combustible no forestal.** 20 % (Epuyén) y 36 % (Alerces 2016) de lo quemable es GR/GS/SH
  con `cc > 0`; ELMFIRE le da WAF de bosque (`dosel-coherente`, medido y no adoptado). Más arriba, B1 muestra
  que ese WAF depende de un default sin decidir.
- **Alineación.** Todos los rásteres (dem, slp, asp, cc, ch, cbh, cbd, adj, fbfm40, phi, ws, wd, m1/m10/m100) comparten transform, tamaño
  y CRS (EPSG:32719, 30 m) en los tres paquetes (`scratchpad/E/grillas.py`); `A_SRS`, esquina SO y celda salen
  del `dem.tif` (`namelist_writer.py:444-459`). La esquina no es múltiplo de 30 (p. ej. 282.379,6) y se escribe con
  2 decimales: ≤ 0,005 m, irrelevante. `fbfm40` declara `nodata = 99`, que también es NB9: sólo afecta a lectores
  GDAL de la capa (ELMFIRE trata 90–100 como no combustible, `elmfire_init.f90:~150`).

### Topografía

- **Fuente y remuestreo.** Copernicus GLO-30 (COP30, `ingestion/topography/opentopography/client.py:22`) → UTM 19S 30 m,
  bilinear, Int16 (`raster_aligner.py:135-160`). GLO-30 es un modelo de superficie (incluye el dosel); eso no
  está documentado como tal. Medido: a igual terreno a 150 m, el cociente tan²(30 m)/tan²(150 m) en bosque
  (CH ≥ 15 m, CC ≥ 50 %) contra abierto es 1,03 (Epuyén) y 0,99 (Alerces 2016): sin exceso de pendiente por el dosel.
- **Unidades.** `slp` en grados enteros y `asp` en grados (0–359) como ELMFIRE los usa
  (`TANSLP2(NINT(slp))`, `elmfire_subs.f90:1075`; `ASP` por `NINT`, `elmfire_level_set.f90:1692`), con la
  convención "hacia dónde mira la ladera" (AUDITORIA-FISICA, orientación v3, pinned por `tests/test_topo_aspect.py`).
  El redondeo a entero es el que ELMFIRE hace de todos modos (tan² media 0,1599 entero contra 0,1598
  continuo).
- **Cálculo.** `np.gradient` a 2 celdas (base 60 m) en vez de Horn 3 × 3: 2 % más de tan² media que Horn
  (0,1598 contra 0,1566 en Epuyén; 0,1969 contra 0,1928 en Alerces 2016) → ≈ +2 % en φs.
  Pendiente media 15,4° (Epuyén), 18,5° (Alerces 2016); 36–45 % del terreno supera 20°, 9–11 % supera 35°.
  No hay documento específico; el efecto es menor que la discretización de ELMFIRE.

### Benchmark contra app (punto 6)

- **Mismo código en los builders.** El benchmark parte de la preparación de la app (`origen.preparacion` del paquete) y la
  completa con `cadena._preparar` (`validation/cadena.py:119-300`). `adj = 1`, LH 30, LW 100, dt 30/300, `NUM_METEOROLOGY_TIMES` y
  el relleno de columnas salen de `write_namelist` en los dos caminos. `HUMEDAD_VIVA_BASE` fija LW 110 pero la receta `lw-100-001` lo pisa con
  100: iguales (`cadena.py` ~l. 247-252).
- **Diferencias, todas documentadas:** (i) clima: análisis encadenado contra pronóstico de un ciclo (arriba); ERA5×1,3 sólo en el benchmark
  (AUDITORIA-FISICA loop D); (ii) año del mapa de combustible por caso (`fbfm40_ccsbap2013/2017`) contra el 2017 fijo de la app; (iii) el
  reasignado por edad de quema (LYQ-3) vive en la receta del benchmark y se aplica siempre en la app (ESTADO-RESEARCH l.115-120; no
  regresión 0,439/0,501); (iv) ventana de 24 h contra `simulation_hours=12` fijo en la preparación de la app
  (`preparation/service.py`); (v) las perillas de `cadena._preparar` no existen en la app (humedad con criterio, viento
  diurno, atlas). Ninguna es un bug; (i) es la que más puede abrir una brecha entre el Dice del benchmark y el
  desempeño operativo.
- Paquetes anteriores a la auditoría física (p. ej. `cadena-96h-interior-retardo`, `phi` en metros hasta 49.650) los
  rechaza `cadena.correr` (`semilla_en_metros`); sirvieron aquí sólo para comparar `m1` contra `m1_retardo`.

## 3. Orden por efecto estimado sobre la velocidad de propagación

1. B1 `CROWN_RATIO` por omisión: +20–66 % de ROS en el 41–83 % de lo quemable (bajo dosel).
2. m1 en SH4 (24–28 % de lo quemable): ±25 % de ROS por pp; encadenado con LW (aproximación documentada, sensibilidad no).
3. Sesgo de viento del reanálisis (0,4–0,87×): −20 a −55 % si la estación es la verdad (documentado, probado, no adoptado).
4. Análisis contra pronóstico en la app: ±20–25 % (indicativo, un caso).
5. EMC instantáneo contra retardo en m1: ±1–2 % en el pico, ±4–13 % a media mañana (cancela en el día).
6. Convergencia de meridianos (~2° de rumbo), DSM (sin efecto medible), pendiente a 2 celdas (+2 % φs), ráfagas subhorarias (+1–9 %).
