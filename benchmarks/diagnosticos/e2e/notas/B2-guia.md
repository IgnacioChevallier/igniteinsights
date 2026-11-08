# B2 — Conversión de `ELMFIRE_Guide.pdf`

Salida: `docs/referencias/elmfire/elmfire-guide.md` (130 páginas, marcadores `[p. N]` = página del PDF; la numeración impresa es N-1).

**Versión documentada: ELMFIRE 1.1** ("ELMFIRE1.1 User Guide", Cloudfire Inc. / UC Berkeley / U. Maryland, junio 2026; la p. 6 cita además el branch `2025.1002`). El proyecto está fijado en **2025.0212** y no se actualiza. Keywords, defaults y comportamiento pueden diferir: la verdad es el fuente del tag 2025.0212. Cualquier cita de esta guía debe contrastarse con ese tag antes de usarla para tocar `app/elmfire/`.

Método: texto extraído con PyMuPDF (subíndices `_` recuperados de los trazos del PDF); ecuaciones (cap. 2, 3, 4) transcritas a LaTeX desde las imágenes de página; tablas del cap. 5 reconstruidas por posición (páginas apaisadas). Erratas del original transcritas tal cual (ver "Inconsistencias").

## Índice de secciones (página PDF)

| Sección | p. | Sección | p. |
|---|---|---|---|
| 1.1 Introduction (instalación, primer run) | 5 | 2.2 Wildfire Spread (Rothermel) | 52 |
| 1.2 Surface Fire Spread (inputs, unidades) | 9 | 2.2.1 Modelo canadiense FBP | 53 |
| 1.2.1 Alternative Spread Models (CFFDRS) | 11 | 2.2.2 Wind Scaling (WAF) | 55 |
| 1.2.2 Grid Declination | 12 | 2.2.3 Directional Rate of Spread (elipse) | 55 |
| 1.3 Domain size / extents | 12 | 2.2.4 Canopy Fires | 56 |
| 1.4 Time (dt, CFL, interpolación) | 12 | 2.2.5 Level Set Propagation | 57 |
| 1.4.1 Overnight Adjustment | 13 | 2.2.6 Acceleration | 60 |
| 1.5 Fire Initialization | 14 | 2.3 Spotting (generación, transporte, ignición, consumo) | 60 |
| 1.6 Outputs (Tablas 1.1, 1.2) | 15 | 2.3.2 Transport | 62 |
| 1.7 Miscellaneous (fuel_models.csv) | 19 | 2.3.3 Ignition | 67 |
| 1.8 Parallelisation and MPI | 20 | 2.3.4 Decay and Consumption | 69 |
| 1.9 Physics and Numerics options | 21 | 2.4 Smoke | 71 |
| 1.9.2 Elliptical dimensions | 21 | 2.5 Suppression | 73 |
| 1.9.3 Crown fire | 22 | 2.6 Urban Fire Spread (Hamada, WU-E) | 81 |
| 1.9.4 Wind fluctuations | 22 | 2.7 Diurnal Profiles (sunrise/sunset) | 85 |
| 1.9.5 Misc. (BANDTHICKNESS, SEED) | 22 | 3 Verification (3.1 p. 87; 3.2 p. 88) | 87 |
| 1.9.6 Cell Untagging | 23 | 3.2.1-3.2.6 Point, Windy, Valley, Quadrant, Complex, Moisture Quad | 92-98 |
| 1.9.7 End Conditions | 23 | 3.2.7 Canopy | 100 |
| 1.10 Barriers and Breaching | 23 | 3.2.8 Firebrand | 102 |
| 1.11 Spotting | 24 | 3.2.9 Overnight | 104 |
| 1.11.1-1.11.4 Generation / Transport / Accumulation / Ignition | 24 / 27 / 29 / 29 | 3.2.10 Suppression | 106 |
| 1.11.5 Consumption | 31 | 3.3 FBP Test Cases (Tabla 3.2) | 107 |
| 1.11.6 Cheat sheet (Tabla 1.3) | 31 | 4.1 CONUS: Automated Validation (WildfireAV) | 109 |
| 1.11.7 Stochastic Parameters | 32 | 4.2 Canada: Dogrib Fire | 110 |
| 1.11.8 Spotting Outputs | 33 | 5 Input Parameters, Tabla 5.1 (MISCELLANEOUS, SMOKE p. 116; INPUTS 117-118; OUTPUTS 119; TIME_CONTROL y MONTE_CARLO 121; SIMULATOR 123; WUI 124; SPOTTING 124-126; SUPPRESSION 126; CALIBRATION 127) | 116-127 |
| 1.12 Monte Carlo Analysis | 34 | Bibliography | 128-130 |
| 1.12.1-1.12.5 Ignitions / Weather / Perturbaciones de rasters / Wind fluct. / Outputs | 34 / 36 / 36 / 39 / 39 | 1.13 Urban Fire Spread | 39 |
| 1.14 Suppression (initial / extended) | 42 | 1.15 Fire Potential Mode (MODE) | 45 |
| 1.16 Assets at Risk | 45 | 1.17 Pyrome Calibration | 46 |
| 1.18 Smoke (HYSPLIT) | 47 | 1.19 Memory Optimization (MEMOPT) | 48 |
| 1.20 Docker | 48 | 1.21 Data sources / helper scripts | 49 |
| 1.22 Process Flowchart (orden del bucle level set) | 50 | | |

