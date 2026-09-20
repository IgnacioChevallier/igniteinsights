# End-to-end simulation audit

> **ARCHIVADO el 2026-09-15.** Registro histórico: auditoría de una corrida real del
> 2026-08-31. Casi todos sus hallazgos se resolvieron en la Etapa A. Su §12 (diseño de
> validación) era la única parte viva y se movió a `IGN-26-VALIDACION.md`.
> Se conserva porque es la evidencia que motiva la Etapa B y se cita en la tesis.

**Date:** 2026-08-31
**Scope:** ingestion → preparation → ELMFIRE → postprocessing → dashboard, plus a
"Done vs. actually implemented" comparison against the Linear thesis project.
**Method:** code read + numerical inspection of a real run on disk.

**Run inspected**
- inputs: `data/elmfire/inputs/cbe60579-5adc-4007-8dfd-a424380610b9/`
- outputs: `data/elmfire/outputs/30bb0a15-019a-4c6d-8b8e-3e753a015257/`
- 12 h horizon, `DTDUMP=3600`, `DT_METEOROLOGY=3600`, EPSG:32719 @ 30 m, domain 1414×1525

---

## 1. Verdict on the tight isochrones

**The map is drawing the model output faithfully. The model is the thing that is
wrong — or at least, is being asked a question it cannot answer honestly.**

The isochrones are packed together because the fire barely moves. They are not a
rendering artifact.

### The numbers

| Quantity | Value |
|---|---|
| FIRMS-derived ignition perimeter (`phi < 0`) | 73,514 cells = **6,616 ha** |
| Total burned at t=12 h (`time_of_arrival` valid) | 87,476 cells = **7,873 ha** (19,454 ac — matches `fire_size_stats.csv`) |
| **Newly burned in 12 h** | 13,962 cells = **1,257 ha** |
| Share of the painted "fire" that is the input, not the prediction | **84%** |
| Separate ignition polygons | **26** (matches the 26 rings on screen) |

Median distance a cell burns from the initial perimeter, by arrival hour:

```
h= 0  median   60 m   p90  180 m   max   330 m
h= 1  median   90 m   p90  360 m   max   690 m
h= 3  median  120 m   p90  450 m   max   750 m
h= 6  median  120 m   p90  450 m   max  1020 m
h= 9  median  120 m   p90  510 m   max  1110 m
h=11  median  150 m   p90  600 m   max  1200 m
```

**The median does not move.** Hour 1 burns 90 m out; hour 11 burns 150 m out. Only
the tail advances (330 m → 1200 m, ≈ 1.7 m/min in the fast fingers). The bulk of a
100+ km fire front is effectively stalled.

Measured directly against the isochrone vertices:

- **87.3%** of all 72,698 isochrone vertices lie **within 150 m (5 pixels)** of the
  ignition perimeter. Median distance: **30 m — one pixel.**
- 94.9% within 300 m.

So all twelve hourly contours are stacked inside a ~5-pixel band hugging the FIRMS
concave hulls. **What you are looking at on the map is the ignition perimeter,
redrawn twelve times.** That is exactly the visual in the screenshot.

ELMFIRE's own spread-rate raster confirms it independently:

```
vs_*.tif   (spread rate)      median 0.39   p90 8.5    p99 31.9   max 145.6
flin_*.tif (fireline int.)    median 4.6    p90 168    p99 918    max 8279  kW/m
```

A median fireline intensity of **4.6 kW/m** is a smouldering creep. The distribution
is extreme: the median cell is not really burning, a small tail is running hard.

---

## 2. Why the fire barely spreads

Ranked by how much each one is costing you. **None of these are ELMFIRE bugs — ELMFIRE
is behaving correctly given the inputs it is handed.**

### 2.1 The fuel crosswalk maps 60% of the park to a near-inert litter model

`app/elmfire/builder/fuels_builder.py:19-31` maps WorldCover *Tree cover* → **FBFM 183
(TL3, "Moderate Load Conifer Litter")**.

Actual distribution in the run:

| FBFM | Model | Share |
|---|---|---|
| **183** | **TL3 conifer litter** | **59.7%** |
| 102 | GR2 low-load dry grass | 17.1% |
| 93 | NB3 bare (unburnable) | 15.3% |
| 98 | NB8 water (unburnable) | 7.7% |
| 145 | SH5 high-load dry shrub | 0.04% |

TL3 is a surface-litter model with no live/shrub component and very low wind response.
Combined with a median canopy cover of **89%** (`cc.tif`), the midflame wind reduction
crushes what little wind sensitivity it has. It is the canonical "why won't my fire
spread" fuel model.

Los Alerces is *Nothofagus* / *Austrocedrus* forest with a heavy understory and standing
dead — closer to **TU5 (165)** "very high load, dry-climate timber-shrub", or a
shrub model where the understory dominates. Meanwhile **shrubland is 0.04%** of the
map, which for Patagonian matorral is not credible; the WorldCover classification is
collapsing understory into "tree cover".

