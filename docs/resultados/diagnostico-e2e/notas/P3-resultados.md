# P3. Resultados de la fase 3: frentes 1 y 2

Sin ELMFIRE, sin Earth Engine, sin commit. Sólo calibración; el conjunto de prueba se re-puntuó
únicamente para informar (frente 1, tabla aparte). Código: `scripts/diagnostico_metrica.py` (frente 1),
`scripts/diagnostico_severidad.py` (frente 2); tests mínimos en `tests/test_diagnostico_metrica.py` y
`tests/test_diagnostico_severidad.py`. Tablas: `docs/resultados/diagnostico-e2e/datos/P3_*.csv`.
El diseño y los umbrales son los registrados en `DIAGNOSTICO-PRECISION-E2E.md` §3-§4; no se ajustó ninguno.

## Enmiendas (enmienda registrada por la revisión antes de ver resultados)

1. **Frente 1 (a).** *Enmienda registrada por la revisión antes de ver resultados.* La variante "puntuar sólo
   dentro de `vistas ∪ cicatriz`" era incorrecta: `cicatriz.tif` ya es `positivo ∧ vistas`
   (`scripts/benchmark.py:104-105`), de modo que esa variante excluye todo falso positivo lejos del fuego y premia
   sobre-propagar. Se reemplaza por: excluir SÓLO las islas no vistas =
   `relleno(cicatriz FINAL sin truncar) ∧ ¬cicatriz_final ∧ ¬vistas`; el resto se puntúa como en la oficial.
   La variante vieja se calculó antes de la enmienda y se conserva en
   `P3_f1a_variante_descartada_*.csv`, rotulada "variante descartada por la revisión (premia sobre-propagar)".
   El resultado del frente es la nueva.
2. **Frente 1 (b).** *Enmienda registrada por la revisión antes de ver resultados.* "Quitar el anillo ya visto"
   significa EXCLUIRLO de la puntuación (ni TP ni FP ni FN). Verificado: `excluido_estricto` suma
   `(vistas_h <= 0) & ~semilla` al `excluido` que `pronostico.puntuar` pasa a `puntuacion.metricas`, y ésta
   descarta esas celdas tanto de `pred` como de `ref` (`puntuacion.py`, `metricas`: `p = pred & donde`,
   `o = ref & donde`). Se aplica igual a P-24, cadena y persistencia. Cubierto por un test.
3. **Frente 2.** *Enmienda registrada por la revisión antes de ver resultados.* El criterio numérico queda igual;
   el veredicto tiene tres salidas. SÍ: se cumple el criterio en Patriada y Alerces 2024. INDISCRIMINADO: la
   fracción de los días siguientes en bosque es > 0,67, o el control SH4 del día 1 da una fracción >= 0,8× la del
   bosque del día 1, o el Landsat/proxy no es confiable para ese incendio. NO: ninguno de los dos casos
   anteriores. Si hay causa de INDISCRIMINADO en alguno de los dos incendios del criterio, prevalece (la
   precedencia no estaba escrita; la fijé así y dejo el cumplimiento del criterio en columna aparte, `cumple`).
   Secundarias descriptivas: RdNBR y FRP media de VIIRS.

## Frente 1

### (a) Dice por receta, 7 casos de calibración, `lw-100-001` y las otras 4 recetas completas

Las cinco recetas con iteraciones en los 7 casos v6: `base-001`, `lw-100-001`, `lw100-atlas-001`,
`lw100-supresion-30-001`, `lw100-supresion-60-001` (coincide con ESTADO-RESEARCH §3).

**Control: cumple.** Con la métrica oficial, el Dice reproducido es idéntico a `principal.dice` de `metricas.json`
en las 35 iteraciones (diferencia máxima 0,0; `control_ok` = True). Además la cicatriz truncada que recalculo
(`pos ∧ vistas r = 375 m`) coincide celda a celda con el `cicatriz.tif` empaquetado (0 celdas de diferencia).

Dice por incendio, `lw-100-001`:

