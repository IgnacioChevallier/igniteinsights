# Diagnóstico e2e de la precisión de modelo-v0

> Corte: 2026-10-18. Es un diagnóstico, no una reapertura: no se creó ninguna receta física
> nueva, no se corrió ELMFIRE y el conjunto de prueba no se usó para elegir nada (sólo se
> re-puntuó para informar). Las notas de trabajo, con todas las citas, están en
> `docs/resultados/diagnostico-e2e/notas/`:
>
> - A: inventario de lo probado.
> - B1 y B2: los PDF de ELMFIRE pasados a markdown.
> - C: cómo funciona ELMFIRE.
> - D: auditoría de la referencia.
> - E: cadena de insumos.
> - F: descomposición del error.
> - G: literatura.
> - H: unidades de la relación L/W.
> - R: revisión adversarial.
> - S: diagnóstico complementario.
> - P3: fase 3.
> - W: puerta meteorológica, GFS y SMN WRF contra estaciones (frente 4, cerrado).
> - T: por qué la semilla de P-24 queda fuera de la cicatriz (D bug 4, decisión 2).
>
> Las tablas están en `docs/resultados/diagnostico-e2e/datos/`. El código está en
> `scripts/diagnostico_{error,metrica,severidad,viento_estaciones,semilla}.py`, cada uno con su test. **Decidir si se reabre
> algo es del usuario.**
>
> **Nota (2026-10-31): las cifras de P-24 de este diagnóstico son hindcast.** El +0,096 en 6 de 6 a
> 12 h y el +0,131 en 5 de 6 a 24 h contra la cadena (y el +0,168 con el anillo) usan, en cada
> reinicio, análisis GFS emitidos después del reinicio, o ERA5 en Cholila y Alerces 2016. Lo mismo
> vale para las notas de `diagnostico-e2e/notas/` anteriores a esa fecha. Con el último ciclo GFS ya
> publicado en cada reinicio, sobre los cuatro incendios GFS, P-24 gana a la cadena por +0,118 en
> 4 de 4 a 12 h y por +0,154 en 3 de 4 a 24 h
> ([Z](diagnostico-e2e/notas/Z-p24-pronostico-gfs.md) §4). El texto de abajo no se reescribió.

## Respuesta corta

La predicción no es mejor, sobre todo, por **dónde** quema el modelo, no por **cuánto** quema.

**El error de área es grande, pero igualar el área no arregla el Dice.**

- En el producto operativo (P-24, 34 reinicios de calibración) el crecimiento predicho está errado
  en ×4 de área (\|ln sesgo\| mediano 1,35–1,41).
- Llevado al área observada, el Dice no cambia (mediana −0,013 a 12 h y −0,003 a 24 h).
- Por eso el Dice lo decide la forma: el crecimiento predicho rodea toda la semilla (elongación
  1,5) mientras que el observado avanza hacia un lado (2,9–3,2), y el rumbo está errado en 58–67°
  de mediana.
- En la cadena libre de modelo-v0, ese error de velocidad cambia de signo con el tiempo y con el
  combustible, y termina convertido en error de forma: el día 1 llega tarde, después de las 48 h
  llega temprano, y en bosque el modelo va a la mitad de la velocidad observada.

**Lo que no explica el Dice bajo:**

- **La referencia.** Su techo está en el orden de 0,7–0,9 según la convención. La corrección de las
  islas no vistas cambia el Dice de modelo-v0 de 0,439 a 0,440.
- **La dispersión meteorológica de GEFS.** Su dispersión de entrada es de 3–11° en dirección y
  7–15 % en velocidad, varias veces menor que el error del GFS contra estaciones en las horas de
  corrida (σ circular 30–41°, RMSE 0,44–0,52 de la rapidez observada; W).
  Con esa banda no se puede afirmar ni negar que la meteorología sea la incertidumbre dominante:
  el ensamble está sub-dispersado de entrada.

## 1. Presupuesto de error por etapa

Base: los seis incendios de calibración sin el caso límite. Dice medio al horizonte 0,510 (F1,
`ESTADO-RESEARCH.md` §7). Las componentes **no son aditivas**. Como heurística con errores
independientes, Dice observado ≈ Dice(modelo, verdad) × techo de la referencia (R O3). Con un
techo ≈ 0,85, el Dice contra la verdad sería ≈ 0,60.

