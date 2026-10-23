# I · Isotropía del crecimiento de P-24: ¿abrigo bajo dosel, método o supresión?

> 2026-10-18. Frente 2 de `DIAGNOSTICO-PRECISION-E2E.md` §3, con sus criterios registrados sin cambios.
> Sin ELMFIRE, sólo calibración, artefactos guardados, nada se commiteó, modelo-v0 intacto.
> Código: `scripts/diagnostico_isotropia.py` (`uv run python -m scripts.diagnostico_isotropia`, ~2 min);
> test: `tests/test_diagnostico_isotropia.py`. Datos: `datos/I_isotropia_{por_reinicio,resumen,veredicto}.csv`.

## Veredicto

**No es abrigo.** Con los criterios registrados el frente 2 da **"método"** en 3 de 4 estadísticos. El
cuarto (mediana a 12 h) da "supresión/límite" porque el exceso es **mayor** donde hay viento (WAF ≥ 0,15),
lo contrario de lo que pide "abrigo". La etapa B (`CROWN_RATIO` de la literatura) **no se abre**: el
frente 3 sólo tenía sentido con "abrigo" (§3, condición de orden).

| Plazo | Estadístico | Exceso WAF < 0,15 | Exceso WAF ≥ 0,15 | Razón | Semilla fuera | Semilla dentro | Veredicto |
|---|---|---:|---:|---:|---:|---:|---|
| 12 h | mediana por reinicio (principal) | 0,44 | 0,68 | 0,64 | 0,70 | 0,30 | supresión/límite |
| 12 h | celdas sumadas | 0,51 | 0,42 | 1,21 | 0,64 | 0,30 | método |
| 24 h | mediana por reinicio (principal) | 0,37 | 0,49 | 0,76 | 0,55 | 0,19 | método |
| 24 h | celdas sumadas | 0,49 | 0,41 | 1,20 | 0,57 | 0,28 | método |

"Abrigo" exigía razón ≥ 1,5 y no se cumple en ninguno de los cuatro. Por incendio, sólo se cumple en
Cholila a 12 h (0,47 contra 0,30), es decir en 1 de 6 incendios a 12 h y 0 de 6 a 24 h. La concentración
en la semilla fuera de la cicatriz (≥ 1,5×) sí se cumple en el agregado: 1,9–2,9× en los cuatro
estadísticos.

Por incendio es menos firme:

- Fuera > dentro en 5 de 6 incendios a cada plazo. Las excepciones son Alerces 2024 a 12 h (−0,01 contra
  0,20) y Patriada a 24 h (0,15 contra 0,23).
- ≥ 1,5× en 4 de 6 a 12 h y en 3 de 6 a 24 h. Patriada a 12 h da 1,49; Epuyén a 24 h, 1,2; Alerces 2024
  a 24 h, 1,47.

## Método

- **Reinicios.** Son los 34 k ≥ 1 de `lw-100-obs-001` sobre `*/pronostico-v6` en los 6 incendios de
  calibración no límite (Golondrinas no tiene P-24).
  - Las máscaras son las de `pronostico.puntuar` sin el anillo, igual que S1. Control: el Dice coincide
    con `pronostico.json` en las 68 filas (0 diferencias).
  - Con referencia ≥ 20 celdas quedan 24 reinicios a 12 h y 34 a 24 h.
- **Sectores.** Se toma el rumbo de cada celda desde el centroide de la semilla y se compara con el rumbo
  observado (semilla → centroide del crecimiento observado):
  - cabeza: ≤ 45°;
  - flanco: 45–135°;
  - retroceso: > 135°.

  Exceso = fracción del crecimiento predicho en flancos + retroceso menos la del observado, dentro de
  cada estrato.
- **Decisiones fijadas antes de mirar** (los criterios registrados no decían cómo agregar):
  - Estadístico principal: mediana por reinicio (como S1), con ≥ 20 celdas (1,8 ha) del estrato en lo
    predicho y en lo observado. Secundario: las celdas sumadas sobre los mismos reinicios.
  - "Igual entre WAF" quiere decir que ningún estrato supera 1,5× al otro.
  - "Método" exige que el exceso de la semilla fuera de la cicatriz sea ≥ 1,5× el de dentro (la misma
    vara que "abrigo").