| Incendio | Oficial | Corregida (islas no vistas) | Islas no vistas excluidas (ha) |
|---|---:|---:|---:|
| Alerces 2023 | 0,528 | 0,528 | 0 |
| Epuyén 2025 | 0,501 | 0,501 | 20 |
| Alerces 2024 | 0,635 | 0,635 | 200 |
| Patriada 2026 | 0,496 | 0,496 | 1.811 |
| Las Golondrinas 2021 (límite) | 0,012 | 0,012 | 686 |
| Alerces 2016 | 0,389 | 0,389 | 2 |
| Cholila 2015 | 0,513 | 0,518 | 1.526 |
| **Media / mediana** | **0,439 / 0,501** | **0,440 / 0,501** | |

Las cinco recetas (media / mediana sobre los 7):

| Receta | Oficial | Corregida | Puesto (media) of./corr. | Puesto (mediana) of./corr. |
|---|---:|---:|---:|---:|
| lw-100-001 | 0,439 / 0,501 | 0,440 / 0,501 | 1 / 1 | 1 / 1 |
| lw100-atlas-001 | 0,417 / 0,483 | 0,417 / 0,483 | 2 / 2 | 2 / 2 |
| base-001 | 0,413 / 0,459 | 0,414 / 0,463 | 3 / 3 | 4 / 4 |
| lw100-supresion-30-001 | 0,411 / 0,471 | 0,412 / 0,471 | 4 / 4 | 3 / 3 |
| lw100-supresion-60-001 | 0,368 / 0,410 | 0,369 / 0,410 | 5 / 5 | 5 / 5 |

**El orden de las recetas no cambia, y `lw-100-001` sigue siendo la mejor** (media y mediana). Con el criterio
registrado ("se acepta como método si no cambia el orden de la mejor receta"), la corrección se acepta; no hay
decisión pendiente del usuario.

Lo que no reproduce D: D estimó que el truncado asimétrico limitaba a un modelo perfecto de perímetro a
0,85 (Patriada, Cholila). Para `modelo-v0` el efecto medido es nulo (Patriada) o de +0,005 (Cholila): la
corrección sólo quita falsos positivos en islas no vistas y modelo-v0 casi no quema ahí (en Patriada ni
siquiera cubre la cicatriz, sesgo 0,70). El techo existe; la pérdida real de modelo-v0 por ese mecanismo es
despreciable.

**Variante descartada** (`P3_f1a_variante_descartada_*.csv`, "premia sobre-propagar"): media 0,530 /
mediana 0,594 para `lw-100-001` (+0,09), con el mismo mejor puesto pero con 4.º y 3.º intercambiados por la
media; reduce el dominio puntuado de 61.888 a 2.313 ha en Alerces 2023. Se muestra sólo para documentar por
qué fue descartada: los +0,09 vienen de no contar la sobre-propagación (p. ej. Alerces 2016: sesgo 1,69 → 0,76,
Dice 0,389 → 0,597).

**Prueba: sólo informativo** (`P3_f1a_prueba_solo_informativo.csv`; no decide nada): la corrección no cambia el
Dice de ninguno de los 4 casos de prueba con `lw-100-001` (El Turbio 0,122, Puerto Café 0,207, Epuyén 2019
0,128, Alerces 2015 0,309). Sólo `lw-100-001` y `base-001` tienen los 4 casos; las supresiones 2 de 4.

### (b) P-24: ΔDice mediano con y sin el anillo "ya visto" (excluido, no negativo)

**Control: cumple.** Sin corrección reproduzco las ocho líneas de `data/benchmark/p24/tabla-pronostico-v6.md`
(líneas 47, 49, 96, 98) y de `tabla-pronostico-oraculo-v6.md`: p. ej. semilla FIRMS contra cadena +0,168 (6/6) a 12 h
y +0,163 (5/6) a 24 h; oráculo +0,107 (6/6) y +0,141 (5/6). `control_ok` = True en las 8.

ΔDice mediano de P-24 (n = 6 incendios, k ≥ 1; entre paréntesis, incendios que mejoran):

