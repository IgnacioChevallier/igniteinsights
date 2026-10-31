# Historia de la búsqueda

> 2026-10-31. Registro, para el informe, de cómo se llegó a modelo-v0: qué se probó en cada loop, con
> qué recetas, qué dio en calibración y por qué se adoptó o no. No agrega cifras: cada número sale de
> la sección citada. Las fuentes son la bitácora de `docs/historico/RESULTADOS-CSS-BAP.md` §4–§5
> (loops 0–9, protocolos v1–v3) y la de `docs/resultados/AUDITORIA-FISICA.md` §5–§6 (loops A–M,
> protocolos v4–v6). El estado vigente está en `ESTADO-RESEARCH.md`.

Convenciones de las tablas:

- **Media / mediana:** Dice al horizonte en calibración.
- **GFS (5):** media sobre los cinco incendios GFS, Las Golondrinas incluida. **Los 7:** los siete
  de calibración.
- **Alarmas:** casos con sesgo de área fuera de [0,5; 2], sin el caso límite (Las Golondrinas).
- **CV:** validación cruzada dejando un incendio afuera (`benchmark.py validar`).

## 1. Cuánto se buscó

Conteo sobre lo versionado en git al commit de este documento:

| Qué | Cantidad | Cómo se contó |
|---|---:|---|
| Recetas definidas | 122 | `benchmarks/recetas/*.json` |
| Recetas con al menos una iteración | 117 | recetas distintas en `benchmarks/iteraciones/*/*/*/manifiesto.json` |
| Iteraciones con manifiesto | 1.175 | `benchmarks/iteraciones/<incendio>/<protocolo>/<receta>/manifiesto.json` |
| … con `metricas.json` | 1.167 | las 8 restantes no terminaron (por ejemplo, la supresión a 120 %/día, que corta la cadena; AUDITORIA §5 loop M) |
| Casos (incendio × protocolo) con iteraciones | 261 | |
| Iteraciones sobre los 7 casos de calibración de modelo-v0 (v6) | 44 | |

Por familia de protocolo, las que más iteraciones juntan son `calibracion-v5` (239),
`calibracion-era5-v5` (132), `calibracion-v6` (126), `calibracion-v4` (121) y `calibracion-v2` (110).
Incluye las variantes de ignición (`-ign-*`), horizonte (`-h54`), crosswalk (`-x1`–`-x3`) y viento
(`-a`, `-d`).

Las cifras de este documento salen sobre todo de una fracción de esas iteraciones: las que cada loop
puso en su tabla. El resto son diagnósticos, controles de reproducción, robustez a la ignición y casos
de prueba.

## 2. Etapa 1: loops 0–9 (RESULTADOS-CSS-BAP §4)

Protocolos `calibracion` (v1), `-v2` (orientación del terreno corregida) y `-v3` (más el atlas de
WindNinja). **Toda esta etapa corrió con los hallazgos 1–3 de la auditoría:** el clima congelado en la
banda 0, `phi.tif` en metros con el frente a la mitad y `wd` interpolado como ángulo plano
(AUDITORIA §3). Los loops 0–2 además tenían la pendiente invertida.