Also: **23% of the AOI is unburnable** (NB3 + NB8). Whether that much of the park is
genuinely bare rock/water or whether WorldCover class 60 is over-assigned at 10 m is
worth a spot check — it is chopping the front into fragments.

**This is the single biggest lever on the result — and per the decision in §10 it is
the thesis contribution, not a defect.** The current crosswalk is the *baseline* a
Patagonian fuel-model map has to beat; §2.1 is the motivation section, and the numbers
above (59.7% TL3, 0.04% shrub, median FLI 4.6 kW/m) are the quantified statement of
why WorldCover-derived fuels are inadequate here.

### 2.2 Fuel moisture is equilibrium moisture, with no burning-period correction

`weather_builder.derive_moisture` (`app/elmfire/builder/weather_builder.py:55-82`) runs
Nelson (1984) EMC straight off GFS 2 m T/RH and writes it as `m1`.

Actual values: **m1 median 11.1%, mean 11.9%, max 21.5%**.

Two problems:

1. Equilibrium moisture is not burning-period fine fuel moisture. On an afternoon fire
   run, 1-h dead fuels sit at **4–8%** — sun-exposed, wind-ventilated, well below the
   air's equilibrium. Feeding 11% into TL3 (moisture of extinction 20%) puts you deep
   into the damped regime. There is no diurnal, solar-exposure, slope/aspect or
   drying-history correction anywhere in the pipeline.
2. `m10 = emc + 2` and `m100 = emc + 5` (lines 75-76) are **invented offsets**. Time-lag
   classes are damped toward a running mean, not offset upward from the instantaneous
   equilibrium. There is no source for +2/+5; it is a placeholder wearing a citation.

### 2.3 Weather is a single frozen snapshot for the whole horizon

Every weather raster on disk has **`bands=1`**:

```
ws: bands=1   wd: bands=1   m1: bands=1   m10: bands=1   m100: bands=1
```

But the namelist declares `DT_METEOROLOGY = 3600.0`, which per
`.claude/skills/elmfire/references/interface-gotchas.md` means *"one band per hour,
ELMFIRE interpolates between them."* The pipeline emits a 1-band raster and tells
ELMFIRE it is an hourly time series.

Consequence: the 12 h run uses one instant of weather throughout. There is **no diurnal
cycle** — no afternoon wind peak, no RH minimum, no evening recovery. Those are precisely
what drive Patagonian fire runs. A 12 h forecast that cannot represent 14:00 differing
from 02:00 cannot produce a realistic 12 h isochrone series.

> Behaviourally this appears to clamp to band 1 rather than fail (spread continues at a
> steady ~1,100 cells/hour for all 12 hours). But it is a documented interface mismatch
> and should not be left to luck. Confirm against upstream `elmfire_io.f90`.

This is one of the two gaps in §7.1 that genuinely matter, and it is a **prerequisite
for validation harness B** (§12.2) — a multi-day run on one frozen weather band cannot
be defended.

### 2.4 ADJ — the calibration knob — is pinned at 1.0

`app/preparation/service.py:80-83` writes a uniform `adj.tif = 1.0`. Verified on disk:
min 1.0, max 1.0.

`ADJ` is ELMFIRE's spread-rate adjustment factor: the intended place to tune a model
against observed fire behaviour for a region. It is the one knob designed for exactly
the calibration problem this pipeline has, and it is unused. For a thesis, a
per-fuel-model ADJ tuned against a known Los Alerces burn is defensible and cheap.

### 2.5 Wind: 10 m wind fed in where ELMFIRE expects 20-ft wind

`derive_wind` computes `sqrt(u10² + v10²)` from GFS **10 m** wind and writes it to
`ws.tif`. ELMFIRE follows the LANDFIRE/US convention, where `WS` is conventionally
**20-ft (6.1 m)** wind. 10 m → 20 ft is roughly ×0.87.

✅ **Confirmed** — no longer an open question. Linear **IGN-11**'s own accepted criterion
reads *"La conversión de viento de 10 m a 20 pies está correctamente implementada"*, and
it is ticked. So the project already established that ELMFIRE wants 20-ft wind; the
conversion was simply never written. See §7.1.

Note the sign: this makes the current wind ~15% *too high*, so it is not a cause of the
slow spread — but it is a correctness gap, and it is an accepted criterion that is false.

Secondary: `ws.tif` is written as **Int16 mph** (`weather_builder.py:49`), quantizing to
±0.45 m/s. Values on disk: min 0, max 13, median 7 mph. Sloppy but not decisive.

### 2.6 The run is not anchored to wall-clock time

`fire_size_stats.csv` reports `Start timestamp 1970-01-01 00:00`.

- `namelist_writer` writes `SIMULATION_TSTART = 0.0` and there is no real-world clock
  anywhere in the namelist.
