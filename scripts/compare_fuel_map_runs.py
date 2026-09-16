"""B6 — Compare ELMFIRE runs that differ only in the fuel map.

Same ignition, same weather, same topography, same ADJ: only fbfm40.tif changes. Scores the
**growth ring only** — cells the model burned that were not already in the FIRMS seed
(`IGN-26-VALIDACION.md` §12.1). Scoring the union would mostly measure the seed, which matches
the burn scar by construction.

    uv run python scripts/compare_fuel_map_runs.py
"""
import argparse
from pathlib import Path

import numpy as np
import rasterio

CELL_HA = 0.09  # 30 m × 30 m


def load(run: str, inputs_root: Path, outputs_root: Path) -> dict:
    out_dir = outputs_root / f"cmp_{run}"
    toa_files = sorted(out_dir.glob("time_of_arrival*.tif"))
    if not toa_files:
        raise FileNotFoundError(f"no time_of_arrival raster in {out_dir}")
    with rasterio.open(toa_files[-1]) as src:
        toa = src.read(1).astype("float64")
    with rasterio.open(inputs_root / f"cmp_{run}" / "phi.tif") as src:
        phi = src.read(1)
    with rasterio.open(inputs_root / f"cmp_{run}" / "fbfm40.tif") as src:
        fbfm = src.read(1)

    seed = phi <= 0                      # ignition_builder: phi > 0 is unburned
    burned = toa > 0                     # isochrone_converter's own rule
    growth = burned & ~seed

    flin = None
    flin_files = sorted(out_dir.glob("flin*.tif"))
    if flin_files:
        with rasterio.open(flin_files[-1]) as src:
            f = src.read(1).astype("float64")
        vals = f[growth & (f > 0)]
        flin = vals if vals.size else None

    return {"toa": toa, "seed": seed, "burned": burned, "growth": growth,
            "fbfm": fbfm, "flin": flin}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", default=["worldcover", "mapbiomas", "ccsbap"])
    ap.add_argument("--inputs-root", type=Path, default=Path("data/elmfire/inputs"))
    ap.add_argument("--outputs-root", type=Path, default=Path("data/elmfire/outputs"))
    args = ap.parse_args()

    runs = {name: load(name, args.inputs_root, args.outputs_root) for name in args.runs}
    first = runs[args.runs[0]]
    print(f"Semilla FIRMS (phi ≤ 0): {first['seed'].sum() * CELL_HA:,.0f} ha "
          f"— idéntica en las {len(runs)} corridas: "
          f"{all((r['seed'] == first['seed']).all() for r in runs.values())}")

    print("\n=== Crecimiento predicho a 12 h (sólo el anillo, sin la semilla) ===")
    print(f"{'Mapa':14s}{'anillo (ha)':>14s}{'vs baseline':>13s}{'semilla+anillo':>15s}"
          f"{'FLI mediana':>14s}{'FLI p90':>10s}")
    base = runs[args.runs[0]]["growth"].sum() * CELL_HA
    for name, r in runs.items():
        ring = r["growth"].sum() * CELL_HA
        med = f"{np.median(r['flin']):.1f}" if r["flin"] is not None else "—"
        p90 = f"{np.percentile(r['flin'], 90):.0f}" if r["flin"] is not None else "—"
        delta = "—" if name == args.runs[0] else f"{100 * (ring - base) / base:+.1f}%"
        print(f"{name:14s}{ring:14,.0f}{delta:>13s}"
              f"{(r["burned"] | r["seed"]).sum() * CELL_HA:15,.0f}{med:>14s}{p90:>10s}")

    print("\n=== Acuerdo entre mapas sobre el anillo (IoU) ===")
    names = list(runs)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ga, gb = runs[a]["growth"], runs[b]["growth"]
            inter, union = (ga & gb).sum(), (ga | gb).sum()
            print(f"  {a:12s} vs {b:12s}  IoU {inter / union if union else 0:.3f}"
                  f"   sólo {a}: {(ga & ~gb).sum() * CELL_HA:6,.0f} ha"
                  f"   sólo {b}: {(gb & ~ga).sum() * CELL_HA:6,.0f} ha")

    print("\n=== Qué combustible quemó cada corrida (top 6 del anillo) ===")
    from app.elmfire.builder.fuels_builder import fuel_model_info
    for name, r in runs.items():
        codes, counts = np.unique(r["fbfm"][r["growth"]], return_counts=True)
        top = sorted(zip(codes, counts), key=lambda p: -p[1])[:6]
        total = counts.sum() or 1
        pretty = ", ".join(
            f"{fuel_model_info(int(c))['name']} {100 * n / total:.0f}%" for c, n in top
        )
        print(f"  {name:12s} {pretty}")


if __name__ == "__main__":
    main()