## Secciones prioritarias por tema

1. **Propagación superficial (Rothermel y ajustes)**: 2.2 (p. 52, ec. 2.1-2.3), 1.2 (p. 9, rasters de entrada y unidades), 1.9.2 (p. 21, `MAX_LOW`, `WSMFEFF_LOW_MULT`, `PHIW_ADJ`, `PHIS_ADJ`), 2.2.3 (p. 55, elipse, ec. 2.8-2.13), 2.2.2 (p. 55, WAF), 1.4.1 y 2.7 (p. 13, 85, ajuste nocturno), `ADJ_FILENAME` (p. 9) y 1.17 (p. 46, factores por pyrome), 2.2.6 (p. 60, aceleración), 3.2.1-3.2.6 (p. 92-98, verificación vs BEHAVE), Tabla 5.1 (p. 123, SIMULATOR).
2. **Copa (iniciación y propagación)**: 1.9.3 (p. 22: `CROWN_FIRE_MODEL` = 1 Cruz 2005, `CRITICAL_CANOPY_COVER` 0.39, `CROWN_FIRE_ADJ`, `CROWN_FIRE_SPREAD_RATE_LIMIT` 250 ft/min), 2.2.4 (p. 56-57: Van Wagner I0, R0, R_C,P de Cruz, pasiva/activa, φ_w,C), 3.2.7 (p. 100, verificación), unidades CBH/CBD/CH en 1.2 (p. 10).
3. **Pavesas (spotting)**: 1.11 (p. 24-33), 2.3 (p. 60-71, modelos UMD/Qin), Tabla 1.3 (p. 31), 1.11.7 (p. 32, parámetros estocásticos), Tabla 5.1 SPOTTING (p. 124-126; ojo `USE_SUPERSEDED_SPOTTING` default `.TRUE.` en p. 126), 3.2.8 (p. 102).
4. **WAF / dosel**: 2.2.2 (p. 55, ec. 2.6-2.7 y tabla por CC para FBP), 3.2.2 (p. 93, ec. 3.1-3.2 con CH/CBH), 1.2 (p. 11, `CROWN_RATIO`), 1.2 (p. 10, CC en %), 1.9.3 (CC crítico).
5. **Humedad de combustibles**: 1.2 (p. 9-10: M1/M10/M100 rasters, `LH/LW/FOLIAR_MOISTURE_CONTENT`, `USE_CONSTANT_*`, bandas y `DT_METEOROLOGY`), 1.4 (p. 12-13, `DT_INTERPOLATE_*`), 3.2.6 (p. 98, Moisture Quad), 4.2 (p. 112, 1-h FMC vs HFFMC), 2.2.1 (p. 53, M en FBP).
6. **Esquema numérico / paso temporal**: 2.2.5 (p. 57-60: level set, RK2, superbee, ec. 10a/10b), 1.4 (p. 12-13: `SIMULATION_DT`, `SIMULATION_DTMAX`, `TARGET_CFL`), 1.9.5 (p. 22, `BANDTHICKNESS`), 1.9.6-1.9.7 (p. 23, untagging, condiciones de fin), 1.22 (p. 50-51, orden del bucle), 2.3.2 (p. 64, CFL propio del transporte de pavesas), 1.10 (p. 24, spotting fuerza `BANDTHICKNESS = 1`).
7. **Monte Carlo / ensambles / perturbaciones**: 1.12 (p. 34-39), en particular 1.12.2 (p. 36, bandas de meteorología: `METEOROLOGY_BAND_START/STOP/SKIP_INTERVAL`, `NUM_METEOROLOGY_TIMES`), 1.12.3 (p. 36-38, `RASTER_TO_PERTURB`, `PDF_TYPE` UNIFORM/GAUSSIAN/LOGNORMAL, perturbables: ADJ, CBD, CBH, CC, CH, FMC, M1, M10, M100, MLH, MLW, WAF, WD, WS), 1.12.4 (p. 39, fluctuaciones de viento), 1.9.4 (p. 22), 1.12.5 (p. 39, `CALCULATE_TIMES_BURNED`), 1.8 (p. 20, MPI), Tabla 5.1 MONTE_CARLO (p. 121-122), 1.11.7 (p. 32).
8. **Calibración**: 1.17 (p. 46-47, pyromes y constantes por pyrome), 1.4.1 (p. 13), `ADJ_FILENAME`, `PHIW_ADJ`/`PHIS_ADJ`/`WSMFEFF_LOW_MULT` (p. 21-22), `CROWN_FIRE_ADJ` (p. 22), 4.1 (p. 109, WildfireAV: Jaccard 0.178, Sorensen 0.278, kappa 0.241), 4.2 (p. 110-114, Dogrib y diferencia en rate de spread hacia atrás, ec. de ROS_b p. 113).