| Etapa | Componente | Magnitud medida | Evidencia |
|---|---|---|---|
| Referencia | Umbral dNBR y acuerdo con MCD64A1 (cicatriz final) | Acuerdo de 0,80–0,89 | D §4 |
| Referencia | Convención del radio de `vistas` (375 contra 187,5 m; la huella real es de 240–300 m) | Área ×1,09–1,89. Con referencias anidadas, Dice entre convenciones de 0,69–0,96 (media ≈ 0,84). Es la incertidumbre de referencia más grande para el objeto que se puntúa | D §3; R O3 |
| Métrica | Islas no vistas que puntúan como FP | **Despreciable para modelo-v0:** 0,439 → 0,440; el orden de las recetas no cambia | P3 §1a |
| Métrica (P-24) | Anillo "ya visto" contado como crecimiento | **ΔDice FIRMS contra la cadena a 12 h: +0,168 → +0,096** (6/6 igual); a 24 h, +0,163 → +0,131 | P3 §1b |
| Métrica (P-24) | Semilla reconstruida que se sale de la cicatriz | 26–61 % del área sembrada. Alarga el perímetro de arranque e infla el "×4" | D §5 bug 4 |
| Combustible | Mapa | Calibración: CCS-BAP 0,510, MapBiomas 0,430, WorldCover 0,131. Prueba (sólo informada): 0,191, 0,284 y 0,272. **Es la palanca medida más grande** | ESTADO-RESEARCH §7 |
| Física: área / velocidad | Error de área | P-24: ×4 (\|ln\| 1,35–1,41). En la cadena, el día 1 llega +12 a +65 h tarde, lo posterior a 48 h llega temprano, y en TU, TL y GR la ROS es 0,49–0,63× la observada | S1, F2, F6 |
| Física: forma / dirección | **Residuo dominante en el Dice** | Igualar el área no sube el Dice (P-24: −0,01; cadena: −0,07 a +0,01, y en Patriada podría llegar a +0,11). Crecimiento casi isótropo (1,5 contra 2,9–3,2). \|Δθ\| 58–67° en P-24. FSS +0,15 de 30 m a 2 km. La elongación total es más redonda en 4–5 de 6, robusta a la variante; el eje girado no es robusto (S2) | S1, S2, F4 |
| Física: relieve | Laderas S y SE | Tasa de FN 1,7× la de N, NO y O, igual dentro y fuera de TU (1,69 / 1,70); concentrada en Cholila, Patriada y Epuyén. No la explica la pendiente | F3, S3 |
| Física: supresión | Reinicios tardíos | 25 de 28 reinicios k ≥ 2 sobre-propagan (confundido con la semilla inflada) | F5, D |
| Insumos: viento | Contra estaciones (SYNOP crudo, horas de corrida P-24) | GFS recibido: desvío mediano −13° (Futaleufú), +23° (Esquel) y **+81° (El Bolsón)**; rapidez 0,52–0,80×. SMN WRF 4 km no lo mejora (frente 4). ERA5 0,40–0,70× (con Meteostat) | W; AUDITORIA-FISICA:283 |
| Insumos: humedad | m1 en SH4 (24–28 % de lo quemable) | ±25 % de ROS por punto de m1; LW de 100 a 110 %, −50 % de ROS. El retardo de 1 h vale ≤ 2 % en el pico | E |
| Insumos: dosel | `CROWN_RATIO` (default 1 = máximo abrigo, no se escribe) | WAF 0,07–0,09 bajo dosel. Con CR 0,5, +19–32 % de ROS en el 41–83 % de lo quemable | E B1; R S8 |
| Meteorología como ensamble | Dispersión GEFS | De entrada: 3–11° y CV 0,07–0,15. De salida: banda del 4–14 % del área | S5; ENSAMBLE |

### Verificaciones propias y correcciones a lo que dijeron los agentes

- **Unidades de L/W: no es un bug.** Anderson (1983) con U en m/s. behave y pyretechnics usan la
  forma equivalente en mph (H).
- **`CROWN_RATIO`: no es un bug, pero queda sin decidir.** Sólo entra en el WAF
  (`elmfire_init.f90:561, 620`). Mi argumento inicial de coherencia con el CBH era circular (R S8):
  el CBH de 1–1,5 m representa la escalera de caña, mientras que el CR de Albini y Baughman es la
  profundidad de la copa arbórea. Pasa a ser un frente (§3).
