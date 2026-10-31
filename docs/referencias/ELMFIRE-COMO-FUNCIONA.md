# ELMFIRE 2025.0212: cómo funciona (lo que afecta la predicción)

> Redactado el 2026-10-17 para el diagnóstico de precisión (tarea C). Todo lo que sigue sale del
> **código Fortran de la rama/tag `2025.0212`** (`github.com/lautenberger/elmfire`), de la
> documentación de ese mismo tag y de lo que emite este repo. No se corrió ELMFIRE. ELMFIRE
> queda fijado en 2025.0212: nada de este documento propone pasar a 1.1+.

## 0. Fuentes y cómo citarlas

| Sigla | Qué es |
|---|---|
| `f90:línea` | Archivo de `build/source/` del tag 2025.0212, p. ej. `elmfire_spread_rate.f90:115`. Copia de sólo lectura en el scratchpad de la sesión; el clon es `git describe` = `tags/2025.0212`. |
| `rst:línea` | Documentación del mismo tag (`docs/user_guide/*.rst`, `docs/tech_ref.rst`). Es el texto completo que los PDF de `docs/referencias/elmfire/` (sitio "2025.0212 documentation") sólo traen como índice. |
| `NW:línea` | `app/elmfire/builder/namelist_writer.py`, lo que este repo emite hoy. |
| PDF 2025.0212 | `docs/referencias/elmfire/Tutorial 0X…pdf`, cita por página del PDF. |

**Dos fuentes que NO son de 2025.0212 y no sirven como verdad:**

- `docs/referencias/elmfire/ELMFIRE_Guide.pdf` es la **"ELMFIRE 1.1 User Guide" (junio 2026)**, no la de
  2025.0212 (PDF p. 1). Describe funciones que el binario fijado no tiene: modelo de superficie
  canadiense `SURFACE_SPREAD_MODEL='CFFDRS'` (PDF p. 10-11), `WS_IN_KPH`, `LANDSCAPE_FILENAME`.
  Verificado: ninguna de las tres aparece en el fuente 2025.0212 (0 coincidencias en `*.f90`).
  Se lo usó sólo para confirmar que un texto conceptual coincide con el código; cada afirmación
  de abajo está respaldada por el fuente 2025.0212.
