# S · Diagnóstico complementario (S1, S2, S3, S5 de la revisión R)

Código: funciones agregadas al final de `scripts/diagnostico_error.py` (F1–F6 intactos) y tests en
`tests/test_diagnostico_error.py`. Sin ELMFIRE, sólo calibración, artefactos guardados.
`uv run python -c "import scripts.diagnostico_error as de; de.main_s()"` (S1–S3, ~1 min) y
`de.main_s5()` (S5, ~30 min por la lectura de 7.130 GRIB). Datos: `datos/S*.csv`.

## S2. F7 versionada (`datos/S2_f7_elongacion_variantes.csv`, `S2_f7_resumen.csv`)

`elongacion(m)` = √(λ1/λ2) de la covarianza de las coordenadas de las celdas; eje = grados desde el norte, módulo 180.
El eje sólo se informa si la elongación pasa de 1,3 (`eje_crudo` queda aparte). Intervalo 95 % por bootstrap de
celdas (200 réplicas, eje circular módulo 180). **Aviso:** el bootstrap de celdas ignora la autocorrelación
espacial, así que los intervalos (±0,02 de elongación, ±1° de eje) sólo miden el ruido de muestreo de píxeles y
no la incertidumbre real; no sirven para decir «significativo». La variante A reproduce `F7_elongacion.csv` (1,61/101,6° …).

Variantes (observado / predicho): A actual (observado truncado a vistas / predicho al horizonte con recorte por
exclusión), B igual con la predicción en t\*, C cicatriz final / predicho sin recorte, D como C en t\*, E sólo sin recorte,
F y G = A y C con la componente conexa mayor.

| Variante | Mediana obs | Mediana pred | Pred más redondo | n con eje en ambos | Mediana \|Δeje\| | \|Δeje\| > 45° |
|---|---:|---:|---:|---:|---:|---:|
| A actual (F7) | 2,30 | 1,40 | 5/6 | 4 | 48° | 2 |
| B actual, pred en t\* | 2,30 | 1,63 | 5/6 | 4 | 47° | 2 |
| C cicatriz final, pred sin recorte | 1,95 | 1,36 | 4/6 | 3 | 36° | 1 |
| D como C, pred en t\* | 1,95 | 1,47 | 4/6 | 3 | 36° | 1 |
| E sólo sin recorte | 2,30 | 1,36 | 5/6 | 4 | 45° | 2 |
| F comp. mayor, actual | 2,72 | 1,40 | 5/6 | 4 | 51° | 2 |
| G comp. mayor, final sin recorte | 2,53 | 1,36 | 4/6 | 3 | 36° | 1 |

Lectura: «lo predicho es más redondo» sobrevive en todas las variantes (4/6 con la cicatriz final, 5/6 con la
truncada); la mediana observada baja de 2,3 a 1,95 con la cicatriz final, como anticipó R (1,96). El eje es
indefinido (elongación predicha ≤ 1,3) en Alerces 2023 y Alerces 2024 en todas las variantes; donde está definido
en ambos, el desvío es ≈ 80° en Epuyén y Alerces 2016 y ≈ 15° en Patriada y Cholila (A). Con la cicatriz final, Epuyén
(1,27) y Patriada (1,32) pasan a casi redondos, y sólo quedan 3 incendios con eje comparable, así que «eje girado
≈ 80° en 3/6» **no se sostiene**: son 2 de 4 comparables con A y 1 de 3 con C. Quitar el recorte por exclusión
baja Cholila de 1,96 a 1,58 (confirma R/O2) pero no cambia el resumen.

## S1. F1 por reinicio de P-24 (`datos/S1_p24_por_reinicio.csv`, `S1_p24_resumen.csv`)

