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
detection in the last 24 h. Its stable ID is a digest of its first detection. Its display name
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
ensemble agreement only if the admin enabled it. Time-of-arrival and fireline intensity are
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
5. **cron** (live mode): a Railway cron service, every 30 min, running
   `curl -fsS -X POST http://api.railway.internal:8000/api/v1/operativo/tick`. The tick does
   nothing while the mode is `demo`.

The runner keeps the 15-min HTTP limit in mind: a window over a fire box runs in minutes.

## 8. The demo

```bash
AOI_NORTH=-41.90 uv run python scripts/demo_operativo.py 2026-01-05 2026-01-09
```

Only Puerto Patriada, from its first pass (2026-01-05 19:20 UTC); detections before that instant
and other fires in the AOI are deliberately excluded from grouping, seeding and the replay. It
leaves the mode in `demo` with the clock on
the first forecast; the admin
walks forward from there. Starting on day 1 is deliberate: it shows the weak point and how each
pass corrects it. `AOI_NORTH` matters only if `.env` overrides it (the repo `.env` had
`-42.9`, which leaves Patriada out).

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

The admin switches the mode to `vivo`. Every 30 min the cron ticks: FIRMS (last 2 days) →
fires → a window for each new pass. Polling every 30 min instead of every 3 h costs one small
FIRMS request per tick (ELMFIRE runs only on a new pass) and avoids adding up to 3 h on top of
FIRMS's own latency. VIIRS passes over the AOI cluster at 04–07 and 18–20 UTC. A failed window
(GFS or runner down) is retried on the next tick; the client keeps the last good forecast.

When the admin enables `calcular_ensamble`, each new deterministic P-24 run also freezes its
non-weather inputs and runs the 31 GEFS members. At least 24 valid members are required. The
agreement artifact records the effective denominator and failures, and is served with the
simulation; a failed optional ensemble never hides an otherwise valid deterministic forecast.
The client still chooses whether to show that layer, which is off by default and explicitly
described as agreement rather than probability.