- **`CRITICAL_SPOTTING_FIRELINE_INTENSITY`** es un arreglo por combustible
  (`elmfire_level_set.f90:779`). `namelist_writer.py:72` le asigna un escalar, que por la semántica
  de namelist de Fortran llena sólo el elemento 0. Sólo afecta las pruebas de pavesas cerradas; no
  lo verifiqué con `gfortran`.
- **Cifras invertidas.** `DIA-1-PROPUESTA.md` §7.2 y `RIESGOS_Y_SUPOSICIONES.md:201` atribuyen a la
  semilla FIRMS los +0,107 / +0,141, que son del oráculo
  (`data/benchmark/p24/tabla-pronostico-v6.md:47,96`). Sin el anillo, FIRMS da +0,096 / +0,131 y el
  oráculo +0,155 a 12 h. No los corregí: depende de la decisión 1 (§6).
- **El retardo de humedad y `CROWN_FIRE_MODEL` 0/1 se midieron antes de la corrección del clima**
  (`docs/historico/RESULTADOS.md:296`). El cálculo offline con física corregida (E) y DIA-1 §7.4 los
  cubren. No hay nada que rehacer.
- **`ELMFIRE_Guide.pdf` y elmfire.io documentan la 1.1, no 2025.0212** (B2, C). La verdad son el
  fuente y los `docs/*.rst` del tag.
- **El comentario de `namelist_writer.py:51-53` está desactualizado.** Hay rásters por celda de MLH,
  MLW y FMC (C). Es una corrección de documentación pendiente.

## 2. Lo ya cerrado

Inventario completo, con 66 hipótesis y las 120 recetas por familia:
[`notas/A-inventario.md`](diagnostico-e2e/notas/A-inventario.md). De esas recetas, 65 corrieron sin
reporte en los documentos.

| Tema | Estado | Dónde |
|---|---|---|
| 5 bugs de interfaz, orientación, capa sin ignición | Corregidos | [AUDITORIA-FISICA §3](AUDITORIA-FISICA.md) |
| ADJ = 1; LW 100 % | Adoptados | [AUDITORIA-FISICA loops C y E](AUDITORIA-FISICA.md) |
| Paso temporal, rugosidad, CBH/CBD, pérdida previa de Hansen | Decididos | [PENDING_PARAMETERS §1](PENDING_PARAMETERS.md) |
| Pavesas, supresión, ERA5 ×1,3, dosel abierto en matorral, WindNinja (atlas, diurno y rotaciones), alternativas de estepa | Medidos, no adoptados | [AUDITORIA-FISICA loops D, G, K, L y M](AUDITORIA-FISICA.md) |
| m10/m100; humedad en altura; retardo | Insensibles o límite | [HUMEDAD-ALTURA-PROPUESTA](HUMEDAD-ALTURA-PROPUESTA.md); [RESULTADOS §8](../historico/RESULTADOS.md) |
| Día 1 y copa | Límite; P-24 como protocolo | [DIA-1-PROPUESTA §7](DIA-1-PROPUESTA.md) |
| Lo ya quemado; ingesta FIRMS | Resueltos en la app | [LO-YA-QUEMADO-PROPUESTA](LO-YA-QUEMADO-PROPUESTA.md) |
| Las Golondrinas | Caso límite | [RIESGOS §3](RIESGOS_Y_SUPOSICIONES.md) |
| Comparación de mapas | CCS-BAP se mantiene; MapBiomas no es inferior | [COMPARACION-MAPAS-MODELO-V0-RESULTADOS](COMPARACION-MAPAS-MODELO-V0-RESULTADOS.md) |
| Ensamble GEFS | Capa de acuerdo; sin mejora predictiva | [ENSAMBLE-BACKTESTS-CONSOLIDADO](ENSAMBLE-BACKTESTS-CONSOLIDADO.md) |
| Ventana PRE de 26 meses | Deliberada | mask-dataset-gen |

### Hipótesis semilla

