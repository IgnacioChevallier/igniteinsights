# IGN-26 · Diseño de validación

> Estado: **especificado, no implementado.** Es la única parte viva de la auditoría del
> 2026-08-31, extraída de `docs/historico/SIMULATION_AUDIT.md` §12 el 2026-09-15 para que
> no siguiera enterrada en un documento histórico.
>
> Se conserva la numeración original (§12.1 … §12.5) porque el resto de los planes la citan
> con esos números. Bloquea: `ETAPA-A §A7` (congelar el baseline) y `ETAPA-B §B6`
> (comparación de mapas de combustible contra el perímetro observado).

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

