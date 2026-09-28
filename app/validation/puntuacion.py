"""Aritmética de la validación: llevar referencias a la grilla, contar y coser tiempos.

Reglas que deciden si un número significa algo (IGN-26):

- **Se puntúa el anillo, nunca la semilla** (§12.1). Lo que ya ardía al empezar coincide
  con lo observado por construcción e infla cualquier métrica.
- **La exclusión no cuenta**: ni acierto, ni falso positivo, ni no predicho. Ahí van las
  celdas sin observación válida y los cambios que la máscara no atribuye al incendio.
- **Las referencias salen de la observación, nunca de la predicción**. En una cadena
  sembrada con lo predicho, "ya quemado" para el modelo y para la referencia son cosas
  distintas, y mezclarlas haría que el modelo se puntúe contra sí mismo.

Sin I/O de benchmark: recibe arrays y rutas de máscaras, devuelve arrays y dicts.
"""
import csv
from pathlib import Path

import numpy as np
import rasterio
from rasterio.errors import WindowError
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds

# Fuera de este rango lo predicho ya no es comparable con lo observado: un recall alto
# quemando 458× la referencia no significa nada (RESULTADOS.md §6).
SESGO_ALARMA = (0.5, 2.0)
BANDAS_PCT = [(0, 10), (10, 40), (40, 70), (70, 100.1)]
# Capas de mask-dataset-gen que la máscara NO atribuye al incendio objetivo.
EXCLUIDAS_POR_DEFECTO = ("cambio_no_confirmado", "otro_incendio_probable")


class Grilla:
    """La grilla de la corrida. Las máscaras se llevan a ella y no al revés: puntuar a 20 m
    inventaría una resolución que el modelo no tiene."""

    def __init__(self, referencia: Path) -> None:
        with rasterio.open(referencia) as ref:
            self.transform, self.crs = ref.transform, ref.crs
            self.shape = (ref.height, ref.width)
            self.perfil = ref.profile

    @property
    def celda_ha(self) -> float:
        return abs(self.transform.a * self.transform.e) / 10_000

    def traer(self, tile: Path, contenido: bool) -> tuple[Window, np.ndarray] | None:
        """Reproyecta un tile a la grilla, **sólo dentro de su ventana**: un tile de 5 km
        toca una porción mínima del dominio y reproyectarlo entero costaba 196 pasadas."""
        with rasterio.open(tile) as src:
            izq, abajo, der, arriba = transform_bounds(src.crs, self.crs, *src.bounds)
            ventana = from_bounds(izq, abajo, der, arriba, self.transform)
            ventana = ventana.round_offsets().round_lengths()
            try:
                ventana = ventana.intersection(Window(0, 0, self.shape[1], self.shape[0]))
            except WindowError:
                return None   # el tile cae entero fuera del dominio
            if ventana.width <= 0 or ventana.height <= 0:
                return None
            destino = np.zeros((int(ventana.height), int(ventana.width)), dtype=np.uint8)
            fuente = ((src.read(1) == 1).astype(np.uint8) if contenido
                      else np.ones((src.height, src.width), dtype=np.uint8))
            reproject(source=fuente, destination=destino,
                      src_transform=src.transform, src_crs=src.crs,
                      dst_transform=rasterio.windows.transform(ventana, self.transform),
                      dst_crs=self.crs,
                      resampling=Resampling.mode if contenido else Resampling.nearest)
        return ventana, destino.astype(bool)

    def mosaico(self, tiles: list[Path], contenido: bool = True) -> np.ndarray:
        lienzo = np.zeros(self.shape, dtype=bool)
        for tile in tiles:
            recorte = self.traer(tile, contenido)
            if recorte is None:
                continue
            ventana, datos = recorte
            f, c = int(ventana.row_off), int(ventana.col_off)
            lienzo[f:f + datos.shape[0], c:c + datos.shape[1]] |= datos
        return lienzo


def cargar_cicatriz(run_dir: Path, grilla: Grilla,
                    excluidas: tuple[str, ...] = EXCLUIDAS_POR_DEFECTO,
                    ) -> tuple[np.ndarray, np.ndarray]:
    """(positivo, excluido) de un run de mask-dataset-gen, sobre la grilla.

    Acepta los dos formatos: `legacy-v1` (sólo `mascaras/`, la cobertura es la huella de
    los tiles) y el de runs con filtro de evento (`calidad/observacion_valida` como
    cobertura y capas de cambio no atribuido). Lo que no está cubierto queda excluido.
    """
    tiles = sorted((run_dir / "mascaras").glob("*.tif"))
    if not tiles:
        raise FileNotFoundError(f"{run_dir}/mascaras no tiene tiles")
    positivo = grilla.mosaico(tiles)
    valida = run_dir / "calidad" / "observacion_valida"
    cobertura = (grilla.mosaico(sorted(valida.glob("*.tif"))) if valida.is_dir()
                 else grilla.mosaico(tiles, contenido=False))
    excluido = ~cobertura
    for capa in excluidas:
        if (run_dir / capa).is_dir():
            excluido |= grilla.mosaico(sorted((run_dir / capa).glob("*.tif")))
    return positivo & ~excluido, excluido