- `preparation.run_preparation` computes `ignition_datetime` from the newest FIRMS
  detection (`service.py:157-159`), `POST /simulations/run` accepts it, and
  `SimulationRun.ignition_datetime` stores it — **and then nothing uses it.** It never
  reaches the namelist, and weather bands are never aligned to it.

So "the prediction for today" has no defined start instant. Combined with 2.3, the
simulation cannot express *when* in the day it is running, which is most of the physics.

### 2.7 Crown fire is enabled by omission

The namelist never sets `CROWN_FIRE_MODEL`. Per the skill reference, ELMFIRE defaults it
**on**. The run reports 696.8 ac of crown fire out of 19,454 ac. That is probably what
you want — but it is currently on by accident, not by decision, and `cbh`/`cbd` are
derived from the FBFM lookup rather than measured, so the crown-fire threshold rests on
the same crosswalk flagged in 2.1.

### 2.8 The weather/fire coherence guard is advisory only

`preparation.run_preparation` (`service.py:161-184`) correctly detects a fire/weather
period mismatch >48 h and returns it in `warnings`. But:

- the warning is returned only in the `POST /ingestion/run` response;
- `POST /simulations/run` takes a bare `inputs_dir` and never re-checks it;
- nothing is persisted on `SimulationRun`.

A stale or mismatched prep can be simulated with no visible warning anywhere, and the
resulting isochrones look exactly like a valid run.

---

## 3. A real bug: the isochrone hour labels are wrong

Independent of the physics, `arrival_hours` — the value the map colours by — is broken.

`app/postprocessing/isochrone_converter.py:36-63` recovers each contour's time by
sampling `time_of_arrival_*.tif` at the **midpoint vertex** of the line. The module
docstring is honest about why: the runner's `gdal_contour` call passes no `-a`, so the
level is not stored on the feature.

Measured on the real output, replicating the API's exact sampling:

| Check | Result |
|---|---|
| Features | 8,498 |
| Expected distinct arrival values (12 hourly levels) | ~12 |
| **Actually recovered distinct values** | **1,032** |
| **Fraction landing on a true hour boundary** | **19.6%** |
| **Features labelled `arrival_hours = 0.0`** | **1,324 (15.6%)** |

Root cause: a contour line runs *along the boundary between* two cells. `ds.index()`
floors the coordinate into one of them, and because the contours hug the ignition
perimeter (§1), that cell is frequently a `TOA = 0` interior cell. Result: 1 in 6 late-hour
contours is labelled "arrives immediately" and painted pale yellow. Adjacent contours get
scrambled colours — that is the speckled red/orange/yellow interleaving on the map.

**The fix is a deletion, not an addition.** Have the runner emit the level as an
attribute:

```
gdal_contour -a arrival_s -i <DTDUMP> time_of_arrival_*.tif hourly_isochrones.shp
```

Then delete `enrich_with_arrival_time` entirely and read the attribute. That is one flag
in `elmfire-runner/app/runner.py` and ~30 lines removed here. Per the skill reference,
this is expected: *"if isochrone output is ever wrong, the bug is in the runner's
gdal_contour invocation."*

---

## 4. Other findings, ranked

| # | Finding | Location | Severity |
|---|---|---|---|
| 1 | Isochrone hour labels wrong (§3) | `isochrone_converter.py:36-63` | **High** — visibly wrong output |
| 2 | Prediction is indistinguishable from input on the map (§1) | API + `fire-map.tsx` | **High** — 84% of the drawn fire is the FIRMS perimeter with no separate styling or label |
| 3 | Fuel crosswalk 60% TL3 (§2.1) | `fuels_builder.py:19-31` | **High** — dominant physical lever |
| 4 | Single-band weather vs `DT_METEOROLOGY=3600` (§2.3) | `weather_builder.py` + `namelist_writer.py:115` | **High** — interface mismatch |
| 5 | `m10 = emc+2`, `m100 = emc+5` invented (§2.2) | `weather_builder.py:75-76` | **Medium** |
| 6 | `ignition_datetime` accepted, stored, never used (§2.6) | `simulations.py:102`, `namelist_writer.py` | **Medium** — misleading API surface |
| 7 | Coherence warning never reaches the simulation (§2.8) | `simulations.py:82-131` | **Medium** |
| 8 | 4 MB GeoJSON, 8,498 unaggregated LineStrings per request | `simulations.py:232-253` | **Medium** — measured payload; no hour filter, no simplification, re-read from shapefile every call |
| 9 | `enrich_with_arrival_time` assumes LineString | `isochrone_converter.py:49` | **Low** — `coords[len//2]` throws on MultiLineString |
| 10 | `adj.tif` missing from `EXPECTED_ELMFIRE_INPUTS` | `dashboard.py:14-30` | **Low** — dashboard reports `ready: true` with `adj.tif` absent, though the namelist references it |
| 11 | Test coverage thin | `tests/` | **Medium** — `ignition_builder`, `perimeter_reconstruction`, `weather_builder`, `fuels_builder` still untested; that is where the physics lives. (`isochrone_converter` now covered — see §11.) |
| 11b | **CI never runs the tests** | `.github/workflows/*.yml:16-20` | **Medium** — the workflow runs `ruff check app/` and `mypy app/` and stops. No `pytest` step, and `tests/` is outside the lint path, so a broken test is invisible to CI. |
| 12 | `SimulationOutput.geom` (MULTIPOLYGON) never populated | `repository.py:269-288` | **Low** — documented in the docstring; isochrones are LineStrings so the column can't hold them. Dead column. |
| 13 | TOA overlay min-max normalized over a range dominated by zeros | `raster_overlay.py:59-67` | **Low** — 84% of pixels are exactly 0, so the overlay is one flat colour over the ignition area |
| 14 | **Static topo cache silently defeats code fixes** | `raster_aligner.py:31-37` | **High** — `data/static/{dem,slp,asp}.tif` are stale float32 from 12 May while the code writes int16; regeneration is skipped whenever the files exist, and the stale copy propagates into every inputs folder. No cache-invalidation key. See §7.4. |

