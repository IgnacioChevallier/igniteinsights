# IGN-26 · Diseño de validación

> Estado: **harness B implementado y ejecutado** (2026-09-16); harness A pendiente.
> El diseño es la única parte viva de la auditoría del 2026-08-31, extraída de
> `docs/historico/SIMULATION_AUDIT.md` §12 el 2026-09-15.
>
> Implementación: `scripts/score_against_observed.py`. Lleva las 196 máscaras de Sentinel-2
> a la grilla de la corrida —y no al revés, porque puntuar a 20 m inventaría una resolución
> que el modelo no tiene—, descuenta la semilla y estratifica por `pct_quemado`.
>
> Se conserva la numeración original (§12.1 … §12.5) porque el resto de los planes la citan
> con esos números. Bloquea: `ETAPA-A §A7` (congelar el baseline) y `ETAPA-B §B6`
> (comparación de mapas de combustible contra el perímetro observado).

## Resultado del harness A (2026-09-19)

Diez ventanas de 24 h repartidas en las cinco semanas de actividad del incendio, tres mapas
de combustible cada una: **30 corridas**. Semilla: todas las detecciones FIRMS hasta T0.
Referencia: las detecciones nuevas de (T0, T1] fuera de la semilla. Dominio recortado al
frente activo. Reproducible con `scripts/harness_a.py`.

### Agregado sobre las diez ventanas

| Mapa | Recall | Recall cercano | Precisión | IoU | Acierto |
|---|---|---|---|---|---|
| WorldCover 2021 (baseline) | 0,162 | 0,222 | 0,033 | 0,028 | 6.445 ha |
| MapBiomas 2024 | 0,283 | 0,387 | **0,068** | **0,058** | 11.253 ha |
| **CCS-BAP 2017** | **0,342** | **0,467** | 0,048 | 0,044 | **13.587 ha** |

*Recall cercano*: restringido a la referencia dentro de 5 km de la semilla, que es el alcance
físico del frente en 24 h. Las detecciones más lejos son igniciones nuevas, y un modelo de
propagación no predice dónde se inicia un foco.

### Recall por ventana: el orden se repite

| Ventana | WorldCover | MapBiomas | **CCS-BAP** |
|---|---|---|---|
| 06-01 | 0,030 | 0,090 | **0,099** |
| 08-01 | 0,181 | 0,432 | **0,488** |
| 09-01 | 0,133 | 0,157 | **0,201** |
| 20-01 | 0,180 | 0,432 | **0,546** |
| 24-01 | 0,142 | 0,355 | **0,458** |
| 25-01 | 0,104 | 0,294 | **0,315** |
| 31-01 | 0,729 | 0,740 | **0,937** |
| 01-02 | 0,438 | 0,494 | **0,671** |
| 06-02 | 0,793 | 0,981 | **1,000** |
| 07-02 | 0,794 | 0,556 | **0,952** |

**CCS-BAP tiene el mayor recall en las diez ventanas**, y los dos mapas patagónicos superan
al baseline en nueve de diez. Que el orden se repita ventana por ventana es lo que convierte
el resultado de §6.1 en algo más que una corrida afortunada.

### La salvedad que limita la lectura: el modelo sobre-propaga

| Ventana | Referencia | Predicho (CCS-BAP) | Veces la referencia |
|---|---|---|---|
| 06-01 | 12.318 ha | 3.135 ha | 0,3× |
| 08-01 | 6.032 ha | 10.286 ha | 1,7× |
| 09-01 | 4.979 ha | 10.102 ha | 2,0× |
| 20-01 | 1.951 ha | 21.900 ha | 11,2× |
| 25-01 | 6.447 ha | 36.177 ha | 5,6× |
| 31-01 | 1.454 ha | 41.700 ha | 28,7× |
| 01-02 | 3.711 ha | 73.280 ha | 19,7× |
| 06-02 | **63 ha** | 28.875 ha | **458×** |
| 07-02 | 260 ha | 27.850 ha | 107× |

