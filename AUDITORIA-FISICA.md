# Auditoría física del pipeline ELMFIRE

> Rama `feat/auditoria-fisica`, desde `main` (que ya contiene `feat/calibracion-ccsbap`).
> Antecedente: `RESULTADOS-CSS-BAP.md` (no se edita). Banco de pruebas:
> `scripts/pruebas_fisicas.py`. Fuente de ELMFIRE consultado: etiqueta `2025.0212`.

## 1. Estado actual

*(se reescribe en cada loop — última: loop L, 2026-10-03)*

- **Receta final: `lw-100-001` sobre los protocolos v6** (LW 100 %, ADJ 1, CCS-BAP anterior al
  fuego), con el crosswalk y el dosel del loop L ya en los builders: Estepa → GR2 y sobre 1.300 m →
  NB9, remanente → SH3, CBH por tipo de bosque de literatura, CBD 0,16 en pino y sin dosel en la
  pérdida previa de Hansen. `benchmarks/particion.json` apunta a v6. Las decisiones y su
  fundamento: `DECISIONES-DIRECTOR.md`.
  - Calibración (7): media **0,439**, mediana **0,501**, sin alarmas fuera del caso límite (v5:
    0,381 / 0,451). IoU 0,297, precisión 0,448, recall 0,504.
  - Validación cruzada sobre las 28 recetas del loop: 0,424 / 0,501 fuera de muestra.
  - Prueba (4): 0,191 / 0,167, 2 alarmas (v5: 0,213 / 0,220, 3 alarmas). Mejoran Café, Epuyén 2019 y
    Alerces 2015; El Turbio baja (0,296 → 0,122) porque deja de sobre-propagar (5,73 → 1,08).
  - Costo: Alerces 2016 (0,451 → 0,389): la copa del bosque con caña lo acelera.
  - Robustez a la ignición sobre v6: ver loop L.
- **Bugs confirmados y corregidos:** 1 (clima congelado en la banda 0), 2 (`phi` en metros: frente
  a ~0,5×), 3 (`wd` interpolado como ángulo plano), 4 (cobertura sin altura), 5 (grilla de clima
  alta), la capa "sin ignición" leída como quemada y los GeoTIFF sin comprimir. En el benchmark desde
  v5. El loop L no encontró bugs nuevos: cambió insumos.
- **Medido y no adoptado:** dosel coherente con el combustible (sospecha 6, también por clase), ERA5
  × 1,3, pavesas (plantilla de hindcast: inactivas; fuertes: alarmas), lenga achaparrada → SH3,
  LW 95 / 105 %, combustible de quema de 0–2 años.
- **Métricas:** la principal guarda Dice, IoU, precisión, recall y tp/fp/fn; `tabla` y `objetivo`
  las muestran, también para las iteraciones viejas (las leen de su ventana).
- **Límites que quedan:** el día explosivo (Epuyén 2025: 167 ha a las 24 h contra 1.730, ni con la
  copa medida del pino), la supresión (El Turbio, Epuyén 2019), la dirección del viento de superficie
  (Alerces 2015, loop K) y Las Golondrinas.
- **Próximo paso:** si sigue el trabajo, el viento de superficie en valles (el error de dirección
  es lo que más queda en los incendios de terreno empinado) y un CBH medido para coihue y ciprés con
  caña, el valor más incierto de la tabla y el que más mueve (Cholila contra Alerces 2016).

## 2. Supuestos

1. **La rama sale de `main`.** `feat/calibracion-ccsbap` ya está mergeada en `main` (commit
   `68b734e` + el de Railway `4af8a3c`); no hay otra punta con `RESULTADOS-CSS-BAP.md`.
2. **Los cambios de Railway no alteran las corridas.** `verificar` da TOA idéntico byte a byte
   en `los-alerces-2023/calibracion-v3 lw100-adj115-001` (3 ventanas) y
   `epuyen-2025/calibracion-v3 base-001` (4 ventanas). Con
   `elmfire_runner_transfer_files = False` (valor por defecto) el cliente no transfiere nada.
3. **Los protocolos anteriores quedan congelados, no se re-corren con código nuevo.** Las
   correcciones cambian lo que recibe ELMFIRE; `verificar` sigue reproduciendo los manifiestos
   viejos (re-ejecuta los insumos registrados), pero una receta nueva sobre un paquete viejo
   mezclaría la semilla vieja (metros) con ventanas encadenadas nuevas (±1). `cadena.correr`
   lo rechaza: un paquete con `phi` > 1 exige re-empaquetar como `-v4`. Sin banderas de modo
   heredado: el código sólo sabe hacer lo correcto.
4. **La transformación de `wd` va al final de `cadena._preparar`**, después de las perillas,
   porque `rotacion_viento` y `viento_atlas` vuelven a envolver el ángulo a [0, 360). También
   la aplica `derive_wind`, así la app queda cubierta.
5. **La referencia de Rothermel del banco pesa la carga neta por subclase de tamaño**
   (g_ij, Albini 1976), como BehavePlus. Con f_ij a secas (Rothermel 1972) daba un 17 % menos
   en GR2: era mi error, no de ELMFIRE (una transcripción de su código da exactamente su `vs`).
6. **Espacio en disco.** A las 01:21 del 29-sep el disco llegó al 100 % (932 GB; el almacén
   del benchmark ocupa 220 GB y creció 5,6 GB en 4 h, casi todo clima sin comprimir de los
   paquetes v4) y Docker Desktop se cayó. Se liberó sin tocar ningún registro:
   - `data/benchmark/trabajo/` (scratch que cada corrida recrea);
   - los objetos huérfanos creados ese día por corridas abortadas (0,67 GB); los huérfanos
     viejos (2,9 GB) se dejan, porque el historial de git puede referenciarlos;
   - `data/benchmark/vistas/` comprimido en el lugar con DEFLATE, verificando igualdad de
     datos archivo por archivo: de 14,65 a 0,27 GB.

   Y en la causa: los escritores del repo (clima, `phi`, perillas de `cadena`, capas del
   paquete, vistas) escriben GeoTIFF con DEFLATE. ELMFIRE lee los insumos con
   `gdal_translate` (`elmfire_io.f90`), así que la compresión no cambia lo que recibe.
7. **Tolerancias del banco:** ±10 % en velocidad, ±15 % en largo/ancho, ±5° en rumbo, ±1
   celda en posición. Son las del pedido o las que admite la discretización a 10–30 m.

## 3. Hallazgos

### Hallazgo 1 — ELMFIRE usaba la banda 0 del clima durante toda la corrida

- **Evidencia en el fuente.** `&MONTE_CARLO NUM_METEOROLOGY_TIMES` vale 1 por defecto
  (`elmfire_namelists.f90`, `READ_MONTE_CARLO`, que corre siempre, esté o no el grupo). El
  level set calcula la banda con `ITLO = MIN(1 + FLOOR(T/DT_METEOROLOGY), NUM_METEOROLOGY_TIMES)`
  y sólo la recalcula después del primer paso si `NUM_METEOROLOGY_TIMES > 1`
  (`elmfire_level_set.f90`). Con el valor por defecto, banda 1 (la 0 del repo) para siempre.
  Los tutoriales transitorios de ELMFIRE (02 y 03) lo fijan en 8. El repo nunca lo escribió.
- **Experimento** (`pruebas_fisicas.py tiempo`): plano, GR2, banda 0 sin viento y desde la
  banda 1 viento de 20 mph del oeste, 2 h.
  - Namelist anterior: círculo, desplazamiento 0 m (3,6 ha en 3 h: la velocidad sin viento).
  - Con `NUM_METEOROLOGY_TIMES`: la cabeza va al este, 1.063 m de desplazamiento.
- **Alcance.** Todas las corridas del benchmark (cada ventana de 24 h, con el clima de su
  primera hora) y de la app. En la app además hacía inútil el anclaje de `SIMULATION_TSTART`:
  siempre se usaba la banda 0, no la hora de la ignición.
  - Las ventanas arrancan a la hora de la ignición (o 24 h después), así que cada incendio corrió
    con **un único instante del día congelado**: Alerces 2023 (22 h ART) con el viento y la
    humedad de la noche; los que arrancan a la tarde, con la tarde entera.
  - Explica, por ejemplo, que la hora de ignición (±2 h) moviera tanto el Dice (loop 5c): movía
    *todo* el clima de la ventana, no sólo el arranque.
- **Corrección.** `write_namelist` escribe `&MONTE_CARLO NUM_METEOROLOGY_TIMES` con la
  cantidad de bandas de `ws.tif` (`weather_band_count`), y `validate_weather_coverage` rechaza
  rásters de clima con distinta cantidad de bandas (ELMFIRE los indexa a todos igual). Keyword
  existente del fuente, expuesto porque la prueba física muestra que hace falta.
- **Tests.** `tests/test_elmfire_convenciones.py` (el namelist declara las 25 bandas; series
  distintas se rechazan). Trampa en el skill (`interface-gotchas.md`).

### Hallazgo 2 — `phi.tif` en metros frenaba el frente a la mitad

- **Evidencia.** ELMFIRE vuelca en `vs` la velocidad que calcula en cada celda del frente. En
  GR2 con 10 mph calcula 10,66 m/min en la cabeza (igual a Rothermel), pero el TOA avanza una
  celda de 30 m cada ~337 s: 5,7 m/min.
  - No es el paso de tiempo (con `dt` 1/10 s sube a 7,4) ni la frecuencia de actualización
    (`DT_INTERPOLATE_*` de 300 a 10 s: idéntico).
  - Es el campo inicial. `ignition_builder` escribía la distancia con signo en metros afuera
    (+30, +60, …) y −1 adentro (el piso por el reseteo de `PHI0 < −1,1`). ELMFIRE usa ±1 en
    todos sus tutoriales y verificaciones, y su level set (upwinding con limitador superbee
    sobre una banda de 2 celdas, `LIMIT_GRADIENTS` y `RK2_INTEGRATE` en
    `elmfire_level_set.f90`) sólo avanza a la velocidad calculada sobre ese campo.
- **Experimento** (`pruebas_fisicas.py nivel`): avance del frente sobre velocidad calculada.

  | phi inicial | Sin viento | 10 mph | 20 mph |
  |---|---|---|---|
  | Distancia en metros (el repo hasta hoy) | 0,65 | 0,53 | 0,49 |
  | Distancia en celdas | — | 0,85 | — |
  | ±1 (ELMFIRE) | 0,99 | 1,01 | 1,01 |

  Sin viento, en 3 h: 3,6 ha contra 9,0 ha (la geometría con R0 = 0,67 m/min da 8,7 ha).