### Checked and found correct

- `_signed_distance` L1 transform (`ignition_builder.py:128-155`) — verified numerically
  against exact L1 on a synthetic case, **max error 0.0**. Not a bug.
- The `PHI0 < -1.1` clamp (`_PHI_IGNITION_FLOOR = -1.0`) is correctly applied; verified
  `phi.tif` has 73,514 cells at exactly -1.0 and no interior cell below the floor.
- `resolve_dtdump_s` clamping, and `simulations.py` forwarding the *resolved* value to the
  runner — correct, matches the documented gotcha.
- Raster basenames are extensionless in the namelist — correct.
- Canopy Int16 scaling (`ch` ×10, `cbh` ×10, `cbd` ×100, `cc` plain percent) — correct
  in code, verified on disk (`ch` max 536 = 53.6 m, `cc` max 100).
- Ignition perimeter reconstruction: 26 polygons, 6,614 ha — consistent with the module's
  stated calibration and with the 26 rings visible on the map.
- Fire detection dedup + unique constraint — implemented (`models.py:78-88`, migration 0003).

---

## 5. Documentation drift

`CLAUDE.md` says: if a doc disagrees with `namelist_writer.py`, trust the code and fix
the doc. **`docs/elmfire-mapping.md` has drifted again** — five errors, all in the units
section:

| `docs/elmfire-mapping.md` claims | Code actually does | Verified on disk |
|---|---|---|
| `ws.tif` **(km/h)**: `sqrt(u²+v²) × 3.6` | **mph**: `× 2.23694` (`weather_builder.py:43`) | — |
| `cc.tif` **(fracción 0–1)**, `scale_factor=0.01` | percent 0–100, `scale_factor=1.0` (`service.py:202-209`) | `cc` max = **100** ✗ |
| `ch.tif` **(metros)** | 10×metres, `scale_factor=10.0` (`service.py:221`) | `ch` max = **536** ✗ |
| `cbh.tif` **(metros)** | 10×metres (`canopy_builder.py:19-29`) | `cbh` max = **15** ✗ |
| `cbd.tif` **(kg/m³)** | 100×kg/m³ (`canopy_builder.py:31-41`) | `cbd` max = **20** ✗ |

The mapping table row for Hansen GFC also says "scale ×0.01", same error. The WorldCover
crosswalk table is missing three classes the code has: **70** (snow/ice → NB3), **95**
(mangroves → TL3), **100** (moss/lichen → GR1).

`docs/architecture.md` is accurate as far as checked.

---

## 6. What is actually implemented

Inventory for the Linear comparison in §7.

### Fully implemented and verified working

- **FIRMS ingestion** — VIIRS NOAA-20, historical `start_date`, normalizer, dedup +
  DB unique constraint (migration 0003).
- **DEM ingestion** — OpenTopography COP30, idempotent, cached.
- **GFS ingestion** — Herbie, u10/v10/t2m/rh, live + historical cycles, `valid_time`
  on `RasterAsset` (migration 0002).
- **WorldCover ingestion** — COG windowed reads, multi-tile merge, idempotent.
- **Canopy ingestion** — Hansen GFC (cc) + ETH height (ch).
- **Preparation orchestration** — auto-runs at the end of `POST /ingestion/run`,
  produces all 16 ELMFIRE inputs + namelist, reports `generated`/`missing`/`warnings`.
- **All 6 builders** — topo, fuels, weather, canopy, ignition, namelist.
- **Perimeter reconstruction** — dedup → single-linkage clustering → concave hull;
  well-documented and calibrated against real Los Alerces data.
- **Namelist writer** — with structural validation and `DTDUMP` clamping.
- **Runner HTTP client** — typed errors, horizon-aware timeout.
- **API** — fires, ingestion (per-source + combined), simulations (run/status/isochrones/
  stats/rasters), dashboard summary.