**Un recall alto se consigue quemando de más.** El 6 de febrero CCS-BAP alcanza recall 1,000
prediciendo 28.875 ha contra una referencia de 63 ha: el número no significa nada. A partir
del 20 de enero, cuando la semilla ya es grande, las tres corridas se desbocan.

Consecuencias, en orden de importancia:

1. **Las ventanas interpretables son las tres primeras** (06, 08 y 09 de enero), donde lo
   predicho está entre 0,3 y 2 veces la referencia. También ahí CCS-BAP gana en las tres.
2. **El recall agregado favorece al mapa que más superficie predice**, y CCS-BAP predice
   282.164 ha contra 166.079 ha de MapBiomas en total. Por eso MapBiomas gana en IoU y en
   precisión: equilibra las dos caras. **No hay un ganador único, y la tesis debe decirlo
   así.**
3. **Falta modelar la supresión.** Los incendios reales se combaten; ELMFIRE corre sin
   extinción, así que una corrida libre de 24 h con una semilla grande no tiene nada que la
   frene. Es la explicación más simple de un factor 100, y está sin representar en todo el
   pipeline.
4. `ADJ` sigue en 1,0 uniforme, o sea sin calibrar (`PENDING_PARAMETERS` §1.3). Calibrarlo es
   lo que corresponde **después** de la comparación de combustibles, y este resultado es
   precisamente la evidencia de que hace falta.

### Qué sigue

1. Modelar o acotar la supresión, o restringir la validación a ventanas de crecimiento libre
   —las primeras de cada pulso— donde el supuesto de no intervención se sostiene.
2. Recién después, calibrar `ADJ` contra estas mismas ventanas.
3. La duración completa del incendio (37 días encadenados) sigue pendiente: ~50 h de cómputo.

---

## Resultado (2026-09-16)

Primera comparación de los tres mapas de combustible contra el perímetro observado, que es
la pregunta que la Etapa B vino a responder.

**Configuración.** AOI definitivo (2.563 × 3.222), incendio del 1-2 de febrero de 2026,
ignición 2026-02-02 19:46 UTC, 12 h de horizonte, 13 bandas horarias de meteorología,
`SIMULATION_TSTART` anclado al reloj, humedad viva medida (`LH` 30 %, `LW` 110 %). Lo único
que cambia entre corridas es `fbfm40.tif`. Semilla FIRMS: 17.747 ha, idéntica en las tres.
Los tiles de Sentinel-2 cubren el 46,2 % del dominio y dentro de esa cobertura la cicatriz
observada es de 76.178 ha.

| Mapa | IoU | Recall | Precisión | Acierto | Falso positivo | No predicho |
|---|---|---|---|---|---|---|
| WorldCover 2021 (baseline) | 0,036 | 0,043 | 0,182 | 2.827 ha | 12.697 ha | 62.896 ha |
| MapBiomas 2024 | 0,045 | 0,048 | **0,412** | 3.175 ha | 4.537 ha | 62.549 ha |
| **CCS-BAP 2017** | **0,067** | **0,082** | 0,267 | **5.362 ha** | 14.715 ha | 60.362 ha |

Estratificado por `pct_quemado`, que es donde el número informa (§12.4):

| Banda | Tiles | IoU WorldCover | IoU MapBiomas | **IoU CCS-BAP** |
|---|---|---|---|---|
| 0-10 % | 96 | 0,035 | 0,044 | 0,048 |
| 10-40 % | 62 | 0,029 | 0,043 | 0,053 |
| 40-70 % | 27 | 0,039 | 0,045 | 0,070 |
| **70-100 %** | 11 | 0,047 | 0,051 | **0,101** |

### Qué dice

**El mapa patagónico predice mejor que el baseline**: IoU 0,067 contra 0,036, casi el doble,
y en los tiles con más del 70 % de superficie quemada —los que contienen el borde real del
fuego— la diferencia se agranda a 0,101 contra 0,047. Es el resultado que hace falsable la
Etapa B en vez de asertiva.

