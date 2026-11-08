# F · Descomposición del error de modelo-v0 (sin correr ELMFIRE)

Script: `scripts/diagnostico_error.py` (`uv run python scripts/diagnostico_error.py`, ~1 min).
Test: `tests/test_diagnostico_error.py`. Tablas: `benchmarks/diagnosticos/e2e/datos/F*.csv`.

## 0. Alcance y método común

- **Sólo calibración** (`benchmarks/particion.json`; el script rechaza cualquier caso fuera de la lista).
  Receta `lw-100-001` sobre `los-alerces-2023/calibracion-v6-h54`, `epuyen-2025`, `los-alerces-2024`,
  `puerto-patriada-2026`, `los-alerces-2016/calibracion-era5-v6`, `cholila-2015/calibracion-era5-v6` y
  `las-golondrinas-2021`. Este último es un **límite** declarado en la partición (24 h, 82 celdas
  alcanzadas de 21.637 detectadas, sesgo de área 0,02): está en las tablas por incendio con
  `limite=True` y **fuera** de todo agregado.
- P-24 (`lw-100-obs-001` sobre `pronostico-v6`) existe para 6 de esos 7 casos (no Golondrinas).
- Se reusan `p.coser`, `p.horas_relativas`, `p.area_igualada`, `p.metricas` y las lecturas del
  almacén de `cadena`. **Control**: el Dice al horizonte (0,5006) y el t\* (77,999 h; Dice 0,4493) de
  Epuyén coinciden dígito a dígito con `metricas.json`.
- La predicción al horizonte es la línea de tiempo cosida de la cadena (semilla `prediccion`); la
  referencia es la cicatriz final truncada al horizonte; semilla del caso y zona de exclusión
  quedan fuera. Celda de 30 m (0,09 ha).
- Zona horaria: ART = UTC−3.

## 1. Velocidad vs dirección (`F1_velocidad_direccion.csv`)

Método: t\* = hora en que el área predicha (cosida) iguala el área de la cicatriz observada
(`area_igualada`, IGN-26). Se compara con el horizonte H. Ángulo: rumbo del centroide de la semilla
al centroide del crecimiento (predicho y observado, norte arriba), diferencia en (−180, 180].

| Incendio | H (h) | t\* (h) | t\*/H | sesgo de área | Dice @H | Dice @t\* | Δ ángulo (pred−obs) | desplaz. centroide pred/obs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Alerces 2023 | 54 | 39,8 | 0,74 | 1,86 | 0,528 | 0,455 | −45° | 1,15 / 1,85 km |
| Epuyén 2025 | 96 | 78,0 | 0,81 | 1,41 | 0,501 | 0,449 | +9° | 1,87 / 3,92 km |
| Alerces 2024 | 120 | 96,6 | 0,81 | 1,35 | 0,635 | 0,617 | −22° | 1,66 / 3,20 km |
| Alerces 2016 | 72 | 53,3 | 0,74 | 1,69 | 0,389 | 0,400 | −112° | 1,01 / 2,19 km |
| Patriada 2026 | 96 | 96,0 (no alcanzada) | 1,00 | 0,70 | 0,496 | 0,496 | −65° | 1,61 / 4,72 km |
| Cholila 2015 | 120 | 120,0 (no alcanzada) | 1,00 | 0,87 | 0,513 | 0,513 | +11° | 2,62 / 8,88 km |

Lectura:

- **Velocidad (área):** en 4 de 6 el modelo alcanza el área observada 19–26 % antes del horizonte
  (t\*/H = 0,74–0,81; sobre-propagación de 1,35–1,86×). En Patriada y Cholila queda corto: nunca
  llega al área observada dentro del horizonte (sesgo 0,70 y 0,87).
- **Forma/dirección:** igualar el área **no sube** el Dice (cambio Dice@t\* − Dice@H: −0,07, −0,05,
  −0,02, +0,01 en los cuatro con t\* alcanzado). Con el área corregida, Dice = precisión = recall =
  0,40–0,62: ése es el techo de un arreglo puro de velocidad. El resto es dónde quema.