- **Frontend** — MapLibre dashboard, satellite/street basemaps, active fires, isochrones,
  TOA + FLIN raster overlays, growth-stats panel.
- **Infra** — Docker Compose, Alembic ×3, CI, Railway deploy.

### Implemented but not honest end-to-end

- **`ignition_datetime`** — computed, accepted, stored, **never influences the simulation**.
- **Weather/fire coherence guard** — computed, **never blocks or warns at simulation time**.
- **`adj.tif`** — generated, uniform 1.0, **never calibrated**.
- **Weather time series** — declared hourly via `DT_METEOROLOGY`, **emitted as 1 band**.
- **`arrival_hours`** — computed, **~80% wrong** (§3).
- **`SimulationOutput.geom`** — column exists, always NULL.

### Not implemented at all

- Multi-band / forecast-horizon weather.
- Any model validation against an observed fire perimeter.
- Ensemble / Monte Carlo (`MODE=2`, `&MONTE_CARLO`).
- Spotting, suppression, assets-at-risk.
- Explicit `CROWN_FIRE_MODEL` configuration.
- Async simulation jobs — `POST /simulations/run` blocks for the whole ELMFIRE run.
- Auth on any endpoint.
- Tests for anything but `namelist_writer`.

---

## 7. Linear "Done" vs. implemented

Workspace `ignite-insights`, team `IGN`, project `Tesis`.

**Framing (decided 2026-08-31):** working code wins over issue text. Types and formats
should be what **ELMFIRE actually needs**, not what an issue happened to specify. So
this section separates the two, and only the first half is worth acting on.

### 7.1 Gaps that matter — ELMFIRE genuinely needs these

Two, both inside **IGN-11**, both ticked as accepted and neither built.

| Gap | What ELMFIRE needs | What it gets | Consequence |
|---|---|---|---|
| **Weather is single-band** | One band per `DT_METEOROLOGY` interval; ELMFIRE interpolates between them | **1 band**, while the namelist declares hourly | No diurnal cycle across a 12 h run — no afternoon wind peak, no RH minimum. The physics that drives Patagonian fire runs is absent. §2.3 |
| **No 10 m → 20 ft wind conversion** | 20-ft (6.1 m) wind, per the LANDFIRE convention ELMFIRE follows | Raw GFS **10 m** wind, m/s→mph only | Wind ≈ **15% too high**. §2.5 |

IGN-11's own criteria state both requirements verbatim — *"Float32 multibanda, una banda
por hora"* and *"La conversión de viento de 10 m a 20 pies está correctamente
implementada"*. This isn't a spec quibble: they're real model requirements, and they're
the prerequisite for the validation harness in §12 (harness B is indefensible on a
frozen weather band).

### 7.2 The other gap that matters — stale cache defeats code fixes

Not tracked by any issue. `data/static/{dem,slp,asp}.tif` are float32 from 12 May;
`raster_aligner` writes int16. Regeneration is skipped whenever the files exist:

```python
if not (dem_out.exists() and slp_out.exists() and asp_out.exists()):
    ...derive...
else:
    logger.info("Topography already cached — skipping")
```

The float32/int16 mismatch itself is **cosmetic** — ELMFIRE reads either. What matters is
that there is **no cache-invalidation key**, so *any* future change to topography
derivation will appear to work and change nothing until someone deletes `data/static/`.
Verified: the May 12 `dem.tif` is copied byte-identical into every inputs folder. This
will cost someone a day. See §4 finding 14.

### 7.3 Not worth acting on — issue text drifted, the code is fine

Recorded so nobody re-opens them later. **No action recommended.**

| Issue | Criterion says | Code does | Verdict |
|---|---|---|---|
| IGN-10 | `dem.tif` in 16-bit integer | float32 on disk | ELMFIRE reads either. Cosmetic. |
| IGN-13 | `phi` outside perimeter = `1.0` | True signed distance (m) | **The code is better.** A distance field has \|∇φ\|=1, which is what a level-set solver wants; the ±1 binary is the vendor tutorial's shortcut. Keep the code, fix the issue. |
| IGN-14 | outputs named `toa_*.tif`, `spread_rate_*.tif` | `time_of_arrival_*.tif`, `vs_*.tif` | The issue names files ELMFIRE never writes. Code is right. |
| IGN-14 | isochrones via `DUMP_ISOCHRONE_SHAPEFILES = .TRUE.` | runner's `gdal_contour` | **That keyword doesn't exist in ELMFIRE.** Criterion is unsatisfiable; the real mechanism works. |
| IGN-31 | VPS + Let's Encrypt + domain | Railway | Deployed and running. Different platform, same outcome. |

IGN-14 (the Hito 3 gate) and IGN-31 were both closed with every criterion unchecked. The
*outcomes* are real — verified ELMFIRE output, isochrones, DB registration, a live
deploy. Only the criteria text is stale.

### 7.4 Genuinely not built