MapBiomas se queda en el medio en IoU pero **gana en precisión** (0,412): predice poco y lo
que predice cae adentro. CCS-BAP predice más, acierta más en términos absolutos (5.362 ha
contra 3.175) y también se equivoca más (14.715 ha de falso positivo). Cuál de los dos
comportamientos es preferible depende de para qué se use el sistema, y conviene decirlo así
en la tesis en vez de declarar un ganador único.

### Qué NO dice

**Los valores absolutos son bajos y no miden la calidad del modelo.** Es §12.2 en acción: la
referencia es la cicatriz final de todo el período febrero-marzo y la corrida es de 12 h, así
que el recall está acotado por construcción. Las ~62.000 ha "no predichas" son sobre todo
tiempo de simulación que no existió, no error del modelo. **Lo comparable es el orden entre
mapas, no la magnitud.**

Además: es **un incendio y una ventana**. Para que esto sea un resultado de tesis y no una
anécdota hace falta repetirlo sobre varias ventanas y, si se puede, sobre más de un incendio.

### Lo que falta

1. Correr con la **duración real del incendio**, no 12 h, para que el recall deje de estar
   acotado. Requiere meteorología que cubra ese horizonte.
2. Barrer varias ventanas (`Δ` ∈ {6, 12, 24} h del harness A) y reportar cuántas resultan
   puntuables, que es en sí un resultado.
3. Recién después, calibrar `ADJ` (IGN-25). Antes no: absorbería el error del combustible y
   haría desaparecer justamente esta diferencia.

---

## 12. Validation design

Working through the approach proposed on 2026-08-31: *"validation will work with just
the final footprint … prediction starting from 4 hrs before, 8 hrs before and so on,
seeing the accuracy (false positives and false negatives, true positives)"*, with 4/8 h
windows chosen because they are the closest we get to a valid `phi.tif` given satellite
revisit gaps.

The instinct is right and it lands on the existing **IGN-26** (IoU gate). Two structural
constraints shape it.

### 12.1 The one metric decision that decides whether the number means anything

**Score only the cells NOT in the initial `phi`.** Never the union.

From §1: 84% of what a run reports as burned is the FIRMS seed. If TP/FP/FN are computed
over the whole footprint, the seed dominates and you get a flattering IoU that mostly
measures *"does the FIRMS perimeter match the burn scar"* — which it does by
construction, and which says nothing about ELMFIRE. On the run in §1 that would report
IoU ≈ 0.8-ish while the model contributed 16% of the area.

Mask out the seed and score the **growth annulus only**. Expect a much lower and much
more honest number. This is the single most important line in the harness.

### 12.2 The Sentinel-2 mask is a final scar, so it can't score a 4 h window

A pre/post dNBR mask is one observation covering the whole `fecha_pre` → `fecha_post`
interval. There is no observed footprint *at* T+4 h to compare a 4 h run against. So the
4/8/12 h idea needs a different reference than the Kaggle mask. Two harnesses, testing
different things:

**A. Time-resolved skill — reference is FIRMS itself (no Sentinel-2 needed).**
Build `phi` from detections ≤ T−Δ, run Δ hours, and ask whether the newly-predicted
burned cells cover the detections that appeared in (T−Δ, T].
- Gives exactly the 4/8/12 h accuracy the proposal describes, at the horizon the product
  actually claims.
- **Recall is trustworthy; precision is not.** A predicted cell with no detection may be
  a false positive *or* an overpass/cloud gap — the very gap noted in the proposal.
  Report recall as the headline and treat precision as a loose upper bound on error.
- **Δ = 4 h will often have zero new detections.** VIIRS gives ~2 overpasses/day per
  platform. Δ = 12 h is the natural cadence; 4 h mostly produces empty reference sets.
  Suggest sweeping Δ ∈ {6, 12, 24} and reporting how many windows were scorable at all —
  that count is itself a result worth publishing.

