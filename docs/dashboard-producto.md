# Product dashboard: users, demo clock and operational forecast

Design agreed on 2026-10-23 (grill session) and implemented on branch `feat/dashboard-producto`.
The audience is the thesis jury: a demo shaped like the final product, not an operational
alert system. Section numbers are the decision branches; code comments cite them.

## 1. What the product is

A client logs in, sees whether there is a fire in the AOI and how it may spread over the next
24 h. Everything we use today (fuels, validation, simulator, data, ingestion settings) stays
behind the **admin** role. A **client** (Better Auth role `user`, shown as "cliente") sees only
the map, the documentation tab and their account.

**Rule of thumb: the admin decides what is computed; the client decides what to look at.**
Nothing a client does starts a computation.

### 1b. The clock

One global mode in table `operativo` (single row):

- `demo`: a frozen clock (`operativo.reloj`) that only the admin moves, one VIIRS pass at a
  time (`POST /operativo/pasada?direccion=±1`). Every client sees the same instant and a
  banner: "Modo demostración … no es un incendio en curso".
- `vivo`: the real clock.

A pass only exists for the client once FIRMS published it: detections are visible when
`acq_datetime + 3 h <= clock` (`LATENCIA_FIRMS_H`, FIRMS FAQ "within 3 hours", best effort).

## 2. One forecast path for demo and live (decision C)

`app/operativo/servicio.py`. `tick(ahora)` reads the visible detections, groups them into fires
(§3) and runs one P-24 window (24 h, modelo-v0 physics) for every fire whose latest pass has no
forecast yet. The cron calls it in live mode; `scripts/demo_operativo.py` calls the **same**
function for every pass of a past fire, with the clock set to `pasada + 3 h`, and stores the
results. During the defence nothing has to run; the admin can still trigger a live tick.

What a window is made of:

