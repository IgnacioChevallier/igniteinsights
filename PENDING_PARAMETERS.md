# Pending parameters — values set without a criterion

Every value in this pipeline that is currently set **arbitrarily, by eye, or by
convention borrowed from elsewhere**, and what would be needed to set it with an actual
criterion.

**Scope.** Physical constants (`MS_TO_MPH = 2.23694`), API endpoints, dataset version
strings and values *forced* by an external interface are deliberately excluded — they
are not judgement calls. What is listed here is everything where a different reasonable
person could have picked a different number and nothing in the repo would object.

Companion to `SIMULATION_AUDIT.md`. Last swept 2026-08-31.

**Legend for "Basis"**
- 🔴 **Arbitrary** — no stated justification; a placeholder that stuck.
- 🟡 **By eye** — tuned until the output looked right on one dataset, never validated.
- 🟢 **Conventional** — a defensible standard from the literature, but not verified for
  Patagonia specifically.
- ⚫ **Forced** — dictated by ELMFIRE, a sensor, or a data provider. Listed only where
  someone might mistake it for a choice.

---

## 1. The ones that move the answer most

Ranked by how much the predicted fire changes if you change them.

### 1.1 🔴 WorldCover → FBFM40 crosswalk

`app/elmfire/builder/fuels_builder.py` · `WORLDCOVER_TO_FBFM40`

| Value | Assigned | Effect |
|---|---|---|
| Tree cover → **183 (TL3)** | 🔴 | **59.7% of the AOI.** Near-inert litter model; drives median fireline intensity to 4.6 kW/m |
| Shrubland → 145 (SH5) | 🔴 | 0.04% of the AOI — implausibly low for Patagonian matorral |
| Grassland → 102 (GR2) | 🔴 | 17.1% |
| Bare/sparse → 93 (NB3) | 🔴 | 15.3%, unburnable |
| Snow/ice → 93, Mangrove → 183, Moss → 101 | 🔴 | Negligible area; mangrove in Patagonia is a no-op mapping |

**This is the single biggest lever on the output** and, per the decision in
`SIMULATION_AUDIT.md` §10, it is the thesis contribution — the current table is the
baseline to beat, not a bug.

**Criterion needed:** field plots or a trained classification giving fuel type per pixel.
WorldCover at 10 m cannot see understory at all, so any crosswalk from it is a guess with
a citation attached. Tracked as IGN-20/21/22.

### 1.2 🔴 Fuel moisture time-lag offsets

`weather_builder.derive_moisture` · `m10 = emc + 2`, `m100 = emc + 5`

No physical basis. Time-lag classes damp toward a running mean; they are not a fixed
offset from the instantaneous equilibrium. **Criterion needed:** a drying history —
several days of prior GFS — which the ingestion does not retain today.

Related and equally unaddressed: `m1` is raw equilibrium moisture (median **11.1%**)
where an afternoon burning period sits at **4–8%**. There is no diurnal, solar-exposure
or slope/aspect correction anywhere. This depresses spread across the whole domain.

### 1.3 🔴 `adj.tif` = 1.0 uniform

`app/preparation/service.py` · `_write_uniform_raster(..., 1.0)`

ELMFIRE's spread-rate adjustment factor — the knob explicitly designed for calibrating a
model against observed regional fire behaviour. Currently neutral everywhere, i.e.
**unused**. **Criterion needed:** an observed fire perimeter to tune against; tune
per-fuel-model, and only *after* the fuels comparison, or ADJ absorbs the fuel error and
the fuels result disappears. Tracked as IGN-25.

### 1.4 🟢 Wind roughness length `z0 = 0.22 m`

`weather_builder.WIND_ROUGHNESS_LENGTH_M`

Chosen to reproduce the ~0.87 factor standard in fire weather (stations sited over
vegetation). Open grassland (`z0 = 0.03`) would give 0.915 instead — a ~5% difference in
wind speed. Defensible and now derived rather than hardcoded, but **not measured for Los
Alerces**. **Criterion needed:** effective aerodynamic roughness for the AOI's canopy,
or a roughness raster derived from `ch.tif` instead of one scalar.

### 1.5 🔴 Canopy CBH/CBD lookup by fuel model

`canopy_builder.py` · `_FBFM40_CBH`, `_FBFM40_CBD`

Attributed to Scott & Reinhardt (2005), but the per-FBFM assignment was made by hand and
inherits every error in §1.1 — TL3 → CBH 1.5 m, CBD 0.20 kg/m³ applies to 59.7% of the
map. These set the **crown-fire initiation threshold**. **Criterion needed:** derive CBH
from `ch.tif` and canopy structure rather than from the fuel model, or measure it.

---

## 2. Ignition perimeter reconstruction

`app/elmfire/builder/perimeter_reconstruction.py`. These decide the shape and size of the
seed — which is **84% of what the map paints as fire** (`SIMULATION_AUDIT.md` §1).