`s1_reinicio`: 34 reinicios k ≥ 1 en 6 incendios (`lw-100-obs-001` sobre `pronostico-v6`, semilla FIRMS), a 12 y
24 h, con la referencia de crecimiento estricta (se excluyen las celdas con `vistas_h ≤ 0` fuera de la semilla; verificado
igual a `pronostico.puntuar` con `exc | ((vistas ≤ 0) & ~semilla)`, como `paso7`). t\* se busca en [0, plazo]; si el modelo no
llega al área observada se marca `t_star_alcanzada = False` y se informa la precisión a la hora final. Ángulo:
semilla → centroide del crecimiento (predicho al plazo y observado). Elongación: del crecimiento solo y de
semilla + crecimiento.

**Cuidado con la referencia chica:** con el anillo excluido, la referencia a 12 h queda vacía en 8 de 34 reinicios (sin
sesgo ni Dice) y bajo 20 ha en 12; el sesgo mediano es 2,4× (12 h) y 3,1× (24 h) en buena parte porque el denominador
es chico. Los medianos de abajo usan los reinicios con referencia no vacía.

| Plazo | n (con ref.) | alcanzan el área | Mediana \|ln sesgo\| | Mediana Dice | Mediana Dice@t\* − Dice (sólo alcanzan) | Mediana \|Δángulo\| | Elong. crec. pred / obs |
|---|---:|---:|---:|---:|---:|---:|---:|
| 12 h | 26 | 17 de 34 (8 sin ref.) | 1,41 (×4,1) | 0,17 | −0,013 | 67° | 1,50 / 3,19 |
| 24 h | 34 | 28 de 34 | 1,35 (×3,9) | 0,27 | −0,003 | 58° | 1,56 / 2,85 |

Por incendio (mediana de \|ln sesgo\| / ΔDice@t\* / \|Δángulo\|; 12 h | 24 h):

| Incendio (reinicios) | 12 h | 24 h |
|---|---|---|
| Alerces 2023 (3) | 0,84 / −0,014 / 28° | 0,95 / −0,007 / 41° |
| Epuyén 2025 (6) | 2,62 / +0,059 / 95° | 2,23 / +0,023 / 72° |
| Alerces 2024 (8) | 0,83 / −0,037 / 38° | 0,79 / −0,009 / 31° |
| Patriada 2026 (6) | 2,72 / −0,008 / 67° | 1,09 / +0,040 / 59° |
| Alerces 2016 (4) | 1,89 / +0,005 / 106° | 3,46 / +0,023 / 156° |
| Cholila 2015 (7) | 1,70 / +0,016 / 97° | 1,34 / −0,007 / 95° |

Lectura (con la salvedad de R/O1: truncar en t\* no es corregir la velocidad, sólo quita la sobre-propagación
tardía de la ventana):

- En el producto operativo el error de **área es grande** (≈ ×4 en mediana, sobre-propagación en 16 de 26 reinicios a
  12 h y 23 de 34 a 24 h con sesgo > 2) pero **igualar el área no recupera Dice**: Dice@t\* − Dice es −0,01 a 0,00. Con el área
  igualada el Dice sigue en 0,20–0,25 (mediana de los que la alcanzan).
- El **rumbo** del crecimiento falla en mediana 58–67° (16 de 26 reinicios a 12 h y 18 de 34 a 24 h, > 45°), y el
  crecimiento predicho es mucho más redondo que el observado (elongación 1,5 contra 2,9–3,2).
- Entonces, para el Dice de P-24, el error dominante es de **forma/dirección** (dónde crece), no de velocidad, aunque la velocidad (el
  sesgo de área) también está mal por un factor ~4. Cuando el modelo no llega al área (9 de 26 a 12 h, 6 de 34 a 24 h; sesgo mediano 0,4–0,5)
  su precisión a la hora final es 0,45–0,49, no 0,2: es el caso de «lento pero bien orientado».
  Igualar el área ayuda algo (ΔDice +0,02 a +0,06) sólo en Epuyén, Alerces 2016 y, a 24 h, Patriada, justo donde el rumbo falla
  en 59–156°: la velocidad corregida no alcanza si la dirección está mal.
- Límites: n = 6 incendios correlacionados; ángulo de centroides de una cuña ancha; el crecimiento de una semilla grande
  es un anillo (la elongación del crecimiento solo es sensible al anillo excluido).