- **WAF.** Es el ráster que ELMFIRE arma al iniciar, `CALC_WIND_ADJUSTMENT_FACTOR_EVERYWHERE`
  (`elmfire_init.f90:523-571`, tag `2025.0212`).
  - Se calcula con `cc`, `ch` y `fuel_models.csv` de los insumos de cada ventana, con `CROWN_RATIO = 1`.
  - Usa `copa.waf_elmfire`, ajustado para que sea exacto: la tabla va por CC entero en % y CH entero en m
    (`:121-127`), y vale 0 con CC > 0 y CH = 0. Además se agregó el kwarg `crown_ratio`. Esto cambia sólo
    esos bordes; el diagnóstico de `benchmark.py:1479` y su test no cambian.
- **Viento contra pendiente.** Se mide el ángulo entre `wd` + 180 y cuesta arriba (`asp` + 180), con el
  `wd` de la banda horaria más cercana a la llegada.
  - La llegada es el TOA en lo predicho y la primera detección (`vistas_horas`, acotada a [0, plazo]) en
    lo observado.
  - A favor es < 90°. Las celdas con pendiente < 3° van aparte, como plano.
- **Semilla fuera o dentro.** Cada celda de crecimiento toma la etiqueta del borde de semilla más cercano,
  según si ese borde cae dentro o fuera de `cicatriz.tif`.
  - La mediana de la semilla fuera de la cicatriz es 42 % (D: 26–61 %).

## Resultados (todos los reinicios; mediana por reinicio | celdas sumadas)

| Estrato | 12 h | 24 h | Lados pred / obs (mediana, 12 h · 24 h) |
|---|---|---|---|
| Todo | 0,51 \| 0,49 | 0,39 \| 0,49 | 0,71 / 0,08 · 0,67 / 0,22 |
| WAF < 0,15 | 0,44 \| 0,51 | 0,37 \| 0,49 | 0,70 / 0,08 · 0,65 / 0,22 |
| WAF ≥ 0,15 | 0,68 \| 0,42 | 0,49 \| 0,41 | 0,86 / 0,04 · 0,77 / 0,20 |
| Viento a favor de la pendiente | 0,50 \| 0,46 | 0,38 \| 0,44 | |
| Viento en contra | 0,49 \| 0,50 | 0,43 \| 0,49 | |
| Semilla fuera de la cicatriz | 0,70 \| 0,64 | 0,55 \| 0,57 | 0,88 / 0,02 · 0,85 / 0,19 |
| Semilla dentro | 0,30 \| 0,30 | 0,19 \| 0,28 | 0,59 / 0,08 · 0,51 / 0,21 |

Lectura:

- **El crecimiento observado es una cuña y el predicho, un anillo.**
  - Lo observado pone sólo el 8 % (12 h) y el 22 % (24 h) en flancos y retroceso.
  - Lo predicho pone el 67–71 %, contra el 75 % de un círculo perfecto.
  - Medido contra su propio rumbo, lo predicho pone el 56–57 %. Es decir, tiene algo de dirección, pero
    mucho menos que lo observado, y además está girado (S1: 58–67°).
- **El abrigo no ordena el exceso.**
  - Donde el viento llega a la llama (WAF ≥ 0,15: pasto, matorral sin dosel) lo predicho es **igual o más
    isótropo** (0,77–0,86 de lados) que bajo el bosque (0,65–0,70).
  - Si el WAF de 0,07–0,09 fuera la causa, el modelo tendría que estirarse en lo abierto, y no lo hace.
  - El crecimiento observado cae en un 73–78 % bajo WAF < 0,15; el predicho, sólo en un 53–54 %. El
    modelo crece relativamente más en lo abierto, coherente con los FP en GR y en terreno plano de F3.
- **Viento contra pendiente: sin señal.**
  - Fuera del estrato plano, la diferencia es ≤ 0,06 en todo el agregado.
  - Bajo WAF < 0,15, el exceso en contra de la pendiente es 1,2× el de a favor (24 h, mediana 0,40 contra
    0,34; 12 h sumado, 0,52 contra 0,45). Es el mecanismo del loop K, pero lejos de explicar el resto.
