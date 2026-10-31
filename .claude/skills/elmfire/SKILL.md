---
name: elmfire
description: ELMFIRE 2025.0212 input/namelist interface reference for igniteinsights. Use before touching app/elmfire/builder/*.py, app/elmfire/runner/*, namelist_writer.py, elmfire.data, or ELMFIRE raster inputs/outputs (dem, slp, asp, fbfm40, cc, ch, cbh, cbd, ws, wd, m1, m10, m100, adj, phi), or when adding features like MODE, DT_METEOROLOGY, crown fire, Monte Carlo, or multi-ignition support.
---

# ELMFIRE interface reference

This repo generates inputs for ELMFIRE 2025.0212 and hands them off to a separate
runner microservice — ELMFIRE itself does not run inside this repo.

- Input rasters + `elmfire.data` namelist are built by `app/elmfire/builder/*.py`
  (`raster_aligner.py`, `fuels_builder.py`, `weather_builder.py`, `canopy_builder.py`,
  `ignition_builder.py`, `namelist_writer.py`), orchestrated by `app/preparation/service.py`.
- `app/elmfire/runner/client.py` POSTs to the elmfire-runner microservice, which executes
  `mpirun -n 1 elmfire_2025.0212 elmfire.data`.
- Both services share a data volume; expected input filenames are fixed (see
  `references/interface-gotchas.md`).

## Ground-truth hierarchy

When you need to know what ELMFIRE expects, check things in this order — **do not
skip straight to guessing a parameter name or unit**:

1. **This repo's code.** `app/elmfire/builder/namelist_writer.py` is the authoritative
   definition of the `elmfire.data` this project currently emits. The other
   `builder/*.py` files are authoritative for what raster values/units are currently
   produced. If you're changing what we emit, start by reading these.
2. **`references/namelist-reference.md` and `references/interface-gotchas.md`** in this
   skill — condensed, cross-checked against the vendor ELMFIRE tutorials (2025.0212)
   for conventions and gotchas not obvious from the code alone (e.g. unit scaling,
   file-naming rules, MODE differences).
3. **Upstream ELMFIRE source** (`github.com/lautenberger/elmfire`, pinned branch
   `2025.0212`) for anything not covered by the above. The vendor "User Guide" PDF
   we have on file (`docs/referencias/elmfire/User Guide — ELMFIRE 2025.0212 documentation.pdf`)
   turned out to be a bare table of contents with no body content — treat namelist
   groups it lists but that aren't in this skill or in our code (Spotting, Suppression,
   Assets at Risk, full Monte Carlo randomization) as **unverified**.

## Hard rule

Don't invent, rename, or guess an ELMFIRE namelist keyword, raster filename, or unit
scaling. If `references/` here disagrees with `namelist_writer.py` or the builder
code, **the code is right** — fix the reference doc, not the code, unless you have
independently confirmed against upstream ELMFIRE source that the code is wrong.

See `references/namelist-reference.md` for the parameter/keyword catalog and
`references/interface-gotchas.md` for unit/format traps.