## S3. Cruces de F3 (`datos/S3_cruces_f3.csv`, `S3_senal_se_s.csv`)

Agrupado sobre los 6 incendios no límite (`incendio = TODOS`); `n_celdas` = celdas válidas del estrato.
Tasa FN = FN/(TP+FN); FP = FP/(TP+FP).

**TU × orientación (tasa FN, n celdas):**

| Sector | TU | no-TU |
|---|---:|---:|
| N | 0,26 (87 k) | 0,40 (423 k) |
| NE | 0,38 (96 k) | 0,42 (492 k) |
| E | 0,58 (107 k) | 0,49 (529 k) |
| SE | 0,71 (125 k) | 0,64 (471 k) |
| S | 0,70 (140 k) | 0,49 (403 k) |
| SO | 0,48 (143 k) | 0,36 (420 k) |
| O | 0,47 (144 k) | 0,31 (481 k) |
| NO | 0,48 (99 k) | 0,27 (423 k) |
| plano/sin dato | 0,61 (85 k) | 0,59 (883 k) |

**La señal SE/S sobrevive dentro y fuera de TU:** SE+S contra N+NO+O, FN 0,70 contra 0,42 en TU (razón 1,69; 265 k y
330 k celdas) y 0,55 contra 0,32 fuera de TU (1,70; 874 k y 1,33 M). Pero está concentrada: por incendio, la razón > 1
vale en 4 de 6 dentro de TU y 3 de 6 fuera; la dan Cholila (0,62 contra 0,38 en TU; 0,68 contra 0,37 fuera), Patriada
(0,92/0,62; 0,51/0,24) y Epuyén (0,40/0,31; 0,57/0,47), mientras que Alerces 2023 y 2024 no tienen señal o la tienen invertida
(0,15–0,29 contra 0,20–0,38). No depende del combustible (misma razón 1,7 en ambos), así que no se explica por TU; apunta a
la orientación (sol/viento/humedad) o a la dirección del fuego real.

**Grupo × pendiente (tasa FN / FP, n celdas), grupos con modelo quemable:**

| Grupo | 0–5° | 5–15° | 15–25° | 25–35° | > 35° |
|---|---|---|---|---|---|
| GR | 0,59 / 0,91 (527 k) | 0,38 / 0,75 (185 k) | 0,39 / 0,71 (58 k) | 0,42 / 0,75 (42 k) | 0,40 / 0,75 (33 k) |
| SH | 0,56 / 0,61 (338 k) | 0,34 / 0,44 (549 k) | 0,37 / 0,39 (389 k) | 0,43 / 0,53 (402 k) | 0,46 / 0,62 (238 k) |
| TU | 0,56 / 0,68 (171 k) | 0,49 / 0,46 (349 k) | 0,58 / 0,48 (256 k) | 0,59 / 0,44 (174 k) | 0,49 / 0,33 (77 k) |
| TL | 0,40 / 0,62 (100 k) | 0,43 / 0,53 (214 k) | 0,40 / 0,41 (202 k) | 0,40 / 0,32 (177 k) | 0,48 / 0,24 (65 k) |

(NB: FN = 1,00 en todas las pendientes por construcción, sin FP; las celdas de agua/roca nunca arden.) No hay gradiente
de FN con la pendiente dentro de TU ni de TL (0,40–0,59 plano); sí lo hay en GR y SH a pendiente baja (FN 0,56–0,59 en
0–5°, contra 0,34–0,43 en el resto: mapa de combustible o terreno llano mal representado) y en FP (decrece con la pendiente en
TU y TL: 0,68 → 0,33 y 0,62 → 0,24). Es decir: en TU la pendiente no ordena los FN; la orientación sí.

## S5 (parcial). Dispersión de ENTRADA del ensamble GEFS (`datos/S5_dispersion_*.csv`)