| Parameter | Value | Basis | Notes |
|---|---|---|---|
| `_CLUSTER_EPS_M` | 1500 m | 🟡 | Tuned on the 2026-02 window until it yielded "8-14 clusters" and didn't bridge the lake. One dataset, one eyeball. |
| `_HULL_RATIO` | 0.4 | 🟡 | Concave-hull concavity. No sensitivity analysis. |
| `_MIN_HULL_POINTS` | 4 | 🔴 | Below this, points become buffers instead. |
| `_DEDUP_GRID_M` | 10 m | 🔴 | Collapses re-ingested duplicates. Harmless but unjustified. |
| `VIIRS_PIXEL_M` | 375 m | ⚫ | Real VIIRS I-band pixel width. Not a choice. |
| `_PHI_IGNITION_FLOOR` | -1.0 | ⚫ | Forced: ELMFIRE resets `PHI0 < -1.1` to unburned. Must stay above -1.1. |

**Criterion needed:** sensitivity analysis over `eps` × `hull_ratio` against the observed
burn scar (§5), reporting how seed area and final IoU respond. Cheap to run once the
validation harness exists, and it directly bounds the uncertainty on every result.

---

## 3. Simulation and namelist

`app/elmfire/builder/namelist_writer.py`

| Parameter | Value | Basis | Notes |
|---|---|---|---|
| `dt_s` (`SIMULATION_DT`) | 30 s | 🔴 | Minimum timestep. Never varied. |
| `dtmax_s` (`SIMULATION_DTMAX`) | 300 s | 🔴 | Maximum timestep. Never varied. |
| `dtdump_s` (`DTDUMP`) | 3600 s | 🟢 | Hourly isochrones — a product decision, and it matches `DT_METEOROLOGY`. |
| `dt_meteorology_s` | 3600 s | 🟢 | Matches GFS hourly output. Must change together with the raster band count. |
| `simulation_tstart_s` | **0.0** | 🔴 | **The run is not anchored to wall-clock time.** `ignition_datetime` is computed, stored, and never reaches the namelist. Now materially wrong: with real hourly bands, the run should start at the correct hour of the diurnal cycle. |
| `horizon_hours` (default) | 12 | 🔴 | API default. No basis. |
| `CROWN_FIRE_MODEL` | *unset* | 🔴 | ELMFIRE defaults it **on**. Currently enabled by omission, not decision. 696.8 of 19,454 acres burned as crown fire. |
| `MODE` | 1 | ⚫ | Transient spread. The only mode this repo supports. |

**Criterion needed** for `dt_s`/`dtmax_s`: a convergence check — halve them and confirm
the isochrones don't move. If they do, the timestep is doing physics.

---

## 4. Ingestion, grid and domain

| Parameter | Value | Where | Basis | Notes |
|---|---|---|---|---|
| `resolution_m` | 30 m | `raster_aligner` | 🟢 | Native Copernicus GLO-30. Sensible; also sets the isochrone resolution floor. |
| `target_crs` | EPSG:32719 | `raster_aligner` | ⚫ | Correct UTM zone for the AOI. |
| AOI bbox | -72.0, -42.9, -71.5, -42.5 | `config.py` | 🔴 | **Covers only part of the validation dataset** — see §5. |
| `gfs_forecast_hours` | 24 | `config.py` | 🟡 | Last GFS forecast hour fetched → band count. Now configurable per ingestion run; **must cover the simulation horizon** or ELMFIRE freezes the weather at the last band. Ceiling is f120 (5 days) from one cycle. |
| `MAX_LOOKBACK_DAYS` | 2 | `gfs/client` | 🔴 | How far back to hunt for an available cycle. |
| `_WEATHER_MISMATCH_MAX_S` | 48 h | `preparation/service` | 🟡 | Threshold for flagging fire/weather period mismatch. |
| `fires_since` default | 48 h | `preparation/service` | 🔴 | Detection window feeding `phi.tif`. Directly sets seed size. |
| `ACCEPTED_CONFIDENCE` | `{n, h}` | `firms/normalizer` | 🟢 | Drops FIRMS low-confidence detections. Standard practice. |
| `firms_day_range` | 1 (max 5) | `api/v1/ingestion` | ⚫ | FIRMS API limit. |
| Moisture clip | 1–40% | `weather_builder` | 🟡 | Bounds EMC output. 40% exceeds every fuel model's extinction moisture anyway. |
| `elmfire_runner_timeout` | 300 s | `config.py` | 🔴 | |
| `JOB_TIMEOUT_BUFFER_SECONDS` | 600 s | `runner/client` | 🔴 | Mirrors the runner's own buffer. |

---

## 5. Validation ground truth — `mask-dataset-gen`

**These parameters define the ground truth, so they set a ceiling on every accuracy
number the thesis will report.** They deserve the most scrutiny and currently have the
least.

`../mask-dataset-gen/generar_dataset.py`

