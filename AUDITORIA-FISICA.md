# Auditoría física del pipeline ELMFIRE

> Rama `feat/auditoria-fisica`, desde `main` (que ya contiene `feat/calibracion-ccsbap`).
> Antecedente: `RESULTADOS-CSS-BAP.md` (no se edita). Banco de pruebas:
> `scripts/pruebas_fisicas.py`. Fuente de ELMFIRE consultado: etiqueta `2025.0212`.

## 1. Estado actual

*(se reescribe en cada loop — última: loop A, 2026-09-29)*

- **Tres bugs de interfaz confirmados con ELMFIRE real** (§3). Los tres estaban en todas las
  corridas del repo, incluidas las de `RESULTADOS-CSS-BAP.md`:
  1. **Sin `NUM_METEOROLOGY_TIMES`, ELMFIRE usaba la banda 0 del clima toda la ventana.** Cada
     ventana de 24 h corrió con el viento y la humedad de su primera hora.
  2. **`phi.tif` en metros frenaba el frente a ~0,5×** la velocidad que ELMFIRE mismo calcula.
  3. **`wd` se interpola como ángulo plano** (latente mientras existía el 1): un viento del
     sur gira una vuelta por hora.
- **Corregidos en la causa**, con tests: `namelist_writer` (1), `ignition_builder` y el
  playground (2), `weather_builder.wd_for_elmfire` más `cadena` (3). Trampas en el skill.
- **Mejor receta:** todavía `lw100-adj115-001` sobre v3 (0,372 / 0,411). Sobre v4 deja de
  estar calibrada: los tres bugs frenaban el modelo, así que hay que recalibrar ADJ y LW.
- **Corriendo:** empaquetado `-v4` de los siete de calibración; en la cola, `base-001` y
  `lw100-adj115-001` sobre esos siete.
- **Próximo paso:** con `base-001` v4, leer las curvas (`analizar`) y barrer ADJ hacia abajo
  (0,5–1,0) y LW; la Fase B (insumos reales) en paralelo.

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
6. **Tolerancias del banco:** ±10 % en velocidad, ±15 % en largo/ancho, ±5° en rumbo, ±1
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
- **Sin corregir todavía**: impacto chico y la corrección toca `canopy_builder` (derivación
  del dosel), fuera de lo que la tesis fundamenta. Queda en §7.

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

## 6. Resultados

*(pendiente: `base-001` y `lw100-adj115-001` sobre v4)*

## 7. Para corregir afuera

- **Todos los números de `RESULTADOS-CSS-BAP.md`, `RESULTADOS.md` e `IGN-26-VALIDACION.md`**
  salen de corridas con los hallazgos 1 y 2: clima congelado en la primera hora de cada
  ventana y frente a la mitad de la velocidad calculada. Las comparaciones entre recetas o entre
  mapas de combustible bajo esas condiciones no se trasladan a v4 sin re-correrlas.
  - Los veredictos que dependen de la velocidad (ADJ 1,3, LW 100 %, "el día 1 queda 10–50×
    por debajo") hay que rehacerlos.
  - Los que comparan insumos sin correr ELMFIRE (H1 y H3 del loop 0–1: m1 de estaciones contra
    GFS, Fosberg, ERA5) siguen valiendo.
- **Documentos con la redacción "banda n en TSTART + n × DT"** (el código hacía lo correcto,
  el texto no): `docs/elmfire-mapping.md`, `app/ingestion/meteorology/gfs/client.py`,
  `app/preparation/service.py`, `scripts/trim_weather_bands.py`,
  `tests/test_fuels_source_and_clock.py`.
- **Dosel (hallazgo 4):** celdas con cobertura de Hansen ≥ 15 % y altura de ETH 0 quedan sin
  viento. Corregirlo en `canopy_builder` (sin altura, sin dosel) con su versión de caché.