| # | Hipótesis | Veredicto | Evidencia |
|---|---|---|---|
| 1 | ADJ secuencial por ventana | Nunca se corrió. **Falsada offline en su forma simétrica:** \|ln sesgo\| 1,39 → 1,41, y los 7 reinicios con ADJ > 1 empeoran. Sólo "reducir" tiene señal, es post hoc y está confundida con la semilla inflada | F5, D |
| 2 | El error dominante es paramétrico o estructural, no meteorológico | **No se puede afirmar con el ensamble.** GEFS está sub-dispersado de entrada (3–11° contra un error del GFS en estaciones de σ 30–41°, W). El loop K agrega que, con WAF ≈ 0,08, ni la dirección del valle mueve el bosque. Lo dominante en el Dice es la forma. I descarta el abrigo bajo el dosel como causa: la mayor parte del exceso de flanco brota de semilla fuera de la cicatriz, y queda un residuo sin estrato que lo ordene | S1, S5, I; AUDITORIA loop K |
| 3 | Parte del Dice bajo es techo o sesgo de la referencia | **El techo es real pero no explica la brecha:** ≈ 0,7–0,9, y el sesgo de las islas vale +0,001. En P-24 sí había un sesgo a favor (el anillo) | D, P3 |
| 4 | SMN WRF nunca fue la meteorología principal | **Confirmado:** sólo existe un prototipo de ensamble. Puesto a prueba en estaciones (frente 4), no mejora al GFS: no pasa | A, E, W |
| 5 | Opciones de ELMFIRE no probadas | Un solo modelo de copa (Van Wagner + Cruz 2005, binario, con CC ≥ 0,39). Sin probar: `CROWN_RATIO`, `FOLIAR_MOISTURE_CONTENT` (90 % por defecto), `FMC/MLW/MLH_FILENAME`, `CROWN_FIRE_ADJ`, `CRITICAL_CANOPY_COVER`, `PHIW_ADJ`/`PHIS_ADJ`, `WSMFEFF_LOW_MULT`/`MAX_LOW`, Monte Carlo con deltas globales. No hay asimilación | C; [ELMFIRE-COMO-FUNCIONA](../referencias/ELMFIRE-COMO-FUNCIONA.md) |
| 6 | ROS empírica por combustible entre pasadas | 1,8–2,9 m/min, sin un orden resoluble (±0,6). El modelo da 0,76–0,88× en SH y 0,49–0,63× en TU, TL y GR | F6 |

## 3. Frentes, ordenados por impacto esperado y evidencia (después de la revisión)

Clasificación según la regla de parada: **[M]** método de medición, **[B]** bug físico, **[E]**
evidencia externa nueva, **[P]** producto distinto de modelo-v0, **[K]** perilla (no habilita
nada).

### 1. Métrica de P-24 sin el anillo [M] — ejecutado; decidido el 2026-10-18 (§6.1)

- **Resultado (P3).** La métrica principal no cambia (0,440). P-24 sigue ganando a la cadena en
  6 de 6 a 12 h, pero con +0,096 en lugar de +0,168.
- **Decisión del usuario.** Si P-24 se puntúa sin el anillo, hay que corregir las cifras de DIA-1
  §7.2, RIESGOS y la tesis. Lo mismo para la semilla inflada (D bug 4): ¿se recorta la semilla a
  lo detectado o se mantiene la reconstrucción de la app?

### 2. Isotropía del crecimiento: ¿WAF bajo dosel, supresión de flancos o semilla? [diagnóstico, 0 corridas] — cerrado: "método", no abrigo

- **Resultado (2026-10-18, [I](diagnostico-e2e/notas/I-isotropia.md)).** Se usaron los 34 reinicios
  de P-24 sin el anillo. El Dice coincide con `pronostico.json` en las 68 filas.
  - El crecimiento observado pone el 8–22 % en flancos + retroceso; el predicho, el 67–71 % (un
    círculo da 75 %).
  - **No es abrigo.** El exceso con WAF < 0,15 contra WAF ≥ 0,15 es 0,44/0,68 y 0,51/0,42 a 12 h, y
    0,37/0,49 y 0,49/0,41 a 24 h (mediana | celdas sumadas). La razón va de 0,64 a 1,21, nunca ≥ 1,5:
    donde llega el viento, lo predicho es igual o más redondo.
  - **Sí se concentra en la semilla fuera de la cicatriz.** El 70 % del crecimiento predicho brota
    de ahí, con un exceso de 0,55–0,70 contra 0,19–0,30 desde la semilla bien puesta (1,9–2,9×).
  - Veredicto: "método" en 3 de 4 estadísticos. La mediana a 12 h da "supresión/límite", porque el
    WAF alto tiene 1,55× más exceso, lo contrario de "abrigo".
  - Viento contra pendiente: sin señal (≤ 0,06).
  - Laderas S y SE: FN de P-24 1,2–1,4× la de N/NO/O, sin diferencia por WAF.
  - Queda un residuo de 0,19–0,30 desde la semilla bien puesta que ningún estrato ordena.