**Qué hay guardado.** Los rásters de viento por miembro (`u10/v10/ws/wd.tif`) se borraron tras cada corrida («retained and
cleaned», `run_ensemble_backtest_case.py`); sólo quedan en un caso (`backtest-epuyen-20250115T1833Z-gefs-2025011512`). Pero los
**GRIB2 recortados de los 31 miembros × 10 horas sí están retenidos** en los 23 backtests (`<raíz>/sources/<miembro>/source/fNNN.grib2`,
caja −72…−70 °O, −44…−42 °S, 8×8 celdas de 0,25°), así que la dispersión se calcula leyendo `u10/v10` con la misma
`_read_gefs_fields` del ensamble. Por miembro-hora de pronóstico (3-hourly; 10 por caso, 230 filas): desvío estándar circular de la dirección
(√(−2 ln R)) y coeficiente de variación de la rapidez entre los 31 miembros, promediados sobre las 64 celdas del dominio. «Tarde» = 15, 18 y 21 UTC
(12, 15 y 18 h ART). Faltaría, para medirlo sobre lo que ve ELMFIRE: los `ws/wd` interpolados a 30 m por miembro (hoy no guardados), y las
estaciones de los días de los backtests (sólo hay las ya medidas, abajo).

**Medianas por incendio (mediana de las medianas de cada reinicio; el ensamble sólo cubre 4 de los 6 incendios):**

| Incendio (reinicios) | σ dirección, todas las horas | σ dirección, tarde | CV rapidez, todas | CV rapidez, tarde | rapidez media (m/s) |
|---|---:|---:|---:|---:|---:|
| Epuyén 2025 (6) | 5,5° | 5,9° | 0,10 | 0,12 | 3,5 |
| Alerces 2023 (3) | 3,3° | 3,3° | 0,07 | 0,09 | 4,4 |
| Alerces 2024 (8) | 6,0° | 6,8° | 0,10 | 0,14 | 3,6 |
| Patriada 2026 (6) | 11,4° | 8,0° | 0,15 | 0,14 | 3,3 |

Global (230 horas): σ dirección mediana 5,1° (todas) y 5,5° (tarde), CV rapidez 0,08 y 0,11. La dispersión de entrada es **angosta**: 3–11° y
7–15 % por incendio. Sólo 3 reinicios superan los 20°, todos de Patriada: w03 (13,7° todas / 33° tarde), w04 (30° / 37°) y w05
(25° / 10°), y los CV llegan a 0,3. En esos mismos reinicios la banda de salida sigue estrecha: el área de `agreement ≥ 0,10` frente a `≥ 0,80`
(`ENSAMBLE-BACKTESTS-CONSOLIDADO`) difiere 7–9 % en w03 (12/24 h), 12–17 % en w04 y 9–14 % en w05.

**Para O4:** la hipótesis «angosto porque los miembros comparten la escala sinóptica» queda **respaldada en la entrada** (σ ≈ 5° es
mucho menor que el error de dirección contra estaciones), pero eso no distingue por sí solo de la alternativa (insensibilidad al viento bajo dosel,
loop K/M): la falsación (a) de R, entrada ≥ 20–30° con banda angosta, se cumple parcialmente (3 de 23 reinicios, todos
de Patriada, banda 7–17 %), lo que favorece la insensibilidad en esos casos. Es poca evidencia (n = 3 reinicios correlacionados de un incendio).
Sigue faltando (b), (c) y (d) de R (rumbos de las corridas contra viento a 10 m y estaciones por día de corrida).

**Ya medido contra estaciones** (`docs/resultados/AUDITORIA-FISICA.md:283`): dirección del viento del modelo a 10 m contra El Bolsón,
Esquel y Futaleufú en días de fuego (Meteostat, > 5 km/h): **desvío mediano de −14° a +30°**, nunca ~180°; velocidad GFS 0,50–0,87× la
estación, ERA5 0,40–0,70×. Es decir, el sesgo medido de GFS (decenas de grados, velocidad 0,5–0,9×) es varias veces la dispersión
de entrada entre miembros (≈ 5°, CV ≈ 0,1): el ensamble GEFS no cubre el error real del forzante.