| Semilla | Contra | Plazo | Con anillo (actual) | **Sin anillo** |
|---|---|---:|---:|---:|
| FIRMS | cadena | 12 h | +0,168 (6/6) | **+0,096 (6/6)** |
| FIRMS | cadena | 24 h | +0,163 (5/6) | +0,131 (5/6) |
| FIRMS | persistencia | 12 h | +0,061 (6/6) | +0,060 (6/6) |
| FIRMS | persistencia | 24 h | +0,122 (6/6) | +0,142 (6/6) |
| Oráculo | cadena | 12 h | +0,107 (6/6) | +0,155 (6/6) |
| Oráculo | cadena | 24 h | +0,141 (5/6) | +0,185 (6/6) |
| Oráculo | persistencia | 12 h | +0,062 (6/6) | +0,080 (5/6) |
| Oráculo | persistencia | 24 h | +0,107 (6/6) | +0,126 (5/6) |

**Criterio: cumple.** P-24 sigue en pie: con (b) mejora a la cadena en **6 de 6** incendios a 12 h (semilla
FIRMS, la que se informa en la tabla principal; también 6/6 con oráculo). El ΔDice mediano contra la cadena a
12 h baja de +0,168 a +0,096 con semilla FIRMS (el anillo inflaba el resultado, como estimó D). Contra la
persistencia a 12 h queda en +0,060 con 6/6. Con semilla oráculo el signo se invierte (sube de +0,107 a
+0,155): al excluir el anillo, la cadena pierde más que P-24; no investigué el mecanismo. Los números por
incendio están en `P3_f1b_p24_por_incendio.csv`. Los más débiles a 12 h con FIRMS contra la cadena: Cholila
+0,014 y Alerces 2023 +0,035.

## Frente 2

### Escala, fuente y límites del dNBR

- **Fuente:** `imagenes_pre/` y `imagenes_post/` del run indicado en `referencias.cicatriz.run` de cada caso
  (`event-filter-001`; Alerces 2023, `event-filter-002`): 6 bandas (B2, B3, B4, B8, B11, B12), medianas de
  reflectancia (S2 SR_HARMONIZED, 0-10000; Landsat 8 SR reescalado a la misma escala), píxel de 20 m (S2) o
  30 m (L8) en EPSG:4326.
- **Escala del dNBR: 0-1 (NO ×1000).** NBR = (B8 − B12)/(B8 + B12) es un cociente adimensional en [−1, 1]
  (independiente de que la reflectancia esté en 0-10000); dNBR = NBR_pre − NBR_post en [−2, 2]. El umbral
  0,66 equivale al 660 de Key y Benson (2006). El umbral de la máscara (0,3) está en la misma escala.
  Sanidad: mediana del dNBR dentro de la cicatriz 0,61-0,90; fuera de ella ≈ 0 (−0,02 a +0,02); entre el 88 y
  el 95 % de las celdas de cicatriz tienen dNBR ≥ 0,3.
- **Remuestreo a la grilla de 30 m del caso, con el criterio de la cicatriz:** la clase (dNBR válido; dNBR ≥ 0,66)
  se decide en el píxel de origen y se lleva con `Resampling.mode`, como `Grilla.traer`. El dNBR y el RdNBR
  continuos se llevan con `average` y sólo se usan para medianas.
- **Combustible y dosel:** `fbfm40.tif` y `cc.tif` de la ventana 0 de la iteración `lw-100-001` (lo que ELMFIRE
  leyó). TU3 = 163, TU5 = 165, TL2 = 182, TL6 = 186, TL8 = 188, SH4 = 144. Las celdas no válidas
  (`excluido.tif` del paquete: sin observación, `cambio_no_confirmado`, `otro_incendio_probable`) no cuentan.