- **Evidencia.** S1: el crecimiento de P-24 es casi isótropo (1,5 contra 2,9–3,2) y gira 58–67°.
  F3: FN en las laderas S y SE en todos los combustibles. C: con WAF 0,07–0,09, la elipse bajo dosel
  sale con L/W ≈ 1,1. Loop K: la pendiente le gana al viento bajo el bosque.
- **Experimento falsable.** Por reinicio de P-24, repartir el crecimiento predicho y el observado
  en tres sectores respecto del rumbo observado: cabeza (±45°), flancos y retroceso. Estratificar
  por (i) WAF de la celda (< 0,15 contra ≥ 0,15), (ii) viento a favor o en contra de la pendiente
  (ángulo entre `wd` + 180 y la orientación) y (iii) semilla dentro o fuera de la cicatriz.
- **Criterios fijados de antemano.**
  - Si el exceso de flanco y retroceso predicho es ≥ 1,5× mayor con WAF < 0,15 que con WAF ≥ 0,15,
    el mecanismo es el abrigo y habilita el frente 3.
  - Si el exceso es igual en ambos estratos de WAF y se concentra donde la semilla cae fuera de la
    cicatriz, es método (frente 1).
  - Si no se cumple ninguno de los dos, queda como supresión y límite.
- **Costo.** 0 corridas. **Fuga:** ninguna.

### 3. `CROWN_RATIO` medido para el bosque patagónico [E condicionada → candidato a v1] — cerrado: no se abre

- **Cierre (2026-10-18).** El frente 2 no dio "abrigo", así que no se cumple la condición de orden.
  No se buscó literatura ni se creó la receta.
- En el fuente quedó confirmado que es un escalar global de `&SIMULATOR` (`elmfire_namelists.f90:580`,
  default 1,0 en `:595`). Entra en la tabla del WAF (`elmfire_init.f90:620`) y en la mezcla (`:561`),
  y además en `elmfire_spotting.f90:932`, que no se usa (I).

- **Evidencia.** Es un default de ELMFIRE que nunca se decidió. CR = 1 es el máximo abrigo y deja
  WAF 0,07–0,09. Con CR 0,5, +19–32 % de ROS en el 41–83 % de lo quemable (E B1). Eso actúa
  justamente donde están el 49 % de los FN (TU) y la ROS de 0,5× (F6).
- **Condición para que sea [E].** Un valor de profundidad de copa / altura publicado para coihue,
  lenga, ñire y pino de la región, fijado antes de correr. Como `CROWN_RATIO` es un escalar global,
  el valor sería el ponderado por el área de bosque de calibración. Sin ese dato es [K].
- **Experimento.**
  - Receta hija de `lw-100-001` sobre los 7 casos v6.
  - Criterios fijados de antemano: Dice medio ≥ +0,02, ninguna alarma nueva, tasa de FN en TU ≥
    10 % menor, y validación cruzada que no empeore.
  - Riesgo conocido: LW se calibró con CR = 1, así que el mínimo puede correrse; LW no se recalibra
    en esta receta.
- **Costo.** ≈ 30 corridas de ventana (7 casos), ~1 h de VM, más la validación cruzada.
- **Fuga.** Baja si el valor viene de la literatura.
- **Condición de orden.** Sólo tiene sentido si el frente 2 da "abrigo".

### 4. Puerta meteorológica: GFS (y SMN WRF si está archivado) contra estaciones, día a día [E si WRF gana; 0 corridas] — cerrado: no pasa

- **Resultado (2026-10-18, [W](diagnostico-e2e/notas/W-viento-estaciones.md)).** WRF está
  archivado para los 4 incendios y se leyó sólo el viento por rango HTTP (~2,5 GB). Contra SYNOP
  crudo, en 395 estación-horas, pasa en **1 de 3** estaciones:
  - Esquel (n = 322): \|Δθ\| mediano 26,8° → 30,7°, sesgo −12 %;
  - Futaleufú (n = 52): 19,1° → 39,1°, sesgo +13 %;
  - El Bolsón (n = 21): 81,4° → 11,6°, sesgo −45 %.

  El orden se repite incendio por incendio y con la celda más cercana. No se crea
  `lw-100-obs-wrf-001`. La señal de El Bolsón (la estación más cercana a Epuyén y Patriada) queda
  como pedido de estaciones de valle (RIESGOS §3), no como receta. Hallazgo lateral: el Meteostat
  de El Bolsón es mayormente relleno, lo que corrige AUDITORIA-FISICA:283 y RIESGOS §3.