- `https://elmfire.io/` es el sitio de esa misma línea 1.1 (su índice lista "Canadian Fire Spread
  Model", "Barriers and Breaching", etc.). Se consultó sólo el índice; sus páginas de
  `user_guide.html#…` / `input_reference.html#…` describen 1.1.

La documentación de 2025.0212 **contradice al código en varios puntos** (sección 11). Cuando
difieren, vale el código.

## 1. Un paso de tiempo, de punta a punta

`LEVEL_SET_PROPAGATION` (`elmfire_level_set.f90:18`) hace, por paso (MODE 1):

1. `T = T + DT` (`:467`). Opcional: factor diurno (`:470-490`, apagado por defecto).
2. Índice de banda de clima y fracción de interpolación (`:516-520`).
3. Para las celdas del **borde etiquetado** (`LIST_TAGGED`), re-interpola m1/m10/m100/MLH/MLW/FMC y
   viento cuando venció el reloj de cada uno (`:572-641`).
4. `SURFACE_SPREAD_RATE` (Rothermel) si algo se re-interpoló (`:656`) y `CROWN_SPREAD_RATE`
   (`:660`).
5. Dos etapas RK2: vectores normales a φ, `UX_AND_UY_ELLIPTICAL` (velocidad por celda y
   dirección), CFL, limitador de gradientes, integración (`:663-685`).
6. Celdas con φ ≤ 0 pasan a quemadas: tiempo de llegada, pavesas (`:689-866`), `TAG_BAND`.
7. Ignición por pavesas, clima para celdas recién etiquetadas (`:947-985`), supresión
   (`:994-`), des-etiquetado cada `UNTAG_CELLS_TIMESTEP_INTERVAL` pasos (`:1025-1028`).

El modelo es **local**: cada celda del frente es una elipse independiente (Huygens) cuya forma
sale de Rothermel + viento/pendiente de *esa* celda y *ese* instante (`rst`: `physics.rst:13-22`).

## 2. Propagación superficial

### 2.1 Rothermel (1972) por celda
`SURFACE_SPREAD_RATE` (`elmfire_spread_rate.f90:12-127`). Docstring: "Applies Rothermel surface fire
spread model" (`:14`).

- **Humedades** por clase (`:57-62`): `M(1)=m1`, `M(2)=m10`, `M(3)=m100`, `M(4)=m1` (el "muerto
  dinámico" se fija a m1), `M(5)=MLH`, `M(6)=MLW`. Todas son fracción interna; con
  `DEAD_MC_IN_PERCENT`/`LIVE_MC_IN_PERCENT` = `.TRUE.` (default, `elmfire_namelists.f90:130-131`)
  el lector divide por 100 (`elmfire_io.f90:183-199`).
- **Combustible**: la tabla `FUEL_MODEL_TABLE_2D(modelo, ILH)` con `ILH = NINT(100·MLH)` acotado a
  [30, 120] (`:64-65`). Los modelos "dinámicos" (`.TRUE.` en `fuel_models.csv`, col. 3) reparten
  la carga herbácea viva entre viva y muerta linealmente con MLH entre 30 % y 120 %
  (`elmfire_init.f90:781-795`): **MLH = 30 % = hierba totalmente curada**.
- **Constantes fijas del modelo** (no son keywords): `SIG(10 h)=109`, `SIG(100 h)=30`, `RHOP=32`,
  `ST=0.055`, `SE=0.01` (`elmfire_init.f90:745-751`). Las columnas de `fuel_models.csv` son
  `id, nombre, dinámico, W0(1h), W0(10h), W0(100h), W0(herb), W0(leñoso), SIG(1h), SIG(herb),
  SIG(leñoso), profundidad, Mx_muerto(%), calor de combustión` (`:764-765`).
  Los coeficientes B, C, E, β_op, ξ, Γ' son los de Rothermel/Albini (`:826-858`).
- **Humedad de extinción viva** (`:67-75`), calor de preignición `QIG = 250 + 1116·M` (`:79`),
  amortiguamiento por humedad `1 − 2.59x + 5.11x² − 3.52x³` (`:91-101`), intensidad de reacción
  `IR = IR_muerto + IR_vivo` (`:103`).
- **Factores**: `WS_LIMIT = 0.9·IR` (límite original de Rothermel; el de Andrews-Cruz-Rothermel
  2013 está comentado, `:105-106`); `φw = PHIWTERM · min(WSMF, WS_LIMIT)^B` (`:109`); `φs =
  min(PHISTERM · tan²(pendiente), φw_máx)` (`:112-113`).
- **Velocidad base** (`:115`):

  `VS0 = (ADJ + PERTURB_ADJ) · SUPPRESSION_ADJUSTMENT_FACTOR · DIURNAL_ADJUSTMENT_FACTOR · IR · ξ / ρb·ε·Qig`

  y `VELOCITY_DMS = VS0·(1 + φs + φw)` (`:116`). **`ADJ` multiplica toda la velocidad** (la base y,
  por lo tanto, también los términos de viento y pendiente, porque `1+φs+φw` multiplica a VS0).
  `ADJ` es un ráster Float32 (`elmfire_namelists.f90:104`) copiado al nodo (`elmfire_subs.f90:1074`);
  `PERTURB_ADJ` es **aditivo** (no multiplicativo). Una celda con `ADJ ≤ 0` no se enciende por
  pavesa (`elmfire_level_set.f90:906,926,950`).
- **Intensidad de línea de fuego** `FLIN = TR · IR · V · 0.3048` kW/m (`:121`; recalculada con la
  velocidad direccional en `elmfire_level_set.f90:1783`).
- **Celdas no quemables**: FBFM 90-100, 256 o ≤ 0 (`elmfire_init.f90:157-164`).
- **Redondeos que importan**: pendiente y aspecto entran por tablas indexadas por **grado entero**
  (`NINT`): `TANSLP2(NINT(SLP))` (`elmfire_subs.f90:1075,1098`), `ASP` con `NINT` (`elmfire_level_set.f90:1692`).

### 2.2 Viento y pendiente: factores vectoriales
- La pendiente empuja hacia `ASP − 180°` y el viento hacia `WD − 180°` (`elmfire_level_set.f90:1692-1723`;
  `elmfire_init.f90:111-112`). Ambos se suman como vectores: `φ = φs + φw` (`:1721-1726`), y
  `VELOCITY_DMS = VS0·(α + |φ|)` (`:1735`) con α = factor de aceleración (§2.4).
- `PHIS_ADJ` y `PHIW_ADJ` (default 1) multiplican esas dos contribuciones
  (`:1695,1708,1711`; `elmfire_namelists.f90:605-606`).

### 2.3 Elipse, relación largo/ancho, retroceso y flancos
- **Viento medio de llama efectivo**: se despeja de `|φ|` invirtiendo Rothermel (`:1738`);
  se limita a `0.9·IR` salvo que haya fuego de copa (`:1739`).
- **L/W** (`:1742`): `min(0.936·exp(0.2566·U) + 0.461·exp(−0.1548·U) − 0.397, MAX_LOW)` con
  `U = WSMFEFF · WSMFEFF_LOW_MULT`, `MAX_LOW = 8`, `WSMFEFF_LOW_MULT = 5.07955E-3`
  (`elmfire_namelists.f90:599,620`). Es la forma de Anderson (1983) usada en FARSITE
  (`tech_ref.rst:167-181`). **Ojo:** `5.07955E-3 = 0.3048/60`, o sea ft/min → **m/s**; la doc
  dice "mph" (`tech_ref.rst:176,198-199`). Con 10 mph de viento medio efectivo (880 ft/min) sale
  L/W = 2.78 con el código y 8 (tope) si la fórmula recibiera mph (cuenta propia sobre la
  fórmula de arriba). Este repo ya reproduce la versión en m/s (`scripts/pruebas_fisicas.py:161`).
- **Retroceso**: `VBACK = BOH · VELOCITY_DMS`, con `BOH = (L/W − √(L/W² − 1)) / (L/W + √(L/W² − 1))`
  (`:1744-1749`), es decir, **el retroceso sale de la propia elipse**. La doc dice lo contrario
  ("por defecto el retroceso es V_s0", `tech_ref.rst:230-236`): el código 2025.0212 no tiene esa
  opción.
- **Elipse de Richards (1995)** con foco en el origen del frente (`:1752-1778`; `tech_ref.rst:203-228`),
  rotada a la dirección de máxima propagación y luego **proyectada al plano** del mapa con
  `UXOUSX = 1 − |sin(asp)|·(1 − cos(pendiente))` (`:1698,1775,1778`).
- `NO_SURFACE_FIRE` (en `&SPOTTING`) fija U = 1e-5 (`:1785-1788`); no es parte de nuestro flujo.

### 2.4 Aceleración, ADJ y supresión como multiplicadores
- `SURFACE_ACCELERATION_TIME_CONSTANT` (default 1.0) sólo actúa si es > 30 s
  (`elmfire_level_set.f90:558-565`); con el default α = 1 siempre.
- `DIURNAL_ADJUSTMENT_FACTOR` (1.0 salvo `USE_DIURNAL_ADJUSTMENT_FACTOR = .TRUE.`): fuera de un
  período de quema de `BURN_PERIOD_LENGTH` horas centrado en `SUNRISE + 0.667·(SUNSET−SUNRISE)`
  multiplica VS0 por `OVERNIGHT_ADJUSTMENT_FACTOR` (0.1) (`:470-490`;
  `elmfire_namelists.f90:363-387`).

## 3. Fuego de copa

Un solo modelo, sin alternativas. `CROWN_FIRE_MODEL` sólo se compara con `> 0` o `≤ 0` en todo el
fuente (11 apariciones, ninguna `== 2`; ver `elmfire_level_set.f90:399,660,986,1707,1739,1791,1841`),
y la propia doc de 2025.0212 lo dice: "Currently, only one crown fire model is implemented"
(Tutorial 04, PDF p. 3). El `2` de las plantillas del proveedor se comporta como `1`.

`CROWN_SPREAD_RATE` (`elmfire_spread_rate.f90:131-206`):

1. **Condiciones de partida** (`:161`): `VS0 > 0`, `FLIN_DMS_SURFACE > 0`, `CBD > 1e-3 kg/m³` y
   `CC > 1e-3`. Si CBD o CC son ~0 la celda **nunca** tiene copa.
2. **Iniciación: Van Wagner (1977).** `I_crítica = (0.01 · CBH · (460 + 26·FMC))^1.5` kW/m
   (`:167-169`), con CBH en metros (+ `PERTURB_CBH`, mínimo 0.1 m) y `FMC` = humedad foliar en %.
   CBH < 0 → `9E9` (no inicia nunca, `:171`). Se calcula **una vez por nodo** (cuando
   `CRITICAL_FLIN > 1E9`, `:164`) con el FMC de ese momento.
   Hay copa cuando `FLIN_DMS_SURFACE > I_crítica` (`:175`). Ejemplo (cuenta propia): FMC = 90 %,
   CBH = 2 m → 419 kW/m; CBH = 1 m → 148 kW/m.
3. **Velocidad de copa: Cruz et al. (2005)** (`physics.rst:29-32`; `tech_ref.rst:325-338`):
   `CROS_activo = CROWN_FIRE_ADJ · 11.02 · U10^0.9 · CBD^0.19 · exp(−0.17·M1_%)` m/min (`:178`; el
   `/0.3048` la pasa a ft/min), con `U10` = viento de 20 ft **sin reducir por dosel** convertido a
   10 m con ÷0.87 (`:140,177`), tope `CROWN_FIRE_SPREAD_RATE_LIMIT` = 250 ft/min (`:179`).
4. **Activo vs. pasivo** (`:180-197`): `R0 = 3/CBD` (crítico de Van Wagner) y `CAC = CROS/R0`.
   `CAC > 1` → activo: `CROWN_FIRE=2` y `CROS = CROS_activo` **si** `CC ≥ CRITICAL_CANOPY_COVER`
   (0.39 fracción, `elmfire_namelists.f90:591`); si `CC` es menor, marca 1 pero sin velocidad de
   copa. `CAC ≤ 1` → pasivo: `CROS = CROS_activo · exp(−CAC)` (mismo requisito de CC).
5. **Cómo se combina con la superficie** (`tech_ref.rst:340-356`): la copa **no suma**; sube el
   factor de viento: `PHIW_CROWN = min(max(CROS/max(VS0,0.001) − 1, 0), 200)` (`:187,195`) y la
   celda usa `APHIW = PHIW_ADJ · max(PHIW_SURFACE, PHIW_CROWN)` cuando `FLIN_SURFACE ≥ CRITICAL_FLIN`
   (`elmfire_level_set.f90:1707-1709`). Además se quita el tope `0.9·IR` al viento efectivo
   (`:1739`), así que L/W sube; y la celda se re-evalúa una vez más si pasó a copa durante el
   cálculo (`:1704,1791-1797`). La pendiente sigue sumándose igual.
   Matiz: el tope `0.9·IR` se levanta apenas `FLIN_SURFACE ≥ CRITICAL_FLIN`, **aunque `CC < 0.39`**
   (ahí la copa no aporta velocidad, pero la elipse se afila). Resultado: la copa acelera el
   **frente** (cabeza) y cambia la forma.
6. **Humedad foliar (FMC)**: constante `FOLIAR_MOISTURE_CONTENT` = **90 %** por defecto
   (`elmfire_namelists.f90:123`), **y hay ráster por celda y por banda** con
   `USE_CONSTANT_FMC = .FALSE.` + `FMC_FILENAME` (`:92,122,152`; `elmfire_io.f90:232-241`;
   `io.rst:104-117`). Este repo no escribe ninguna de las dos (usa el 90 por defecto implícito;
   `app/validation/copa.py:25` lo sabe). La plantilla de hindcast del proveedor usa 110 %
   (`runs/hindcasts/templates/hindcast/elmfire.data`, `FOLIAR_MOISTURE_CONTENT = 110.0`).
7. **Rásters que entran**: `cc` (fracción tras ÷100, `elmfire_io.f90:298`), `ch` (÷10, `:308`), `cbh` (÷10 → m,
   `:278`), `cbd` (÷100 → kg/m³, `:288`); `CH` interviene además en el WAF (§5). `HPUA_CANOPY =
   CBD·(CH−CBH)·12000` kJ/m² sólo alimenta `FLIN_CANOPY`/salidas (`:165`; `level_set:1841`).
8. `CROWN_RATIO` (default 1.0) sólo entra en el WAF (`elmfire_init.f90:561`), no en la copa.

## 4. Pavesas (spotting)

Apagado por defecto (`ENABLE_SPOTTING = .FALSE.`, `elmfire_namelists.f90:693`). Con
`USE_SUPERSEDED_SPOTTING = .TRUE.` (default, `:736`) se usa `elmfire_spotting_superseded.f90`, no
`elmfire_spotting.f90`; ninguno de los dos es el modelo del paper original (`spotting.rst:7-9`).

- **Cuándo se generan** (al quemarse una celda, `elmfire_level_set.f90:769-866`): (a) copa: si
  `FLIN_SURFACE ≥ CRITICAL_FLIN`, con probabilidad `CROWN_FIRE_SPOTTING_PERCENT/100` (`:773-776`);
  (b) superficie, si `ENABLE_SURFACE_FIRE_SPOTTING` y no hubo (a): si `FLIN_SURFACE ≥
  CRITICAL_SPOTTING_FIRELINE_INTENSITY(fbfm)`, con probabilidad
  `SURFACE_FIRE_SPOTTING_PERCENT(fbfm)/100` (`:778-783`).
- **Cuántas**: `NEMBERS = NEMBERS_MIN + NINT(R·(NEMBERS_MAX − NEMBERS_MIN))`
  (`elmfire_spotting_superseded.f90:45-46`). El default `NEMBERS_MIN = 30` con `NEMBERS_MAX = 1`
  (`elmfire_namelists.f90:704,707`) da hasta 30 pavesas por evento; este repo escribe 1 y 1.
- **Distancia**: lognormal con media `m = MEAN_SPOTTING_DIST · FLIN^SPOT_FLIN_EXP · WS20^SPOT_WS_EXP`
  (mínimo 1 m) y varianza `NORMALIZED_SPOTTING_DIST_VARIANCE · m`
  (`superseded.f90:30-32,146-152`; `spotting.rst:36-72`). `WS20` en mph, FLIN en kW/m. Con
  `SPOTTING_DISTRIBUTION_TYPE = 'UNIFORM'` se usan `MIN/MAX_SPOTTING_DISTANCE` (`:144-145`).
- **Transporte**: línea recta con el viento de 20 ft de la celda de lanzamiento, **congelado**
  tras el primer paso (`:232-241`), con un desvío angular uniforme de ±4° por pavesa
  (`EPS = 8·(R − 0.5)`, `:140,224`). No modela ascenso ni deriva por terreno; el aterrizaje sale
  cuando la distancia acumulada alcanza la sorteada (`:196`).
- **Ignición**: con probabilidad `PIGN/100 · SOURCE_FUEL_IGN_MULT`, sólo si la pavesa recorrió
  > 1.5 celdas y **no hay celda quemada (φ < 0) a ≤ 3 celdas** del aterrizaje (`:283-299`);
  luego `TAG_BAND` y φ = −1 si `ADJ > 0` y la celda es quemable (`elmfire_level_set.f90:945-957`).
- **Sorteo aun en corrida única** (confirmado en el repo, `interface-gotchas.md`):
  con `ENABLE_SPOTTING`, `NUM_PARAMETERS_SPOTTING = 8` (`elmfire_namelists.f90:756-760`) y en cada
  caso `SET_SPOTTING_PARAMETERS` pisa `MEAN_SPOTTING_DIST`, `NORMALIZED_…VARIANCE`, `SPOT_WS_EXP`,
  `SPOT_FLIN_EXP`, `NEMBERS_MAX`, `GLOBAL_SURFACE_FIRE_SPOTTING_PERCENT`, `CROWN_FIRE_SPOTTING_PERCENT`
  y `PIGN` con un valor entre `_MIN/_MAX` (`elmfire_spotting.f90:20-38`; `elmfire.f90:574`), y
  recalcula `SURFACE_FIRE_SPOTTING_PERCENT(:) = GLOBAL% · MULT(:)` (`:38`): el keyword por modelo
  de combustible `SURFACE_FIRE_SPOTTING_PERCENT(:)` que muestra la doc **se descarta**.
- `STOCHASTIC_SPOTTING` está marcado "not currently used" (`elmfire_namelists.f90:726`); la doc lo
  presenta como interruptor (`spotting.rst:127-133`).
- Modelos alternativos (UMD/Sardoy, euleriano, ignición por brasas): hay código
  (`USE_UMD_SPOTTING_MODEL`, `USE_EULERIAN_SPOTTING`, … `elmfire_namelists.f90:730-748`) pero no
  están documentados en 2025.0212; no se evaluaron.
- **Lo que emite este repo** (sólo si se pasa `spotting=`): `NW:69-83,113-131`, plantilla de
  hindcast con `_MIN = _MAX` (valor declarado, no sorteado). Producción (`modelo-v0`, receta
  `lw-100-001`) **no** activa pavesas.

## 5. Factor de reducción de viento (WAF) y dosel

- ELMFIRE recibe `ws` en **mph a 20 ft** (`io.rst:87`); con `WS_AT_10M = .TRUE.` multiplica por 0.87
  (`elmfire_io.f90:178`; `elmfire_namelists.f90:162`). Este repo convierte 10 m → 20 ft antes
  (`weather_builder.py:41-81`) y no usa `WS_AT_10M`.
- **Viento de llama** `WSMF = WS20 · max(WAF + PERTURB_WAF, 0) · 5280/60` ft/min
  (`elmfire_subs.f90:496`). El WAF es **un ráster interno, fijo en el tiempo**, calculado una vez
  al iniciar (`elmfire_init.f90:141,523-571`) a partir de `cc`, `ch` y del modelo de combustible
  — **no** lee cbh ni cbd.
- **Sin dosel o dosel ralo** (`F < 0.05`, o CH sin dato): factor de Albini & Baughman (1979) con la
  profundidad `DELTA` del lecho de combustible (`elmfire_init.f90:624-636`, ~0.28 a 0.55 para
  profundidades 0.2-6 ft).
- **Con dosel** (`CC > 1e-4` y `CH > 1e-4`, `:615-623`): `WAF = [1/ln((20+0.36H)/(0.13H))] ·
  [0.555/√(F·H)]`, con `H = CH/0.3048` pies y `F = 0.3333·CC·CROWN_RATIO` (estilo BEHAVE/FARSITE).
  Se tabula para CC 0-100 % y CH 0-120 m **a paso entero** (`:123-127,557-558`). Ejemplos (cuenta
  propia): CC 60 %/CH 20 m → 0.094; CC 30 %/CH 20 m → 0.133; CC 80 %/CH 30 m → 0.074.
- **Mezcla** (`:559-570`): `WAF = min(sombreado, sin dosel)`; si `F ≥ 0.05` (CC ≳ 15 %) se usa el
  sombreado puro; si no, se interpola linealmente con `1 − 20F`. `CC < 0` (nodata) → WAF 0.
- Casos límite que ya están en `interface-gotchas.md`: CC ≥ 15 % con CH = 0 ⇒ WAF = 0 (sin viento).
- **Altura de viento**: todo el modelo de superficie supone 20 ft; la copa convierte a 10 m
  internamente (`÷0.87`, `elmfire_spread_rate.f90:140`); las pavesas usan el 20 ft crudo ×0.447
  m/s por mph (`superseded.f90:172`).
- `PERTURB_WAF` es un delta aditivo global (la plantilla del proveedor usa U(0, 0.05)).

## 6. Humedad de combustibles

| Clase | Origen | Dinámica |
|---|---|---|
| m1, m10, m100 | Rásters multibanda `M1/M10/M100_FILENAME` (`elmfire_io.f90:183-199`) | Interpolación lineal entre bandas, aplicada sólo a celdas del frente cada `DT_INTERPOLATE_M1/M10/M100` = 300/3000/30000 s (`elmfire_namelists.f90:367-369`; `level_set:572-602`). Piso 1 % (`elmfire_subs.f90:440,449,458`). |
| MLH, MLW | **Escalar** `LH/LW_MOISTURE_CONTENT` (default 60 %, `:128-129`) **o ráster multibanda** `MLH/MLW_FILENAME` con `USE_CONSTANT_LH/LW = .FALSE.` (`:143-144,153-154`; `elmfire_io.f90:202-241`; `io.rst:104-117`) | `DT_INTERPOLATE_MLH/MLW = 9E8` (efectivamente fija). **Pisos: MLH ≥ 30 %, MLW ≥ 60 %** (`elmfire_subs.f90:467,476,934,938`). |
| FMC (foliar) | Escalar `FOLIAR_MOISTURE_CONTENT` = 90 % o ráster `FMC_FILENAME` (§3.6) | `DT_INTERPOLATE_FMC = 9E8`. |

- **No hay modelo de retardo ni de humedad de equilibrio dentro de ELMFIRE.** No existe ninguna
  referencia a Nelson/EMC/time-lag en el fuente (`grep -i nelson|equilibrium|EMC|timelag` → sólo
  nombres de variables `RH_FILENAME`, `TMP_FILENAME` declarados en `elmfire_vars.f90:44` y sin uso
  de cálculo). ELMFIRE consume m1/m10/m100 ya calculados. En este repo eso lo hace
  `weather_builder.derive_moisture*` (EMC de Nelson + retardo, `weather_builder.py:134-230`).
- `USE_ERC`/`ERC_FILENAME` sólo modulan la probabilidad de ignición aleatoria
  (`elmfire_subs.f90:1391`), no la propagación.
- Un detalle: el índice de carga herbácea viva `ILH` usa sólo MLH, y MLW sólo entra en las
  humedades de extinción/amortiguamiento (`spread_rate.f90:64,95-101`).

## 7. Esquema numérico del frente

- **Level set de banda estrecha**: φ es un campo ±1; el frente es φ = 0. Se integra
  `∂φ/∂t + Ux·∂φ/∂x + Uy·∂φ/∂y = 0` con RK2 y limitador **superbee** (`tech_ref.rst:28-44`;
  `elmfire_level_set.f90:1915-1943,1465`). Sólo se calcula en celdas a `BANDTHICKNESS = 2`
  celdas del frente (`physics.rst:70-74`; `TAG_BAND`, `:1477-1505`).
- **φ debe ser +1/−1** (el repo ya lo corrigió, `interface-gotchas.md`). El RK2 recorta φ a
  [−100, 100] (`:1927-1930`).
- **Paso de tiempo**: arranca en `SIMULATION_DT`; **desde el 6.º paso** `CALC_CFL` lo ajusta a
  `DT = min(TARGET_CFL·DT/CFL, SIMULATION_DTMAX)` con `CFL = Umax·DT/celda` (`level_set:674,1882-1908`;
  `io.rst:241-246`). Los 5 primeros pasos no se controlan. `TARGET_CFL` por defecto 0.4
  (`elmfire_namelists.f90:386`); el proveedor usa 0.9 en hindcast. Este repo no lo escribe.
  `SIMULATION_DT`/`DTMAX` = 30/300 s (`NW:310-311`).
- **Clima**: `ITLO = clamp(1 + floor(T/DT_METEOROLOGY), 1, NUM_METEOROLOGY_TIMES)`, `ITHI = ITLO+1`
  (tope en el último), `F = (T − (ITLO−1)·DT_MET)/DT_MET` (`level_set:516-520`). Banda 1 es T = 0
  (`io.rst:230-231`). Interpolación **lineal en el tiempo**; en el espacio, vecino más cercano de
  la grilla de clima (`MAP_FINE_TO_COARSE`; bilineal sólo con `WX_BILINEAR_INTERPOLATION`, con el
  bug de `J2` ya documentado). El viento se interpola como ángulo "hacia" (`INTERP_WD_RASTER`,
  `elmfire_subs.f90:363-388`, ya corregido del lado del repo).
- **Re-evaluación**: Rothermel y copa sólo se recalculan cuando algún reloj `DT_INTERPOLATE_*` venció
  (`level_set:656-660`). Con todo en 300 s (viento, m1) y 3000/30000 s para m10/m100, las
  celdas del frente usan valores "escalonados" entre re-interpolaciones; las celdas recién
  etiquetadas reciben el clima del instante (`:961-985`). El repo midió que bajar esos relojes de
  300 s a 10 s no cambia nada (`AUDITORIA-FISICA.md:279`); m100 a 30000 s (8.3 h) no se probó.
- **Des-etiquetado**: cada `UNTAG_CELLS_TIMESTEP_INTERVAL` = 10 pasos y con > 100 celdas
  etiquetadas; quita celdas aisladas, celdas con 1 semana, y (opcionales, apagados)
  `UNTAG_TYPE_2/3` (`:1026-1028,1508-1612`).
- **Fin anticipado**: con ≤ 2 celdas etiquetadas la corrida termina (`:1032-1038`; ya en
  `interface-gotchas.md`).
- **Aleatoriedad**: semilla `SEED = 2024` (`RANDOMIZE_RANDOM_SEED = .FALSE.`, `elmfire.f90:149-152`):
  determinista para un mismo insumo, aunque los sorteos de pavesas son "caóticos".

## 8. Ensamble, Monte Carlo y calibración

**Qué hay** (`&MONTE_CARLO`, `elmfire_namelists.f90:405-443`; `monte_carlo.rst`):

1. **Ignición aleatoria** (`RANDOM_IGNITIONS`, `EDGEBUFFER`, máscara de ignición). No aplica: usamos
   `phi.tif` con el perímetro observado.
2. **Barrido de bandas de clima** (`METEOROLOGY_BAND_START/STOP/SKIP_INTERVAL`): cada caso empieza
   en otra banda de un ráster apilado (`elmfire.f90:309-320,381`; `monte_carlo.rst:60-100`).
   Sirve para correr N ventanas climáticas distintas en una sola invocación.
3. **Perturbación de rásters** (`PERTURB_RASTERS`, `elmfire_subs.f90:156-190`): para `ADJ, CBD, CBH,
   FMC, M1, M10, M100, MLH, MLW, WAF, WD, WS` se sortea **un delta aditivo uniforme** entre
   `PDF_LOWER_LIMIT` y `PDF_UPPER_LIMIT` por caso y se suma en el punto de uso
   (`spread_rate.f90:115,168,176`; `elmfire_subs.f90:380,440-476,496`). Solo `PDF_TYPE='UNIFORM'`
   (`elmfire_namelists.f90:492-495`). `NUM_ENSEMBLE_MEMBERS` define el tamaño.
4. **Fluctuaciones de viento** (`WIND_FLUCTUATIONS` en `&SIMULATOR` + rangos `_MIN/_MAX` en
   `&MONTE_CARLO`): cada `DT_WIND_FLUCTUATIONS` (15 s) un único factor de velocidad y de dirección
   para todo el frente (`elmfire_subs.f90:1008-1032`). La intensidad de dirección es una **fracción
   de 360°**, no grados (`:1018-1022`).
5. **Pavesas sorteadas** entre `_MIN/_MAX` (§4).
6. Receta del proveedor para hindcast con ensamble: `runs/hindcasts/templates/hindcast/elmfire.data`
   (100 miembros; ADJ ±0.30, WS ±3 mph, WD ±7.5°, M1 −0.02/+0.01, M10 −0.02/+0.01, M100 ±0.015, WAF
   0-0.05, fluctuaciones 0.01-0.10, pavesas con rangos).

**Límites verificados en el código** (importantes para no creer la doc):

- `SPATIAL_PERTURBATION` ('GLOBAL'/'PIXEL') y `TEMPORAL_PERTURBATION` ('STATIC'/'DYNAMIC') se
  **validan** (`elmfire_namelists.f90:484-491`) pero **no se usan en ningún otro lugar** (grep en
  todo `build/source/`); `PERTURB_RASTERS` aplica siempre un escalar global y estático. Además
  `CC`, `CH` y `FBFM` se aceptan como `RASTER_TO_PERTURB` (`:497-515`) pero no tienen variable
  `PERTURB_*` (`elmfire_vars.f90:76-77`): se ignoran sin aviso. `PIXEL` y `DYNAMIC` sólo cambian la
  cuenta de parámetros (`:531-537`), con riesgo de desfasar índices de `COEFFS`.
- No hay otra distribución que la uniforme.

**Calibración / asimilación: no hay.** `elmfire_calibration.f90` (115 líneas) sólo **lee tablas**
por pirioma: `ADJUSTMENT_FACTORS_BY_PYROME` (matriz ADJ[pirioma, modelo de combustible] que pisa el
ráster `adj`, `elmfire.f90:229-237`), `DURATION_PDF_BY_PYROME` y constantes de supresión por
pirioma (`elmfire_calibration.f90:21-109`), todo con `NUM_PYROMES = 128` (CONUS) y requiere un
ráster de piriomas (`USE_PYROMES`). `CALIBRATION_TARGET` figura como "deprecated"
(`elmfire_io.f90:115`) y no existe ningún código de optimización/ajuste contra perímetros
(`grep -i optimi|assimil|genetic|simplex|fitness` → sólo comentarios de rendimiento). La doc de
spotting habla de "`CALIBRATION = .TRUE.` … optimizar el acuerdo con perímetros observados"
(`spotting.rst:127-131`): **esa función no está en el binario 2025.0212**. La calibración de ADJ
contra observaciones es externa (la que hace este repo en el banco).

## 9. Supresión (breve)

`&SUPPRESSION` (`elmfire_namelists.f90:781-790`), todo apagado por defecto. Sólo el **ataque
ampliado** es determinista: cada `DT_EXTENDED_ATTACK` sube la contención objetivo según
`MAX_CONTAINMENT_PER_DAY` y `AREA_NO_CONTAINMENT_CHANGE` (acres/día) y anula
`SUPPRESSION_ADJUSTMENT_FACTOR` (`spread_rate.f90:115`) en los sectores más lentos del perímetro
(`elmfire_suppression.f90`; `elmfire_level_set.f90:994-1110`). El ataque inicial sortea con
`RANDOM_NUMBER`. Detalles y trampas (también perturba el frente con 0 %/día, fuego que se
extingue sin ráster) ya están en `.claude/skills/elmfire/references/interface-gotchas.md`. Se
emite con `NW:142-161` sólo si se pasa `suppression=`.

## 10. Tabla de opciones de namelist que afectan la propagación

Convenciones: *Default* = valor en `elmfire_namelists.f90:línea` (NL). *Usamos* = lo que emite
`namelist_writer.py:línea` (NW) con sus valores por omisión de `write_namelist`; "no" = el keyword
no se escribe y rige el default. "Probado" refiere a recetas/auditorías del repo.

### &INPUTS

| Keyword | Default (NL) | Qué hace | ¿Usamos? | Comentario |
|---|---|---|---|---|
| `DT_METEOROLOGY` | −9999.9 (`:120`) | Segundos entre bandas de clima | 3600.0 (`NW:391`) | Banda 1 = T 0 |
| `WS_AT_10M` | `.FALSE.` (`:162`) | ×0.87 al ráster `ws` | no | Conversión hecha en `weather_builder.py` |
| `DEAD_MC_IN_PERCENT` / `LIVE_MC_IN_PERCENT` | `.TRUE.` (`:130-131`) | Escala m1/m10/m100 y MLH/MLW ÷100 | no | OK con %/% |
| `LH_MOISTURE_CONTENT` | 60 (`:128`) | MLH constante (%). Piso real 30 | 30.0 (`NW:392,182`) | Decide la carga herbácea muerta/viva (§2.1) |
| `LW_MOISTURE_CONTENT` | 60 (`:129`) | MLW constante (%). **Piso real 60** | 100.0 (`NW:393,183`) | Receta `lw-100-001` |
| `USE_CONSTANT_LH` / `USE_CONSTANT_LW` | `.TRUE.` (`:153-154`) | `.FALSE.` ⇒ leer `MLH/MLW_FILENAME` por celda y banda | no | Ráster por celda **existe** |
| `MLH_FILENAME` / `MLW_FILENAME` | ' ' (`:143-144`) | Rásters de humedad viva | no | Mismas bandas que `ws` (`io.rst:114-117`) |
| `FOLIAR_MOISTURE_CONTENT` | 90 (`:123`) | FMC constante (%), Van Wagner | no | Proveedor usa 110 |
| `USE_CONSTANT_FMC` / `FMC_FILENAME` | `.TRUE.` / ' ' (`:152,122`) | FMC por celda y banda | no | Existe |
| `CBD_TIMES_100`, `CBH_TIMES_10`, `CH_TIMES_10`, `CC_IN_PERCENT` | `.TRUE.` (`:112,114,118,116`) | Escalas de los rásters Int16 | no (defaults) | `canopy_builder.py` pre-escala |
| `GRID_DECLINATION`, `ROTATE_ASP`, `ROTATE_WD` | 0, `.FALSE.` (`:125,147-148`) | Rota aspecto/viento por declinación de grilla | no | Convergencia de grilla UTM no aplicada (ASP/WD tomados como norte de grilla) |
| `*_FILENAME` (DEM, SLP, ASP, FBFM, CC, CH, CBH, CBD, WS, WD, M1, M10, M100, ADJ, PHI) | ' ' (`:104-161`) | Nombres de ráster | `NW:376-390` | `adj` = 1.0 uniforme (`preparation/service.py:93`) |
| `FUELS_AND_TOPOGRAPHY_DIRECTORY`, `WEATHER_DIRECTORY` | ' ' | Directorios | `NW:374-375` | |
| `USE_ERC`, `ERC_FILENAME`, `IGNITION_*`, `TIMED_LOCATIONS_CSV` | `.FALSE.`/'null' | Sólo ignición aleatoria/ubicaciones | no | No tocan propagación |

### &TIME_CONTROL

| Keyword | Default (NL) | Qué hace | ¿Usamos? | Comentario |
|---|---|---|---|---|
| `SIMULATION_TSTART` | 0 (`:382`) | Inicio (s, absoluto desde banda 1) | variable (`NW:413`) | |
| `SIMULATION_TSTOP` | 3600 (`:383`) | Fin | `NW:416` | |
| `SIMULATION_DT` | 5 (`:380`) | Paso inicial | 30.0 (`NW:310,414`) | CFL sólo desde el 6.º paso |
| `SIMULATION_DTMAX` | 600 (`:381`) | Tope de paso | 300.0 (`NW:311,415`) | |
| `TARGET_CFL` | 0.4 (`:386`) | CFL objetivo | no | Proveedor: 0.9 en hindcast. No probado |
| `DT_INTERPOLATE_M1/M10/M100` | 300/3000/30000 (`:367-369`) | Reloj de re-interpolación | no | M1 a 10 s sin efecto (`AUDITORIA-FISICA.md:279`) |
| `DT_INTERPOLATE_MLH/MLW/FMC` | 9E8 (`:370-372`) | idem vivo/foliar | no | Fijo en la práctica |
| `DT_INTERPOLATE_WIND` | 300 (`:373`) | Reloj de viento | no | La doc lo llama `_WS/_WD` (`io.rst:257`): no existen |
| `USE_DIURNAL_ADJUSTMENT_FACTOR` | `.FALSE.` (`:387`) | Multiplica VS0 por `OVERNIGHT_ADJUSTMENT_FACTOR` fuera del período de quema | no | No probado (hay recetas `diurno` que lo hacen por viento, no por esto) |
| `OVERNIGHT_ADJUSTMENT_FACTOR` | 0.1 (`:378`) | Factor nocturno | no | |
| `BURN_PERIOD_LENGTH`, `BURN_PERIOD_CENTER_FRAC` | 10, 0.667 (`:364-365`) | Ventana de quema | no | |
| `LATITUDE`, `LONGITUDE`, `CURRENT_YEAR`, `HOUR_OF_YEAR`, `FORECAST_START_HOUR` | −40, −120, 1970, 4368, 20 (`:356,374-377`) | Salida/puesta del sol | no | Defaults no son de Patagonia: habría que fijarlos |
| `RANDOMIZE_SIMULATION_TSTOP` | `.FALSE.` (`:379`) | | no | |

### &SIMULATOR

| Keyword | Default (NL) | Qué hace | ¿Usamos? | Comentario |
|---|---|---|---|---|
| `MODE` | 1 (`:601`) | 1 = level set transitorio | 1 (`NW:420`) | `_validate_parameters` rechaza otro |
| `CROWN_FIRE_MODEL` | 1 (`:593`) | >0 = copa Van Wagner + Cruz | 1 (`NW:421,61`) | Un solo modelo |
| `CROWN_FIRE_ADJ` | 1.0 (`:592`) | Multiplica la velocidad de copa (`spread_rate:178`) | no | No probado |
| `CROWN_FIRE_SPREAD_RATE_LIMIT` | 250 ft/min (`:594`) | Tope de CROS (≈76 m/min) | no | No probado |
| `CRITICAL_CANOPY_COVER` | 0.39 (`:591`) | CC mínimo para copa (fracción) | no | No probado |
| `CROWN_RATIO` | 1.0 (`:595`) | F = CC/3·CROWN_RATIO en el WAF | no | Afecta WAF bajo dosel |
| `MAX_LOW` | 8.0 (`:599`) | Tope de L/W | no | No probado |
| `WSMFEFF_LOW_MULT` | 5.07955E-3 (`:620`) | ft/min → unidad de U en la fórmula de L/W (m/s) | no | Doc dice mph; ver §2.3 y §12 |
| `PHIS_ADJ` / `PHIW_ADJ` | 1.0 (`:605-606`) | Multiplican φs / φw | no | No probados |
| `SURFACE_ACCELERATION_TIME_CONSTANT` | 1.0 (`:609`) | >30 s activa α(t)=1−e^{−t/τ} | no | Con τ>30 s atenúa el arranque |
| `BANDTHICKNESS` | 2 (`:590`) | Ancho de banda | no | Innecesario tocarlo |
| `UNTAG_CELLS_TIMESTEP_INTERVAL`, `UNTAG_TYPE_2/3` | 10, F, F (`:611-613`) | Limpieza de celdas | no | Proveedor: 5, T, T. Rendimiento |
| `WIND_FLUCTUATIONS`, `DT_WIND_FLUCTUATIONS`, `WIND_SPEED_/DIRECTION_FLUCTUATION_INTENSITY` | F, 15, 0, 0 (`:597,614-616`) | Ráfagas globales | no | Dirección = fracción de 360° |
| `WX_BILINEAR_INTERPOLATION` | `.FALSE.` (`:621`) | Clima bilineal | no | Bug de `J2` (ver gotchas); no usar |
| `NUM_IGNITIONS`, `X_IGN`, `Y_IGN`, `T_IGN` | 0 (`:603,610,617-618`) | Ignición puntual | no | Usamos `phi.tif` |
| `ALLOW_NONBURNABLE_PIXEL_IGNITION` | `.TRUE.` (`:589`) | Sólo ignición aleatoria | no | |
| `USE_PYROMES` | `.FALSE.` (`:619`) | Tablas por pirioma | no | Ver §8 |
| `RANDOMIZE_RANDOM_SEED` | `.FALSE.` (`:608`) | Semilla del reloj | no | SEED fijo ⇒ reproducible |
| `MAX_RUNTIME` | 999999 s (`:600`) | Corte por tiempo de pared | no | |

### &MONTE_CARLO

| Keyword | Default (NL) | Qué hace | ¿Usamos? | Comentario |
|---|---|---|---|---|
| `NUM_METEOROLOGY_TIMES` | 1 (`:427`) | Cantidad de bandas de clima | nº de bandas de `ws.tif` (`NW:432,252`) | Sin esto, banda 0 fija |
| `NUM_ENSEMBLE_MEMBERS` | 1 (`:425`) | Miembros | no | Sin perturbaciones, miembros idénticos salvo pavesas |
| `SEED` | 2024 (`:435`) | Semilla | no | |
| `NUM_RASTERS_TO_PERTURB`, `RASTER_TO_PERTURB(:)`, `PDF_TYPE(:)`, `PDF_LOWER_LIMIT(:)`, `PDF_UPPER_LIMIT(:)` | 0, 'null', 'null', 0, 0 (`:426,428-434`) | Perturbación aditiva global por miembro | no | Ver §8; sin PIXEL/DYNAMIC reales |
| `SPATIAL_PERTURBATION(:)`, `TEMPORAL_PERTURBATION(:)` | 'null' (`:436-437`) | Validados, **sin efecto** | no | |
| `WIND_DIRECTION_/WIND_SPEED_FLUCTUATION_INTENSITY_MIN/MAX` | −1 (`:440-443`) | Sortea la intensidad de ráfaga | no | |
| `METEOROLOGY_BAND_START/STOP/SKIP_INTERVAL` | −1 (`:422-424`) | Barrido de ventanas | no | |
| `RANDOM_IGNITIONS`, `EDGEBUFFER`, `USE_IGNITION_MASK`, … | `.FALSE.`, 3000 (`:419,432,439`) | Ignición aleatoria | no | No aplica |

### &SPOTTING (sólo si `write_namelist(spotting=…)`; apagado en `modelo-v0`)

| Keyword | Default (NL) | Qué hace | ¿Usamos? | Comentario |
|---|---|---|---|---|
| `ENABLE_SPOTTING` | `.FALSE.` (`:693`) | Activa pavesas (y sorteo de 8 parámetros) | `.TRUE.` si hay `spotting=` (`NW:70`) | |
| `ENABLE_SURFACE_FIRE_SPOTTING` | `.FALSE.` (`:694`) | Pavesas desde fuego superficial | `.TRUE.` (`NW:71`) | |
| `CRITICAL_SPOTTING_FIRELINE_INTENSITY(:)` | 0 (`:687`) | kW/m mínimo para pavesa superficial | 1000.0 escalar (`NW:72`) | Es un arreglo `(0:303)` (`vars:120`); un escalar podría fijar sólo el elemento 0 (sin verificar) |
| `CROWN_FIRE_SPOTTING_PERCENT[_MIN/_MAX]` | 100 (`:688-690`) | % de celdas con copa que lanzan | 0.65 (`NW:81`) | Pisado por el sorteo |
| `GLOBAL_SURFACE_FIRE_SPOTTING_PERCENT[_MIN/_MAX]` | 0 (`:695-697`) | % superficie, todos los modelos | 0.065 (`NW:80`) | Pisa `SURFACE_FIRE_SPOTTING_PERCENT(:)` |
| `SURFACE_FIRE_SPOTTING_PERCENT(:)`, `…_MULT(:)` | 100, 1 (`:727-728`) | Por modelo de combustible | no | Se descarta (`spotting.f90:38`) |
| `MEAN_SPOTTING_DIST[_MIN/_MAX]` | 0 (`:699-701`) | Coeficiente `a` de la distancia media | 10.0 (`NW:74`) | Con 0 y sin rango ⇒ MSD = 1 m |
| `SPOT_FLIN_EXP[_LO/_HI]` | 0.5 (`:720-722`) | Exponente de FLIN | 0.3 (`NW:77`) | |
| `SPOT_WS_EXP[_LO/_HI]` | 0.9 (`:723-725`) | Exponente del viento | 0.55 (`NW:76`) | |
| `NORMALIZED_SPOTTING_DIST_VARIANCE[_MIN/_MAX]` | 0 (`:710-712`) | `d`: varianza/media | 425.0 (`NW:75`) | |
| `NEMBERS_MIN`, `NEMBERS_MAX[_LO/_HI]` | 30; 1 (`:704-709`) | Pavesas por evento | 1; 1 (`NW:78-79`) | Default da hasta 30 |
| `PIGN[_MIN/_MAX]` | 1.0 % (`:713-715`) | Prob. de ignición al aterrizar | 100.0 (`NW:82`) | |
| `SPOTTING_DISTRIBUTION_TYPE` | 'LOGNORMAL' (`:719`) | Distribución | 'LOGNORMAL' (`NW:73`) | |
| `MIN/MAX_SPOTTING_DISTANCE` | 0 (`:698,702`) | Sólo 'UNIFORM' | no | |
| `SOURCE_FUEL_IGN_MULT(:)` | 1 (`:718`) | Multiplica PIGN por modelo | no | |
| `USE_SUPERSEDED_SPOTTING` | `.TRUE.` (`:736`) | Elige el código de pavesas | no | Default |
| `USE_UMD_SPOTTING_MODEL`, `USE_EULERIAN_SPOTTING`, `USE_EMBER_IGNITION_MODEL`, `EMBER_GR`, `TAU_EMBERGEN`, … | F (`:730-748`) | Modelo alternativo (UMD/Sardoy) | no | No documentado en 2025.0212; no evaluado |
| `STOCHASTIC_SPOTTING` | F (`:726`) | "Not currently used" | no | Doc lo presenta como interruptor |

### &SUPPRESSION (sólo si `suppression=…`; apagado en `modelo-v0`)

| Keyword | Default (NL) | Qué hace | ¿Usamos? | Comentario |
|---|---|---|---|---|
| `ENABLE_EXTENDED_ATTACK` | F (`:783`) | Contención creciente | T (`NW:144`) | |
| `ENABLE_INITIAL_ATTACK`, `INITIAL_ATTACK_TIME` | F, 1800 (`:784,786`) | Ataque inicial estocástico | F (`NW:143`) | |
| `DT_EXTENDED_ATTACK` | 3600 (`:782`) | Intervalo | 1800 (`NW:146`) | |
| `MAX_CONTAINMENT_PER_DAY` | 100 %/día (`:787`) | Tasa de contención | 120 (`NW:147`) | Recetas usan < 100 |
| `AREA_NO_CONTAINMENT_CHANGE` | 10000 acres/día (`:785`) | Crecimiento que anula la contención | 15000 (`NW:148`) | |
| `USE_SDI`, `B_SDI`, `SDI_FACTOR`, `USE_SDI_LOG_FUNCTION` | F, 1, 1, F (`:781,788-790`) | Índice de dificultad | `USE_SDI` F (`NW:145`) | |

### &CALIBRATION (tablas por pirioma; no es calibración automática)

| Keyword | Default (NL) | Qué hace | ¿Usamos? | Comentario |
|---|---|---|---|---|
| `ADJUSTMENT_FACTORS_BY_PYROME`, `ADJUSTMENT_FACTORS_FILENAME` | F, '' (`:814-815`) | ADJ[pirioma×fuel] | no | Requiere `USE_PYROMES` y ráster de piriomas |
| `CALIBRATION_CONSTANTS_BY_PYROME` (+ FILENAME) | F (`:816-817`) | Constantes de supresión/ignición | no | |
| `DURATION_PDF_BY_PYROME`, `DURATION_MAX_DAYS` | F, 28 (`:818-820`) | Duración de incendio | no | |

### &OUTPUTS (no afectan la propagación; diagnósticos útiles)

| Keyword | Default (NL) | Qué hace | ¿Usamos? | Comentario |
|---|---|---|---|---|
| `DTDUMP` | 3600 (`:245`) | Intervalo de volcado | resuelto (`NW:404`) | < TSTOP |
| `DUMP_TIME_OF_ARRIVAL`, `DUMP_FLIN`, `DUMP_SPREAD_RATE` | F (`:257,264,268`) | TOA, intensidad, velocidad | T (`NW:407-409`) | |
| `DUMP_CROWN_FIRE` | F (`:250`) | Ráster de fuego de copa (0/1/2) | no | **Diagnóstico directo de dónde actúa la copa** |
| `DUMP_FLAME_LENGTH`, `DUMP_REACTION_INTENSITY`, `DUMP_WS20`, `DUMP_WD20` | F (`:256,262,275,274`) | Más diagnósticos | no | WS20/WD20 muestran el clima que ELMFIRE efectivamente usó |
| `DUMP_EMBER_FLUX`, `DUMP_SPOTTING_OUTPUTS` | F | Pavesas | no | |
| `CONVERT_TO_GEOTIFF` | T (`:244`) | | T (`NW:406`) | |

## 11. Discrepancias entre la documentación y el código 2025.0212

| La doc dice | El código hace | Cita |
|---|---|---|
| L/W con viento medio en mph | multiplica por 5.07955E-3 (ft/min→m/s) | `tech_ref.rst:176,198` vs `elmfire_level_set.f90:1742`, `elmfire_namelists.f90:620` |
| Retroceso = V_s0 por defecto, opción para elipse | siempre `BOH·V_DMS` (elipse) | `tech_ref.rst:230-236` vs `level_set:1744-1749` |
| `WIND_DIRECTION_FLUCTUATION_INTENSITY` en grados | fracción de 360° | `physics.rst:55-63` vs `elmfire_subs.f90:1018-1022` |
| `SPATIAL/TEMPORAL_PERTURBATION` PIXEL/DYNAMIC | sin efecto (todo global y estático) | `monte_carlo.rst:155-161` vs `elmfire_subs.f90:156-190` |
| Se pueden perturbar `CC`, `CH` | se aceptan y se ignoran | `monte_carlo.rst:114-115` vs `elmfire_vars.f90:76-77` |
| `DUMP_ISOCHRONE_SHAPEFILES`, `CALCULATE_BURN_PROBABILITY` | no existen | `io.rst:374`, `monte_carlo.rst:202` vs `elmfire_namelists.f90:221-234` |
| `DT_INTERPOLATE_WS/WD` | existe `DT_INTERPOLATE_WIND` | `io.rst:257` vs `elmfire_namelists.f90:373` |
| Calibración automática de pavesas (`CALIBRATION = .TRUE.`) | no existe | `spotting.rst:127-131` vs `elmfire_calibration.f90` |
| `SURFACE_FIRE_SPOTTING_PERCENT(:)` por combustible | se pisa en `SET_SPOTTING_PARAMETERS` | `spotting.rst:101-117` vs `elmfire_spotting.f90:38` |

## 12. Opciones no probadas que podrían importar (sólo documentadas; decide el usuario)

Las respuestas a las preguntas del diagnóstico, con evidencia:

1. **¿Más de un modelo de iniciación o propagación de copa?** **No.** Hay un único camino: criterio
   de Van Wagner (1977) con `FMC` y `CBH`, velocidad de Cruz et al. (2005), activo/pasivo por
   `CAC = CROS/(3/CBD)` y piso `CC ≥ 0.39` (§3). `CROWN_FIRE_MODEL` es un interruptor binario
   (`level_set.f90:399,660,986,1707,1739,1791,1841`; Tutorial 04 PDF p. 3). Tampoco hay otro modelo de
   superficie: el canadiense (FBP/CFFDRS) es de 1.1 (ELMFIRE_Guide.pdf p. 10-11) y su keyword no
   está en el fuente 2025.0212. Las perillas reales de la copa son `FOLIAR_MOISTURE_CONTENT`,
   `CRITICAL_CANOPY_COVER`, `CROWN_FIRE_ADJ`, `CROWN_FIRE_SPREAD_RATE_LIMIT`, `FMC_FILENAME` y los
   rásters `cbh`/`cbd`/`cc`/`ch`.
2. **¿Ráster de FMC por celda?** **Sí** (también de MLH y MLW): `USE_CONSTANT_FMC = .FALSE.` +
   `FMC_FILENAME` (multibanda, mismas bandas que el clima) y `USE_CONSTANT_LH/LW = .FALSE.` +
   `MLH/MLW_FILENAME` (`elmfire_namelists.f90:92,122,143-144,152-154`; `elmfire_io.f90:202-241`;
   `io.rst:104-117`). Este repo escribe escalares y su comentario `NW:51-53` ("no hay ráster de
   humedad viva") es incorrecto para 2025.0212. Un mapa de LFMC por celda (p. ej. por especie, como
   Bianchi & Defossé 2015) sería posible sin cambiar de versión. Atención a los pisos de MLH ≥ 30 % y
   MLW ≥ 60 % (§6).
3. **¿Asimilación o calibración automática de ADJ contra perímetros u observaciones?** **No.**
   `elmfire_calibration.f90` sólo carga tablas por pirioma (§8); no hay optimizador. La única
   forma "dentro de ELMFIRE" de hacer ADJ por clase es `ADJUSTMENT_FACTORS_BY_PYROME`, pero exige
   `USE_PYROMES` y un ráster de 128 piriomas; sin eso, equivale a escribir un `adj.tif` por
   modelo de combustible, que este repo ya puede hacer.
4. **¿Perturbación estocástica de parámetros para Monte Carlo?** **Sí, limitada:** deltas
   aditivos uniformes **globales y estáticos por miembro** sobre `ADJ, CBD, CBH, FMC, M1, M10, M100,
   MLH, MLW, WAF, WD, WS`; fluctuaciones de viento por paso; y rangos de pavesas (§8). La
   perturbación espacial o temporal por píxel documentada no está implementada. Hay que fijar
   `NUM_ENSEMBLE_MEMBERS`. Cada miembro con la misma semilla/entrada y sin perturbar es idéntico.

Otras opciones sin probar en este repo, ordenadas por su relación con lo que el diagnóstico
busca (efecto esperado sin medir; todo es hipótesis hasta correr el banco):

| Opción | Por qué podría importar | Riesgo / nota |
|---|---|---|
| `FOLIAR_MOISTURE_CONTENT` (hoy 90 % implícito) y/o `FMC_FILENAME` | Mueve `I_crítica = (0.01·CBH·(460+26·FMC))^1.5`: de 90 a 110 % sube ~29 % la intensidad mínima de copa ((3320/2800)^1.5) | Cuenta propia sobre la fórmula; la receta `lw100-cbh*` ya movió CBH |
| `CRITICAL_CANOPY_COVER`, `CROWN_FIRE_ADJ`, `CROWN_FIRE_SPREAD_RATE_LIMIT` | Controlan si la copa existe en coberturas discontinuas y cuánto acelera | `copas-off-001` ya mostró el efecto global de apagarla |
| `WSMFEFF_LOW_MULT`, `MAX_LOW` | Forma de la elipse: con la unidad actual (m/s) L/W ≈ 2.8 a 10 mph de viento medio; con mph se saturaría en 8. Cambia ancho de frente y flancos | Hay que decidir contra observaciones; el repo ya reproduce la versión m/s |
| `PHIW_ADJ`, `PHIS_ADJ` | Calibrar viento y pendiente por separado de ADJ (que escala todo junto) | Tres perillas correlacionadas con ADJ y con el WAF |
| `MLH/MLW_FILENAME` por celda; piso real 60 % de MLW | LFMC espacial en vez de un escalar por dominio | Pisos 30/60 % |
| `USE_DIURNAL_ADJUSTMENT_FACTOR` (+ `OVERNIGHT_ADJUSTMENT_FACTOR`, lat/lon, hora) | Reduce VS0 de noche; hoy la noche se resuelve sólo vía humedad/viento | Necesita LATITUDE/LONGITUDE/HOUR_OF_YEAR/FORECAST_START_HOUR correctos |
| `TARGET_CFL` (0.4 → 0.9) | Sólo velocidad de cómputo; verificar que no mueva el TOA | El proveedor usa 0.9 |
| `DT_INTERPOLATE_M100` (30000 s) | M100 se re-interpola cada 8.3 h en celdas ya etiquetadas | Probablemente irrelevante (la banda ya cubre las celdas nuevas) |
| Perturbaciones Monte Carlo (`ADJ`, `WS`, `WD`, `M1`…) con `NUM_ENSEMBLE_MEMBERS` | Banda de incertidumbre sin lanzar N invocaciones (un ELMFIRE por vez en la VM de 7.75 GB) | Sólo deltas globales; los rangos son un juicio |
| `METEOROLOGY_BAND_START/STOP/SKIP_INTERVAL` | Varias ventanas climáticas (p. ej. miembros GEFS apilados) en una corrida | Ráster de clima apilado; semántica de bandas en §8 |
| `SURFACE_ACCELERATION_TIME_CONSTANT` > 30 s | Aceleración desde ignición puntual | Nuestras semillas son perímetros, no puntos |

Y una hipótesis a **verificar** antes de nada (no confirmada, no está en `interface-gotchas.md`):
`CRITICAL_SPOTTING_FIRELINE_INTENSITY` es un arreglo `REAL (0:303)` (`elmfire_vars.f90:120`) y la
plantilla del proveedor, igual que `NW:72`, le asigna un escalar. En un namelist Fortran
estándar un escalar sin subíndice llena sólo el primer elemento (el 0), de modo que el umbral
quedaría en 0 para los modelos de combustible reales. Se confirma con un programa Fortran de 10
líneas con `gfortran` (no hay compilador local), no corriendo ELMFIRE.