- **Dirección:** |Δ ángulo| mediano 34° (rango 9–112°). Sólo Epuyén y Cholila quedan dentro de ~11°.
  En los 6 incendios el desplazamiento del centroide predicho es 0,29–0,62 del observado: el crecimiento
  predicho es más compacto/isótropo que el observado, que se estira en una dirección.
- Caveat: el ángulo es de centroides de un crecimiento que es una cuña ancha, no un vector de
  velocidad; con n = 6 no hay inferencia.
- **Diagnóstico:** error mixto. El sesgo de velocidad existe pero es secundario frente a la forma.
  Las series de t\* son además un promedio sobre el horizonte; F2 muestra que el signo del error de
  velocidad cambia con el tiempo.

## 2. Error de tiempo de llegada (`F2_toa_resumen.csv`, `F2_toa_por_tiempo.csv`)

Método: error = TOA cosido − hora de la primera detección VIIRS que cubre la celda (disco de medio
píxel, 187,5 m; `ref_firms_horas` de cada ventana + su desfase). Sólo celdas con detección,
fuera de semilla y exclusión, y **sólo las que el modelo alcanzó** (condicional; la fracción nunca
alcanzada se informa aparte). La detección es cota superior de la llegada real.

| Incendio | mediana (h) | IQR (h) | nunca alcanzadas | pendiente error vs t_det (h/h) | Spearman TOA–detección |
|---|---:|---:|---:|---:|---:|
| Alerces 2023 | −4,9 | 34,4 | 36 % | −0,95 | 0,05 |
| Epuyén 2025 | +51,2 | 29,9 | 38 % | −0,84 | 0,25 |
| Alerces 2024 | +20,8 | 41,8 | 32 % | −0,61 | 0,44 |
| Patriada 2026 | +37,5 | 44,3 | 62 % | −0,52 | 0,33 |
| Alerces 2016 | +36,5 | 18,6 | 50 % | +0,29 | 0,43 |
| Cholila 2015 | +16,4 | 44,2 | 58 % | −0,45 | 0,47 |

Evolución con el tiempo desde la ignición (bins de la detección observada; tabla completa en
`F2_toa_por_tiempo.csv`): lo detectado en las **primeras 24 h se predice tarde** (medianas +12 a +65 h
en Epuyén, Alerces 2024, Alerces 2016 y Patriada, +33 y +18 h en Alerces 2023; Cholila ≈ 0 a −2 h en 0–24 h),
y lo detectado después de ~48 h se predice cada vez **más temprano** (Alerces 2023: −12,5 y −14,2 h en 24–48 y
48–72 h; Epuyén +3,3 h a 48–72 h). Las pendientes ≈ −0,5 a −1 h/h y el Spearman de 0,05–0,47 dicen que el
orden de llegada predicho está débilmente relacionado con el observado: la cadena no ordena bien las
celdas en el tiempo, además de errar su nivel medio. Es el déficit del día 1 (DIA-1 §7.3) seguido de
sobre-propagación posterior.

## 3. FN/FP por estrato (`F3_estratos.csv`, incendio `TODOS` = suma de los 6 sin Golondrinas)

Método: por celda, TP/FP/FN al horizonte (misma confusión que 1). `tasa_fn` = FN/(TP+FN),
`tasa_fp` = FP/(TP+FP) = 1 − precisión; `razon_*` = tasa del estrato / tasa global; `frac_area` =
fracción del dominio válido (no excluido ni semilla). Estratos: `fbfm40` de la receta (ccsbap2017),
pendiente (slp, grados), orientación (asp, 8 sectores + plano/sin dato), dosel (cc %). Hay filas por
incendio, que pueden diferir del agregado.

Agregado (6 incendios):