- **IGN-28** — automatic pipeline orchestrator. No scheduler anywhere: grep for
  `cron`/`apscheduler`/`celery`/`schedule` across `pyproject.toml`, `app/`,
  `docker-compose.yml`, `Dockerfile` returns nothing. Ingestion is manual `POST` only.
  Correctly still in Backlog.
- **Tests** claimed by IGN-10 and IGN-13 (`slp`/`asp` ranges, phi rasterization) don't
  exist. Real gap, but a test-coverage concern rather than a correctness one — the code
  itself is right.

### 7.5 Built but uncredited — resolved

| Issue | Was | Now | Evidence |
|---|---|---|---|
| **IGN-27** Esquema PostGIS | Backlog | **Done** ✅ | 6 tables, correct spatial types, 3 Alembic migrations, and **GIST indexes present** on `areas_of_interest.geom`, `fire_detections.geom`, `raster_assets.bbox`, `simulation_outputs.geom` (migration `0001`). Every criterion genuinely met. |
| **IGN-30** Dashboard | Backlog | **Done** ✅ | MapLibre map, toggleable layers, fires + isochrones, TOA/FLIN overlays, stats side panel. |
| **IGN-29** API FastAPI | Backlog | *unchanged* | **Also fully built** — `/fires/active`, `/simulations/*`, `/ingestion/*`, `/dashboard/summary`. Not marked Done because it wasn't explicitly authorized; flag if you want it moved. |

IGN-31 (DevOps) was Done while declaring itself blocked by IGN-29 and IGN-30 — that
inversion is now half-resolved, and fully resolved if IGN-29 moves too.

### 7.6 The audit findings map onto issues that already exist

Most of §2 is not unknown work — it is **Hito 5**, correctly still open:

| Audit finding | Existing issue | Status |
|---|---|---|
| §2.1 fuel crosswalk / TL3 (the thesis contribution) | **IGN-20** crosswalk, **IGN-21** raster, **IGN-22** spatial validation | In Progress / Todo |
| §2.4 ADJ pinned at 1.0 | **IGN-25** Calibración del factor de ajuste (adj.tif) | Backlog |
| Validation against the observed fire | **IGN-26** Evaluación formal — **métrica IoU** — Gate de calidad | Backlog |
| §7.1 + §7.2 input defects | **IGN-23** Verificación de consistencia de todas las capas de entrada | Backlog |

**IGN-23 would have caught both §7.1 gaps and §7.2.** It is still in Backlog and Hito 3
was gated closed without it. Worth pulling forward — §7.1 and §7.2 are its findings,
already written.

IGN-26 already specifies **IoU**, matching the design in §12.

## 8. Recommended order of work

**Fix first — visibly wrong, cheap:**

1. **Isochrone hour labels** (§3). Add `-a arrival_s` to the runner's `gdal_contour`;
   delete `enrich_with_arrival_time`. Net negative diff.
2. **Separate prediction from input on the map.** Draw `ignicion.shp` as its own layer,
   distinctly styled and labelled "perímetro FIRMS observado". Right now 84% of the
   painted fire is the input and nothing says so. This is the single change that most
   improves how the product reads, and it is not a physics change.

**Then decide the physics — these need your call, see below:**

3. Fuel crosswalk (§2.1) — the dominant lever.
4. Burning-period fuel moisture (§2.2).
5. Multi-band weather (§2.3) + anchor to `ignition_datetime` (§2.6).

**Then hygiene:**

5b. **Clear `data/static/` once, or add a cache key** (§7.2) — do this *before* any topo
   change, or the change will silently do nothing.
6. Fix the five unit errors in `docs/elmfire-mapping.md` (§5).
7. Surface the coherence warning at simulation time (§2.8).
8. Tests for `ignition_builder`, `weather_builder`, `fuels_builder`, `isochrone_converter`.
9. Implement the 10 m → 20 ft wind conversion (§2.5 — IGN-11 already accepted it as
   done); set `CROWN_FIRE_MODEL` explicitly (§2.7); add `adj.tif` to
   `EXPECTED_ELMFIRE_INPUTS` (§4.10).
10. Clear `data/static/` once, or add a cache key, before trusting any topo change (§7.4).

---

## 9. Open questions (superseded by §10 where answered)

These change what gets built and are not mine to decide.

1. **Is the goal a calibrated operational forecast, or a defensible thesis pipeline?**
   A thesis can ship with TL3 and a documented limitations section. An operational tool
   cannot. This determines whether §2.1–§2.4 are bugs or scope.

2. **Do you have an observed fire perimeter to validate against?** Without one there is
   no way to tell "the model is too slow" from "that was a mild day" — and no basis for
   tuning ADJ. If a Los Alerces burn with a known perimeter exists, that is the highest-
   value input to this whole effort.

3. **Fuel crosswalk: retune, or add a second data source?** Cheap: remap tree cover
   183 → 165 (TU5) and re-run. Honest: WorldCover at 10 m cannot see understory at all,
   so any crosswalk from it is a guess with a citation attached.