- **"Día 1":** el texto del diseño admite dos lecturas ("hasta la primera pasada + 24 h desde la ignición").
  Usé la que coincide con el primer reinicio de P-24: detecciones con `acq_datetime` <= (primera pasada + 24 h),
  donde primera pasada = fin del primer grupo de detecciones separadas < 2 h (`pronostico.pasadas`) del
  `firms.csv` del caso. "Días siguientes" = detecciones posteriores hasta el fin de la última ventana, en celdas
  no cubiertas por los discos del día 1. Discos de r = 187,5 m. Como sensibilidad (no sustituye) también calculé
  "ignición + 24 h" (`definicion_dia1` en el CSV): no cambia ninguna conclusión.
- **Límites.**
  - Las imágenes guardadas son medianas **sin** máscara de nubes (D §4: fidelidad contra la máscara guardada
    0,94-0,99 en S2, **0,78 en L8**). Alerces 2016 y Cholila 2015 son Landsat: no confiable.
  - Fecha del POST: ventana POST de 2 a 9 semanas después de la ignición en S2 (Patriada, 1 feb-8 mar 2026; Alerces 2024,
    20 feb-31 mar 2024; Epuyén, 1 feb-8 mar 2025; Alerces 2023, 20 feb-31 mar 2023) y otoñal en Landsat (Cholila
    7 abr-31 may 2015; Alerces 2016 15 feb-15 abr 2016: caída de hoja de lenga y mortalidad diferida pueden
    subestimar o sesgar). La PRE no se reabre (decisión deliberada, memoria del proyecto).
  - Saturación: el 10-15 % de las celdas de bosque del día 1 en Epuyén, Alerces 2024 y Patriada tienen dNBR
    medio >= 1,0 (`frac_dnbr_ge_1`); la escala de dNBR no distingue copa consumida de fuego de superficie
    intenso (el propio diseño lo advierte para Nothofagus con caña).
  - El dNBR dice que la celda ardió con cierta severidad, no cuándo ni por qué mecanismo; la asignación al día
    la hace sólo el instante de la detección VIIRS (un disco de 187,5 m cubre ≈ 58-70 % de cicatriz).
  - Las celdas de los discos que no son cicatriz bajan la fracción. Por eso reporto también "sólo cicatriz"
    (no registrado; informativo).
  - n alto de celdas pero casi todas dependen de pocos discos: las celdas están autocorrelacionadas; no hay
    intervalos de confianza.

### Fracción de severidad alta (dNBR >= 0,66), bosque con dosel (TU3, TU5, TL2, TL6, TL8; cc > 0)

Definición principal, todas las celdas válidas en los discos (`P3_f2_severidad.csv`, `P3_f2_criterio.csv`):

| Incendio | Día 1 | Días siguientes | Razón | SH4 día 1 | SH4 / bosque día 1 | Motivo INDISCRIMINADO |
|---|---:|---:|---:|---:|---:|---|
| **Patriada 2026** (criterio) | 0,40 | 0,42 | 0,96 | 0,40 | 0,99 | SH4 día 1 >= 0,8× bosque |
| **Alerces 2024** (criterio) | 0,41 | 0,14 | 2,98 | 0,56 | 1,35 | SH4 día 1 >= 0,8× bosque |
| Alerces 2023 | 0,41 | 0,63 | 0,65 | 0,22 | 0,54 | — |
| Epuyén 2025 | 0,40 | 0,22 | 1,85 | 0,23 | 0,57 | — |
| Alerces 2016 (L8) | 0,49 | 0,22 | 2,18 | 0,68 | 1,40 | SH4; Landsat |
| Cholila 2015 (L8) | 0,20 (n = 703) | 0,34 | 0,59 | sin celdas | — | Landsat |
| Las Golondrinas 2021 (límite) | 0,00 (n = 8) | 0,40 | — | 0,00 (n = 5) | — | muestra insuficiente |

**Criterio numérico: no cumple.** Patriada: 0,40 < 0,5 y razón 0,96 < 1,5. Alerces 2024: razón 2,98 (cumple
1,5×) pero 0,41 < 0,5. Se exigían ambos incendios.

**Veredicto con la enmienda: INDISCRIMINADO.** En los dos incendios del criterio, el control SH4 del día 1 da una
fracción >= 0,8× la del bosque del día 1 (Patriada 0,40 contra 0,40; Alerces 2024 0,56 contra 0,41): la severidad
del día 1 es alta en todos los combustibles, no específica del bosque con dosel. Las condiciones de los días
siguientes (> 0,67) y de Landsat no se activan para esos dos incendios (S2).