| Input | Source |
|---|---|
| dem, slp, asp, adj, fbfm40, cc, ch, cbh, cbd | `run_preparation(only_static=True)` for the fire's year, cached in `data/operativo/estaticos/<year>/`, cropped to the box |
| ws, wd, m1, m10, m100 | the GFS cycle available at the pass (§2b), hours `t0 − cycle` onwards |
| phi.tif, ignicion.shp | every detection of the fire up to the pass, `ignition_builder.build_ignition_layer` (the benchmark's seed rule) |
| namelist | `write_namelist`, `SIMULATION_TSTART` = the pass minutes, LH 30 % / LW 100 % |

Results are ordinary `simulation_runs`, so `/simulations/{id}/isochrones|ignition|stats|wind`
serve them unchanged. Table `pronosticos` links each one to a stable fire ID, its display name,
pass, availability time and GFS cycle.

### 2b. Weather: the forecast that existed, not the hindcast

`pronostico.ciclo_disponible(pass)`: the latest 6-hourly GFS cycle published when the pass
became visible (pass + 3 h FIRMS latency − 4 h GFS publication, floored to the cycle).

The validated P-24 cases (`pronostico-v7`) use **chained GFS analyses** from cycles issued
after t0 — a meteorological hindcast. `benchmarks/casos/*/pronostico-gfs-v7.json` repeat four
of them (Alerces 2023, Alerces 2024, Epuyén 2025, Patriada 2026; GFS 0.25° archives start in
2021, so Cholila 2015 and Alerces 2016 cannot) with this forecast weather and nothing else
changed (`empaquetado.clima = "pronostico"` in `scripts/benchmark.py::_pronostico`). Results go
to `docs/resultados/ESTADO-RESEARCH.md` §6.

## 3. What is a fire

Any detection of nominal or high confidence (the FIRMS normalizer drops low). Detections closer
than 3 km and separated by no more than 24 h are linked (single linkage,
`filtro_conexo_m` of the P-24 cases) over the last 7 days; a group is active if it has a
detection in the last 24 h. Its stable ID is a digest of its first detection (ties in time broken
by position, §8). Its display name
is "Cerca de <nearest locality to its first detection> · desde dd-mm" (fixed list in
`LOCALIDADES`); names need not be unique.

### 3b. Domain

A box around the fire's detections plus 15 km, clipped to the AOI — not the whole AOI. Measured
before deciding: a Patriada-sized window already uses ~5.6 GB of the 7.75 GB Docker VM, and the
AOI is ~6× larger. The P-24 cases use a hand-drawn box over the final scar, which does not exist
in real time.

## 4. Authentication and authorization

- Better Auth 1.7 in Next (`frontend/lib/auth.ts`), email + password, **sign-up disabled**,
  admin plugin for roles. Tables in the same Postgres, created by alembic `0006`.
- `frontend/middleware.ts` is the only gate and denies by default. Clients reach `/`,
  `/cuenta`, `/documentacion` and GET on `/api/v1/operativo/estado`,
  `/api/simulations/{id}/{isochrones,ignition,stats,wind,ensemble-agreement}` and terrain
  tiles. Everything else is admin-only (403 / redirect).
- **FastAPI has no auth and must have no public domain.** Next reaches it over the private
  network (`API_BASE_URL`). As of 2026-10-23 `igniteinsights-api.up.railway.app` is public with
  open `/docs`, `/ingestion/*` and `/simulations/run`; see §7.

## 5. Client view

`frontend/components/client-map.tsx`, also embedded under the admin's "Producto" section with
the clock controls (`producto-panel.tsx`). Layers: FIRMS detections (24 h), observed perimeter,
animated isochrones, wind (particles, optional speed), 3D relief, growth summary, and the
ensemble agreement only if the admin enabled it **and** the selected forecast has one
(`pronostico.ensamble` in `/operativo/estado`, an `is_file()` on its `ensemble_agreement.json`);
otherwise the option is simply absent. Time-of-arrival and fireline intensity are
admin-only. States: no fire (with last and next pass), one fire (zoom), several (side list).
A fixed line under the map: "Propagación potencial bajo condiciones modeladas, sin supresión ·
próximas 24 h desde la pasada VIIRS de las HH:MM (disponible HH:MM)".

## 6. Documentation tab

`frontend/app/documentacion/page.tsx`: the model limits in plain language (from ESTADO §6 and
`RIESGOS_Y_SUPOSICIONES.md`), every data source with its attribution and licence, and the
academic disclaimer. Keep it in step with those documents.

## 7. Deployment (Railway Pro, existing project)

Deployment target: Railway project `Ignite Insights`, production environment.

1. **api**: remove its public domain. Keep the service; Next reaches it at
   `http://api.railway.internal:8000` (set `API_BASE_URL` on the frontend to that).
2. Run `alembic upgrade head` on the api (adds `0005` operativo and `0006` users).
3. **frontend**: add `DATABASE_URL` (the Postgres URL, `postgresql://`, not `+asyncpg`),
   `BETTER_AUTH_SECRET` (`openssl rand -base64 32`) and `BETTER_AUTH_URL` (its public URL).
4. Create the accounts (§9) and run the demo precompute (§8) against the Railway database and
   runner, or copy the local results.
5. **cron** (live mode): a Railway cron service on `*/30 5-10,18-23 * * *` (UTC; only while
   VIIRS data can arrive, see §10), running
   `curl -fsS -X POST http://api.railway.internal:8000/api/v1/operativo/tick`. The tick does
   nothing while the mode is `demo`.

The runner keeps the 15-min HTTP limit in mind: a window over a fire box runs in minutes.

## 8. The demo

```bash
AOI_NORTH=-41.90 uv run python scripts/demo_operativo.py 2026-01-05 2026-01-09
```

The replay starts at the first Puerto Patriada pass (2026-01-05 19:20 UTC) and precomputes every
active fire visible in the AOI at each pass. Detections before that instant are excluded from
grouping and seeding. The cutoff is stored in `operativo.demo_desde` (migration `0007`) so that
`tick` and `estado` group the same detections: a fire's id comes from its first detection, and a
cutoff applied only by the precompute left the panel unable to find its demo forecast. The script
is resumable, so rerunning it fills forecasts missing from an existing Puerto Patriada-only demo
without repeating completed windows. It leaves the mode in `demo` with the clock on the first
forecast; the admin walks forward from there. Starting on day 1 is deliberate: it shows the weak
point and how each pass corrects it. `AOI_NORTH` matters only if `.env` overrides it (the repo
`.env` had `-42.9`, which leaves Patriada out).

A fire's id is a digest of its first detection, and the first pass brings many detections with
the same time; the tie is broken by position (`min` over `(t, lat, lon)` in
`incendios_activos`), so the id no longer depends on each database's row order (74c27d3). The
precompute ends by walking every demo clock through `servicio.estado` and printing how many saved
forecasts it finds (`ids: estado encuentra N/N`); anything less means ids drifted again.

**Ensemble agreement in the demo.** `demo_operativo.py` runs P-24 only, without ensemble. The
ensemble is added afterwards to three Puerto Patriada steps, not to all 19 demo forecasts: at
~35 min and 1.4 GiB per step (`ESTADO-RESEARCH.md` §6, note AD) every pass would take ~11 h,
and three steps are enough to show the layer where it says something. The steps are the first
pass (2026-01-05 19:20 UTC, where the replay starts) plus the two with the largest growth in
their own deterministic 24 h window: total area from `fire_size_stats.csv` (what `/stats`
serves) minus the seeded area (burning cells of `phi.tif`). The script prints that table and the
choice, so it is measured rather than picked by eye:

```bash
uv run python scripts/demo_ensamble.py --sin-correr   # just the table and the choice
uv run python scripts/demo_ensamble.py                # the GEFS ensemble of those 3 steps
```

It never repeats a P-24: it reuses each forecast's frozen inputs (`elmfire_inputs_dir/
operativo-<id>`; if they are gone it rebuilds them with `servicio.congelar`, the same code the
run uses, and says so), runs one step at a time, prints minutes per step, and is resumable (a
step with `ensemble_agreement.json` is skipped). In demo mode the cron does not run ELMFIRE, so
it does not compete with another window. Any other demo forecast has no checkbox for the layer.
It runs against a local database and runner, never on Railway. To put the ensemble of a
Railway forecast (live or demo) on the dashboard, use the export → local run → register path
of §10 (skill `ensamble-local`).

## 9. Accounts

One per person, created by script; the initial password is printed and changed by the user
under "Cuenta".

```bash
cd frontend
DATABASE_URL=postgresql://… npm run usuarios -- crear jurado@x.com "Nombre" [cliente|admin]
DATABASE_URL=postgresql://… npm run usuarios -- resetear jurado@x.com
DATABASE_URL=postgresql://… npm run usuarios -- listar
```

## 10. Live mode

The admin switches the mode to `vivo`. Every 30 min inside the pass windows the cron ticks:
FIRMS (last 2 days) → fires → a window for each new pass. Polling every 30 min instead of every 3 h costs one small
FIRMS request per tick (ELMFIRE runs only on a new pass) and avoids adding up to 3 h on top of
FIRMS's own latency. VIIRS passes over the AOI cluster at 04–07 and 18–20 UTC (local FIRMS
2015–2026: no pass outside them), so with FIRMS's ≤3 h latency the cron only runs 05–10 and
18–23 UTC and the api and runner can sleep the rest of the day. Within a cluster only the first
pass that gets a forecast runs ELMFIRE (`RACIMO_H`): the next satellite 1–2 h later would hold the
runner for a near-duplicate. A failed window
(GFS or runner down) is retried on the next tick; the client keeps the last good forecast.

Railway never computes the GEFS ensemble (31 members, ~35 min and ~1.7 GB per run). It is run
by hand on the local machine and only its `ensemble_agreement.json` is uploaded into the
forecast's output folder (skill `ensamble-local`); that file is what marks the forecast as
having an ensemble. Railway keeps `phi.tif` (the seed on the grid) so the local run can rebuild
the same frozen inputs: `scripts/ensamble_exportar.py` (on Railway) prints the window and the
seed, `scripts/ensamble_local.py` rebuilds the static inputs from `data/operativo/estaticos/`,
aborts if they do not fall on the seed's grid and runs the 31 members, and
`scripts/ensamble_registrar.py` (on Railway, contract on stdin) validates it before placing it
where the map reads it. All three go through `railway ssh`; no public API endpoint. Once a
forecast is done, `podar` keeps only what the map reads again (`wind-field.json`, `ignicion.*`)
plus `phi.tif`; a one-off `scripts/podar_volumen.py` applied that to the older forecasts on
2026-11-07 (34 GB → 0.7 GB). At least 24 valid members are required, and the artifact records the
effective denominator and failures. `calcular_ensamble` now only decides whether clients see
the layer (admin toggle "Acuerdo del ensamble visible para clientes"). The client still chooses
whether to show that layer, which is offered only on forecasts that have it, is off by default
and is explicitly described as agreement rather than probability.