| Estrato | % del dominio | % de los FN | tasa FN (razón) | tasa FP (razón) |
|---|---:|---:|---:|---:|
| TU (todo) | 18,5 | **49,3** | 0,54 (1,15) | 0,48 (0,97) |
| TU5 | 11,0 | 30,2 | 0,56 (1,20) | 0,48 (0,98) |
| TU3 | 7,5 | 19,1 | 0,51 (1,08) | 0,47 (0,95) |
| SH4 | 18,5 | 21,5 | 0,39 (0,83) | 0,46 (0,93) |
| GR (GR1/2/5) | 15,2 | 1,9 | 0,44 (0,93) | **0,79 (1,60)** |
| NB (no combustible) | 18,1 | 1,9 | 1,00 (2,13) | — |
| SH3 | 3,0 | 3,0 | **0,79 (1,68)** | 0,47 (0,94) |
| TL8 | 1,7 | 1,2 | 0,29 (0,63) | 0,24 (0,48) |
| Pendiente 0–5° | 24,5 | 10,0 | 0,56 (1,18) | **0,69 (1,38)** |
| Pendiente 5–35° | 63 | 76 | 0,43–0,49 | 0,44–0,48 |
| Orientación SE / S | 10,7 / 9,8 | 13,9 / 19,8 | **0,68 (1,44) / 0,61 (1,29)** | 0,53 / 0,53 |
| Orientación N / NO / O | 9,2 / 9,4 / 11,3 | 6,7 / 5,5 / 11,2 | 0,35 / 0,34 / 0,37 | ~0,49 |
| Dosel 0 % | 50,1 | 16,8 | 0,44 (0,93) | 0,55 (1,11) |
| Dosel 80–100 % | 26,4 | 52,6 | 0,45 (0,95) | 0,44 (0,88) |

Lectura:

- **Los FN se concentran en el bosque tipo TU** (ñire y coihue/ciprés con caña): 49 % de los FN con
  18,5 % del dominio. La *tasa* de FN sólo es 1,15× la global; es que ahí está lo observado.
- Los **FP** se concentran en terreno **plano** (0–5°: 0,69; plano/sin dato 0,75) y en **pastizal**
  (GR: 0,79; GR1/GR5 0,98 y 0,90): el modelo quema donde la cicatriz no está.
- **Orientación:** FN más altos en laderas SE/S (0,68/0,61) que en N/NO/O (0,34–0,37). Compatible con un
  sesgo de viento/radiación dominante, pero no identificado aquí.
- **Dosel:** sin una señal fuerte (razón 0,93–1,17); no discrimina.
- NB: 179 ha de cicatriz caen en celdas no combustibles del mapa (1,9 % de los FN): ése es el límite del
  crosswalk, no del modelo.
- **Hora del día de llegada.** (a) Hora **predicha** (sobre TP+FP): la tasa de FP es plana entre
  franjas de 3 h (0,47–0,53). (b) Hora de la **primera detección observada** (celdas de la cicatriz a ≤ 375 m
  de una detección; 53 % de las celdas con hora se detectan entre 00 y 03 ART y 33 % entre 15 y 18 ART): tasa de FN
  0,51 / 0,71 / 0,16 / 0,35 en 00–03 / 03–06 / 12–15 / 15–18 ART. Pero la hora observada la fija el calendario de
  pasadas VIIRS (no hay franjas 06–12 ni 18–24), así que sólo distingue "lo visto de noche" (peor) de "lo visto
  de tarde" (mejor). Dice que hay más FN en lo que el satélite ve de noche, pero no permite
  concluir que el modelo falle según el ciclo diurno.
- Los estratos no son independientes (TU, pendiente y orientación se solapan) y el agregado pesa más a los
  incendios grandes; las filas por incendio están en el CSV. No se ajustó por multiplicidad.

## 4. Métricas complementarias (`F4_fss.csv`, `F4_distancia_perimetro.csv`)

**FSS** (Roberts y Lean 2008) sobre el crecimiento (fuera de semilla/exclusión), dominio = caja de la unión
predicho/observado + 2,1 km. Ventanas 1, 3, 7, 15, 33, 67 celdas = 30 m, 90, 210, 450, 990 m, 2,0 km. Umbral
"útil" = 0,5 + f/2 (f = fracción observada en el dominio; 0,55–0,59 aquí; depende del dominio).

| Incendio | FSS 30 m | 210 m | 990 m | 2 km | escala mínima útil |
|---|---:|---:|---:|---:|---|
| Alerces 2023 | 0,53 | 0,56 | 0,61 | 0,65 | 210 m |
| Epuyén | 0,50 | 0,54 | 0,61 | 0,67 | 450 m |
| Alerces 2024 | 0,64 | 0,68 | 0,75 | 0,79 | ≤ 30 m |
| Patriada | 0,50 | 0,54 | 0,61 | 0,66 | 990 m |
| Cholila | 0,51 | 0,55 | 0,61 | 0,66 | 990 m |
| Alerces 2016 | 0,39 | 0,41 | 0,45 | 0,48 | nunca (< 2 km) |