**B. Total-extent skill — reference is the Sentinel-2 scar (the independent one).**
Seed from the earliest detections, run the full fire duration, compare final footprint
against the mosaicked mask. IoU / Dice + the TP/FP/FN split.
- This is the only **independent** check. FIRMS is not independent — it built `phi`.
- Blocked on §2.3: a multi-day run on a single frozen weather band is indefensible.
  **Multiband weather (IGN-11's own unmet criterion) is a prerequisite for B**, not
  optional polish.

Run A first — it needs nothing new. B is the thesis gate.

### 12.3 Why this serves the fuels contribution

B gives the objective function: IoU(baseline WorldCover crosswalk) vs IoU(Patagonian
fuel map). That is what makes IGN-20/21/22 falsifiable rather than asserted, and it is
the number that belongs in the thesis. Tune ADJ (IGN-25) *after* the fuels comparison,
never before — otherwise ADJ absorbs the fuel error and the fuels result vanishes.

### 12.4 Stratify by `pct_quemado`

The dataset is tiled with a per-tile burned fraction. Tiles near 0 or 1 are trivially
predicted and will inflate any aggregate score. **The informative tiles are the
partial-burn ones containing the actual fire edge.** Report stratified by
`pct_quemado` band, not just pooled.

### 12.5 Dataset characterised (2026-08-31)

All open questions answered from `../mask-dataset-gen`. Full parameter list in
`PENDING_PARAMETERS.md` §5.

| | |
|---|---|
| Masks | `dataset/mascaras/tile_NNN.tif`, uint8 `{0,1}`, **separate files**, 196 tiles 257×257 |
| Imagery | 6 bands (B2,B3,B4,B8,B11,B12) float64, pre and post separately |
| CRS | **EPSG:4326** @ 0.00017966° (~20 m) — needs a warp to EPSG:32719 30 m |
| `escala_m` | 20 (Sentinel-2 SWIR native) |
| Method | dNBR = NBR_pre − NBR_post, threshold **0.30**, with snow/water/cloud rejection |

**Three findings that change the harness design:**

1. **The pre-fire window is 2023-11-01 → 2023-12-31 — 26 months before the fire.** The
   mask captures everything that changed between Dec 2023 and Mar 2026, not just the
   Feb 2026 fire. That is an unquantified false-positive floor on any IoU. The
   generator's own README claims 2025-11/12 instead; code and shipped `metadata.csv`
   both say 2023. **Resolve this before computing any accuracy number.**
2. **Post window is 2026-02-01 → 2026-03-08 (5 weeks).** Confirms §12.2: this is a final
   scar. Harness B measures total extent, never rate.
3. **Only 70 of 196 tiles intersect the simulation AOI** (50 with >1% burned). The
   dataset spans lat -42.818…-42.079 while the AOI stops at -42.5. Either widen the AOI
   or scope the claim.

Also: `pct_quemado` is a **percent 0-100** (max 88.14), not a fraction — 58 tiles are
under 1% burned and will dominate any pooled metric. Stratify (§12.4).

### 12.6 Still needed

1. **`fecha_pre` / `fecha_post` values** — if that interval is weeks, harness B measures
   the fire's total extent and nothing about rate; if it is days, rate is recoverable.
2. **`escala_m`** — 10 or 20 m, for aggregation onto the 30 m grid.
3. **CRS of the `.tif`s** — EPSG:32719 makes this trivial; EPSG:4326 needs a warp.
4. **Mask layout** — separate mask `.tif`s, or a band inside each tile?
5. **Fire date window** — to re-ingest FIRMS and the matching GFS cycles (and to clear
   the §2.8 weather/fire coherence warning).

The dataset could not be read from this session: no Kaggle CLI or credentials on this
machine, the download URL 404s unauthenticated, and `visionArtificial` is not on disk
(only a Cursor project reference at `~/.cursor/projects/Users-ichevallier-Projects-visionArtificial`,
implying it lived at `~/Projects/visionArtificial`).

---