Variantes (informativas, mismo veredicto):

- Sólo cicatriz (no registrada): Patriada 0,53 contra 0,59 (razón 0,90, no cumple); Alerces 2024 0,55 contra 0,24
  (razón 2,3, cumple el numérico en ese incendio); SH4 día 1 0,55 y 0,59: sigue >= 0,8× el bosque.
- Ignición + 24 h (sensibilidad): Patriada 0,38 contra 0,42; Alerces 2024 0,43 contra 0,17.
- En 4 de 7 incendios la severidad alta (>= 0,66) es <= 0,5 incluso sobre toda la cicatriz (0,44-0,71), así que el
  umbral de 0,5 del criterio es exigente por construcción.

Lectura honesta: en 3 de 6 incendios con datos (Epuyén, Alerces 2024, Alerces 2016) el bosque del día 1 es más severo que el de los días siguientes, pero SH4 sube igual
(Epuyén 0,23/0,12, Alerces 2023 0,22/0,07, Alerces 2024 0,56/0,19, Patriada 0,40/0,21). Es compatible con que los
discos del día 1 caen en las zonas de fuego más intenso (o con la diferencia de edad de la observación), sin
distinguir copa de superficie. El resultado **no da evidencia de copa en el día 1** ni la descarta: no habilita la
variante única del primer reinicio de P-24 de DIA-1 §7.6 y el límite de copa queda como estaba.

### Secundarias descriptivas

- **RdNBR** = dNBR / sqrt(|NBR_pre|) (Miller y Thode 2007), escala 0-1 (la cita usa ×1000), en
  `P3_f2_severidad.csv` (`rdnbr_p25/mediana/p75`). No encontré un umbral de severidad alta de RdNBR en el repo ni
  en `docs/`, y no lo verifiqué en la literatura, así que no calculé una fracción: sólo distribuciones. Bosque día
  1 / siguientes (mediana): Patriada 0,79/0,77, Alerces 2024 0,71/0,39, Epuyén 0,70/0,41, Alerces 2023 0,77/1,14.
  SH4 día 1: Patriada 0,90, Alerces 2024 1,09. Mismo patrón que el dNBR: el contraste día 1-siguientes aparece en
  Alerces 2024 y Epuyén, pero SH4 no queda atrás.
- **FRP media de VIIRS** (MW, detecciones con píxel en bosque con dosel / SH4), día 1 contra días siguientes
  (`P3_f2_frp.csv`): Alerces 2024 bosque 84,5/20,3 y SH4 107,5/25,7 (n SH4 día 1 = 7); Alerces 2023 56,7/20,6 y
  43,3/8,3; Patriada 36,0/9,3 y 17,8/6,1; Epuyén 53,2/22,1 y 19,0/25,4. La FRP del día 1 es 2-4× la posterior en
  bosque en los cuatro incendios; en Patriada y Alerces 2023 la FRP del día 1 en bosque supera la de SH4
  (36,0 contra 17,8; 56,7 contra 43,3), en Alerces 2024 no (84,5 contra 107,5). Descriptivo; mezcla de
  sensores/ángulo de barrido y no distingue copa de superficie.

## Resumen contra los criterios registrados

| Criterio | Resultado |
|---|---|
| F1(a): no cambia el orden de la mejor receta | **Cumple** (`lw-100-001` primera; media 0,439 → 0,440, mediana 0,501 → 0,501) |
| F1(b): P-24 mejora a la cadena en >= 5/6 incendios a 12 h con (b) | **Cumple** (6/6, ΔDice mediano +0,096; oráculo 6/6, +0,155) |
| F2: fracción alta >= 0,5 y >= 1,5× en Patriada y Alerces 2024 | **No cumple**; veredicto con la enmienda: INDISCRIMINADO (SH4 día 1 >= 0,8× el bosque) |