- **Evidencia (antes de la prueba).** La dispersión de entrada de GEFS es de 3–11°, contra un
  desvío del GFS frente a las estaciones de −14° a +30°. Es una sub-dispersión documentada.
- **Experimento.** Dirección y rapidez a 10 m en El Bolsón, Esquel y Futaleufú durante las horas
  de corrida de los 4 incendios 2023–2026. Se calcula el error medio angular y el sesgo de rapidez
  del GFS y de SMN WRF (4 km).
- **Criterio.** WRF reduce el error angular mediano en ≥ 10° y el sesgo de rapidez en ≥ 20 % en
  ≥ 2 de 3 estaciones.
- **Si pasa**, se corre `lw-100-obs-wrf-001` en P-24:
  - 23 reinicios, una corrida por vez;
  - se usa la métrica sin el anillo;
  - éxito si mejora en ≥ 3 de 4 incendios, con mediana ≥ +0,02, y si el \|Δθ\| mediano por
    reinicio (S1) baja ≥ 15°.
- **Advertencia (R O7).** La resolución efectiva de WRF (~25–30 km) es mayor que el ancho de los
  valles, y WindNinja a 90 m ya falló.

### 5. Ensamble paramétrico para P-24 [P] — fuera de alcance (decisión del usuario, 2026-10-19)

- **Decisión.** No entra en la tesis. Su objetivo es la cobertura P10–P90 y la relación spread-skill,
  y la tesis no afirma una probabilidad calibrada (DECISIONES-TESIS-TRANSPARENCIA-INCERTIDUMBRE §2). La
  forma isótropa ya quedó como límite (I, U), así que un ensamble paramétrico no la corrige.
- La sub-dispersión de GEFS queda como limitación declarada de la capa de acuerdo.
- Diseño conservado en [`docs/out-of-scope/ENSAMBLE-PARAMETRICO.md`](../out-of-scope/ENSAMBLE-PARAMETRICO.md).

- **Objetivo.** Representar la incertidumbre que GEFS no muestrea.
- **Miembros.** 20 miembros con σ fijados de antemano desde lo medido, no ajustados:
  - ln ADJ ~ N(0; 0,4) (Cruz y Alexander 2013);
  - WD ±25° (el desvío contra estaciones);
  - m1 ±1 punto.
  El ADJ va por miembro en la receta, porque el Monte Carlo de ELMFIRE sólo aplica deltas
  globales (C).
- **Criterios (corregidos por R O8).**
  - Cobertura P10–P90 del crecimiento observado ≥ 0,8, por separado en los reinicios con sesgo < 1
    y con sesgo > 1.
  - Correlación spread-skill (Spearman entre el ancho de la banda y \|ln sesgo\|) ≥ 0,3.
  - Comparación contra GEFS en los mismos 23 reinicios.
- **Costo.** 460 corridas, del orden de GEFS.
- **Alcance.** No toca modelo-v0.

### 6. Humedad viva por celda con LFMC medida [E condicionada] — cerrado: no se abre

- **Cierre (2026-10-22, [V](diagnostico-e2e/notas/V-humedad-viva.md)).** La serie de Bianchi y
  Defossé que no se usó para calibrar es la Tabla 2, con el LFMC medio por especie. Con Rothermel,
  ese LW por celda frena SH4 a 0,33×, SH8 a 0,70×, TU3 a 0,80× y el TU5 de ciprés a 0,75×, cuando
  el modelo ya va 0,49–0,88× de la ROS observada (F6). Sólo acelera la colihue (×1,18–1,27). No se
  crea receta.

- **Evidencia.** En SH4, LW de 100 a 110 % baja el ROS de 3,0 a 1,5 m/min (E). `MLW_FILENAME`
  existe (C). Bianchi y Defossé (2015) midieron LFMC por especie en la región.
- **Condición.** Una serie por especie y mes que no se haya usado para calibrar. Sin eso es [K].

### 7. Regla "sólo reducir" en reinicios tardíos [P, exploratoria]

- **Evidencia (F5).** 17 mejoran y 4 empeoran (\|ln\| 1,39 → 1,03), pero la regla es post hoc y
  está confundida con la semilla inflada (R O5).
- **Condición.** Sólo con incendios futuros, después de decidir el frente 1.

### Cerrados por este diagnóstico

