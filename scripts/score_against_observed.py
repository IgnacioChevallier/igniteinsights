"""IGN-26 harness B — puntuar una corrida contra el perímetro observado.

Referencia independiente: la cicatriz final de Sentinel-2 del dataset de máscaras, 196
tiles de 20 m. FIRMS no sirve como referencia acá porque es lo que construyó `phi`.

Regla que decide si el número significa algo (IGN-26 §12.1): **se puntúa sólo el anillo de
crecimiento**, nunca la unión con la semilla. El 84 % de lo que una corrida reporta como
quemado es la propia semilla, que coincide con la cicatriz por construcción; puntuar la
unión daría un IoU halagüeño que no mide nada del modelo.

Se estratifica por `pct_quemado` (§12.4): los tiles cerca de 0 o 100 son triviales; los
informativos son los de quema parcial, que contienen el borde real del fuego.

    uv run python scripts/score_against_observed.py --run cmp_b5_ccsbap
"""
import argparse
import csv
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

CELL_HA = 0.09
BANDAS = [(0, 10), (10, 40), (40, 70), (70, 100.1)]


class Grilla:
    """La grilla de la corrida. Las máscaras se llevan a ella y no al revés: puntuar a 20 m
    inventaría una resolución que el modelo no tiene."""

    def __init__(self, referencia: Path) -> None:
        with rasterio.open(referencia) as ref:
            self.transform, self.crs = ref.transform, ref.crs
            self.shape = (ref.height, ref.width)

    def traer(self, tile: Path, contenido: bool) -> np.ndarray:
        """Reproyecta un tile a la grilla: su máscara quemada, o dónde el tile tiene dato."""
        destino = np.zeros(self.shape, dtype=np.uint8)
        with rasterio.open(tile) as src:
            fuente = (src.read(1) if contenido
                      else np.ones((src.height, src.width), dtype=np.uint8))
            reproject(source=fuente, destination=destino,
                      src_transform=src.transform, src_crs=src.crs,
                      dst_transform=self.transform, dst_crs=self.crs,
                      resampling=Resampling.mode if contenido else Resampling.nearest)
        return destino.astype(bool)


def cargar_observado(tiles_dir: Path, grilla: Grilla) -> tuple[np.ndarray, np.ndarray]:
    """Mosaico de las máscaras sobre nuestra grilla, y dónde hay dato observado."""
    observado = np.zeros(grilla.shape, dtype=bool)
    cobertura = np.zeros(grilla.shape, dtype=bool)
    for tile in sorted(tiles_dir.glob("*.tif")):
        observado |= grilla.traer(tile, contenido=True)
        cobertura |= grilla.traer(tile, contenido=False)
    return observado, cobertura


def metricas(pred: np.ndarray, obs: np.ndarray, donde: np.ndarray) -> dict:
    p, o = pred & donde, obs & donde
    tp, fp, fn = int((p & o).sum()), int((p & ~o).sum()), int((~p & o).sum())
    union = tp + fp + fn
    return {
        "tp_ha": tp * CELL_HA, "fp_ha": fp * CELL_HA, "fn_ha": fn * CELL_HA,
        "iou": tp / union if union else 0.0,
        "recall": tp / (tp + fn) if (tp + fn) else 0.0,
        "precision": tp / (tp + fp) if (tp + fp) else 0.0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="nombre bajo data/elmfire/{inputs,outputs}")
    ap.add_argument("--tiles", type=Path, default=Path("../mask-dataset-gen/dataset/mascaras"))
    ap.add_argument("--metadata", type=Path,
                    default=Path("../mask-dataset-gen/dataset/metadata.csv"))
    args = ap.parse_args()

    inputs = Path("data/elmfire/inputs") / args.run
    outputs = Path("data/elmfire/outputs") / args.run
    toa_files = sorted(outputs.glob("time_of_arrival*.tif"))
    if not toa_files:
        raise SystemExit(f"{outputs} no tiene time_of_arrival: ¿corrió la simulación?")

    with rasterio.open(toa_files[-1]) as src:
        quemado_pred = src.read(1) > 0
    with rasterio.open(inputs / "phi.tif") as src:
        semilla = src.read(1) <= 0

    grilla = Grilla(inputs / "phi.tif")
    observado, cobertura = cargar_observado(args.tiles, grilla)
    print(f"Corrida: {args.run}")
    print(f"Tiles observados sobre el dominio: {100 * cobertura.mean():.1f} % de la grilla")
    print(f"Semilla FIRMS: {semilla.sum() * CELL_HA:,.0f} ha · "
          f"observado dentro de cobertura: {(observado & cobertura).sum() * CELL_HA:,.0f} ha")

    # El anillo: lo que el modelo agregó, contra lo que la cicatriz agrega sobre la semilla.
    donde = cobertura & ~semilla
    m = metricas(quemado_pred & ~semilla, observado & ~semilla, donde)
    print("\n=== Anillo de crecimiento (sin la semilla) ===")
    print(f"  IoU {m['iou']:.3f} · recall {m['recall']:.3f} · precisión {m['precision']:.3f}")
    print(f"  acierto {m['tp_ha']:,.0f} ha · falso positivo {m['fp_ha']:,.0f} ha · "
          f"no predicho {m['fn_ha']:,.0f} ha")

    if not args.metadata.exists():
        return
    filas = list(csv.DictReader(args.metadata.open()))
    print("\n=== Estratificado por pct_quemado del tile ===")
    print(f"{'banda':>12s}{'tiles':>7s}{'IoU':>8s}{'recall':>9s}{'precisión':>11s}")
    for lo, hi in BANDAS:
        elegidos = [f for f in filas if lo <= float(f["pct_quemado"]) < hi]
        if not elegidos:
            continue
        mascara = np.zeros_like(cobertura)
        for f in elegidos:
            ruta = args.tiles / f"{f['tile']}.tif"
            if ruta.exists():
                mascara |= grilla.traer(ruta, contenido=False)
        mb = metricas(quemado_pred & ~semilla, observado & ~semilla, mascara & ~semilla)
        print(f"{f'{lo:.0f}-{hi:.0f} %':>12s}{len(elegidos):7d}{mb['iou']:8.3f}"
              f"{mb['recall']:9.3f}{mb['precision']:11.3f}")


if __name__ == "__main__":
    main()