| Loop | Qué se probó | Recetas | Calibración | ¿Se adoptó? Por qué |
|---|---|---|---|---|
| 0 | Sin corridas: el −6 de m1 contra estaciones (H1), si la copa puede iniciarse (H2), humedad con criterio (H3) | define `altura-001`, `fosberg-001` | — | No. El −6 no corrige el clima: m1 GFS y estación difieren < 1 punto. La copa es imposible con CBH 10,5 m en TL8 (§4 loop 0) |
| 1 | Humedad con criterio sobre Alerces 2023 y Epuyén 2025 | `base-001`, `humedad-m6-001`, `fosberg-001` | Alerces 2023: 0,425 (base) contra 0,423 (Fosberg) | No. Fosberg no seca; el −6 es «una perilla de velocidad disfrazada de humedad» (§4 loop 1) |
| 2 | Dirección del viento y ADJ por grupo, sobre los dos chicos; hallazgo de la pendiente invertida | `rotacion-060-001`, `adj-sh-150/200/250-001`, `adj-tu-130-001` | Rotación: Alerces 2023 0,425 → 0,456, Epuyén 0,128 → 0,118. SH ×2,5: 0,481 / 0,241 | No. **Sí se adoptó la corrección de la orientación** (bug): `raster_aligner` v3 y protocolos `-v2` (§4 loop 2) |
| 3 | v2 en los 7: ADJ global y por grupo, CBH × 0,25, paso a la mitad, z0 por dosel | `base-001`, `adj-130-001`, `adj-160-001`, `adj-sh-200-001`, `adj-tu-130-001`, `humedad-m6-001`, `cbh-025-001`, `paso-mitad-001`, `z0-dosel-001` | Tabla por caso en §4 loop 3. Base: 0,457 Alerces 2023; z0 por dosel, peor | No. ADJ por grupo no es identificable con 7 incendios; CBH no inicia copa; el paso está convergido; z0 duplica el WAF |
| 4 | Atlas de WindNinja (v3), canalización por gradiente de presión (sin ELMFIRE), rotación empírica | `viento-atlas-001`, `rotacion-030/045/060-001`, `adj130-rot030/045/060-001` | Media GFS: ADJ 1,3 0,364; + 30°, 0,366 | No. La conservación de masa no encauza; el efecto de la rotación se cancela entre incendios (§4 loop 4) |
| 5 | ADJ uniforme 1,0–1,6 | `adj-110/120/130/140/160-001` | ADJ 1,3: **0,364 / 0,386** GFS, sin alarmas; 1,0: 0,302 / 0,340 con 2 | **Sí, provisional: `adj-130-001`.** CV v3 la elige en los 5 pliegues (0,364 / 0,386) |
| 5b | La receta en los 4 de prueba (no elige) | `base-001`, `adj-130-001`, `humedad-m6-001` | Prueba: base 0,202, ADJ 1,3 0,191 | — (descriptivo) |
| 5c | Ignición ±500 m y ±2 h | `adj-130-001` | Dice ±0,1–0,2 por caso; Epuyén 0,08–0,50 | — (la incertidumbre de la ignición pesa más que la calibración) |
| 6 | Viento ×1,3 / ×1,6; LW 90 / 80 %; LW + ADJ (6d) | `viento-130-001`, `viento-160-001`, `lw-090-001`, `lw-080-001`, `lw-095-001`, `lw095-adj110-001`, `lw100-adj115-001` | Los 7: `lw100-adj115-001` **0,372 / 0,411**, 0 alarmas; ADJ 1,3 0,364 / 0,386 | **Sí: `lw100-adj115-001`, receta final v3.** CV en 5 de 7 pliegues, 0,364 / 0,366. El viento casi no mueve el día 1 (WAF) |
| 7 | Robustez de la receta final a la ignición (21 corridas) | `adj-130-001`, `lw100-adj115-001` | 0,398 contra 0,395 | Se mantiene la final; ADJ 1,3 queda como alternativa conservadora |
| 8 | Crosswalk de plantaciones; viento de estación | `diag-tl8-tu5-001` (protocolo `-v2`), `estacion-v2` | Epuyén 0,291 → 0,344 (TL8 → TU5); con estación, 0,291 → 0,186 | No: diagnósticos. El crosswalk no se calibra y el viento medido no trae el día 1 |
| 9 | Horizonte ±24 h | `base-001`, `adj-130-001`, `lw100-adj115-001` | Tabla en §4 loop 9 | — (sensibilidad: con horizontes cortos todo sub-propaga más; la regla del horizonte decide en Alerces 2023) |

Resultado de la etapa (RESULTADOS-CSS-BAP §5): `lw100-adj115-001`, 0,372 / 0,411 en los 7 contra
0,312 / 0,340 de `base-001`, sin alarmas; en prueba, 0,212 / 0,211.

## 3. Etapa 2: loops A–M (AUDITORIA-FISICA §5)

Protocolos `-v4` (hallazgos 1–3 corregidos), `-v5` (hallazgos 4 y 5) y `-v6` (decisiones del loop L).