4. **Multi-band weather: worth it before the thesis deadline?** It touches
   `gfs/service.py`, `weather_builder.py`, and `namelist_writer.py` together, and is the
   difference between a 12 h forecast and a 12 h extrapolation of one instant.

---

## 10. Decisions taken

Recorded 2026-08-31.

| Question | Decision |
|---|---|
| Goal | **Thesis now, forecast later.** Presentation and correctness fixes ship immediately; physics changes land as documented future work. |
| Acceptance criteria | **Working code beats issue text.** Types and formats follow what ELMFIRE actually needs, not what an issue specified. Cosmetic drift between the two is recorded in §7.3 and deliberately not acted on. |
| Fuels | **The Patagonian fuel-model map IS the thesis contribution.** ELMFIRE is the vehicle that demonstrates it; the WorldCover crosswalk is the baseline to beat, not a bug to patch. |
| Validation | Kaggle dataset <https://www.kaggle.com/datasets/ignaciochevallier/argentina-wildfire> — Sentinel-2 imagery + **binary burn masks** for the 2026 Los Alerces fire, tiled, CC0, 276 MB. Built in the `visionArtificial` repo. Design in §12; it slots into the existing **IGN-26** (IoU gate). |

### What this changes about the audit

§2.1 is **re-framed from defect to motivation**. The quantified case for a purpose-built
fuels layer is exactly the material in §1 and §2.1: 59.7% TL3, 0.04% shrubland in a
matorral landscape, median fireline intensity 4.6 kW/m, and a 12 h prediction that adds
only 16% to the observed perimeter. That is a defensible "the existing global land-cover
route is insufficient for Patagonian fuels" argument, backed by numbers from a real run.

§2.2–§2.6 stay as future work, but note the dependency: **any fuels improvement is
unfalsifiable without a validation perimeter.** Swapping crosswalks changes the picture;
only an observed perimeter shows whether it changed it for the better.

### Open — needed to proceed on validation

The Kaggle dataset could not be read from this session. To plan the validation harness I
need to know: what geometry type it holds (perimeters, detections, burn scars?), its CRS
and resolution, its time coverage, and whether any fire in it overlaps a period for which
GFS and FIRMS can be re-ingested. Paste the file list and column names, or point me at a
local copy.

---

## 11. Changes made in this pass

Two fixes from §8, both landed and verified.

### Fix 1 — isochrone hour labels (§3), root cause

- `../elmfire-runner/app/runner.py` — `gdal_contour` now passes **`-a arrival_s`**, so each
  contour carries its own level. This is the root cause; every consumer was working around
  its absence.
- `app/postprocessing/isochrone_converter.py` — **deleted `enrich_with_arrival_time`**
  (the raster-resampling heuristic) and split the remainder into `shapefile_to_geojson`
  (bare) and `isochrones_to_geojson` (adds `arrival_s`/`arrival_hours` from the attribute).
- `app/api/v1/simulations.py` — dropped the resampling call and the now-unused
  time-of-arrival glob from the isochrones endpoint.

Runs made before this change carry no `arrival_s`; their features now return **null**
arrival times and render grey ("unknown") rather than being assigned a fabricated hour.
That is deliberate — grey is honest, and the previous behaviour mislabelled ~80% of
features and put 15.6% of them at hour 0. **Re-run a simulation to get timed isochrones.**

### Fix 2 — separate the prediction from the input (§4.2)

- `app/db/repository.py` — `create_simulation_run` accepts `elmfire_config`, reusing the
  **existing, previously-unused** `SimulationRun.elmfire_config` JSONB to record
  `inputs_dir`. No migration needed; `ignicion.shp` lives in the inputs folder and
  `SimulationRun` previously tracked only `output_dir`.
- `app/api/v1/simulations.py` — new **`GET /simulations/{id}/ignition`** serving
  `ignicion.shp` as GeoJSON, documented explicitly as observed input. The isochrones
  endpoint description now cross-references it.
- `frontend/app/api/simulations/[id]/ignition/route.ts` — proxy route.
- `frontend/components/fire-map.tsx` — new ignition layer (muted grey-blue fill + dashed
  outline), added **before** the isochrones so it renders underneath, plus a map legend
  naming the two things: *"Perímetro FIRMS observado (entrada)"* vs *"Isócronas previstas
  0 → 12 h"*. The grey-blue deliberately shares no colour with the YlOrRd prediction ramp.
- `frontend/components/map-panel.tsx` — fetches and wires it per selected run.

Runs recorded before this change have no `inputs_dir` and return an empty
FeatureCollection, so the layer simply does not draw for them.

### Verification

- `tests/test_isochrone_converter.py` — **new**, 6 tests covering the attribute path, the
  missing-attribute path (asserts unknown rather than a guess), reprojection against the
  real domain corner, the ignition-polygon path, and missing-CRS handling.
- Full suite: **10 passed**. `ruff check app/` and `mypy app/` clean (what CI runs).
  `tsc --noEmit` clean on the frontend.