El FSS sube poco con la escala (≈ +0,15 de 30 m a 2 km), de modo que perdonar errores de posición de
1–2 km no resuelve el error: es sistemático. A área igualada (t\*) el FSS **no mejora de forma consistente** (Epuyén 0,45 → 0,61
a 2 km contra 0,50 → 0,67 al horizonte; Alerces 2023 0,46 → 0,69 contra 0,53 → 0,65).

**Distancia de perímetro** (borde de predicho ∪ semilla contra cicatriz ∪ semilla, sin bordes pegados a
exclusión; vecindad de 4; distancia euclídea entre celdas de borde, `shapely.STRtree`):

| Incendio | HD95 (km) @H | ASSD (km) @H | mediana (km) | HD95 @t\* |
|---|---:|---:|---:|---:|
| Alerces 2023 | 2,4 | 0,51 | 0,24 | 1,8 |
| Epuyén | 2,3 | 0,67 | 0,47 | 3,2 |
| Alerces 2024 | 3,1 | 0,89 | 0,63 | 4,5 |
| Alerces 2016 | 3,6 | 1,20 | 0,89 | 4,0 |
| Patriada | 6,9 | 1,50 | 0,63 | = |
| Cholila | 8,6 | 1,81 | 0,45 | = |

La distancia media de borde es 0,5–1,8 km (17–60 celdas), mucho mayor que los 375 m del píxel VIIRS, y el
HD95 es de 2–9 km.

## 5. Hipótesis 1: calibración secuencial con ADJ_k (`F5_*.csv`)

Datos: P-24 (`lw-100-obs-001`, semilla FIRMS), 6 incendios, 34 reinicios k ≥ 1. Sesgo_k = crecimiento
predicho / observado a 24 h contra la cicatriz ya vista por VIIRS (`sesgo_area` de `pronostico.json`, el mismo
que DIA-1 §7.3 y §7.6). Se omiten pares con sesgo 0.

**Autocorrelación de log(sesgo_k) con log(sesgo_{k−1})** dentro de cada incendio (n = pares):

| Plazo | Variante | n | Pearson | Spearman | pendiente | Pearson centrado por incendio | mismo signo |
|---|---|---:|---:|---:|---:|---:|---:|
| 24 h | k ≥ 2 (sin la ventana 0) | 28 | 0,58 | 0,53 | 0,53 | 0,35 | 86 % |
| 24 h | k ≥ 1 | 34 | 0,65 | 0,65 | 0,51 | 0,61 | 79 % |
| 12 h | k ≥ 2 | 28 | 0,28 | 0,31 | 0,26 | 0,05 | 68 % |
| 12 h | k ≥ 1 | 34 | 0,53 | 0,50 | 0,41 | 0,49 | 68 % |

Hay un nivel persistente del sesgo por incendio (a 24 h, 25 de 28 reinicios k ≥ 2 sobre-propagan), pero la
persistencia *dentro* del incendio, una vez quitado su nivel medio, es moderada (0,35) y a 12 h casi nula (0,05).
Por incendio (n = 2–7 pares) la correlación es inestable; ver `F5_autocorrelacion_adj.csv`. El "86 % mismo signo"
es en buena parte trivial: casi todo es sesgo > 1.

**ADJ_k offline.** `ADJ_k = clamp(r_obs/r_sim, 1/4, 4)` con r = √(A_fin/π) − √(A_ini/π) de la
ventana k−1: A_ini = semilla de k−1, A_fin,obs = semilla de k (FIRMS acumulado), A_fin,sim = semilla de k−1 + celdas
con TOA ≤ T_k − T_{k−1} del TOA de P-24 de la ventana k−1. Efecto en k: radio equivalente del crecimiento
escalado por ADJ → G' = (√A_ini + ADJ(√(A_ini+G) − √A_ini))² − A_ini, sesgo' = G'/obs. Aproximación declarada:
ROS lineal en ADJ, pero el ciclo diurno del clima no escala (DIA-1 §3.5).