## Secciones con funciones que probablemente NO existen en 2025.0212

Sin verificar contra el tag 2025.0212; lo único contrastado es la nota de memoria "ELMFIRE 1.1 interface changes" (binario `elmfire_1.1`, `&COMPUTATIONAL_DOMAIN` eliminado, `DEBUG_LEVEL` -> `FEEDBACK_LEVEL`, `LANDSCAPE_FILENAME`, `USE_BARRIERS`, `SPREAD_RATE_IN_M`, CFFDRS). Candidatas:

- Seguras según esa nota: 1.1.2/1.2 `LANDSCAPE_FILENAME` multibanda (p. 6-9); 1.3 dominio derivado con GDAL (p. 12); 1.9.1 `FEEDBACK_LEVEL` (p. 21); 1.10 barreras y breaching (p. 23-24); 1.6 `SPREAD_RATE_IN_M` (p. 15); 1.2.1 y 2.2.1 modelo CFFDRS/FBP (p. 11, 53; 3.3 p. 107; 4.2 p. 110).
- Probables (nuevas o reescritas): 1.11 y 2.3 spotting nuevo (`USE_SUPERSEDED_SPOTTING`, `GENERATION_MODEL` PER-AREA/PER-MW, `SPOTTING_DISTANCE_MODEL` EMPIRICAL, `ACCUMULATION_MODEL` EULERIAN, `IGNITION_MODEL` SIMPLE/PHYSICAL, consumo; p. 24-33, 60-71); 1.11.7 spotting estocástico (p. 32); 1.11.8 y Tabla 1.1 salidas de pavesas (`DUMP_EMBER_FLUX*`, `DUMP_SPOTTING_OUTPUTS`, `ACCUMULATE_EMBER_FLUX`, bins; p. 16-17, 33-34); 1.13 y 2.6 modelos urbanos Hamada/WU-E (p. 39-42, 81-85); 1.14 y 2.5 supresión, en especial extended attack modelo 1 espacial (p. 42-45, 73-81); 1.17 pyromes (p. 46); 1.18 y 2.4 humo/HYSPLIT (p. 47, 71); 1.19 MEMOPT `WX_BANDS_KEPT_IN_MEM` (p. 48); 1.16 assets at risk (p. 45); 1.7 `USE_TILED_IO`, `USE_EXISTING_BSQS`, `USE_BSQ_XML_HEADER` (p. 20); 1.12.3 `PDF_TYPE` GAUSSIAN/LOGNORMAL y `TEMPORAL_PERTURBATION` DYNAMIC (p. 37); 1.9.6-1.9.7 condiciones de fin y untagging (p. 23); 1.4.1 `BURN_PERIOD_*` (p. 13); 1.2.2 `ROTATE_WD`/`ROTATE_ASP` (p. 12); `WX_BILINEAR_INTERPOLATION` (p. 11).
- Probablemente presentes (núcleo histórico): Rothermel, level set + RK2 + superbee, elipse FARSITE, copa Cruz/Van Wagner, Monte Carlo con ignición aleatoria y rasters perturbados, fluctuaciones de viento, `MODE`. Aun así, defaults a verificar.

## Inconsistencias internas de la guía (anotadas, no corregidas)

- CFL: p. 60 dice "set as standard as 0.2"; `TARGET_CFL` default = 0.4 en Tabla 5.1 (p. 121) y en el ejemplo de 1.4 (p. 12).
- Ec. 2.12 (p. 56): `b` sin paréntesis alrededor de `|V_DMS| + V_s0` (transcrita tal cual).
- Esquema RK2 (p. 60): las ecuaciones se numeran "(10a)/(10b)" en el original, no "2.x".
- Fig. 2.3 (p. 74): la tabla de POC no se reproduce desde la fórmula impresa.
- Cap. 3 (p. 90 vs 96): FB4 head ROS = 1.493 en la tabla de verificación pero 1.974 en el texto; Firebrands falla (+44 %, p. 90); FBP cases 13-15 fallan en FI (p. 108, explicado por carga de pasto).
- Tabla 1.3 (p. 31) imprime `NUMBERS_MIN/MAX` donde el texto usa `NEMBERS_MIN/MAX`.
- Comandos de instalación de las pp. 5-6 impresos sin espacios (transcritos tal cual).