| Loop | Qué se probó | Recetas | Calibración | ¿Se adoptó? Por qué |
|---|---|---|---|---|
| A | Banco de pruebas físicas con ELMFIRE real; lectura del fuente | — (`pruebas_fisicas.py`) | — | **Sí, en la causa:** hallazgos 1–3 corregidos, protocolos `-v4` |
| B | Insumos reales sin ELMFIRE; `base-001` v4 en 5 incendios | `base-001` | Sesgo al horizonte ≈ 1 sin calibrar, salvo Alerces 2023 (2,72) | — (el déficit del día 1 que queda ya no es de interfaz) |
| C | ADJ 0,5–1,2 sobre v4; dosel coherente; horizonte de Alerces 2023 a 54 h | `adj-050/070/090/110/120-001`, `base-001`, `lw100-adj115-001`, `dosel-coherente-001` | ADJ 1,1: **0,373 / 0,430**, 0 alarmas; la receta v3 da 2 alarmas | **Sí, candidata: `adj-110-001`** (CV 6 de 7, 0,374 / 0,430). **Sí, el horizonte de 54 h** (la regla de RESULTADOS-CSS-BAP §2.9, aplicada tal cual) |
| D | ERA5 homogeneizado al GFS (×1,3, `-v4w`) | `base-001`, `adj-110-001`, `adj-120-001` | ADJ 1,1 sobre v4w: 0,369 / 0,388 | No. Alerces 2016 no necesitaba viento; a Cholila le falta la explosión |
| E | LW con la física corregida | `lw-100-001`, `lw-095-001`, `lw-090-001` | `lw-100-001`: **0,381 / 0,452**, 0 alarmas | **Sí: `lw-100-001`, receta final.** CV en 7 de 7 pliegues (0,381 / 0,452); robustez 0,460 / 0,480; no necesita ADJ |
| F | ¿La copa era un límite del frente lento? | `cbh-025-001` (diagnóstico) | Cholila 0,255 → 0,528 | No como receta: el dosel no se calibra. Se resolvió con CBH de literatura en el loop L |
| G | Dirección del viento con el modelo a su velocidad | `lw100-rot030-001`, `lw100-atlas-001` | Rotación 0,393 / 0,473 con 1 alarma; atlas 0,380 / 0,480 | No. CV entre 11 recetas: `lw-100-001` en 4 de 7 (0,382 / 0,452) |
| H | Hallazgo 5 (grilla de clima alta) | — (`pruebas_fisicas.py`) | — | **Sí, en la causa** (`write_namelist` rellena el clima) |
| I | Protocolos v5 (hallazgos 4 y 5) | `base-001`, `lw-100-001` | `lw-100-001` v5: 0,381 / 0,451 | Se mantiene. CV 7 de 7 (0,381 / 0,451); los hallazgos mueven ≤ 0,001 por incendio |
| J | Re-medir el documento de combustibles | (fuera de la calibración) | — | — (las conclusiones cualitativas del documento sobreviven) |
| K | Alerces 2015 (prueba, sólo diagnóstico) | `diag-lw100-gr3-nb-001`, `diag-lw100-lenga-nb-001`, `lw100-atlas-001`, `lw100-rot030-001`, `rotacion-060-001`, `altura-001` | — (prueba) | No elige nada: no hay bug, es el viento de ERA5 |
| L | Las decisiones del director (crosswalk, dosel, pavesas) | 28 recetas completas (tabla por palanca en §5 loop L) | Todo junto: **0,440 / 0,501**, 0 alarmas | **Sí, en la causa (protocolo v6):** CBH de literatura, estepa → GR2 y > 1.300 m → NB9, remanente → SH3, sin dosel en la pérdida previa. CV entre las 28: 5 de 7, 0,424 / 0,501. Pavesas y lenga achaparrada → SH3, no |
| M | Alerces 2016, pérdida previa como remanente, supresión, viento diurno | `lw100-perdsh3-001`, `lw100-perdsh2-001`, `lw100-supresion-30/60-001`, `lw100-atlas-001`, `lw100-diurno-002`, `lw100-diurno-dir-001`, `lw100-diurno-vel-001` | `lw-100-001` v6: **0,439 / 0,501**. Mejor alternativa: sólo la velocidad de WindNinja, 0,450 / 0,490 | No. La velocidad de WindNinja baja la mediana y gana casi sólo en Alerces 2016; la supresión empeora; la pérdida como matorral frena Patriada |