Reinicios k ≥ 2, 24 h (n = 28), medido como cambio de |ln sesgo|:

| Subconjunto | n | mejoran | mediana |ln sesgo| antes → después |
|---|---:|---:|---|
| todos | 28 | 17 (11 empeoran) | 1,39 → 1,41 (×4,0 → ×4,1); mediana del cambio +0,20 ln |
| ADJ_k < 1 | 21 | 17 | 1,37 → 0,90 (×3,9 → ×2,5) |
| ADJ_k > 1 | 7 | **0** | 1,42 → 2,42 |
| ADJ saturado (15: 11 en 1/4, 4 en 4) | 15 | 9 | 1,67 → 1,60 |
| sesgo observado > 2 | 20 | 15 | 1,81 → 1,55 (mediana −0,98 ln) |
| sesgo observado ≤ 2 | 8 | 2 | peor (−0,7 a −1,1 ln) |

Por incendio (mejoran / n, mediana del cambio en ln): Epuyén 5/5 (+1,48), Alerces 2016 2/3 (+1,53), Cholila
3/6 (+0,33), Alerces 2024 4/7 (+0,09), Alerces 2023 1/2 (−0,28), Patriada 2/5 (−0,65).
Con la regla "sólo reducir" (aplicar ADJ_k sólo si < 1): 17 mejoran y 4 empeoran, mediana |ln| 1,39 → 1,03
(×4,0 → ×2,8). Esa regla se miró **después** de ver los resultados (n = 21): es exploratoria, no una receta.

**Veredicto.** Un ADJ_k asimilado, tal cual está definido, **no baja el error mediano** (1,39 → 1,41 ln) y empeora
en 11 de 28 reinicios; todos los reinicios con ADJ > 1 empeoran, porque a k ≥ 2 el modelo ya sobre-propaga en
25 de 28. Ayuda cuando el sesgo es grande y sostenido (Epuyén, Alerces 2016, Cholila tardío), que es
justo el régimen de supresión (DIA-1 §7.5), donde absorbería como física un efecto de combate. Y ni ahí lo
corrige: el tope satura en 15 reinicios (11 en 1/4) y en ellos la mediana de |ln sesgo| sólo baja de 1,67 a 1,60 (≈ ×5). Con esto **no se justifica
correr 28 ELMFIRE** de ADJ simétrico. Si se quisiera apostar, sólo la variante "solo reducir" tiene señal
(17/4), y haría falta fijar la regla antes de correrla.

## 6. Hipótesis 6: ROS empírica entre pasadas VIIRS por combustible (`F6_*.csv`)

Método: pasadas = grupos de detecciones separadas > 2 h (`pronostico.SEPARACION_PASADAS_H`); detecciones
dentro de 1 km de la cicatriz y fuera de exclusión, hasta el horizonte. Para el reinicio k (ventana P-24 que
arranca en el fin de la pasada k−1), cada detección de la pasada k es "nueva" si su centro dista ≥ 375 m (un
píxel entero) del centro de toda detección previa o de la ignición y ≤ 5 km. ROS_obs = d / (t_det − T_k) en m/min,
con d la distancia al centro previo más cercano. Misma d para el modelo: ROS_mod = d / TOA_rel de la ventana
k en esa celda (con el frente observado como semilla). Se descartan las celdas dentro de la semilla P-24 (12–40 % de
las nuevas). Combustible de la celda de la detección (`fbfm40` del crosswalk). Hay 2.015 detecciones nuevas con umbral de 187,5 m (antes de
descartar la semilla) y ≈ 1.400 celdas en el resumen con 375 m; Patriada aporta 46 % de las primeras. Sensibilidad al umbral en el CSV (`umbral_d_m`).

**Es una cota gruesa, y hay que leerla así**: (i) el píxel VIIRS es 375 m y el centro de la celda no es el frente
(±375 m en d, es decir ±0,6 m/min con Δt ≈ 11 h); (ii) la detección es cota superior de la llegada, de modo que ROS_obs
es **cota inferior** del tiempo-promedio; (iii) Δt ≈ 11 h (8–24) mezcla noche y día, y el ROS del ciclo diurno
se promedia; (iv) la distancia al centro previo más cercano subestima el avance del frente en la cabeza y
sobreestima en los flancos; (v) el combustible de la celda no es el de todo el trayecto; (vi) se compara con ELMFIRE
sólo en celdas alcanzadas en 24 h, que es un subconjunto sesgado a las rápidas, por eso se agrega la mediana censurada
(no alcanzadas = 0).