| Idea | Cierre |
|---|---|
| ADJ secuencial simétrico | Falsado (F5) |
| Unidades de L/W | Coherentes (H) |
| Retardo de humedad | ≤ 2 % en el pico (E) |
| Sesgo de islas en la métrica principal | +0,001 (P3) |
| Severidad dNBR como evidencia de copa del día 1 | Indiscriminado (P3; §4) |
| `FOLIAR_MOISTURE_CONTENT` | [K] mientras no haya evidencia de copa |
| SMN WRF 4 km como viento de P-24 (frente 4) | No pasa: 1 de 3 estaciones (W) |

## 4. Fase 3: diseño registrado y resultados

**Diseño.** Se eligieron los frentes 1 [M] y 2 [E] del ranking original, ambos sin ELMFIRE. La
revisión registró dos enmiendas **antes de ver resultados**:

- **Frente 1(a).** El diseño original puntuaba dentro de `vistas ∪ cicatriz`, que premia
  sobre-propagar porque `cicatriz.tif` ya es `positivo ∧ vistas` (`scripts/benchmark.py:104-105`).
  Pasó a excluir sólo las islas no vistas: `relleno(cicatriz final) ∧ ¬cicatriz ∧ ¬vistas`. En (b)
  el anillo se excluye; no cuenta como negativo.
- **Frente 2.** Pasó a tener tres salidas: **sí**, **indiscriminado** (fracción de los días
  siguientes > 0,67, o control SH4 ≥ 0,8× el bosque, o dato no confiable) y **no**.

**Controles.**

- La métrica oficial reproduce `metricas.json` en las 35 iteraciones, con diferencia 0,0.
- Sin corrección, P-24 reproduce las 8 líneas de `tabla-pronostico*-v6.md`.

**Resultados.**

| Frente | Criterio | Resultado | Veredicto |
|---|---|---|---|
| 1(a) islas | Que no cambie el orden de la mejor receta | `lw-100-001` sigue primera (0,439/0,501 → 0,440/0,501); las otras 4 conservan el orden. La variante descartada habría dado 0,530/0,594 | Cumple; efecto despreciable |
| 1(b) anillo | P-24 mejora a la cadena en ≥ 5/6 a 12 h | 6/6. FIRMS +0,168 → +0,096; oráculo +0,107 → +0,155 | Cumple (no ciego: D ya lo había medido) |
| 2 severidad | Bosque del día 1 ≥ 0,5 y ≥ 1,5× los días siguientes, en Patriada y Alerces 2024 | Patriada 0,40 contra 0,42. Alerces 2024 0,41 contra 0,14 (razón 3,0, pero < 0,5). Control SH4 del día 1: 0,40 y 0,56, ≥ 0,8× el bosque | **Indiscriminado** (con la precedencia inversa sería "no") |

Datos descriptivos del frente 2:

- La FRP de VIIRS en bosque el día 1 es 2–4× la de los días siguientes.
- Entre el 10 y el 15 % de las celdas de bosque del día 1 tienen dNBR ≥ 1.
- El POST de Sentinel-2 se tomó 2–9 semanas después de la ignición.
- Las imágenes guardadas no tienen máscara de nubes.

**Conclusión de la fase 3.** El límite de copa sigue como estaba: la severidad no separa la copa
del fuego de superficie letal, ni el día 1 de los siguientes. La métrica principal es sana, y la
de P-24 necesita la corrección del anillo. No hubo corridas de ELMFIRE (Docker Desktop además
estaba caído) y no se promovió nada.

## 5. Revisión adversarial

Un revisor opus sin contexto ([`notas/R-revision.md`](diagnostico-e2e/notas/R-revision.md))
encontró cinco errores bloqueantes y nueve objeciones. Se incorporaron así:

| Objeción | Cómo se incorporó |
|---|---|
| E1, E2: diseño del frente 1 | Enmienda antes de ver resultados (§4) |
| E3: F7 sin versionar | Versionada como `f7` con variantes y bootstrap (S2). El eje girado no sobrevive; la redondez sí |
| E4, O3: el presupuesto no cerraba | Ahora es multiplicativo, el techo se da como orden de magnitud y "forma/dirección" figura como residuo |
| E5, O7: el frente 3 original (WRF) | Pasa a ser el frente 4, con una puerta de estaciones previa |
| O1: velocidad | Se rehízo por reinicio de P-24 (S1). La conclusión se mantiene, reformulada |
| O4: GEFS | Se midió la dispersión de entrada (S5): sub-dispersado |
| O5: componentes faltantes | Se agregaron el mapa de combustible, la semilla inflada, la orientación y la convención de `vistas` |
| O6: frente 2 | Tres salidas; dio indiscriminado |
| O8: criterios del ensamble | Estratificados y con spread-skill |
| O9: humedad viva | Ahora se cita la sensibilidad a LW |
| S8: `CROWN_RATIO` | Reabierto como frente 3 condicionado |

