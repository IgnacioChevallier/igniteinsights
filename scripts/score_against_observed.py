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
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.errors import WindowError
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds

CELL_HA = 0.09
BANDAS = [(0, 10), (10, 40), (40, 70), (70, 100.1)]


class Grilla:
    """La grilla de la corrida. Las máscaras se llevan a ella y no al revés: puntuar a 20 m
    inventaría una resolución que el modelo no tiene."""

    def __init__(self, referencia: Path) -> None:
        with rasterio.open(referencia) as ref:
            self.transform, self.crs = ref.transform, ref.crs
            self.shape = (ref.height, ref.width)

    def traer(self, tile: Path, contenido: bool) -> tuple[Window, np.ndarray] | None:
        """Reproyecta un tile a la grilla, **sólo dentro de su ventana**.

        Reproyectar cada tile sobre las 8,3 M celdas del dominio costaba 196 pasadas
        completas por nada: un tile de 5 km toca una porción mínima de la grilla.
        """
        with rasterio.open(tile) as src:
            izq, abajo, der, arriba = transform_bounds(src.crs, self.crs, *src.bounds)
            ventana = from_bounds(izq, abajo, der, arriba, self.transform)
            ventana = ventana.round_offsets().round_lengths()
            dominio = Window(0, 0, self.shape[1], self.shape[0])
            try:
                ventana = ventana.intersection(dominio)
            except WindowError:
                return None   # el tile cae entero fuera del dominio
            if ventana.width <= 0 or ventana.height <= 0:
                return None
            destino = np.zeros((int(ventana.height), int(ventana.width)), dtype=np.uint8)
            fuente = (src.read(1) if contenido
                      else np.ones((src.height, src.width), dtype=np.uint8))
            reproject(source=fuente, destination=destino,
                      src_transform=src.transform, src_crs=src.crs,
                      dst_transform=rasterio.windows.transform(ventana, self.transform),
                      dst_crs=self.crs,
                      resampling=Resampling.mode if contenido else Resampling.nearest)
        return ventana, destino.astype(bool)

    def pegar(self, lienzo: np.ndarray, recorte: tuple[Window, np.ndarray] | None) -> None:
        if recorte is None:
            return
        ventana, datos = recorte
        f, c = int(ventana.row_off), int(ventana.col_off)
        lienzo[f:f + datos.shape[0], c:c + datos.shape[1]] |= datos


def cargar_observado(tiles_dir: Path, grilla: Grilla) -> tuple[np.ndarray, np.ndarray]:
    """Mosaico de las máscaras sobre nuestra grilla, y dónde hay dato observado."""
    observado = np.zeros(grilla.shape, dtype=bool)
    cobertura = np.zeros(grilla.shape, dtype=bool)
    for tile in sorted(tiles_dir.glob("*.tif")):
        grilla.pegar(observado, grilla.traer(tile, contenido=True))
        grilla.pegar(cobertura, grilla.traer(tile, contenido=False))
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
    ap.add_argument("--caso", default=None,
                    help="escribe artefactos para el dashboard en data/validation/harness_b/<caso>")
    ap.add_argument("--mapa", default=None, help="etiqueta del mapa de combustible")
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

    if args.caso:
        escribir_artefactos(args, grilla, semilla, observado, cobertura, quemado_pred, m)

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
                grilla.pegar(mascara, grilla.traer(ruta, contenido=False))
        mb = metricas(quemado_pred & ~semilla, observado & ~semilla, mascara & ~semilla)
        print(f"{f'{lo:.0f}-{hi:.0f} %':>12s}{len(elegidos):7d}{mb['iou']:8.3f}"
              f"{mb['recall']:9.3f}{mb['precision']:11.3f}")


def escribir_artefactos(args, grilla, semilla, observado, cobertura, quemado_pred, m) -> None:
    """Deja la matriz de confusión y las métricas donde el dashboard las lee.

    Códigos del ráster: 0 nada · 1 semilla · 2 acierto · 3 predicho sin cicatriz ·
    4 cicatriz no predicha · 5 fuera de la cobertura de tiles (no se puntúa).
    """
    destino = Path("data/validation/harness_b") / args.caso / (args.mapa or args.run)
    destino.mkdir(parents=True, exist_ok=True)
    pred = quemado_pred & ~semilla
    ref = observado & ~semilla
    confusion = np.full(semilla.shape, 5, dtype="uint8")
    dentro = cobertura & ~semilla
    confusion[dentro] = 0
    confusion[dentro & pred & ref] = 2
    confusion[dentro & pred & ~ref] = 3
    confusion[dentro & ~pred & ref] = 4
    confusion[semilla] = 1

    with rasterio.open(Path("data/elmfire/inputs") / args.run / "phi.tif") as src:
        perfil = src.profile | {"dtype": "uint8", "count": 1, "nodata": None}
    with rasterio.open(destino / "confusion.tif", "w", **perfil) as dst:
        dst.write(confusion, 1)
    (destino / "metrics.json").write_text(json.dumps({
        "caso": args.caso, "mapa": args.mapa or args.run, "run": args.run,
        "semilla_ha": float(semilla.sum() * CELL_HA),
        "observado_ha": float((observado & cobertura).sum() * CELL_HA),
        "cobertura_pct": float(100 * cobertura.mean()),
        **{k: float(v) for k, v in m.items()},
    }, indent=2))
    print(f"  artefactos → {destino}")


if __name__ == "__main__":
    main()