Resultados con umbral 375 m (celdas con n ≥ 30; todos los incendios mezclados):

| Combustible | n celdas (incendios) | ROS_obs mediana [IQR] m/min | modelo no llega en 24 h | ROS_mod mediana (alcanzadas) | razón mod/obs |
|---|---:|---|---:|---:|---:|
| SH (matorral) | 559 (6) | 2,13 [1,15–3,58] | 44 % | 1,64 | 0,77 |
| ↳ SH4 | 368 (6) | 1,94 | 39 % | 1,69 | 0,88 |
| ↳ SH8 | 138 (6) | 1,96 | 39 % | 1,49 | 0,76 |
| TU (bosque con sotobosque) | 522 (6) | 2,33 [1,30–4,44] | 61 % | 1,23 | 0,53 |
| ↳ TU5 | 389 (6) | 2,48 | 63 % | 1,21 | 0,49 |
| ↳ TU3 | 133 (6) | 1,98 | 54 % | 1,25 | 0,63 |
| TL (hojarasca) | 192 (6) | 1,78 [1,06–3,91] | 61 % | 1,06 | 0,60 |
| GR (pastizal) | 48 (6) | 2,86 [2,02–3,89] | 52 % | 1,67 | 0,58 |
| NB (no combustible en el mapa) | 69 (5) | 3,52 [1,67–5,77] | 100 % | — | — |
| SH3 | 48 (1) | 5,03 | 100 % | — | — |

Lectura:

- La ROS observada es ~1,8–2,9 m/min en todo combustible combustible (≈ 110–170 m/h), con dispersión
  grande (IQR ≈ ×3) y sin una ordenación clara por tipo: el rango entre combustibles (1,8–2,9) es menor que la
  incertidumbre de la medida y que la variación entre incendios. **Con esta cota no se puede decir que el crosswalk
  ordene bien las velocidades.**
- En matorral (SH4/SH8) el modelo está cerca (0,76–0,88 de la ROS observada en las celdas que alcanza). En
  bosque (TU5, TU3), hojarasca (TL6) y pastizal (GR) alcanza la mitad o menos de la velocidad observada (0,49–0,63) y
  **no llega en 24 h al 52–63 %** de las celdas nuevas; con censura la mediana de ROS_mod es 0 en TU, TL y GR. Es
  consistente con F3: el 49 % de los FN en TU.
- 69 detecciones nuevas (5 incendios) caen en celdas NB: el fuego pasó donde el mapa de combustible dice que no
  hay combustible (3,5 m/min). Las 48 de SH3 (un incendio) son las de ROS mayor (5,0): una celda "remanente de
  disturbio" por donde el fuego corrió más que en cualquier otro tipo y el modelo no llega.
- Los incendios aportan desigual (Patriada 46 %); los números por incendio están en `F6_celdas_nuevas.csv.gz`
  (agrupar por `incendio`, `codigo`).

## 7. Lo que no se pudo hacer, o se hizo en parte

- **Hora del día de llegada para FN:** no existe hora de llegada predicha en una celda que el modelo no quemó, y
  la observada se limita al calendario de VIIRS (arriba). Haría falta una hora de llegada observada fuera de las
  pasadas VIIRS, que no está en los artefactos.
- **FSS con exclusión:** las celdas excluidas y la semilla no cuentan, pero reducen el denominador de ventanas
  vecinas; no se hizo una versión con relleno. El umbral útil depende del dominio elegido.
- **ADJ offline:** no se reprodujo el clima diurno por escala de tiempo; sólo escalado de radio. No cubre el primer
  reinicio de cada incendio con información previa (usa la ventana 0, que parte de un punto de ignición:
  la variante "k ≥ 1" lo incluye y no cambia la conclusión).
- **ROS_mod en celdas alcanzadas** está sesgada hacia las rápidas; para el tipo NB y SH3 no hay valor.