Cierre (AUDITORIA §5 loop L y M; `MODELO-V0.md`): `lw-100-001` sobre v6 se promueve como modelo-v0 el
2026-10-04, con 0,439 / 0,501 en calibración, 0,416 / 0,496 en CV y 0,191 / 0,167 en prueba.

## 4. La trayectoria del ADJ

ADJ es el multiplicador uniforme de la velocidad de propagación. Pasó de 1,3 a 1,0 al corregir la
interfaz con ELMFIRE, no por una nueva calibración de la física:

| Momento | Interfaz | Receta | ADJ | LW | Calibración | Fuente |
|---|---|---|---:|---:|---|---|
| Loop 5 | con hallazgos 1–3 (v3) | `adj-130-001` | 1,3 | 110 % | 0,364 / 0,386 (GFS) | RESULTADOS-CSS-BAP §4 loop 5 |
| Loop 6d | con hallazgos 1–3 (v3) | `lw100-adj115-001` | 1,15 | 100 % | 0,372 / 0,411 (los 7) | RESULTADOS-CSS-BAP §4 loop 6 |
| Loop C | corregida (v4) | `adj-110-001` | 1,1 | 110 % | 0,373 / 0,430 | AUDITORIA §5 loop C |
| Loop E | corregida (v4) | `lw-100-001` | 1,0 | 100 % | 0,381 / 0,452 | AUDITORIA §5 loop E |
| Loop L | corregida (v6) | `lw-100-001` = modelo-v0 | 1,0 | 100 % | 0,439 / 0,501 | AUDITORIA §5 loop L |

Lectura (AUDITORIA §5 loop C y §6): con el frente a la mitad (hallazgo 2) y el clima congelado en la
hora de arranque (hallazgo 1), el ADJ 1,15–1,3 compensaba en parte los bugs. Corregida la interfaz, el
ADJ que pide cada incendio ronda 1. El intervalo sin alarmas fue ~[1,1; 1,3] en v3 y ~[1,05; 1,15] en
v4. El LW, en cambio, quedó casi igual: el intervalo sin alarmas fue [95; 110] % en v3 y ~[97; 110] %
en v4 (loop E).

## 5. La corrección de la interfaz: v3 → v4 (AUDITORIA §6)

Dice / sesgo al horizonte. Alerces 2023: v3 a 72 h, v4 a 54 h (entre paréntesis, v4 a 72 h).
⚠ = sesgo fuera de [0,5; 2].

**Calibración:**

| Incendio | Clima | v3 `base-001` | v3 `lw100-adj115-001` | v4 `base-001` | v4 `adj-110-001` | v4 `lw-100-001` | v4 `lw100-adj115-001` |
|---|---|---|---|---|---|---|---|
| Alerces 2023 | GFS | 0,457 / 0,95 | 0,522 / 1,61 | 0,460 / 1,55 (0,477 / 2,72 ⚠) | 0,490 / 1,84 (0,445 / 3,38 ⚠) | 0,495 / 1,82 | 0,487 / 2,47 ⚠ |
| Epuyén 2025 | GFS | 0,160 / 0,44 ⚠ | 0,291 / 0,83 | 0,466 / 1,30 | 0,498 / 1,60 | 0,500 / 1,75 | 0,521 / 2,33 ⚠ |
| Alerces 2024 | GFS | 0,522 / 0,53 | 0,555 / 1,02 | 0,556 / 1,37 | 0,561 / 1,55 | 0,563 / 1,54 | 0,571 / 1,88 |
| Patriada 2026 | GFS | 0,340 / 0,69 | 0,454 / 1,14 | 0,321 / 0,74 | 0,335 / 0,83 | 0,368 / 0,91 | 0,397 / 1,18 |
| Las Golondrinas 2021 (límite) | GFS | 0,029 / 0,05 ⚠ | 0,047 / 0,06 ⚠ | 0,010 / 0,02 ⚠ | 0,013 / 0,02 ⚠ | 0,012 / 0,02 ⚠ | 0,014 / 0,02 ⚠ |
| Alerces 2016 | ERA5 | 0,433 / 0,99 | 0,411 / 1,95 | 0,444 / 1,05 | 0,430 / 1,31 | 0,452 / 1,33 | 0,405 / 1,83 |
| Cholila 2015 | ERA5 | 0,244 / 0,44 ⚠ | 0,324 / 0,66 | 0,255 / 0,44 ⚠ | 0,283 / 0,53 | 0,280 / 0,55 | 0,331 / 0,69 |
| **Media / mediana** | | 0,312 / 0,340 | 0,372 / 0,411 | 0,359 / 0,444 | 0,373 / 0,430 | **0,381 / 0,452** | 0,389 / 0,405 |
| **Alarmas** | | 2 | 0 | 1 | 0 | **0** | 2 |