- **Alcance.** Todas las corridas: la semilla del caso y cada ventana encadenada
  (`build_ignition_from_mask`), más el playground. El modelo corría a la mitad de su velocidad
  en todas direcciones. La calibración (ADJ 1,15–1,3, LW 100 %) compensaba en parte.
  - El test del playground afirmaba lo contrario ("un campo ±1 no le daría gradiente al
    frente"). La prueba física lo refuta; el test se reescribió.
- **Corrección.** `ignition_builder._write_phi` escribe −1 adentro y +1 afuera
  (`PHI_IGNITION_FLOOR`, `PHI_UNBURNED`); lo mismo el playground. Nada del repo usaba la
  magnitud de `phi`, sólo el signo.
- **Tests.** `test_phi_es_el_campo_mas_menos_uno_de_elmfire`,
  `test_phi_is_elmfires_plus_minus_one_field`. Trampa en el skill.

### Hallazgo 3 — ELMFIRE interpola la dirección del viento como ángulo plano

- **Evidencia en el fuente.** `INTERP_WD_RASTER` (`elmfire_subs.f90`) pasa cada dirección a
  "hacia" en (0, 360] y la interpola linealmente. De 170° a 190° (viento del sur) es 350° →
  10°: a mitad de la hora, viento del norte.
- **Experimento** (`pruebas_fisicas.py tiempo`): 15 mph con `wd` alternando 170°/190°, 2 h.
  - Crudo: el fuego no va al norte; el centroide se corre 54 m hacia 173° (el viento da una
    vuelta entera por hora).
  - Con `wd_for_elmfire`: la cabeza va a 360°, 822 m.
- **Alcance.** Latente hasta el hallazgo 1: sin interpolación entre bandas no se manifestaba.
  Con el 1 corregido afecta a toda serie que cruce el sur (vientos postfrontales).
- **Corrección** (transformación de rásters, sin keywords):
  `weather_builder.wd_for_elmfire` reescribe la serie de cada píxel con valores cuyo "hacia"
  cambia ≤ 180° de banda a banda. Todo ángulo vale módulo 360, así que el viento es el mismo.
  La aplican `derive_wind` y `cadena._preparar` (después de las perillas).
  - ELMFIRE tiene otra ruta, `WX_BILINEAR_INTERPOLATION = T` (interpola u/v), pero cambia
    también la interpolación espacial; no se usa.
- **Tests.** `test_wd_cruda_del_sur_gira_por_el_norte_en_elmfire` (el bug, reproducido con la
  fórmula transcrita), `test_wd_for_elmfire_interpola_por_el_camino_corto`, idempotencia.

### Hallazgo menor 4 — CC ≥ 15 % con CH = 0 deja la celda sin viento

- **Evidencia.** `CALC_WIND_ADJUSTMENT_FACTOR_EVERYWHERE` (`elmfire_init.f90`): con CH = 0 el
  WAF bajo dosel sale 0 y, con CC ≥ 15 %, la celda lo usa. En el banco (`dosel`), TU5 con CC
  60 % y CH 0 avanza a la velocidad sin viento con 20 mph.
- **Alcance.** 0,1–2,6 % de las celdas quemables de los paquetes de calibración (cobertura de
  Hansen sin altura de ETH): Epuyén 1,5 %, Patriada 1,5 %, Cholila 1,8 %, Las Golondrinas
  2,6 % dentro de la cicatriz.
- **Corregido en la causa** (loop E): `canopy_builder.derive_cbh_cbd`, que ya definía "sin
  combustible de copa" con CH < 2 m, ahora deja también la cobertura en 0 ahí. Test
  `test_cover_without_height_is_not_canopy`.
- **La corrección del loop E no alcanzaba (loop I).** En las preparaciones del benchmark casi
  todas las celdas afectadas tienen CH **sin dato** (−9999), no CH < 2 m: `derive_cbh_cbd` las
  dejaba afuera (`known`). ELMFIRE acota el índice de altura a 0
  (`ICH = MIN(MAX(NINT(CH),0),120)`, `elmfire_init.f90:557`), así que un CH sin dato con CC ≥ 15 %
  da el mismo WAF 0. En `benchmark-aoi-asp3`, de 86.694 celdas con CC ≥ 15 % y sin altura,
  82.889 son CH sin dato; con la corrección del loop E sólo cambiaban 3.805. Ahora la cobertura
  va a 0 también ahí (mismo test, con un CH −9999). cbh y cbd no cambian (siguen sin dato, y la
  copa exige CBD > 0,001, `elmfire_spread_rate.f90:161`).
- **En el benchmark desde v5** (loop I). Celdas quemables de cada paquete que en v4 quedaban sin
  viento: Alerces 2023 0,27 %, Epuyén 2025 1,55 %, Alerces 2024 0,17 %, Patriada 1,52 %, Las
  Golondrinas 1,13 %, Alerces 2016 0,46 %, Cholila 1,89 %, El Turbio 0,59 %, Café 0,89 %,
  Epuyén 2019 0,57 %, Alerces 2015 0,29 %. Efecto en el Dice: ≤ 0,001 (§5, loop I).

### Hallazgo 5 — Con la grilla de clima más alta que ancha, la franja norte lee el clima de otra fila (corregido)

- **Evidencia en el fuente.** `MAP_FINE_TO_COARSE` (`elmfire_subs.f90:296-297`) acota la fila del
  clima con `COARSE%NCOLS` en vez de `NROWS`. Las filas se cuentan desde el sur (el lector las
  invierte, `elmfire_io.f90:1265`), así que toda fila con `IY > NCOLS` lee la fila `NCOLS`. Todas
  las lecturas de clima pasan por `IROW_ANALYSIS_F2C` (propagación, spotting, interpolación de
  humedad); el re-acotado de `WX_IROW_FROM_ANALYSIS_IY` con `NROWS` llega tarde.
- **Experimento** (`pruebas_fisicas.py grilla`): dominio de 81 columnas × 161 filas, viento de
  20 mph del oeste en una mitad y calma en la otra, 2 h.
  - Ignición al sur (IY 41): 879 m al este.
  - Ignición en la franja norte (IY 121): **0 m** (60 celdas, el círculo sin viento): lee la fila 81, en calma.
  - La misma, con el clima rellenado al este hasta 161 columnas: 879 m (3.475 celdas contra 3.479).
    ELMFIRE acepta clima de otra forma que el combustible.
- **Alcance.** 5 de los 10 casos tienen la grilla más alta que ancha, en todos sus protocolos:
  - Epuyén 2025: 147 filas, 4,4 km;
  - Alerces 2015: 149 filas, 4,5 km;
  - Alerces 2016: 146 filas, 4,4 km;
  - Alerces 2024: 105 filas, 3,1 km;
  - Patriada: 160 filas, 4,8 km; `cicatriz-12h`, 659 filas; `ventanas-firms`, 1.034 filas (31 km).
  - La app también: el AOI mide ~72 × 144 km y casi todas sus grillas son altas (2563 × 3222 →
    659 filas, ~20 km).

  Medido sobre los insumos registrados de las 238 iteraciones de esos casos: diferencia entre
  el clima real de la franja y la fila que ELMFIRE leyó, en todas las bandas; y cuánto de lo
  quemado cae en la franja.
  - **Calibración v4: prácticamente sin efecto.** El GFS o ERA5 interpolado apenas cambia en
    4 km: |Δws| medio 0,02–0,12 mph, |Δm1| 0,03–0,09 pp. La cicatriz está fuera de la franja
    (Patriada: 0,2 %). El fuego simulado sólo entra en Alerces 2016 (`lw100-adj115-001` v4:
    687 de 30.292 celdas; `base-001`: 5).
  - **Donde sí pesa:** recetas con detalle de terreno. Con el atlas de WindNinja, |Δws| medio
    1,1–1,4 mph, máx 20–30, y Δwd hasta 180°; con `altura-001`, Δm1 hasta 12–21 pp. En esas el
    fuego casi no entró en la franja (Alerces 2016: 97 y 128 celdas).
  - **`puerto-patriada-2026/ventanas-firms`** (harness A): el 54 % (`legacy-ccsbap`) y el 51 %
    (`humedad-m6-obs-001`) de las celdas quemadas, sumadas por ventana, están en la franja, con
    Δwd hasta 180° y Δm1 hasta 17 pp. Sostiene el punto 6 de `RESULTADOS.md` (la receta no se
    transfiere a Patriada), que ya estaba por rehacerse por los hallazgos 1 y 2.
  - `cicatriz-12h`: 17,7 % de la cicatriz en la franja, pero el fuego simulado nunca entró.
- **Corregido en la causa** (loop H): `namelist_writer.pad_weather_columns`, que llama
  `write_namelist` (el último paso antes de ELMFIRE en la API, la preparación, `cadena._preparar`
  después de las perillas, el banco y los harness), rellena al este `ws`, `wd`, `m1`, `m10` y
  `m100` con su última columna hasta `NCOLS ≥ NROWS`, banda por banda y en un archivo nuevo (los
  insumos de `cadena` son hardlinks de sólo lectura al almacén). Verificado en el fuente antes de
  implementarlo:
  - cada ráster se lee con su propio encabezado (`READ_BSQ_RASTER` → `READ_BSQ_HDR_HEADER`,
    `elmfire_io.f90:1242`), así que el clima puede tener otra forma que el combustible;
    `WX_NCOLS`/`WX_NROWS` salen de `ws` (`elmfire_init.f90:188-189`) y los cinco se rellenan igual;
  - `MAP_FINE_TO_COARSE` (`elmfire_subs.f90:293-297`) usa sólo la esquina inferior izquierda y la
    celda del clima: rellenar al este no las mueve, cada celda del combustible sigue leyendo su
    celda de clima y las columnas extra nunca se leen (`ICOL` ≤ columnas del combustible);
    `WX_ICOL_FROM_ANALYSIS_IX` (`:868`) acota con `WS%NCOLS`, que sólo crece;
  - del lado del repo, `_read_domain` y `_read_srs` leen el `dem`; `validate_weather_coverage` y
    `weather_band_count`, sólo bandas; el runner no mira formas. El único lector posterior es el
    respaldo de `/simulations/{id}/wind` cuando no hay `wind-field.json` (la preparación lo
    escribe antes del namelist): ahí el campo se extendería al este.
  - Usa la forma de cada ráster, así que un clima más grueso que el combustible se rellena en
    sus propias celdas; en grillas anchas no hace nada (re-escribir el namelist es inocuo).

  Tests: `test_grilla_alta_el_clima_se_rellena_hasta_ser_cuadrado` (con `MAP_FINE_TO_COARSE`
  transcrito) y `test_grilla_ancha_el_clima_no_se_toca`. Banco: `grilla` da 879 m en la franja
  con la corrección y 0 m con el clima recortado a mano; `simetria`, `viento` y `tiempo` sin
  cambios. Cambia lo que recibe ELMFIRE en los casos altos: en el benchmark entra con los
  protocolos `-v5` (loop I). Consecuencia: el `ws`/`wd` que una corrida deja en sus insumos puede
  ser más ancho que el `dem`; para comparar celda a celda, recortarlo al ancho del `dem`.

### Sospechas descartadas (con el experimento que las descartó)

| Sospecha | Experimento | Resultado |
|---|---|---|
| Unidades de `slp` | `pendiente`: ladera de 20° derivada con `raster_aligner` | ELMFIRE usa grados (`TANSLP2` por grado); la velocidad ladera arriba coincide con R0 (1 + φs) al 0,3 % |
| Orientación v3 | `pendiente`, 4 orientaciones | El fuego sube en las cuatro (±0°) |
| Humedad en % o fracción | `humedad` | `DEAD_MC_IN_PERCENT` y `LIVE_MC_IN_PERCENT` son `.TRUE.` por defecto; la velocidad coincide con Rothermel con m1 3–13 %, LW 60–200 % y LH 30–90 % |
| Humedad de extinción | `humedad`, m1 = 16 % en GR2 (Mx 15 %) | 0 ha |
| Tabla de combustibles | Diff contra la tabla que ELMFIRE escribe por defecto (`elmfire_init.f90`) | Idéntica (más NB91–99, sin efecto); GR2, GS2, SH4, TU5, TL3, TL8 a ±2 % de Rothermel |
| Escala del dosel (`cc` %, `ch`/`cbh` ×10, `cbd` ×100) | Fuente (`CC_IN_PERCENT`, `CH_TIMES_10`, …) y `dosel` | Coinciden; WAF bajo dosel = Albini y Baughman al 0 % |
| La copa nunca se activa | `dosel`: SH7 seco, 25 mph, CBH 1 m | Se activa: 9,75× de área contra `CROWN_FIRE_MODEL = 0` |
| Convención "desde" de `wd` | `viento`, 4 rumbos y la ruta u/v → `derive_wind` | Cabeza a wd + 180 (±0°) en las dos rutas |
| TOA relativo | `tiempo`, TSTART = 2 h | TOA absoluto (≥ 7.200 s) y banda n = clima a n · DT absoluto |
| Encadenado de ventanas | `tiempo`, 1 h + 1 h contra 2 h | Cociente de áreas 1,05 |
| Georreferencia | `georreferencia`: punto lon/lat → celda | Semilla en la celda exacta; TOA en la grilla del dem |
| `DT_INTERPOLATE_*` | Ver hallazgo 2 | Sin efecto (idéntico de 300 a 10 s) |
| **Fase B:** orientación de la grilla del GFS/ERA5 | Correlación de su orografía con el DEM del AOI, directa y volteada, en las 33 series de la caché | Directa 0,61–0,91 en todas; volteada N-S o E-O, menor o negativa |
| Hora del GFS encadenado | `download_analysis_series`: banda k = inicio + k h, ciclo = hora − hora mod 6, `valid.hour` sobre un `inicio` en UTC | Todas las ventanas de los casos están en `+00:00` |
| Conversión de ERA5 | `_era5_serie`: u = −ws·sin(wd), v = −ws·cos(wd), `timezone=GMT`, grilla centrada | Correcta |
| Dirección del viento del modelo contra estaciones | Viento a 10 m de las series crudas en El Bolsón, Esquel y Futaleufú, días de fuego (Meteostat, > 5 km/h) | Desvío mediano −14° a +30° (nunca ~180°): sin error de convención. Velocidad: GFS 0,50–0,87× la estación, **ERA5 0,40–0,70×** |
| Hora de FIRMS | `acq_date` + `acq_time` con `utc=True` | UTC, como publica FIRMS |
| Alineación combustible–DEM | Planitud (≤ 2°) del agua NB8 con el mapa corrido ±3 celdas | El óptimo es sin corrimiento en los cinco incendios probados (89–95 % plana) |
| DEM sin dato en los bordes | Celdas con `dem` −9999 (→ `slp`/`asp` −9999, que ELMFIRE trata como plano) | Epuyén 1.676 y Patriada 36.180 celdas, en el borde norte; ninguna en la cicatriz ni en lo predicho |
| Semilla o referencia con el dominio entero | `phi` ≤ 0 o `ref_firms` en más del 50 % en los 536 insumos de todos los paquetes | Ninguno. Pero la capa "sin ignición" era −9999 y `phi <= 0` la leía como quemada: ahora es +1 |
| Alerces 2015 sube a la montaña por un error de insumos o de convención (loop K) | v2 contra v5; WAF de ELMFIRE transcrito por celda; φs/φw con la Rothermel del banco; asp contra el lago; ERA5 crudo contra Esquel; ocho variantes en ELMFIRE | Mismo dibujo con y sin los bugs. asp mira al lago y el empuje va a ASP − 180; ERA5 sin error de dirección (+15° contra Esquel). Lo explica la física con viento flojo del ESE bajo dosel, no un bug |
| Hallazgo 3 en los datos | Intervalos horarios cuyo `wd` crudo cruza la discontinuidad de ELMFIRE | 0–1,6 % del dominio en los siete de calibración (régimen del oeste); pegaría en vientos del sur |

## 4. Banco de pruebas físicas

`uv run python scripts/pruebas_fisicas.py [prueba …]` (necesita el runner; no está en `make
check`). Resultados en `data/benchmark/fisica/resultados.json`. Dominios de 121–201 celdas de
10–30 m, GR2 por defecto, m1/m10/m100 = 6/8/10 %, LH 30 %, LW 110 %.

La referencia es una implementación independiente de Rothermel (1972) con Albini (1976), WAF
de Albini y Baughman y la elipse de Anderson (1983), dentro del script.

| Prueba | Qué verifica | Tolerancia | Resultado (tras las correcciones) |
|---|---|---|---|
| `simetria` | Plano, sin viento: círculo centrado, a R0 | máx/mín ≤ 1,15; ±10 %; centroide ≤ 10 m | 1,01; 0,666 contra 0,668 m/min; 0 m |
| `nivel` | Avance del frente / velocidad calculada, según `phi` | 0,9–1,1 | ±1: 0,99 y 1,01. Metros: 0,65 y 0,53 (**hallazgo 2**) |
| `viento` | Rumbo de la cabeza (4 wd), velocidad y largo/ancho (5, 10, 20 mph), ruta u/v | ±5°; ±10 %; ±15 % | Rumbo exacto; 4,64/10,74/28,46 contra 4,30/10,63/27,99 m/min; L/A 1,20/1,30/2,03 contra 1,16/1,38/2,03 |
| `pendiente` | Ladera de 20° en 4 orientaciones, slp/asp de `raster_aligner` | ±1°; ±5°; ±10 % | Todo exacto; 3,89–3,90 contra 3,90 m/min |
| `humedad` | Monotonía en m1, extinción, LW (SH4), LH (GS2) | ±10 % | Todo OK salvo GS2 con LH 60 %: 4,16 contra 4,75 (−12 %) |
| `combustible` | GR2, GS2, SH4, TU5, TL3, TL8 a 10 mph | ±10 % | Todos a ≤ 2 % |
| `dosel` | WAF bajo dosel; CC con CH 0; activación de copa | ±10 %; > 1,5× | 1,05 contra 1,05; WAF 0 (**hallazgo 4**); 9,75× |
| `tiempo` | Bandas, TSTART, `wd` 170/190, cadena | ver arriba | Anterior: 0 m (**hallazgo 1**); crudo: 173° (**hallazgo 3**); corregidos: OK; cadena 1,05 |
| `georreferencia` | Punto → celda; grilla del TOA | ±0,5 celda | Exacto |
| `grilla` | Dominio 81 × 161 con viento en una mitad: ignición al sur, en la franja norte sin el relleno y con el relleno de `write_namelist` | > 500 m al este (sin relleno: < 100) | 879 m; **0 m** (**hallazgo 5**); 879 m (corregido) |

GS2 con LH 60 %: ELMFIRE funde la herbácea curada en la clase 1-h (una clase con SAV
ponderada), mi referencia la deja como clase muerta aparte. Coinciden con curado total (LH 30 %,
el valor del repo) y con verde (90 %); difieren en el curado parcial. Es una diferencia entre
dos implementaciones de la transferencia dinámica, no de los insumos; no afecta a las corridas
(LH fijo en 30 %).

## 5. Bitácora de loops

### Loop A — el banco de pruebas y los tres hallazgos

1. `make check` y `verificar` (supuesto 2): todo igual; los cambios de Railway no tocan nada.
2. Lectura del fuente de ELMFIRE contra cada convención del pipeline: unidades de lectura
   (`elmfire_io.f90`), valores por defecto de cada grupo del namelist, interpolación temporal,
   WAF, Rothermel de superficie, elipse, level set. De ahí salieron las sospechas 1 y 3, y la
   del WAF con CH = 0.
3. El banco con ELMFIRE real confirmó 1 y 3, y encontró el 2, que el fuente solo no mostraba:
   la velocidad calculada (`vs`) era la correcta; sólo el TOA iba lento.
4. Correcciones en la causa, tests, skill. Protocolos `-v4` para los siete de calibración.

### Loop B — insumos reales (sin ELMFIRE) y la primera corrida v4

**Fase B** (tabla de sospechas descartadas, §3): la grilla y la hora del GFS/ERA5, la conversión
de ERA5, FIRMS, la alineación del mapa de combustible con el DEM y los bordes sin dato están
bien. Lo único nuevo es la capa "sin ignición" (−9999 leída como quemada por `phi <= 0`),
latente: ningún paquete la tenía; corregida en la causa. Contra las estaciones, la dirección
del viento no tiene error de convención, pero ERA5 sopla más flojo que el GFS (0,40–0,70× contra
0,50–0,87× de la estación): la equivalencia GFS/ERA5 del supuesto §2.13 de RESULTADOS-CSS-BAP se
midió con los bugs y hay que re-verificarla en v4.

**`base-001` sobre v4, cinco incendios** (Cholila y Las Golondrinas quedaron sin correr por el
disco lleno):

1. **¿Sobre o sub-propaga, y cuándo?** Al horizonte el sesgo queda cerca de 1 sin calibrar
   (Epuyén 1,30, Alerces 2024 1,37, Patriada 0,74, Alerces 2016 1,05), salvo Alerces 2023
   (2,72). El día 1 sigue corto en cuatro de cinco:

   | Incendio | 24 h observado (ha) | v3 `base-001` | v4 `base-001` |
   |---|---|---|---|
   | Alerces 2023 | 485 | 185 | **389** |
   | Epuyén 2025 | 1.730 | 14 | 151 |
   | Alerces 2024 | 851 | 49 | 111 |
   | Patriada 2026 | 2.474 | 118 | 78 |
   | Alerces 2016 | 1.241 | 102 | 83 |

2. **¿Dónde?** Lo no predicho sigue al SE/S y lejos (4–7 km), ladera arriba (Epuyén 27°,
   Alerces 2016 29°); los falsos positivos al E/NE a favor del GFS o ladera arriba al SO
   (Epuyén). El frente real va 20–100° más al sur que el empuje del GFS, como en v3.
3. **¿Por qué?** Dos efectos opuestos de las correcciones:
   - el frente va al doble (hallazgo 2), en todo momento;
   - el clima ya no queda congelado en la hora de arranque (hallazgo 1). Alerces 2023 arrancaba
     a las 22 h ART y corría las 72 h con la noche: ahora tiene sus tardes, y el día 1 sale
     (389 contra 485 ha). Patriada y Alerces 2016 arrancaban de tarde y corrían 24 h con la
     tarde: ahora tienen la noche, y el día 1 v4 es menor que el v3 pese al doble de velocidad.

   El déficit del día 1 que queda (8–30×) ya no es de interfaz: es de proceso (copa, pavesas,
   ráfagas por debajo de la hora) o del viento de superficie, como concluyó RESULTADOS-CSS-BAP.
4. **¿Tiene sentido el test?** Alerces 2023 se frenó por combate a las 54 h: sobre-propagar
   después es la supresión que ELMFIRE no modela (límite conocido), ahora a la vista porque el
   modelo ya no va lento.
5. **Experimento:** ADJ 0,5 / 0,7 / 0,9 sobre los siete (en la cola; interrumpido por el disco).

### Loop C — recalibración sobre v4: ADJ, dosel coherente, ERA5 y el horizonte de Alerces 2023

**Barrido de ADJ uniforme** (Dice / sesgo al horizonte; ⚠ fuera de [0,5; 2]):

| Receta | Alerces 2023 | Epuyén | Alerces 2024 | Patriada | Golondrinas | Alerces 2016 | Cholila | Media / mediana |
|---|---|---|---|---|---|---|---|---|
| ADJ 0,5 | 0,362 / 0,67 | 0,095 / 0,25 ⚠ | 0,445 / 0,40 ⚠ | 0,130 / 0,12 ⚠ | 0,005 | 0,173 / 0,18 ⚠ | 0,100 / 0,14 ⚠ | 0,187 / 0,130 |
| ADJ 0,7 | 0,446 / 1,36 | 0,191 / 0,49 ⚠ | 0,534 / 0,86 | 0,223 / 0,34 ⚠ | 0,007 | 0,293 / 0,44 ⚠ | 0,154 / 0,22 ⚠ | 0,264 / 0,223 |
| ADJ 0,9 | 0,491 / 2,17 ⚠ | 0,406 / 0,95 | 0,549 / 1,21 | 0,310 / 0,63 | 0,009 | 0,422 / 0,86 | 0,222 / 0,34 ⚠ | 0,344 / 0,406 |
| **ADJ 1 (`base-001`)** | 0,477 / 2,72 ⚠ | 0,466 / 1,30 | 0,556 / 1,37 | 0,321 / 0,74 | 0,010 | 0,444 / 1,05 | 0,255 / 0,44 ⚠ | **0,361 / 0,444** |
| `lw100-adj115-001` | 0,385 / 4,17 ⚠ | 0,521 / 2,33 ⚠ | 0,571 / 1,88 | 0,397 / 1,18 | 0,014 | 0,405 / 1,83 | 0,331 / 0,69 | 0,375 / 0,397 |
| `dosel-coherente-001` | 0,397 / 3,99 ⚠ | 0,487 / 1,50 | 0,613 / 1,95 | 0,417 / 0,98 | 0,020 | 0,322 / 2,13 ⚠ | 0,261 / 0,44 ⚠ | 0,360 / 0,397 |

1. **¿Sobre o sub-propaga?** Con los bugs corregidos, el ADJ que pide cada incendio está
   alrededor de 1, no de 1,3: bajar el ADJ sólo ayuda a Alerces 2023, y subirlo a Cholila. Es
   la misma tensión que en v3 (un incendio lento que se frenó por combate contra uno rápido),
   ahora centrada en 1.
2. **¿Dónde?** Igual que en `base-001` (loop B): el día 1 corto y el frente al sur de lo que
   empuja el GFS.
3. **¿Por qué? Dos sospechas de insumos, medidas:**
   - **Dosel incoherente (sospecha 6).** Anular el dosel en GR/GS/SH (LANDFIRE) ayuda donde el
     matorral quemado tiene dosel de Hansen (Patriada +0,096, Alerces 2024 +0,057) y empeora los
     lentos (Alerces 2016 −0,12, Alerces 2023 −0,08). La media no cambia: redistribuye velocidad,
     no la corrige. Queda documentado como incoherencia de insumos (§7), no como corrección.
   - **ERA5 contra GFS en v4.** `base-001` en los mismos incendios: Alerces 2023 0,477 / 2,72
     (GFS) contra 0,501 / 2,17 (ERA5); Epuyén 0,466 / 1,30 contra 0,372 / 1,05. ERA5 propaga un
     ~20 % menos. La equivalencia del supuesto §2.13 de RESULTADOS-CSS-BAP (medida con los bugs)
     ya no es exacta; los dos de calibración con ERA5 (Alerces 2016, Cholila) quedan sesgados
     hacia abajo. Coincide con el viento de ERA5 más flojo contra las estaciones (Fase B).
4. **¿Tiene sentido el test en Alerces 2023?** El área FIRMS deja de crecer a las 54 h (1.055
   ha a las 54 h, 1.056 a las 72 h), y la regla del horizonte (§2.9 de RESULTADOS-CSS-BAP) corta
   ahí; las 72 h redondeaban a ventanas de 24 h. Con el modelo a su velocidad real, esas 18 h
   extra son 18 h de fuego sin supresión: el test lo castiga por lo que el combate hizo. Nuevo
   protocolo `calibracion-v4-h54` (ventanas de 24 + 24 + 6 h), aplicando la regla tal cual.
5. **Experimento:** ADJ 0,8, 1,1 y 1,2 en los siete, y las recetas clave sobre Alerces 2023 h54.

**Resultado** (`objetivo calibracion todas`, Alerces 2023 con h54; ⚠ sin contar el caso límite):

| Receta | A23 h54 | Epuyén | A24 | Patriada | Golondrinas | A16 | Cholila | Media / mediana | Alarmas |
|---|---|---|---|---|---|---|---|---|---|
| `base-001` | 0,460 / 1,55 | 0,466 / 1,30 | 0,556 / 1,37 | 0,321 / 0,74 | 0,010 | 0,444 / 1,05 | 0,255 / 0,44 ⚠ | 0,359 / 0,444 | 1 |
| ADJ 0,9 | 0,433 / 1,28 | 0,406 / 0,95 | 0,549 / 1,21 | 0,310 / 0,63 | 0,009 | 0,422 / 0,86 | 0,222 / 0,34 ⚠ | 0,336 / 0,406 | 1 |
| **ADJ 1,1 (`adj-110-001`)** | 0,490 / 1,84 | 0,498 / 1,60 | 0,561 / 1,55 | 0,335 / 0,83 | 0,013 | 0,430 / 1,31 | 0,283 / 0,53 | **0,373 / 0,430** | **0** |
| ADJ 1,2 | 0,496 / 2,22 ⚠ | 0,519 / 1,87 | 0,560 / 1,71 | 0,341 / 0,98 | 0,014 | 0,414 / 1,60 | 0,312 / 0,63 | 0,379 / 0,414 | 1 |
| `lw100-adj115-001` | 0,487 / 2,47 ⚠ | 0,521 / 2,33 ⚠ | 0,571 / 1,88 | 0,397 / 1,18 | 0,014 | 0,405 / 1,83 | 0,331 / 0,69 | 0,389 / 0,405 | 2 |
| `dosel-coherente-001` | 0,432 / 2,50 ⚠ | 0,487 / 1,50 | 0,613 / 1,95 | 0,417 / 0,98 | 0,020 | 0,322 / 2,13 ⚠ | 0,261 / 0,44 ⚠ | 0,365 / 0,417 | 3 |

- **Receta candidata: `adj-110-001`** (ADJ 1,1, LW 110 %). Es la única que cumple la restricción:
  el intervalo sin alarmas es ~[1,05; 1,15], acotado por Cholila abajo y Alerces 2023 arriba.
  La validación cruzada (`validar todas`) la elige en 6 de 7 pliegues; fuera de muestra, media
  0,374 y mediana 0,430.
- **Lo que dice sobre la calibración vieja:** con la interfaz corregida, el modelo pide ADJ 1,1
  y LW en su valor de base. El ADJ 1,15–1,3 y el LW 100 % de RESULTADOS-CSS-BAP compensaban en
  parte los bugs (frente a la mitad y clima congelado). Las cifras finales se parecen (0,373 /
  0,430 contra 0,372 / 0,411), pero ahora con un modelo que avanza a la velocidad de Rothermel y
  con el clima hora a hora, y sin tocar LW.
- **ERA5 con el viento ×1,3** (`viento-130-001` sobre los ERA5 v4 de control) reproduce al GFS:
  Epuyén 0,455 / 1,30 contra 0,466 / 1,30 del GFS; Alerces 2023 sesgo 2,64 contra 2,72. El
  déficit de ERA5 es de velocidad del viento, y el factor coincide con el cociente GFS/ERA5
  medido contra las estaciones (mediana 1,26). Próximo loop: homogeneizar ERA5 al GFS como
  corrección del insumo (protocolo nuevo), no como perilla de receta.
- **Robustez a la ignición** (±500 m, ±2 h; protocolos `-ign-*` sobre v4, Alerces 2023 con
  h54): 21 corridas por receta.

  | Incendio · receta | Documentada | N 500 | S 500 | E 500 | O 500 | −2 h | +2 h |
  |---|---|---|---|---|---|---|---|
  | Alerces 2023 · base | 0,460 / 1,55 | 0,410 / 1,68 | 0,542 / 1,49 | 0,438 / 1,62 | 0,404 / 1,47 | 0,473 / 1,70 | 0,457 / 1,55 |
  | Alerces 2023 · ADJ 1,1 | 0,490 / 1,84 | 0,423 / 2,09 ⚠ | 0,542 / 1,80 | 0,455 / 2,04 ⚠ | 0,431 / 1,72 | 0,490 / 2,01 ⚠ | 0,480 / 1,81 |
  | Epuyén · base | 0,466 / 1,30 | 0,268 / 0,78 | 0,558 / 1,69 | 0,390 / 0,85 | 0,421 / 1,07 | 0,468 / 1,31 | 0,443 / 1,20 |
  | Epuyén · ADJ 1,1 | 0,498 / 1,60 | 0,360 / 1,07 | 0,549 / 1,91 | 0,441 / 1,09 | 0,490 / 1,51 | 0,501 / 1,57 | 0,500 / 1,57 |
  | Alerces 2016 · base | 0,444 / 1,05 | 0,366 / 1,02 | 0,483 / 0,92 | 0,241 / 1,47 | 0,559 / 0,76 | 0,441 / 1,05 | 0,446 / 1,02 |
  | Alerces 2016 · ADJ 1,1 | 0,430 / 1,31 | 0,391 / 1,29 | 0,479 / 1,15 | 0,266 / 1,65 | 0,528 / 0,99 | 0,429 / 1,34 | 0,444 / 1,25 |

  | Receta | Media | Mediana | Alarmas |
  |---|---|---|---|
  | `base-001` v4 | 0,437 | 0,444 | 0 de 21 |
  | **`adj-110-001` v4** | **0,458** | **0,479** | 3 de 21 (Alerces 2023, 2,01–2,09) |
  | `adj-130-001` v3 (RESULTADOS-CSS-BAP loop 7) | 0,398 | 0,454 | 5 de 21 |
  | `lw100-adj115-001` v3 | 0,395 | 0,440 | 7 de 21 |

  - **La mejora de ADJ 1,1 sobrevive:** gana en 14 de 21 (6 de 7 en Alerces 2023, con un
    empate; 6 de 7 en Epuyén; Alerces 2016 prefiere base en 5 de 7). Las tres alarmas son de Alerces 2023 al borde
    (≤ 2,09): ADJ 1,1 es el extremo superior del intervalo factible.
  - **El modelo corregido es mucho menos frágil a la ignición:** en Epuyén el Dice va de 0,27 a
    0,56 (v3: de 0,08 a 0,50). Con el frente a la mitad, los primeros cientos de metros decidían
    todo; ahora el fuego sale de la trampa del combustible de la ignición.
- **Pendiente:** los cuatro de prueba (en la cola) y la homogeneización de ERA5 (loop D).

### Loop D — ERA5 homogeneizado al GFS

**Hipótesis:** los dos incendios de calibración con ERA5 (Alerces 2016, Cholila) sub-propagan por
el viento de ERA5, un ~30 % más flojo que el GFS (loop C).

**Experimento:** protocolos `calibracion-era5-v4w`, con el viento multiplicado por 1,3 al
empaquetar (`factor_viento_fuente`, declarado en el caso). Control: Alerces 2023 y Epuyén ERA5
v4w dan idéntico a la receta `viento-130-001` sobre v4 (0,484 / 2,64 y 0,455 / 1,30).

| Receta | Alerces 2016 v4 → v4w | Cholila v4 → v4w |
|---|---|---|
| `base-001` | 0,444 / 1,05 → 0,392 / 1,28 | 0,255 / 0,44 ⚠ → 0,260 / 0,44 ⚠ |
| `adj-110-001` | 0,430 / 1,31 → 0,388 / 1,55 | 0,283 / 0,53 → 0,298 / 0,55 |
| `adj-120-001` | 0,414 / 1,60 → 0,381 / 1,81 | 0,312 / 0,63 → 0,333 / 0,65 |

**Conclusión:** homogeneizar ERA5 no mejora el objetivo. Alerces 2016 ya llegaba a su área y se
acelera sin necesitarlo; a Cholila no le falta viento medio sino la explosión de las 30–42 h
(+3.200 ha a 10 km al E/NE), la misma firma del día explosivo del resto. Con v4w, ADJ 1,1 sigue
siendo la única receta sin alarmas (media 0,369, mediana 0,388): **la receta no depende de la
fuente del clima**. Se mantiene v4 (ERA5 sin tocar) en la partición y v4w queda como
sensibilidad.

### Loop E — LW con la física corregida

**Hipótesis:** LW 110 % es el umbral húmedo de grandes incendios de Bianchi y Defossé (2015), no
el valor de un día de gran incendio (RESULTADOS-CSS-BAP loop 6). Con el ADJ ya cerca de 1, LW
—la perilla con criterio regional— puede hacer el trabajo del ADJ.

| Receta | A23 h54 | Epuyén | A24 | Patriada | A16 | Cholila | Media / mediana | Alarmas |
|---|---|---|---|---|---|---|---|---|
| `adj-110-001` | 0,490 / 1,84 | 0,498 / 1,60 | 0,561 / 1,55 | 0,335 / 0,83 | 0,430 / 1,31 | 0,283 / 0,53 | 0,373 / 0,430 | 0 |
| **LW 100 % (`lw-100-001`)** | 0,495 / 1,82 | 0,500 / 1,75 | 0,563 / 1,54 | 0,368 / 0,91 | 0,452 / 1,33 | 0,280 / 0,55 | **0,381 / 0,452** | **0** |
| LW 95 % | 0,502 / 2,03 ⚠ | 0,511 / 2,03 ⚠ | 0,566 / 1,65 | 0,394 / 1,02 | 0,443 / 1,50 | 0,298 / 0,60 | 0,389 / 0,443 | 2 |
| LW 90 % | 0,493 / 2,26 ⚠ | 0,518 / 2,42 ⚠ | 0,584 / 1,77 | 0,422 / 1,18 | 0,424 / 1,79 | 0,315 / 0,66 | 0,395 / 0,424 | 2 |

(Las Golondrinas, el caso límite, 0,012–0,013 en todas; cuenta en la media.)

- **`lw-100-001` gana a ADJ 1,1** en media (0,381 contra 0,373), mediana (0,452 contra 0,430) y
  forma (0,359 contra 0,352), sin alarmas. La validación cruzada la elige en **7 de 7**
  pliegues; fuera de muestra, 0,381 / 0,452.
- **Por qué LW y no ADJ:** LW actúa sólo donde hay carga viva (SH, TU): acelera Patriada (+0,033)
  y Alerces 2016 (+0,022) sin empujar a Alerces 2023 más allá (1,82 contra 1,84), que es
  sobre todo TU/TL. ADJ acelera todo por igual.
- **El intervalo sin alarmas es ~[97; 110] %**, casi el mismo que en v3 ([95; 110]): el LW
  que pide la región no dependía de los bugs. Lo que sí dependía de ellos era el ADJ extra de
  la receta v3 (1,15), que ahora sobra.
- **Robustez a la ignición** (las mismas 21 corridas perturbadas):

  | Receta | Media | Mediana | Alarmas | Gana a base |
  |---|---|---|---|---|
  | `base-001` | 0,437 | 0,444 | 0 | — |
  | `adj-110-001` | 0,458 | 0,479 | 3 (2,01–2,09) | 14 de 21 |
  | **`lw-100-001`** | **0,460** | **0,480** | 3 (2,02, 2,02 y 2,38) | **17 de 21** |

  Las alarmas son de Alerces 2023 (N 500, −2 h) y Epuyén (S 500: cae sobre el arbustal, el
  caso que ya era el extremo en v3), todas cerca del borde.
- **Prueba** (no usados para elegir): `lw-100-001` 0,213 / 0,220, `base-001` 0,209 / 0,191,
  `adj-110-001` 0,204 / 0,203. Alerces 2015, el único del régimen calibrado, pasa de 0,255 a
  0,297 (sesgo 1,50). Los otros tres siguen fuera de alcance por la misma razón que en v3.
- **Receta final: `lw-100-001`** (LW 100 %, ADJ 1, CCS-BAP anterior al fuego). Gana en
  calibración, validación cruzada (7 de 7), robustez y prueba. **No necesita ADJ**: con la
  interfaz corregida, la única perilla que la región pide es la humedad viva por debajo del
  umbral de grandes incendios.

### Loop F — ¿la copa era un límite o un efecto del frente lento?

**Hipótesis:** RESULTADOS-CSS-BAP (loop 3) descartó la copa porque con CBH × 0,25 no cambiaba
nada (+0,004): "la superficie TL8 no alcanza la intensidad". Con el frente a la mitad
(hallazgo 2), la intensidad superficial (∝ velocidad) también estaba a la mitad.

**Experimento:** `cbh-025-001` (diagnóstico, no candidata: el dosel es infraestructura) sobre v4,
contra `base-001` v4.

| Incendio | `base-001` v4 | CBH × 0,25 | 24 h predicho (observado), ha |
|---|---|---|---|
| Cholila | 0,255 / 0,44 ⚠ | **0,528 / 0,90** | 279 → 655 (255) |
| Alerces 2024 | 0,556 / 1,37 | 0,614 / 1,72 | 111 → 324 (851) |
| Epuyén | 0,466 / 1,30 | 0,473 / 1,30 | 151 → 149 (1.730) |
| Patriada | 0,321 / 0,74 | 0,310 / 0,83 | 78 → 79 (2.474) |
| Alerces 2016 | 0,444 / 1,05 | 0,338 / 1,76 | 83 → 298 (1.241) |
| Alerces 2023 h54 | 0,460 / 1,55 | 0,400 / 2,50 ⚠ | — |

- **Límite reabierto:** en v4 la copa se enciende con un CBH bajo, y mueve el Dice hasta +0,27
  (Cholila). El "la copa nunca se inicia" de v3 era en parte el frente a media velocidad.
- **Pero no explica el día explosivo:** en Cholila acelera desde el principio (655 contra 255 ha
  a las 24 h) y llega al área final, sin el salto de las 36–42 h. En Epuyén y Patriada no cambia
  nada: sus igniciones caen en TL8/matorral sin dosel bajo que se encienda.
- **Conclusión:** la estructura del dosel (el CBH derivado como 0,2–0,5 × CH) pasa a ser la
  incertidumbre de insumos más grande que queda. No se calibra (no es un parámetro de esta
  tesis); va al director (§7.2).

### Loop G — la dirección del viento con el modelo a su velocidad

**Hipótesis:** RESULTADOS-CSS-BAP (loop 2) vio que "la dirección pesa sólo cuando el modelo
avanza a la velocidad correcta", y en v3 no avanzaba: la rotación empírica daba +0,002 y el atlas
de WindNinja era neutro. Sobre la receta final v4, ¿cambian?

| Receta | A23 h54 | Epuyén | A24 | Patriada | A16 | Cholila | Media / mediana | Alarmas |
|---|---|---|---|---|---|---|---|---|
| `lw-100-001` | 0,495 / 1,82 | 0,500 / 1,75 | 0,563 / 1,54 | 0,368 / 0,91 | 0,452 / 1,33 | 0,280 / 0,55 | 0,381 / 0,452 | 0 |
| + rotación 30° | 0,526 / 1,73 | 0,544 / 2,09 ⚠ | 0,571 / 1,51 | 0,352 / 0,90 | 0,473 / 1,29 | 0,269 / 0,54 | 0,393 / 0,473 | 1 |
| + atlas de WindNinja | 0,496 / 1,82 | 0,480 / 1,73 | 0,559 / 1,53 | 0,347 / 0,89 | 0,508 / 1,08 | 0,262 / 0,51 | 0,380 / 0,480 | 0 |

- **La rotación ahora sí suma** (+0,012 de media, +0,021 de mediana; en v3 +0,002), como
  anticipaba RESULTADOS-CSS-BAP: gana donde el fuego corre al sur (los valles de Los Alerces,
  Epuyén) y pierde donde fue al NE (Patriada, Cholila). Pero hace pasar a Epuyén a 2,09 y es una
  corrección empírica del insumo, no física.
- **El atlas sigue neutro en media** (0,380) y ayuda en terreno empinado (Alerces 2016 +0,056),
  igual que en v3.
- **Validación cruzada** con las 11 recetas: `lw-100-001` en 4 de 7 pliegues, el atlas en 2,
  la rotación en 1 (con alarma); fuera de muestra 0,382 / 0,452, lo mismo que la receta sola.
- **La receta final no cambia.** La dirección del viento de superficie sigue siendo un límite,
  ahora con un efecto medible (+0,01–0,04 por incendio) que antes el frente lento escondía.

### Loop H — el hallazgo 5 corregido en la causa

**Hipótesis:** el acotamiento de filas de `MAP_FINE_TO_COARSE` se evita del lado del repo, sin
tocar ELMFIRE, rellenando al este los rásters de clima hasta que sean al menos tan anchos como
altos, porque ELMFIRE acepta clima de otra forma que el combustible y lo mapea por coordenadas.

**Experimento:** primero el fuente (§3, hallazgo 5: encabezado propio por ráster, mapeo por la
esquina inferior izquierda y la celda, `WX_*` con la forma de `ws`), después las validaciones del
repo y del runner (ninguna compara la forma del clima con la del `dem`). Implementado en
`write_namelist` (`pad_weather_columns`) y medido con ELMFIRE real en `pruebas_fisicas.py`:
`grilla` (el banco de la otra sesión, ahora con la corrección de `write_namelist` y el caso sin
relleno reproducido recortando el clima después del namelist), más `simetria`, `viento` y `tiempo`.

**Resultado:**
- `grilla`: control al sur 879 m (3.479 celdas); franja norte sin relleno **0 m** (60 celdas, el
  círculo sin viento); franja norte con la corrección 879 m (3.475 celdas, clima 161 × 161).
- `simetria`, `viento` y `tiempo`: los mismos números que antes (10,74 y 28,46 m/min a 10 y
  20 mph; L/A 1,30 y 2,03; 1.063 m con `NUM_METEOROLOGY_TIMES`; `wd_for_elmfire` 822 m a 360°). Las
  dos "fallas" de `tiempo` son las reproducciones de los hallazgos 1 y 3, como siempre.

**Conclusión:** corregido en un solo lugar para la app, el benchmark, el banco y los harness. En
el benchmark cambia los insumos de los casos altos, así que entra con un protocolo nuevo (v5,
loop I) junto con el dosel del hallazgo 4.

### Loop I — protocolos v5: los hallazgos 4 y 5 en el benchmark

**Hipótesis:** los dos hallazgos que faltaban en el benchmark (dosel sin altura, grilla de clima
alta) casi no mueven la calibración: el primero toca 0,2–1,9 % de las celdas quemables y el
segundo una franja donde el clima de 0,25° apenas cambia (§3). Si mueven la velocidad, hay que
re-barrer LW antes de sostener `lw-100-001`.

**Experimento:**
- Preparaciones nuevas, sin tocar las viejas (los paquetes v4 las referencian):
  `scripts/preparar_benchmark.py --dosel-desde data/elmfire/inputs/benchmark-aoi-asp3 --salida
  data/elmfire/inputs/benchmark-aoi-asp3-v5`, y lo mismo con `benchmark-2026-09-28-asp3`.
  Hardlinks de todo salvo cc/cbh/cbd; cc copiado y re-derivado con `derive_cbh_cbd`. cbh y cbd
  salen idénticos a los viejos; sólo cambia cc.
- Al armarlas apareció que la corrección del loop E no cubría el CH sin dato (§3, hallazgo 4):
  corregido en `canopy_builder` antes de armar las preparaciones.
- Once casos v5 (siete de calibración, cuatro de prueba; `calibracion-v5-h54` en Alerces 2023,
  `calibracion-v5s` en Café), copia de los v4 con la preparación nueva y una nota de versión.
  Contra el paquete v4, cambia sólo `cc.tif`; el clima re-empaquetado tiene otros bytes pero datos
  idénticos (comparado banda a banda en Alerces 2023).
- `base-001` y `lw-100-001` sobre los once, por la cola.

**Resultado** (Dice / sesgo; entre paréntesis, v4):

| Incendio | `base-001` v5 | `lw-100-001` v5 |
|---|---|---|
| Alerces 2023 (h54) | 0,461 / 1,55 (0,460 / 1,55) | 0,496 / 1,83 (0,495 / 1,82) |
| Epuyén 2025 | 0,466 / 1,30 (igual) | 0,500 / 1,75 (igual) |
| Alerces 2024 | 0,555 / 1,37 (0,556 / 1,37) | 0,562 / 1,54 (0,563 / 1,54) |
| Patriada 2026 | 0,321 / 0,74 (igual) | 0,368 / 0,90 (0,368 / 0,91) |
| Las Golondrinas (límite) | 0,010 / 0,02 ⚠ (igual) | 0,012 / 0,02 ⚠ (igual) |
| Alerces 2016 | 0,444 / 1,05 (igual) | 0,451 / 1,33 (0,452 / 1,33) |
| Cholila 2015 | 0,255 / 0,44 ⚠ (igual) | 0,280 / 0,55 (igual) |
| **Calibración, media / mediana** | **0,359 / 0,444** (igual) | **0,381 / 0,451** (0,381 / 0,452) |
| Alarmas sin el límite | 1 (1) | **0** (0) |
| El Turbio 2025 | 0,333 / 4,97 ⚠ | 0,296 / 5,73 ⚠ (0,297 / 5,71) |
| Café 2025 (v5s) | 0,128 / 0,26 ⚠ | 0,144 / 0,29 ⚠ (igual) |
| Epuyén 2019 | 0,122 / 15,0 ⚠ | 0,114 / 16,5 ⚠ (igual) |
| Alerces 2015 | 0,255 / 0,96 | 0,298 / 1,49 (0,297 / 1,50) |
| **Prueba, media / mediana** | 0,210 / 0,191 (0,209 / 0,191) | **0,213 / 0,220** (igual) |

- Validación cruzada: `lw-100-001` en 7 de 7 pliegues, fuera de muestra 0,381 / 0,451.
- Sin alarmas nuevas: no hizo falta re-barrer LW.
- Cuatro iteraciones (Alerces 2023 y Epuyén 2025, las dos recetas) quedaron con ventanas
  marcadas `sucio`: mientras corrían había sin commitear scripts del documento de combustibles
  (`corregir_preparacion_legado.py` y los que re-corren §6.1 y §6.3), que el benchmark no importa
  (commit `44f298d`). `verificar` con el árbol limpio: TOA idéntico en las 14 ventanas.

**Conclusión:** los hallazgos 4 y 5 no mueven el benchmark (≤ 0,001 por incendio, que es lo que
anticipaba el §3). La receta final sigue siendo `lw-100-001`, ahora sobre v5, y
`benchmarks/particion.json` apunta a v5. Los dos arreglos importan en la app (franja de ~20 km en
el AOI) y en `ventanas-firms`, no en la calibración.

### Loop J — re-medir el documento de combustibles (§6.1 y §6.3)

**Hipótesis:** las comparaciones entre mapas y el barrido de humedad viva del documento de
combustibles corrieron con los hallazgos 1–5; corregidas, el frente va al doble y las áreas y las
intensidades crecen, pero el orden entre mapas debería sostenerse.

**Experimento:**
- Qué quedaba para reproducir: las corridas viejas siguen en `data/elmfire/{inputs,outputs}/`
  (`cmp_b5_*`, `cmp_aoi_*`, `lfmc_*`), y `compare_fuel_map_runs.py` sobre `cmp_b5_*` reproduce
  la tabla del documento al dígito. Pero los mapas de `data/static/fuel_maps` se regeneraron sobre
  la caja del benchmark (4.333 × 2.591; ya no coinciden con ninguna de las dos grillas), y las
  máscaras del harness B se borraron de `mask-dataset-gen`.
- `scripts/corregir_preparacion_legado.py` re-arma una corrida vieja con la interfaz corregida
  (semilla ±1, `wd` por el camino corto, dosel re-derivado, namelist de `write_namelist` con el
  TSTART, TSTOP, LH y LW del viejo, clima rellenado). `run_three_maps.py --mapas` toma los
  `fbfm40` de las corridas viejas; `sweep_live_moisture.py --base --sufijo`, otra base;
  `score_against_observed.py` lee la columna nueva de `mask-dataset-gen`.
- Corridas, con la cola vacía: tres mapas en la grilla reducida (LW 110 y LW 100), el barrido de
  cuatro humedades y los tres mapas en el AOI; puntuación del AOI, viejas y corregidas, contra
  `baseline-002`.

**Resultado:** §7.4. En corto: el orden WorldCover < MapBiomas < CCS-BAP se sostiene en el
anillo (2,4× en vez de 3,2×) y en el IoU del harness B (0,010 / 0,035 / 0,046); el factor de la
humedad viva se sostiene (2,53). No se cumple que las intensidades se dupliquen: bajan, porque la
corrida ya no se queda con la hora más seca y ventosa. En el AOI el anillo corregido es la mitad
del viejo por la misma razón (la corrida atraviesa la noche).

**Conclusión:** las conclusiones cualitativas del documento sobreviven. Hay que reemplazar
todas sus cifras de §6.1 y §6.3, y decir que la referencia del harness B cambió.

### Loop K — caso Los Alerces 2015: por qué el modelo sube a la montaña

**Pregunta.** En Alerces 2015 (caso de **prueba**, ERA5, CCS-BAP 2013) el modelo quema al O/SO,
ladera arriba sobre el Cordón Situación, y el fuego real corrió ~6 km al N por la ladera baja de
la costa oeste del Futalaufquen. ¿Bug de insumos o de convención, límite de los datos o
problema del test? **Sólo diagnóstico:** nada de este loop elige ni ajusta la receta.

**1. No es un efecto de los bugs.** La captura que motivó la pregunta (`calibracion-era5-v2`,
`lw100-adj115-001`) tiene los hallazgos 1–5, pero v5 da el mismo dibujo (`analizar`, última
ventana):

| Iteración | Dice / sesgo | Falso positivo (ha; O / SO / S) | No predicho (ha; al N) |
|---|---|---|---|
| v2 `lw100-adj115-001` | 0,312 / 1,38 | 1.156; 360 / 244 / 200 | 721; 599 |
| v5 `base-001` | 0,255 / 0,96 | 818; 240 / 210 / 155 | 860; 641 |
| v5 `lw-100-001` | 0,298 / 1,49 | 1.284; 443 / 258 / 232 | 721; 592 |

El falso positivo está a 974–1.349 m (cuartiles) con 29° de pendiente; lo no predicho, a
707–1.000 m, 4 km al N. La ignición está a 841 m, en el extremo sur de la franja entre el lago
(al E) y la montaña (al O).

**2. Hipótesis, una por una.**

- **H1, combustible en la montaña: contribuye al exceso, no a la dirección.** Falso positivo de
  `lw-100-001` por clase de CCS-BAP 2013: bosque de lenga (TF Le → TL6) 342 ha a 1.174 m;
  lenga achaparrada y baja (OFL Le → SH8) 378 ha a 1.250–1.383 m; "Estepa" (OT Herb-Subarb →
  GR3) 158 ha a 1.484 m; coihue (→ TU5) 129 ha; matorral mixto (→ SH4) 113 ha. El cinturón de
  lenga es el 56 % del falso positivo.
  - **No hay roca ni nieve quemable:** sobre 1.500 m el dominio es Erial → NB9 (1.527 ha) y
    Hielo-Nieve → NB92 (322 ha), más 117 ha de GR3; el fuego simulado llega a 1.500–1.700 m en
    65 ha.
  - **La "Estepa" de altura sí es una asignación dudosa:** el crosswalk (§5.8) manda Estepa
    (coirón) → GR3, pero en el Cordón Situación CCS-BAP 2013 llama Estepa a vegetación
    altoandina rala entre roca y nieve (el 73 % del GR3 del caso está sobre 1.300 m). Sin dosel
    (WAF 0,42 contra 0,08 del bosque), el GR3 hace de autopista: con `diag-lw100-gr3-nb-001`
    (GR3 → NB9) el falso positivo baja de 1.284 a 907 ha (al O, de 443 a 146) y el Dice sube de
    0,298 a 0,342. Va a §7.4 como hallazgo; el crosswalk no se toca.
  - **Cota superior:** con `diag-lw100-lenga-nb-001` (TL6 y SH8 no quemables) el fuego se queda
    en 674 ha (Dice 0,323, sesgo 0,59) y **lo no predicho al N sigue igual (596 ha)**. Sacar
    combustible de la montaña frena la subida, pero no manda el fuego al N.
- **H2, viento bajo dosel: no hay costa protegida y montaña expuesta.** El WAF de ELMFIRE
  (`CALC_WIND_ADJUSTMENT_FACTOR_EVERYWHERE`, `elmfire_init.f90:523`, transcrito con
  `pruebas_fisicas.waf_con_dosel`) da una mediana de 0,083 en la costa no predicha, 0,090 en el
  falso positivo y 0,081 en el acierto. Sólo el GR3 y el SH8 alto del falso positivo están
  expuestos (p90 0,42). `dosel-coherente-001` sobre v5: 0,308 / 1,57 (base 0,255 / 0,96), pero
  porque quema más; el falso positivo crece a 1.344 ha (453 al O) y lo no predicho al N no cambia
  (590 ha). Más viento sobre el SH empuja más al O.
- **H3, viento de ERA5: es la causa, y es un límite de datos.** ERA5 en la ignición sopla del
  ESE (95–123° las 24 h del día 1; 4,3–5,3 mph a 20 pies de tarde, 1,7–3,8 de noche); todo el
  dominio cae en una celda (5,2–5,4 mph en la banda de las 17 ART). Esquel (87803, 40 km al E):
  viento del NE/E (50–70°) y del SE (110–140°) los tres días, 22 °C y HR 26–31 % de tarde, un
  régimen del este débil y anticiclónico. ERA5 en la celda de Esquel: 0,55× la estación y +15°
  de desvío mediano (Fase B: 0,40–0,70×). **Ni ERA5 ni la estación tienen una sola hora del
  sector S (135–225°) en las 72 h.**
  - El empuje del ESE (hacia 285°) suma con la pendiente: las laderas de la franja miran al ENE
    (asp mediano 72–80°), así que cuesta arriba es el OSO. Con 3–5 mph y WAF 0,08 la pendiente
    domina en el 90–93 % de las celdas (φs mediano 3,4 en la costa y 6,4 en el falso positivo,
    contra φw 0,6–0,7). En la franja que ardió hacia el N, la suma empuja al O±45° en el 88 % de
    las celdas y al NNO±45° en el 4 %.
  - **Qué viento haría falta:** para que la costa empuje a 343°±45° con el WAF de ELMFIRE, del
    SSE (165°) 16,8 mph a 20 pies (mediana, 99 % de las celdas), del SE (135°) 27 mph (78 %);
    sin dosel, 4 y 8 mph. Del ESE no lo logra ninguna velocidad (6 %).
  - **Las correcciones del viento no lo ven.** WindNinja (protocolo `calibracion-era5-v5a`: v5 byte
    a byte más el atlas, 16 direcciones a 90 m) lleva el ESE de 105° a 114° en la costa y lo
    frena a 0,69×: conservación de masa sin circulación térmica, no encauza al S.
    `lw100-atlas-001` 0,286 / 1,50; `lw100-rot030-001` 0,316 / 1,50; `rotacion-060-001` (viento
    del SSE, el eje del lago) 0,271 / 0,91 contra base 0,255 / 0,96. En las tres, lo no predicho
    al N queda en 590–641 ha: a 3–5 mph bajo dosel, ni con la dirección del valle el viento le
    gana a la pendiente.
- **H4, pendiente con viento flojo: física correcta, no un error.** Las laderas de la franja
  miran al lago (ENE); ELMFIRE empuja a ASP − 180 (OSO). `tests/test_topo_aspect.py` pasa, y la
  prueba `pendiente` del banco ya daba la subida exacta en las cuatro orientaciones (§3).
- **H5, el test: está bien.** El N ardió dentro de las 72 h, y casi todo en las primeras 12 h:
  - 18:53 UTC (2 h 53 después de la ignición supuesta): 8 píxeles a ≤ 1 km;
  - 04:36 UTC del 24: 3,8 km al N. Son ~2,9 km de noche (~300 m/h);
  - 05:58 UTC del 25: 6,3 km.

  A las 18 h la cicatriz alcanzada mide 852 ha y el modelo lleva 80 (`lw-100-001`): el día
  explosivo, ~10× (§7.3). La montaña O/SO está dentro de la cobertura y no excluida, y no ardió:
  hay una sola detección al O/SO de la ignición en 72 h, y 31 ha de cicatriz al S. Sobre el
  combate, las crónicas sólo dicen que los medios aéreos cargaban agua en el lago entre la
  cabecera sur y Punta Mattos desde el día 1 y que la prioridad era proteger viviendas. No se
  puede separar cuánto frenó, pero el combate no explica una carrera nocturna de 300 m/h al N.
- **H6, ignición: no es la causa.** Las primeras detecciones caen 692 m al NE (56°) del punto
  de mask-dataset-gen y 110 m más abajo, ladera abajo contra el empuje del modelo. Con la semilla
  ahí (`calibracion-era5-v5-ign-viirs1`, `lw-100-001`): 0,315 / 1,47, forma 0,334 (contra 0,281).
  El falso positivo se corre al E/SE, hacia la cabecera del lago, y lo no predicho al N/NO sigue
  en 701 ha. No se corrió ±2 h: el viento es del ESE todo el día, así que la hora no cambia la
  dirección.

**3. Conclusión.** **No hay bug.** El modelo sube a la montaña porque, con el viento que tiene
(ERA5 del ESE a 3–5 mph, más flojo que la estación y sin componente S en ninguna hora) y un WAF
de bosque de ~0,08 en toda la franja, la pendiente es lo único que empuja, y empuja al OSO. Nada
de lo que el modelo recibe manda el fuego al N. La carrera real al N, de noche y bordeando el lago
a ~300 m/h, pide un viento local del S de ≥ 17 mph a 20 pies bajo el dosel (sin dosel, ≥ 4 mph)
o un proceso que la corrida no tiene (copa en ciprés/coihue, pavesas). Es el límite de la
dirección del viento de superficie (§7.3), en su caso extremo: un régimen del este con
circulación local que ni ERA5, ni WindNinja, ni la rotación empírica representan. Dos insumos
agravan el exceso montaña arriba sin explicar la dirección:
- la "Estepa" altoandina → GR3 (§7.4);
- la humedad muerta uniforme en altura: m1 5,1 % de 500 a 1.500 m (una celda de ERA5).
  `altura-001` (T llevada al DEM) apenas la mueve: 0,276 / 0,99 contra 0,255 / 0,96, con el
  falso positivo de 818 a 817 ha.

Recetas nuevas, sólo diagnóstico: `diag-lw100-gr3-nb-001`, `diag-lw100-lenga-nb-001`. Protocolos
nuevos: `calibracion-era5-v5a` (atlas) y `calibracion-era5-v5-ign-viirs1`. No hay corrección que
re-evaluar sobre los 7 de calibración.

### Loop L — las decisiones del director, tomadas por el benchmark

**Pregunta.** `DECISIONES-DIRECTOR.md` dejó siete decisiones de dominio abiertas. Con el pedido de
tomarlas nosotros y quedarnos con lo que más mejore el acierto, ¿cuánto sube la calibración?

**Cómo.** Todo sobre la receta final (`lw-100-001`) y los siete de calibración. La prueba se miró
sólo al final.
- **Perillas nuevas en `cadena`** (transformaciones de rásters, sin keywords):
  - `sin_dosel` y `cbh_por_combustible` / `cbd_por_combustible`;
  - `dosel_sin_perdida_previa` y `combustible_perdida_reciente`, con Hansen GFC v1.13 `lossyear`
    (`scripts/perdida_hansen.py`).
- **Variantes del crosswalk** (`scripts/variante_crosswalk.py`): reetiquetan clases de CCS-BAP sobre
  los mapas v5. Entran por protocolos `-x1`, `-x2` y `-x3`, copias byte a byte de v5 con mapas o
  capas agregadas (`ampliar_mapas`).
- **Dos agentes de investigación:** uno para el CBH de literatura y otro para la antigüedad del
  dosel y el rebrote post-fuego. Sus conclusiones y fuentes están en `DECISIONES-DIRECTOR.md`.
- **Pavesas:** `write_namelist(spotting=...)` escribe `&SPOTTING` con la plantilla de hindcast del
  proveedor. ELMFIRE sortea cada parámetro entre su `_MIN` y su `_MAX` aun en una corrida única, así
  que se escriben iguales (trampa en el skill).
- Métricas: `principal` guarda ahora Dice, IoU, precisión, recall y tp/fp/fn; `tabla` y `objetivo`
  los muestran también para las iteraciones viejas.

**Resultado, por palanca** (media / mediana del Dice en calibración; alarmas sin el caso límite):

| Palanca | Mejor variante | Media / mediana | Alarmas | Adoptada |
|---|---|---|---|---|
| Base (`lw-100-001` v5) | — | 0,381 / 0,451 | 0 | — |
| Dosel en el matorral (§1) | sin dosel en SH4 | 0,385 / 0,452 | 1 | no |
| CBH uniforme (§2) | × 0,5 | 0,399 / 0,439 | 0 | no |
| **CBH de literatura (§2, §5)** | por tipo de bosque | **0,414 / 0,495** | 1 (2,03) | sí |
| **Estepa sobre 1.300 m → NB9** | — | 0,390 / 0,447 | 0 | sí |
| Estepa (GR3) → GR1 / GR2 | — | 0,381 / 0,459 · 0,379 / 0,457 | 0 | sí, GR2, por la alarma |
| Lenga achaparrada → SH3 | — | 0,373 / 0,448 | 1 | no (Cholila 0,213) |
| **Remanente → SH3 + pérdida previa (§3, §4)** | — | **0,398 / 0,493** | 0 | sí |
| Pavesas | 10 % copa / 1 % superficie, CBH × 0,5 | 0,415 / 0,468 | 2 | no |
| Combustible de quema de 0–2 años | NB9 / GR1 | +0,000 | 0 | no |
| LW 95 / 105 % (con todo) | — | 0,444 / 0,524 · 0,431 / 0,485 | 1 · 0 | no |
| **Todo junto** | `lw100-lit-altoremsh3-perd-gr2-001` | **0,440 / 0,501** | **0** | — |

- La validación cruzada entre las 28 recetas completas elige la combinación en 5 de 7 pliegues;
  fuera de muestra, 0,424 / 0,501.
- **Las pavesas de la plantilla de hindcast no encienden ni un foco** (TOA idéntico byte a byte en
  Alerces 2016). Fuertes (10 % / 1 %), Cholila sube de 0,425 a 0,514, pero Alerces 2023 y Epuyén se
  pasan. El CBH de literatura logra lo mismo en Cholila (0,508) sin pavesas.
- **El dosel en el matorral se mantiene:** con el WAF de bosque esos matorrales propagan a lo que
  piden los incendios; sin él, se pasan.

**En la causa (protocolos v6).**
- `fuels_builder`: Estepa → GR2, y sobre 1.300 m (DEM de referencia) → NB9; remanente → SH3.
- `canopy_builder.derive_cbh_cbd`: CBH por tipo de bosque y CBD del pino (con el `fbfm40`), y sin
  dosel en la pérdida de Hansen anterior al año del incendio.
- La preparación de la app usa los dos (`settings.hansen_lossyear_path`).
- En el benchmark: `preparar_benchmark.py --combustible-desde` rehace los mapas, y el empaquetador
  deriva el dosel por caso (`dosel_por_combustible`).
- Contra v5, el paquete v6 cambia sólo cc, ch, cbh, cbd y el mapa; las ventanas son idénticas. Los
  mapas v6 difieren del efectivo de `-x3` en 0,07–0,09 % de las celdas (bordes de polígono).
- **`lw-100-001` sobre v6 reproduce la receta: 0,439 / 0,501, sin alarmas** (ningún incendio a más
  de 0,004). `benchmarks/particion.json` apunta a v6.

| Incendio | `lw-100-001` v5 | `lw-100-001` v6 | `base-001` v6 |
|---|---|---|---|
| Alerces 2023 (h54) | 0,496 / 1,83 | 0,528 / 1,86 | 0,488 / 1,59 |
| Epuyén 2025 | 0,500 / 1,75 | 0,501 / 1,41 | 0,469 / 1,14 |
| Alerces 2024 | 0,562 / 1,54 | 0,635 / 1,35 | 0,619 / 1,17 |
| Patriada 2026 | 0,368 / 0,90 | 0,496 / 0,70 | 0,424 / 0,51 |
| Las Golondrinas (límite) | 0,012 / 0,02 | 0,012 / 0,02 | 0,011 / 0,02 |
| Alerces 2016 | 0,451 / 1,33 | 0,389 / 1,69 | 0,421 / 1,11 |
| Cholila 2015 | 0,280 / 0,55 | 0,513 / 0,87 | 0,459 / 0,69 |
| **Calibración** | 0,381 / 0,451 | **0,439 / 0,501** | 0,413 / 0,459 |
| IoU / precisión / recall | 0,249 / 0,386 / 0,458 | 0,297 / 0,448 / 0,504 | 0,274 / 0,468 / 0,423 |
| El Turbio 2025 (prueba) | 0,296 / 5,73 ⚠ | 0,122 / 1,08 | 0,111 / 0,94 |
| Puerto Café 2025 (prueba) | 0,144 / 0,29 ⚠ | 0,207 / 0,30 ⚠ | 0,201 / 0,27 ⚠ |
| Epuyén 2019 (prueba) | 0,114 / 16,5 ⚠ | 0,128 / 14,6 ⚠ | 0,154 / 11,7 ⚠ |
| Alerces 2015 (prueba) | 0,298 / 1,49 | 0,309 / 1,48 | 0,249 / 1,05 |
| **Prueba** | 0,213 / 0,220 (3 alarmas) | 0,191 / 0,167 (2) | 0,179 / 0,178 (2) |

- **La prueba baja de media por El Turbio**, que antes "acertaba" con 5,7× el área. Con el
  remanente lento y sin el dosel de 2000 el área es la correcta (1,08), pero el lugar no: ardió
  latente y combatido diez días, el límite de supresión. Los otros tres mejoran.
- **Alerces 2016 es el costo:** la copa del bosque con caña (TU5 a 1,5 m) lo acelera (sesgo 1,33 →
  1,69). Con TU5 a 2,5 m vuelve a 0,427, pero Cholila cae a 0,313: no hay un valor que sirva a los
  dos.
- Corridas `sucio`: `los-alerces-2023/calibracion-v5-h54 lw100-sin-dosel-sh4-001` corrió con
  cambios sin commitear que no la afectan (`anios_publicados`); receta descartada.

## 6. Resultados

Dice / sesgo al horizonte contra la cicatriz (truncada al horizonte, salvo Las Golondrinas).
⚠ = sesgo fuera de [0,5; 2]. v3 = RESULTADOS-CSS-BAP §5; v4 = con las correcciones de esta
auditoría. Alerces 2023: v3 a 72 h; v4 a 54 h (loop C), con la cifra a 72 h entre paréntesis.

**Calibración** (se usaron para elegir):

| Incendio | Clima | v3 `base-001` | v3 `lw100-adj115-001` | v4 `base-001` | v4 `adj-110-001` | **v4 `lw-100-001`** | v4 `lw100-adj115-001` |
|---|---|---|---|---|---|---|---|
| Alerces 2023 | GFS | 0,457 / 0,95 | 0,522 / 1,61 | 0,460 / 1,55 (0,477 / 2,72 ⚠) | 0,490 / 1,84 (0,445 / 3,38 ⚠) | **0,495 / 1,82** | 0,487 / 2,47 ⚠ |
| Epuyén 2025 | GFS | 0,160 / 0,44 ⚠ | 0,291 / 0,83 | 0,466 / 1,30 | 0,498 / 1,60 | **0,500 / 1,75** | 0,521 / 2,33 ⚠ |
| Alerces 2024 | GFS | 0,522 / 0,53 | 0,555 / 1,02 | 0,556 / 1,37 | 0,561 / 1,55 | **0,563 / 1,54** | 0,571 / 1,88 |
| Patriada 2026 | GFS | 0,340 / 0,69 | 0,454 / 1,14 | 0,321 / 0,74 | 0,335 / 0,83 | **0,368 / 0,91** | 0,397 / 1,18 |
| Las Golondrinas 2021 (límite) | GFS | 0,029 / 0,05 ⚠ | 0,047 / 0,06 ⚠ | 0,010 / 0,02 ⚠ | 0,013 / 0,02 ⚠ | 0,012 / 0,02 ⚠ | 0,014 / 0,02 ⚠ |
| Alerces 2016 | ERA5 | 0,433 / 0,99 | 0,411 / 1,95 | 0,444 / 1,05 | 0,430 / 1,31 | **0,452 / 1,33** | 0,405 / 1,83 |
| Cholila 2015 | ERA5 | 0,244 / 0,44 ⚠ | 0,324 / 0,66 | 0,255 / 0,44 ⚠ | 0,283 / 0,53 | **0,280 / 0,55** | 0,331 / 0,69 |
| **Media / mediana** | | 0,312 / 0,340 | 0,372 / 0,411 | 0,359 / 0,444 | 0,373 / 0,430 | **0,381 / 0,452** | 0,389 / 0,405 |
| **Alarmas (sin el límite)** | | 2 | 0 | 1 | 0 | **0** | 2 |

**Prueba** (no se usaron para elegir):

| Incendio | Clima | v3 `base-001` | v3 `lw100-adj115-001` | v4 `base-001` | v4 `adj-110-001` | **v4 `lw-100-001`** |
|---|---|---|---|---|---|---|
| El Turbio 2025 | GFS | 0,356 / 4,55 ⚠ | 0,256 / 6,75 ⚠ | 0,333 / 4,96 ⚠ | 0,291 / 5,85 ⚠ | **0,297 / 5,71 ⚠** |
| Puerto Café 2025 (`v4s`) | GFS | 0,126 / 0,23 ⚠ | 0,167 / 0,32 ⚠ | 0,128 / 0,25 ⚠ | 0,146 / 0,29 ⚠ | **0,144 / 0,29 ⚠** |
| Epuyén 2019 | ERA5 | 0,129 / 13,7 ⚠ | 0,112 / 16,8 ⚠ | 0,122 / 15,0 ⚠ | 0,118 / 15,8 ⚠ | **0,114 / 16,5 ⚠** |
| Alerces 2015 | ERA5 | 0,195 / 0,40 ⚠ | 0,312 / 1,38 | 0,255 / 0,96 | 0,260 / 1,26 | **0,297 / 1,50** |
| **Media / mediana** | | 0,202 / 0,162 | 0,212 / 0,211 | 0,209 / 0,191 | 0,204 / 0,203 | **0,213 / 0,220** |

**La receta nueva contra las de referencia.** `lw-100-001` sobre v4 sube el Dice de
calibración de 0,312 / 0,340 (`base-001` v3) a 0,381 / 0,452, sin alarmas, y supera a la receta
v3 (`lw100-adj115-001`, 0,372 / 0,411):

- con un modelo que avanza a la velocidad de Rothermel y con el clima hora a hora;
- **sin ADJ**: la receta v3 necesitaba ADJ 1,15 además de LW 100 %, y ese ADJ compensaba los
  bugs;
- mucho más robusta a la ignición: 0,460 contra 0,395–0,398 en las 21 corridas perturbadas, con
  3 alarmas al borde contra 5–7.

En prueba casi no cambia (0,213 contra 0,212): la transferencia la limitan los dos regímenes que
la calibración no ve (supresión cerca de poblados) y la explosión de Café. Alerces 2015, el único
de prueba en el régimen calibrado, mejora de 0,195 (v3 base) a 0,297.

**Qué cambio movió cuánto y por qué** (media de calibración salvo donde se dice):

| Cambio | Efecto | Por qué |
|---|---|---|
| Hallazgos 1 + 2 (clima hora a hora, `phi` ±1), `base-001` v3 → v4 | +0,05 de media, +0,10 de mediana; Epuyén +0,31 | El frente avanza a la velocidad calculada, y cada ventana tiene su ciclo diurno en vez de la hora de arranque congelada |
| Horizonte de Alerces 2023 a 54 h (regla §2.9) | sesgo base 2,72 → 1,55 | El área FIRMS deja de crecer a las 54 h; las 18 h siguientes eran fuego sin supresión |
| LW 110 → 100 % (ADJ 1) | **+0,022 de media, +0,008 de mediana**; Cholila sale de la alarma | Acelera sólo donde hay carga viva (SH, TU): Patriada, Alerces 2016, Cholila; casi no mueve a Alerces 2023 (TU/TL) |
| ADJ 1,0 → 1,1 | +0,014; Cholila sale de la alarma | Único ADJ uniforme sin alarmas: ~[1,05; 1,15], entre Cholila (lento) y Alerces 2023 (combatido) |
| LW 110 → 100 % + ADJ 1,15 (la receta v3) | +0,016 de media, pero dos alarmas | Con la física corregida acelera de más a Epuyén y Alerces 2023 |
| Dosel coherente (sospecha 6) | ±0 de media; +0,10 Patriada, −0,12 Alerces 2016 | Redistribuye velocidad hacia el matorral con dosel de Hansen |
| ERA5 ×1,3 (loop D) | −0,004; Alerces 2016 −0,04 | Alerces 2016 no necesitaba viento; a Cholila le falta la explosión, no viento medio |
| Hallazgo 3 (`wd` por el camino corto) | no medido aparte; 0–1,6 % de los intervalos horarios en estos incendios | Régimen del oeste: casi nunca se cruza el sur |

## 7. Para corregir afuera

### 7.1 Documentos con números afectados por los bugs

**Aplicado el 2026-09-30:** `RESULTADOS-CSS-BAP.md`, `RESULTADOS.md`, `IGN-26-VALIDACION.md`,
`PENDING_PARAMETERS.md` y `docs/historico/IGN-20B-FINAL-CROSSWALK-CCSBAP.md` llevan una nota al
principio y los números corregidos al lado de los anteriores; las secciones de estado y los
veredictos están actualizados. Las bitácoras se conservan como registro. Lo que sigue es la lista
original.

- **`RESULTADOS-CSS-BAP.md`, `RESULTADOS.md` e `IGN-26-VALIDACION.md`:** todas sus corridas
  tienen los hallazgos 1 y 2 (clima congelado en la primera hora de cada ventana y frente a la
  mitad de la velocidad calculada). Lo que hay que rehacer o re-leer:
  - la receta (ADJ 1,15 + LW 100 %) y el ADJ 1,3: con la interfaz corregida sobra el ADJ; la
    receta es LW 100 % (§6);
  - "el día 1 queda 10–50× por debajo": ahora 8–30× en cuatro de siete, y Alerces 2023 lo
    reproduce (389 contra 485 ha);
  - "la ignición (±500 m / ±2 h) mueve el Dice ±0,1–0,2": ahora bastante menos (Epuyén de 0,37
    a 0,50 con la receta final, contra 0,08–0,50);
  - la equivalencia GFS/ERA5 (§2.13): ERA5 propaga ~20 % menos; la receta no cambia (loop D);
  - las comparaciones entre mapas de combustible de `RESULTADOS.md` §4–§8 y los harness A y B
    de IGN-26: hay que re-correrlas en v4 antes de citar sus órdenes.
  - Siguen valiendo los análisis que comparan insumos sin correr ELMFIRE (m1 de estaciones
    contra GFS, Fosberg, ERA5 contra estaciones).
- **Redacción "banda n en TSTART + n × DT"** (el código hacía lo correcto): ya corregida en
  `docs/elmfire-mapping.md`, `app/ingestion/meteorology/gfs/client.py`,
  `app/preparation/service.py`, `scripts/trim_weather_bands.py` (que además calculaba mal las
  bandas con TSTART > 0) y `tests/test_fuels_source_and_clock.py`.
- **Grilla de clima alta (hallazgo 5):** corregido en `write_namelist` (loop H). Lo que hay que
  re-leer: `puerto-patriada-2026/ventanas-firms` (harness A de IGN-26; la mitad del fuego simulado
  estaba en la franja) y el punto 6 de `RESULTADOS.md`, que ya había que rehacer por los
  hallazgos 1 y 2. En la calibración v4 el efecto medido es despreciable.
- **Dosel (hallazgo 4):** corregido (también con CH sin dato) y en el benchmark desde los
  protocolos v5 (loop I); efecto ≤ 0,001 en el Dice.

### 7.2 Para el director (combustible y dosel)

- **Matorral con dosel de bosque (sospecha 6).** Ñire bajo, lenga baja/achaparrada y parte del
  arbustal nativo se asignan a SH (matorral abierto), pero Hansen 2000 + ETH 2020 les dan
  cobertura de bosque cerrado (mediana 78–91 %, 13–18 m). ELMFIRE combina los dos y les aplica
  el WAF de un bosque (~0,08 en vez de 0,46). En Alerces 2024, dos tercios del matorral quemado
  es ñire bajo. Hay que decidir, para esas clases, si son un combustible arbustivo expuesto al
  viento (sin dosel) o un sotobosque bajo dosel (modelo TU). El diagnóstico `dosel-coherente-001`
  mide el efecto: +0,10 en Patriada, +0,06 en Alerces 2024, −0,12 en Alerces 2016.
- **Hansen es de 2000.** En El Turbio 2025, el 83 % de la cicatriz figura como bosque cerrado
  donde CCS-BAP 2017 ve el rebrote de la cicatriz de 2015 (GS3). La cobertura del dosel es 17–25
  años más vieja que los incendios de calibración.
- **El CBH derivado decide la copa (loop F).** `canopy_builder` usa CBH = CH × (0,20 + 0,30 ×
  CC): 5–10 m en los bosques de la región. Con CBH × 0,25, Cholila pasa de 0,255 a 0,528 y
  Alerces 2024 de 0,556 a 0,614, pero Alerces 2016 y 2023 se pasan. Un CBH con fundamento
  (inventario, o la relación de Cruz et al. 2003 por tipo de bosque) es lo que más movería el
  resultado ahora.
- **Forest → TL8** ya casi no pesa con la interfaz corregida: TU5 en vez de TL8 lleva a Epuyén de
  0,500 a 0,503 (`diag-lw100-tl8-tu5-001` sobre v5; en v3 era +0,05). Lo que decide el día 1 en
  la plantación es la copa. **Rem Dist Rec → GS3** sigue igual (RESULTADOS-CSS-BAP §7.2).
- **La "Estepa" sobre el límite del bosque (loop K).** CCS-BAP llama `OT Herb-Subarb Estepa`
  también a la vegetación altoandina rala entre roca y nieve. El crosswalk la manda a GR3 como
  la estepa de coirón, y sin dosel el fuego simulado la cruza rápido. En Alerces 2015 (prueba),
  GR3 → NB9 baja el falso positivo de 1.284 a 907 ha. ¿Separar la estepa altoandina (por altura o
  por el límite del bosque) con un modelo más ralo o no quemable?
- **Humedad muerta sin gradiente de altura.** Con ERA5 a 0,25° (y GFS) el m1 es el mismo a 500
  y a 1.500 m. `altura-001` lo corrige por temperatura y casi no cambia nada. En Los Alerces el
  cinturón de lenga no ardió y el modelo lo quema tan seco como la costa. Dato que haría falta:
  humedad de combustibles por altura (o estaciones de montaña).

### 7.3 Límites que ninguna corrección resuelve

- **Supresión:** El Turbio y Epuyén 2019 sobre-propagan 5–16× también en v4. Y ahora que el
  modelo va a su velocidad, también se ve en Alerces 2023 si se lo corre más allá de las 54 h.
- **El día 1 explosivo:** 8–30× por debajo en cuatro de siete, y la explosión de Cholila a las
  30–42 h y la de Café. Con el CBH derivado la copa casi no participa (0,1–1,7 % de las celdas
  con dosel superan la intensidad crítica); con un CBH bajo sí, pero acelera todo el incendio,
  no el salto (loop F). Las pavesas están apagadas.
- **Dirección del viento de superficie:** el frente real corre 20–100° más al sur que el empuje
  del GFS, igual que en v3. El caso extremo es Alerces 2015 (loop K): régimen del este débil,
  carrera nocturna al N bordeando el lago. Bajo dosel (WAF ~0,08) harían falta ≥ 17 mph del SSE a
  20 pies para que el viento le gane a la pendiente, y ni ERA5, ni Esquel, ni WindNinja tienen
  viento del S.
- **Las Golondrinas:** la ráfaga nocturna del norte no está en el GFS; peor en v4 (0,010) porque
  en v3 corría 24 h con la tarde congelada.

### 7.4 Cambios pendientes en el documento de combustibles (`docs/historico/IGN-20B-FINAL-CROSSWALK-CCSBAP.md`)

**Aplicado el 2026-09-30** en el documento (nota al principio; §5.4, §5.7, §6.1–§6.3, §7 y §9),
a pedido del autor. La tabla de correspondencia (§4) no se tocó. Lista original, sección por
sección:

- **§6.2 Paso 4 contra la quema A4 — cambian los números y una conclusión.** El script
  (`scripts/paso4_quema_a4.py`) corre en el playground, que escribía `phi` en metros (hallazgo
  2), y mide la velocidad con el TOA: todas las velocidades salían a ~0,5×. La llama no cambia
  (sale de la intensidad que ELMFIRE calcula). Re-corrido el 2026-09-30 con el playground
  corregido:

  | Modelo | ROS sostenido (doc → real) | Llama | ROS ráfaga (doc → real) | Llama |
  |---|---|---|---|---|
  | SH8 (148) | 437 → **739 m/h** | 3,5 m | 900 → **1.785 m/h** | 5,6 m |
  | SH4 (144) | 522 → **888 m/h** | 2,2 m | 1.201 → **2.445 m/h** | 3,7 m |
  | GS3 (123) | 627 → **1.098 m/h** | 2,8 m | 1.394 → **2.896 m/h** | 4,5 m |
  | SH9 (149) | 1.034 → 1.966 m/h | 7,9 m | 2.321 → 4.875 m/h | 11,8 m |
  | SH5 (145) | 1.091 → 2.118 m/h | 5,1 m | 2.529 → 5.085 m/h | 7,4 m |

  Observado: 4.800 m/h (pico bajo ráfaga), llama de 3 a 4 m.
  - SH8 sigue por debajo, pero **2,7–6,5×**, no "5 a 11 veces".
  - **SH4 y GS3, con ráfaga, llegan al 51–60 % de lo observado con la llama medida** (3,7 y
    4,5 m): la lectura 1 ("ningún modelo de arbustal reproduce propagación y llama a la vez") ya
    no vale tal cual; con ráfaga, SH4 queda cerca de hacerlo.
  - SH9 y SH5 alcanzan la propagación observada, pero con llamas de 7 a 12 m: siguen
    descartados por llama, como decía el documento.
  - El "sesgo declarado de subestimar la propagación" de SH8, SH4 y GS3 (§5.4, §6.2 "Qué se
    hace con esto", §9) sigue en pie pero es la mitad de grande. Hay que reescribirlo con estos
    números.
- **§6.1 Comparación de los tres mapas y harness B — re-corridos (loop J, 2026-09-30).** Las
  corridas del documento tenían los hallazgos 1–5: además del frente a la mitad, **las 12 h
  corrían con el clima de la banda 0 congelado**. Re-corridas sobre los mismos insumos (misma
  semilla, los mismos tres `fbfm40` de cada corrida vieja) con la interfaz corregida
  (`scripts/corregir_preparacion_legado.py`, loop J). Cambian los números y parte de la lectura.
  - **Comparación preliminar** (grilla reducida 1.414 × 1.526, semilla 8.095 ha, LH 30 / LW 110):

    | Mapa | Anillo (doc → corregido) | FLI mediana (doc → corregido) | FLI p90 |
    |---|---|---|---|
    | WorldCover 2021 | 2.342 → **3.892 ha** | 96,1 → 32,1 kW/m | 333 → 263 |
    | MapBiomas 2024 | 5.849 → **7.268 ha** (+87 %) | 311,1 → 261,5 kW/m | 1.267 → 1.112 |
    | CCS-BAP 2017 | 7.576 → **9.262 ha** (+138 %) | 317,0 → 234,8 kW/m | 1.309 → 1.028 |

    IoU entre mapas: WC–MB 0,245 → 0,302; WC–CCS 0,269 → 0,344; MB–CCS 0,599 → 0,574. Qué quema
    CCS-BAP casi no cambia (SH8 30 %, TL6 18 %, TU5 17 %, GR3 11 %, SH4 10 %, TU3 10 %).
    Con **LW 100 %** (el valor calibrado): 3.892 / 8.095 / 10.113 ha, IoU 0,304 / 0,328 / 0,594.
    - El orden WorldCover < MapBiomas < CCS-BAP se sostiene; la diferencia se achica de 3,2× a
      2,4× (2,6× con LW 100 %).
    - **"FLI ∝ velocidad: se duplican" no se cumplió:** las intensidades bajan. El anillo crece
      menos de 2× y la intensidad baja porque el clima ahora cambia hora a hora: la banda 0 era
      la más seca (m1 medio 5,1 %) y ventosa (5,3 mph); a las 12 h, m1 11,9 % y 1,7 mph.
  - **Harness B** (AOI 2.563 × 3.222, semilla 17.747 ha, TSTART 6.360 s, 12 h). **No se
    reproduce la referencia del documento:** las 196 máscaras con la ventana pre de
    noviembre-diciembre de 2023 ya no están (`dataset/mascaras` y `metadata.csv` salieron de `mask-dataset-gen` en su migración a un dataset por incendio, `c3f67db`–`5318c24`). Se
    puntuó contra `puerto-patriada-2026/runs/baseline-002` (mismo algoritmo dNBR ≥ 0,30 y las
    mismas 196 celdas, pre 2025-11-01 → 2026-01-04; 66.916 ha observadas en la cobertura), las
    corridas viejas y las corregidas:

    | Mapa | IoU (doc / viejas contra baseline-002 / **corregidas**) | Recall | Precisión | Anillo (viejas → corregidas) |
    |---|---|---|---|---|
    | WorldCover | 0,036 / 0,035 / **0,010** | 0,043 / 0,043 / **0,010** | 0,182 / 0,157 / **0,205** | 16.343 → 2.804 ha |
    | MapBiomas | 0,045 / 0,051 / **0,035** | 0,048 / 0,055 / **0,036** | 0,412 / 0,406 / **0,443** | 7.724 → 4.613 ha |
    | CCS-BAP | 0,067 / 0,069 / **0,046** | 0,082 / 0,088 / **0,052** | 0,267 / 0,247 / **0,286** | 22.604 → 10.563 ha |

    Estrato 70–100 % (11 tiles), corregidas: WC 0,010, MB 0,034, **CCS 0,056** (viejas contra
    baseline-002: 0,044 / 0,051 / 0,099; doc: 0,047 / 0,051 / 0,101).
    - **El orden de IoU se sostiene** (CCS-BAP > MapBiomas > WorldCover) y MapBiomas sigue con la
      mayor precisión. Los valores bajan porque el anillo es la mitad: la corrida vieja tenía
      12 h de la tarde de la ignición (banda 0: 9,1 mph, m1 11,3 %); la corregida atraviesa la
      noche (2,4 mph, m1 23 % a las 12 h). El "anclaje temporal corregido" (TSTART 6.360 s) que
      cita el documento no tenía efecto en las corridas viejas: ELMFIRE usaba igual la banda 0.
    - La preparación vieja (`cmp_aoi_*`) tenía 13 bandas por `trim_weather_bands.py` (§7.1) y
      la corrida necesita 14: el clima corregido sale de la preparación original de 25 bandas
      (`c27d2561…`), recortado a 14; las bandas 1–13 son idénticas.
    - Los anillos de WorldCover y MapBiomas cambian de orden entre sí (16.343 > 7.724 en las
      viejas; 2.804 < 4.613 corregidas): el baseline "rápido" de la corrida vieja era el GR2 con
      la tarde congelada.
- **§6.3 Sensibilidad a la humedad viva — re-corrida (loop J).** Misma base corregida, CCS-BAP,
  12 h:

  | LH/LW | Anillo (doc → corregido) | vs 60 % | FLI mediana (doc → corregido) |
  |---|---|---|---|
  | 30 % | 11.293 → **14.120 ha** | +7 % | 512,0 → 391 kW/m |
  | 60 % | 10.537 → **13.241 ha** | — | 484,9 → 367 kW/m |
  | 90 % | 7.472 → **8.930 ha** | −33 % | 327,5 → 245 kW/m |
  | 120 % | 4.513 → **5.575 ha** | −58 % | 220,5 → 154 kW/m |

  - El factor entre 30 y 120 % **se sostiene: 2,53** en superficie (doc 2,50) y 2,54 en
    intensidad mediana (doc 2,3). La humedad viva sigue siendo un driver de primer orden.
  - "La fila de 60 % reproduce la corrida vieja de §6.1" ya no aplica: esa corrida no se
    re-corrió con LH/LW 60 %.
  - Y el valor adoptado: la calibración elige **LW 100 %**, no 110 % (§6 de este documento, loop
    E; se sostiene en v5, loop I). El fundamento de Bianchi y Defossé no cambia: 110 % es el
    umbral por debajo del cual ocurren los grandes incendios, así que el día de un gran incendio
    está por debajo.
- **§5.4 y §5.5 (ñire bajo y lenga achaparrada → SH8):** la asignación no cambia, pero hay que
  declarar la interacción con el dosel (sospecha 6): Hansen 2000 + ETH 2020 les dan cobertura de
  bosque cerrado (mediana 78–91 %, 13–18 m), y ELMFIRE aplica entonces el WAF de un bosque (~0,08
  en vez del 0,46 de un matorral abierto). En Alerces 2024, dos tercios del matorral quemado es
  ñire bajo. Para el director: ¿son combustible arbustivo expuesto al viento (sin dosel) o
  sotobosque bajo dosel?
- **§5.8 OT Herb-Subarb Estepa → GR3 (loop K, pendiente; no aplicado):** declarar que la clase
  incluye vegetación altoandina sobre el límite del bosque, no sólo estepa de coirón. En el caso
  Alerces 2015 (Cordón Situación) los polígonos de Estepa están a 1.484 m de mediana, el 73 % del
  GR3 del caso está sobre 1.300 m, y es el 12 % del falso positivo de `lw-100-001` (158 de
  1.284 ha). Cuantificado con `reasignar_combustible` (`diag-lw100-gr3-nb-001`, GR3 → NB9): falso
  positivo 1.284 → 907 ha, Dice 0,298 → 0,342. Es un caso de prueba, así que la cifra describe el
  efecto, no fija una corrección; la asignación no cambia sin decisión del director (§7.2).
- **§5.7 Rem Dist Rec → GS3:** sumar la evidencia de El Turbio 2025 (RESULTADOS-CSS-BAP §7.2)
  y que Hansen 2000 todavía ve bosque cerrado en el 83 % de esa cicatriz.
- **§7 Limitaciones:** agregar la edad del dosel (Hansen 2000, 17–25 años antes de los
  incendios) y el CBH derivado como la incertidumbre que más mueve el resultado ahora (loop F).
- **§8 Verificación y §9 Estado:** marcar que las fechas 2026-09-16/19 son de corridas previas a
  la auditoría física.