Quedan sin incorporar:

- El bootstrap de S2 es demasiado angosto, porque ignora la autocorrelación espacial. Los
  intervalos de F7 no se usan como evidencia.
- Las ráfagas (S7) siguen como límite del día 1 (DIA-1 §5.2); P-24 las esquiva.

## 6. Qué necesita decisión del usuario

1. **Decidido el 2026-10-18: P-24 se puntúa sin el anillo.**
   - `pronostico.puntuar` lo excluye, con un test.
   - Las tablas de `data/benchmark/p24/` y los `pronostico.json` se regeneraron sin correr ELMFIRE;
     las viejas quedaron como `*-con-anillo.md`.
   - Quedaron corregidos DIA-1 §7.2, §7.3, §7.5 y §7.6, RIESGOS, ESTADO y PENDING.
   - Nuevas cifras: +0,096 / +0,131 (FIRMS) y residuo del día 1 de 2–4,5×.
   - La tesis (`../informe`) queda a cargo del usuario.
2. ¿La semilla reconstruida de la app (26–61 % fuera de la cicatriz) queda como está o se ajusta?
   **Medida (2026-10-19, [U](diagnostico-e2e/notas/U-reconstruccion-semilla.md)):** la regla de
   reconstrucción se mantiene.
   - Las huellas del píxel solas y el casco sin buffer dan un ΔDice de ±0,003 en las estimaciones
     plausibles. Sólo un techo que usa la cicatriz llega a +0,06–0,08.
   - Crecer sólo desde el frente activo da +0,026 a 12 h y −0,027 a 24 h; no pasa el criterio
     registrado.
   - Queda por decidir sólo el filtro conexo de T: 5 corridas en Cholila; no mueve la mediana.
   **Medido (2026-10-18, [T](diagnostico-e2e/notas/T-semilla.md)).** **Decidido después:** el
   filtro se adoptó en `pronostico-v7` el 2026-10-22 (`diagnostico-e2e/notas/T-semilla-v7.md`) y la
   app operativa lo aplica (`AC-semilla-app.md`); la regla de reconstrucción quedó como límite
   declarado el 2026-10-31 (`ESTADO-RESEARCH.md` §6.2).
   - Sólo el 26 % del área de afuera es un bug: detecciones de otros incendios, casi todas en
     Cholila. El 43 % es la huella y el margen del píxel de 375 m, el 16 % el relleno del casco y
     el 16 % quema que la cicatriz no marca.
   - Un filtro de tiempo real (detecciones conectadas a la ignición con saltos ≤ 3 km) equivale al
     oráculo y no pierde cicatriz. En una aproximación sin ELMFIRE, sólo sube el Dice de Cholila
     (24 h: 0,26 → 0,33), y la ventaja de P-24 sobre la cadena sigue en +0,096 / +0,131.
   - Recomendación: adoptar el filtro (5 corridas de Cholila para confirmarlo) y dejar el resto
     como límite del píxel. El exceso de flanco que I atribuye a la semilla de afuera, fuera de
     Cholila, no se va con este filtro.
3. **Respondida (2026-10-18):** el frente 2 se corrió y dio "método", no "abrigo" (I). El frente 3
   no se abre, y el peso pasa a la pregunta 2 (la semilla).
   ~~¿Se corre el frente 2 (isotropía, 0 corridas)? Si da "abrigo", ¿se busca el `CROWN_RATIO` de
   la literatura y se abre una receta candidata a modelo-v1?~~
4. ~~¿Se invierte en la ingesta de SMN WRF y en las estaciones día a día (frente 4)?~~
   **Respondida (2026-10-18):** se midió la puerta y no pasa; no se invierte en la ingesta (W).
5. ~~¿El ensamble paramétrico (frente 5, 460 corridas) entra en el alcance de la tesis, junto a la
   capa GEFS?~~ **Respondida (2026-10-19):** no entra; queda fuera de alcance, con el diseño
   conservado en `docs/out-of-scope/ENSAMBLE-PARAMETRICO.md`.