**Prueba** (no se usó para elegir): v3 `base-001` 0,202 / 0,162; v3 `lw100-adj115-001` 0,212 / 0,211;
v4 `base-001` 0,209 / 0,191; v4 `adj-110-001` 0,204 / 0,203; v4 `lw-100-001` 0,213 / 0,220.

**Qué movió cuánto** (media de calibración, AUDITORIA §6):

| Cambio | Efecto |
|---|---|
| Hallazgos 1 + 2, `base-001` v3 → v4 | +0,05 de media, +0,10 de mediana; Epuyén +0,31 |
| Horizonte de Alerces 2023 a 54 h | sesgo de base 2,72 → 1,55 |
| LW 110 → 100 % (ADJ 1) | +0,022 de media, +0,008 de mediana |
| ADJ 1,0 → 1,1 | +0,014 |
| La receta v3 sobre v4 | +0,016 de media, con dos alarmas |
| Dosel coherente | ±0 de media |
| ERA5 ×1,3 | −0,004 |

Después de v4, el protocolo v6 (loop L) llevó `lw-100-001` de 0,381 / 0,451 (v5) a 0,439 / 0,501.
Es el salto más grande de la etapa, y viene de decisiones de crosswalk y dosel, no de la receta.

## 6. Qué cubre la validación cruzada

El 0,416 / 0,496 fuera de muestra de modelo-v0 (`benchmarks/modelos/modelo-v0.json`, `resultados.
validacion_cruzada`) **cubre sólo la elección final entre 5 recetas**. Son las completas en los siete
casos v6 al 2026-10-04: `base-001`, `lw-100-001`, `lw100-atlas-001`, `lw100-supresion-30-001` y
`lw100-supresion-60-001` (ESTADO §3).

**No cubre el camino de decisiones que se tomaron mirando la calibración:**

- la elección de LW 100 % entre 90, 95, 100 y 110 % (loop E);
- el abandono del ADJ, que se decidió en los mismos siete incendios (loops 5, 6, C y E);
- el horizonte de 54 h de Alerces 2023 (loop C);
- y sobre todo las decisiones del loop L, que eligieron entre 28 recetas mirando la calibración y
  después pasaron al protocolo v6 como datos de entrada. Ahí están el CBH de literatura, la estepa a
  GR2 y NB9, el remanente a SH3 y la pérdida previa.

Desde el loop L, esas decisiones son parte de los casos, no de la receta, así que ninguna validación
cruzada sobre v6 las vuelve a poner a prueba. Varias tienen respaldo externo: el CBH de literatura,
las mediciones regionales de LW (Bianchi y Defossé) y la regla del horizonte, fijada antes del primer
barrido. Pero la cifra de calibración (0,439) y la de CV (0,416) se deben leer como optimistas
respecto de un incendio nuevo. La medida sin ese sesgo de selección es la de prueba (0,191): se miró al cerrar cada
etapa, pero no se usó para elegir nada (RESULTADOS-CSS-BAP §4 loop 5b; AUDITORIA §5 loop L).