| Parameter | Value | Basis | Notes |
|---|---|---|---|
| `DNBR_UMBRAL` | 0.30 | 🟢 | **Accepted for this scope.** Within Key & Benson's low-moderate severity band (0.27–0.44); trialled against 0.22 (`remask_comparisons/`). Known bias: excludes low-severity burn, so the mask runs slightly small. |
| `PRE_NBR_MIN` | 0.15 | 🟡 | Requires pre-fire vegetation. |
| `POST_NBR_MAX` | 0.40 | 🟡 | |
| `NDSI_NIEVE_MAX` | 0.25 | 🟡 | Snow rejection — non-trivial in an Andean AOI. |
| `NDWI_AGUA_MAX` | 0.05 | 🟡 | Water rejection. |
| `CLOUDY_PIXEL_PERCENTAGE` | < 20 | 🟢 | Standard S2 scene filter. |
| `ESCALA` | 20 m | ⚫ | Sentinel-2 SWIR native. Aggregates cleanly onto the 30 m grid. |

### 5.1 The pre-fire window is from 2023 — deliberate, resolved

```
FECHA_PRE_INI  = "2023-11-01"      FECHA_POST_INI = "2026-02-01"
FECHA_PRE_FIN  = "2023-12-31"      FECHA_POST_FIN = "2026-03-08"
```

**Status: deliberate, tested, accepted for this scope (2026-08-31).** The long gap was
chosen to guarantee cloud-free pre- and post-fire composites — a real constraint in
Patagonia — and to put clear separation between the two windows. Nov–Dec is also the same
austral growing-season phase as February, so the phenological match is good; for an NBR
baseline that matters more than recency. The thresholds were trialled repeatedly
(`remask_comparisons/`). **Not an open item.**

Residual, stated as a limitation rather than a risk to resolve: the mask necessarily
includes any *other* land-cover change between Dec 2023 and Mar 2026. If it is ever worth
quantifying rather than caveating, counting mask pixels far from any 2026 FIRMS detection
bounds it empirically in one pass.

⚠️ **`docs/README.md` in that repo still disagrees with the code** — it states PRE =
2025-11-01 to 2025-12-08 and POST = 2026-02-05 to 2026-02-20. Code and shipped
`metadata.csv` both say 2023-11-01/2023-12-31 and 2026-02-01/2026-03-08. The code is
right; **the README should be corrected** so the thesis doesn't cite the wrong window.

### 5.2 Domain overlap is partial

- Dataset bbox: lon **-72.014 … -71.201**, lat **-42.818 … -42.079**
- Simulation AOI: lon -72.0 … -71.5, lat -42.9 … -42.5

**Only 70 of 196 tiles intersect the simulation domain** (50 of those with >1% burned).
The dataset extends well north and east of the AOI.

**Decided (2026-08-31): use the 70 intersecting tiles.** The AOI stays as it is.
Report the scope explicitly alongside any accuracy figure — a reader will otherwise
assume the whole fire.

### 5.3 `pct_quemado` is a percentage, not a fraction

Range 0 – 88.14, mean 20.25. No tile is fully burned. Stratification for reporting:

| Band | Tiles |
|---|---|
| < 1% | 58 |
| 1–10% | 38 |
| 10–50% | 70 |
| > 50% | 30 |

Report accuracy **stratified by this band**. Pooled numbers are dominated by the 58
near-empty tiles, which any model predicts correctly by doing nothing.

### 5.4 Format notes for the harness

- Masks: `dataset/mascaras/tile_NNN.tif`, uint8 `{0,1}`, separate files.
- Images: `dataset/imagenes/` (post) and `imagenes_pre/`, 6 bands (B2,B3,B4,B8,B11,B12), float64.
- 196 tiles, 257×257, **EPSG:4326** at 0.00017966° (~20 m) — needs a warp to EPSG:32719
  at 30 m to meet the simulation grid.

---

## 6. Cosmetic — listed for completeness, no action

| Parameter | Value | Where |
|---|---|---|
| `_RAMP_STOPS` / `_RAMP_COLORS` | ColorBrewer YlOrRd 5-class | `raster_overlay.py` |
| Overlay alpha | 178 (~70%) | `raster_overlay.py` |
| Isochrone `line-width` | 2 px | `fire-map.tsx` |
| Ignition fill | `#5b6b7a` @ 0.35 | `fire-map.tsx` |
| `_NODATA` | -9999 | throughout |
| `_NODATA_FBFM40` | 99 (NB9) | `fuels_builder.py` |

---

## 7. Suggested order

1. ~~§5.1 pre-fire window~~ — resolved: deliberate. Fix the generator README.
2. ~~§5.2 validation domain~~ — resolved: the 70 intersecting tiles.
3. **§3 `simulation_tstart_s`** — anchor runs to `ignition_datetime`. Now the blocker for
   validation: a hindcast has to start at a real wall-clock hour for the hourly weather
   bands to line up with the fire.
4. **§1.3 ADJ + §2 sensitivity analysis** — both need the validation harness first, and
   both convert a guess into a measured range.
5. **§1.1 fuels** — the thesis contribution; §5 must be trustworthy before it can be
   evaluated.
6. **§3 `dt_s`/`dtmax_s` convergence check** — one run at half the timestep answers it.