- **La semilla explica la mayor parte y deja un residuo.**
  - El 70–71 % del crecimiento predicho brota de un borde de semilla que está fuera de la cicatriz; en lo
    observado, sólo el 16–19 %. Ese crecimiento es casi todo flanco y retroceso (0,85–0,88).
  - Desde la semilla bien puesta, el exceso baja a 0,19–0,30, pero no desaparece. Ese residuo no lo ordena
    ni el WAF ni la relación entre viento y pendiente.
  - A través de los reinicios, la correlación entre la fracción de semilla fuera y el exceso es débil
    (Spearman 0,30 a 12 h y 0,19 a 24 h). El efecto es por celda, no un nivel por reinicio.

## Cruce con las laderas S y SE (F3)

| | 12 h | 24 h |
|---|---|---|
| Exceso SE+S / N+NO+O (mediana \| sumado) | 0,52 / 0,43 \| 0,54 / 0,41 | 0,46 / 0,35 \| 0,55 / 0,42 |
| Tasa de FN de P-24, SE+S / N+NO+O | 0,86 / 0,72 (1,19×) | 0,72 / 0,52 (1,39×) |
| Tasa de FN en SE+S, WAF < 0,15 / ≥ 0,15 | 0,87 / 0,82 | 0,73 / 0,70 |

La señal de F3 (1,7× en la cadena) aparece en P-24 más chica: 1,2–1,4×. Dentro de SE+S, el abrigo no la
cambia (FN 0,87 contra 0,82 y 0,73 contra 0,70), igual que F3 con TU. Lo que se ve en las laderas S y SE
no es el WAF.

## Etapa B: no se abrió

Sólo se dejó constancia, en el fuente del tag, de dónde entra `CROWN_RATIO`, por si se reabre:

- Es un `REAL` escalar global del grupo `&SIMULATOR` (`elmfire_namelists.f90:580`), con default 1,0
  (`:595`).
- Entra en la tabla `SHELTERED_WAF_TABLE`, por `CALC_WIND_ADJUSTMENT_FACTOR_SINGLE` (`elmfire_init.f90:620`).
  La tabla se arma en `INIT_LOOKUP_TABLES` (`elmfire.f90:162`), después de `READ_SIMULATOR` (`:122`).
- Entra también en la mezcla de `F` (`elmfire_init.f90:561`).
- Además entra en `elmfire_spotting.f90:932`, pero con pavesas apagadas y `USE_SUPERSEDED_SPOTTING` no
  se usa.

No se buscó literatura ni se diseñó la receta hija. Según la regla del frente 3, sin "abrigo" no hay nada
que el valor medido pudiera arreglar.

## Qué implica

- **Por los criterios registrados, el frente 2 remite al frente 1:** a la decisión 2 de §6, si la
  semilla reconstruida se recorta a lo detectado. Es lo que más isotropía agrega (~2/3 del crecimiento
  predicho brota de semilla fuera de la cicatriz).
- **El residuo de 0,19–0,30 desde la semilla bien puesta queda como "supresión/límite".** El WAF no lo
  ordena, la pendiente contra el viento apenas, y el rumbo errado (S1) apunta al viento de superficie
  (frente 4) más que a la física bajo dosel.

**Actualización (2026-10-19, [U](U-reconstruccion-semilla.md)).** Recortar la semilla no corrige esto:
huellas o casco sin buffer dan ±0,003 de Dice. Lo que brota "fuera de la cicatriz" es el perímetro
inactivo, que ELMFIRE quema igual que la cabeza. Así que en la práctica la salida es
"supresión/límite", no un método corregible.

## Límites

- n = 6 incendios correlacionados.
- El rumbo observado sale del centroide de una cuña, y es el mismo que define los sectores. Eso hace
  chicos los "lados observados" por construcción, pero afecta igual a todos los estratos, y el criterio
  compara entre estratos.
- La llegada observada es la detección VIIRS (una cota superior de la hora).
- `wd` se toma de la banda más cercana, no interpolado (ELMFIRE interpola linealmente).
- La etiqueta de la semilla es geométrica (el borde más cercano), no la trayectoria del frente.
- A 12 h la mediana y el agregado sumado no coinciden. La mediana da otro veredicto, aunque en la
  dirección opuesta a "abrigo".