def bandas_pct(run_dir: Path, grilla: Grilla) -> dict[str, np.ndarray]:
    """Celdas de la grilla por banda de porcentaje quemado del tile (§12.4). Los tiles
    cerca de 0 o 100 son triviales; los informativos son los que contienen el borde."""
    filas = list(csv.DictReader((run_dir / "metadata.csv").open()))
    columna = "pct_quemado_valido" if "pct_quemado_valido" in filas[0] else "pct_quemado"
    salida = {}
    for lo, hi in BANDAS_PCT:
        tiles = [run_dir / "mascaras" / f"{f['tile']}.tif" for f in filas
                 if lo <= float(f[columna]) < hi]
        tiles = [t for t in tiles if t.exists()]
        if tiles:
            salida[f"{lo:.0f}-{min(hi, 100):.0f}"] = grilla.mosaico(tiles, contenido=False)
    return salida


def metricas(pred: np.ndarray, ref: np.ndarray, celda_ha: float,
             excluir: np.ndarray | None = None) -> dict:
    """Confusión sobre las celdas no excluidas. `pred` y `ref` ya vienen sin la semilla."""
    donde = ~excluir if excluir is not None else np.ones(pred.shape, dtype=bool)
    p, o = pred & donde, ref & donde
    tp, fp, fn = int((p & o).sum()), int((p & ~o).sum()), int((~p & o).sum())
    sesgo = (tp + fp) / (tp + fn) if tp + fn else None
    return {
        "tp_ha": tp * celda_ha, "fp_ha": fp * celda_ha, "fn_ha": fn * celda_ha,
        "predicho_ha": (tp + fp) * celda_ha, "observado_ha": (tp + fn) * celda_ha,
        "iou": tp / (tp + fp + fn) if tp + fp + fn else None,
        "dice": 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "precision": tp / (tp + fp) if tp + fp else None,
        "sesgo_area": sesgo,
        "alarma_sesgo": sesgo is not None and not SESGO_ALARMA[0] <= sesgo <= SESGO_ALARMA[1],
        "tp": tp, "fp": fp, "fn": fn,
    }


def horas_relativas(toa: np.ndarray, tstart_s: float) -> np.ndarray:
    """Horas desde el inicio de la ventana; NaN donde no llegó el fuego.

    ELMFIRE escribe el TOA en tiempo **absoluto**: las celdas de la semilla valen
    `SIMULATION_TSTART`, y lo no quemado queda en nodata negativo (verificado sobre
    `cmp_aoi_ccsbap`, TSTART 6.360 s: mínimo 6.360, máximo ≈ TSTOP).
    """
    horas = (toa.astype("float64") - tstart_s) / 3600.0
    return np.where(toa > 0, horas, np.nan)


def coser(ventanas: list[tuple[float, np.ndarray, np.ndarray]]) -> np.ndarray:
    """Una sola línea de tiempo para toda la cadena: (desfase_h, horas_rel, semilla).

    Cada celda conserva la **primera** hora en que algo la dio por quemada. La semilla de
    una ventana aparece en su desfase si nadie la había quemado antes: con la política
    `observacion`, FIRMS puede sembrar celdas que el modelo nunca alcanzó.
    """
    cosido = np.full(ventanas[0][1].shape, np.inf)
    for desfase_h, horas, semilla in ventanas:
        cosido = np.fmin(cosido, np.where(semilla, desfase_h, np.inf))
        cosido = np.fmin(cosido, desfase_h + horas)   # fmin ignora los NaN
    return np.where(np.isinf(cosido), np.nan, cosido)


def error_llegada(horas_pred: np.ndarray, horas_det: np.ndarray) -> dict:
    """Llegada predicha menos detección, en horas, sobre las celdas con detección.

    La detección es una **cota superior** de la llegada real (el satélite pasa después),
    así que un error negativo moderado es lo esperable y el signo importa.
    """
    con_det = ~np.isnan(horas_det)
    if not con_det.any():
        return {"detecciones": 0, "mediana_h": None, "nunca_alcanzadas": None}
    alcanzadas = con_det & ~np.isnan(horas_pred)
    diferencia = horas_pred[alcanzadas] - horas_det[alcanzadas]
    return {
        "detecciones": int(con_det.sum()),
        "mediana_h": float(np.median(diferencia)) if diferencia.size else None,
        "nunca_alcanzadas": float(1 - alcanzadas.sum() / con_det.sum()),
    }


def area_igualada(horas: np.ndarray, ref: np.ndarray, celda_ha: float,
                  excluir: np.ndarray) -> dict:
    """Forma separada de velocidad: el Dice en la hora t* en que lo predicho iguala el área
    observada.

    Contra una cicatriz final de un incendio combatido, Dice en el último corte mezcla dónde
    quema el modelo con cuán rápido: un modelo sin supresión que acelera cubre más cicatriz
    y la desborda. Cortar donde las áreas coinciden deja sólo la forma; t* frente al
    horizonte real dice la velocidad. `horas` es la línea de tiempo cosida, NaN donde no
    llegó el fuego y en la semilla.
    """
    donde = ~excluir
    objetivo = int((ref & donde).sum())
    llegadas = np.sort(horas[donde & ~np.isnan(horas)])
    if objetivo == 0 or llegadas.size == 0:
        return {"hora": None, "alcanzada": False, "dice": None, "iou": None}
    alcanzada = llegadas.size >= objetivo
    t = float(llegadas[objetivo - 1] if alcanzada else llegadas[-1])
    m = metricas(np.nan_to_num(horas, nan=np.inf) <= t, ref, celda_ha, excluir)
    return {"hora": t, "alcanzada": alcanzada, "dice": m["dice"], "iou": m["iou"],
            "recall": m["recall"], "precision": m["precision"]}