### Not done in that pass

- §8 items 3-9 — see §11b, which closed several of them.

---

## 12. Validation design

> **Movido a `IGN-26-VALIDACION.md`** (2026-09-15). Era la única sección viva de
> esta auditoría; se mantuvo su numeración §12.x allá.

## 11b. Second pass — the three gaps that mattered

All three from §7.1/§7.2, plus the doc drift from §5. Verified: `ruff check app/` and
`mypy app/` clean (70 files), **28 tests pass**, `tsc --noEmit` clean.

### Fix 3 — multiband weather (§2.3, §7.1)

Root cause was in ingestion, not the builder: `gfs/client.py` hardcoded `fxx=0`, so only
the analysis hour was ever fetched and there was never more than one band to carry.

- `app/ingestion/meteorology/gfs/client.py` — `download_variable` now takes
  `forecast_hours` (default `range(25)` — 24 h hourly, covering the 12 h default horizon
  with headroom) and writes **one band per forecast hour**, ascending. Per-hour fetch and
  clip moved into `_fetch_clipped`. Grid consistency across hours is asserted.
- `app/elmfire/builder/weather_builder.py` — reads and writes every band instead of
  band 1. Mismatched band counts between paired inputs (u10/v10, t2m/rh) now raise.
- **ws/wd switched Int16 → Float32.** Not cosmetic: the vendor tutorials declare `ws`
  via `FLOAT_RASTER[n]=`, and Int16 mph quantized wind to ±0.45 m/s for no benefit.
- `namelist_writer.validate_weather_coverage()` — **new guard.** ELMFIRE does not error
  when a run outlasts the weather bands; it holds the last band and silently freezes the
  weather mid-simulation. This raises instead, naming the shortfall. Single-band rasters
  still pass with a warning, so pre-existing runs keep working.
- `simulations.py` — a horizon exceeding available bands is now **422**, not 500.

No service change was needed: `run_gfs_ingestion` picks up the default.

### Fix 4 — 10 m → 20 ft wind conversion (§2.5, §7.1)

`weather_builder.wind_height_factor()` implements the log wind profile
`U(z) = U_ref · ln(z/z0) / ln(z_ref/z0)`, with the roughness length `z0` as an explicit
named constant rather than a magic number:

```
z0 = 0.22 m  →  factor 0.8703   (the ~0.87 standard in fire weather)
z0 = 0.03 m  →  factor 0.9148   (open grassland)
```

Deriving it leaves `z0` as the knob to tune if the AOI's effective roughness is ever
characterised, instead of hardcoding 0.87. Wind was previously ~15% too high.

### Fix 5 — topography cache key (§7.2)

`raster_aligner` now writes `.topo_cache_key.json` next to the derived rasters and
regenerates whenever the key changes. The key covers the source DEM's identity
(name/size/mtime), the derivation parameters (CRS, resolution), and
**`DERIVATION_VERSION`** — bump that on any change to how dem/slp/asp are produced.

This self-heals the current stale cache: the existing `data/static/` has no key file, so
the next run regenerates and replaces the float32 rasters from 12 May.

> A test caught a real defect in the first version of this key: `int(st_mtime)` has
> 1-second resolution, so a DEM replaced within the same second looked identical and was
> served from cache. Now uses `st_mtime_ns`.

### Fix 6 — documentation drift (§5)

All five unit errors in `docs/elmfire-mapping.md` corrected (ws km/h→mph, cc scaling,
ch/cbh ×10, cbd ×100), the three missing WorldCover classes (70, 95, 100) added, and the
wind/moisture sections rewritten for multiband + the 20-ft conversion. The unphysical
`m10 = emc+2` / `m100 = emc+5` offsets are now flagged in the doc as well as the code.

### Tests added

- `tests/test_weather_multiband.py` — 12 tests: the 0.87 factor, factor bounds and
  identity, rejection of a target height below `z0`, end-to-end conversion through
  `derive_wind`, band-count preservation and ordering for wind and moisture, mismatched
  band rejection, and the coverage guard (over-long horizon rejected, sufficient bands
  pass, single band warns).
- `tests/test_topo_cache.py` — 5 tests: cache hit, invalidation on `DERIVATION_VERSION`
  bump, invalidation on a replaced source DEM, and rebuild-not-crash on a corrupt key.

### Still open

- **§2.2** burning-period fuel moisture. Multiband makes the *shape* of the diurnal
  curve real, but `m1` is still instantaneous EMC — 11% where an afternoon burning
  period is 4-8%. The `+2`/`+5` offsets need a drying history the ingestion doesn't keep.
- **§2.6** `ignition_datetime` still never reaches the namelist; runs remain anchored at
  `SIMULATION_TSTART = 0.0`. Now more valuable than before — with real hourly bands, the
  run *should* start at the right hour of the diurnal cycle.
- **§2.4** ADJ (IGN-25), **§2.1** fuels (IGN-20/21/22), **§12** validation harness.
