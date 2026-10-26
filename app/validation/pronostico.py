"""Protocolo P-24: pronóstico a 12 y 24 h desde el perímetro observado.

Diseño en docs/resultados/DIA-1-PROPUESTA.md §2. Cada pasada VIIRS es un reinicio: ELMFIRE arranca
de lo observado hasta esa hora y se puntúa sólo el crecimiento (IGN-26 §12.1), contra la cicatriz
dNBR truncada a lo que VIIRS ya había visto al plazo. Lo comparable es el mismo crecimiento
predicho por la cadena de modelo-v0 y por una extrapolación ingenua (persistencia).
"""
import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import rasterio.features
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from app.validation import puntuacion as p

PLAZOS_H = (12, 24)
SEPARACION_PASADAS_H = 2.0   # detecciones a menos de esto son la misma pasada del satélite


# Lo que tarda cada dato en estar a mano (FIRMS FAQ: NRT "within 3 hours", best effort;
# GFSClient.resolve_cycle: un ciclo está completo ~4 h después de su hora nominal).
LATENCIA_FIRMS_H = 3
DISPONIBILIDAD_GFS_H = 4


def ciclo_disponible(t: datetime) -> datetime:
    """El último ciclo GFS publicado cuando la pasada de las `t` ya se ve en FIRMS: el que
    tenía quien miraba el panel, y no los análisis de ciclos posteriores (hindcast)."""
    visto = t + timedelta(hours=LATENCIA_FIRMS_H - DISPONIBILIDAD_GFS_H)
    return visto.replace(hour=visto.hour - visto.hour % 6, minute=0, second=0, microsecond=0)


def pasadas(tiempos: pd.Series, separacion_h: float = SEPARACION_PASADAS_H) -> list[pd.Timestamp]:
    """La hora de la última detección de cada pasada: lo observado está completo recién ahí."""
    t = pd.Series(sorted(tiempos))
    if t.empty:
        return []
    grupo = (t.diff() > pd.Timedelta(hours=separacion_h)).cumsum()
    return list(t.groupby(grupo).max())


def ventana_desde(t: datetime, horas: int = 24) -> dict:
    """Una ventana que arranca en `t`: la banda 0 del clima en la hora entera anterior."""
    t0 = t.replace(minute=0, second=0, microsecond=0)
    return {"t0": t0.isoformat(), "horas": horas, "tstart_s": (t - t0).total_seconds()}


def bandas_necesarias(horas: int, tstart_s: float) -> int:
    """Bandas horarias para interpolar hasta TSTOP: con minutos de arranque, una más que
    `horas + 1` (si no, ELMFIRE sostiene la última banda el final de la ventana)."""
    return math.ceil(tstart_s / 3600 + horas) + 1


def hora_en_base(h: int, desfases: list[int], horas: list[int]) -> tuple[int, int]:
    """(ventana, banda) del paquete base con la hora `h` desde su inicio. Las ventanas base son
    contiguas y comparten la hora de borde (la banda final de una es la 0 de la siguiente)."""
    for j in range(len(desfases) - 1, -1, -1):
        if desfases[j] <= h <= desfases[j] + horas[j]:
            return j, h - desfases[j]
    raise ValueError(f"la hora {h} no está en el clima del caso base")


def puntuar(pred: np.ndarray, semilla: np.ndarray, cicatriz: np.ndarray, excluido: np.ndarray,
            vistas_h: np.ndarray, deteccion_h: np.ndarray, plazo_h: float,
            celda_ha: float) -> dict:
    """El crecimiento predicho a `plazo_h` contra dos referencias.

    - `cicatriz`: la cicatriz ya vista por VIIRS al plazo, fuera de la semilla. Lo de la
      cicatriz que todavía no se vio ardió después (o no se vio) y se excluye, como
      `hasta_horizonte` en el empaquetado. También se excluye el anillo ya visto al
      reiniciar (`vistas_h <= 0` fuera de la semilla): `vistas` usa discos de 375 m y la
      semilla 187,5 m, y ese anillo, pegado a la semilla, no es crecimiento a pronosticar
      (DIAGNOSTICO-PRECISION-E2E §4: inflaba el ΔDice de P-24 a 12 h de +0,096 a +0,168).
    - `firms`: las detecciones nuevas hasta el plazo. Sólo el recall es fiable.
    """
    crecimiento = pred & ~semilla
    vistos = vistas_h <= plazo_h
    anillo = (vistas_h <= 0) & ~semilla
    cic = p.metricas(crecimiento, cicatriz & vistos & ~semilla & ~anillo, celda_ha,
                     excluido | semilla | anillo | (cicatriz & ~vistos))
    nuevas = (deteccion_h >= 0) & (deteccion_h <= plazo_h) & ~semilla
    fir = p.metricas(crecimiento, nuevas, celda_ha, semilla)
    return {"cicatriz": cic, "firms": {k: fir[k] for k in ("recall", "observado_ha")}}


def quemado_en(ventanas: list[tuple[datetime, datetime, np.ndarray, np.ndarray]],
               t: datetime) -> np.ndarray:
    """Lo que una cadena daba por quemado a la hora `t`. `ventanas`: (inicio, fin, semilla,
    horas desde el inicio). En el borde entre dos ventanas, la que termina (la misma corrida);
    pasado el final de la cadena, lo que dejó la última ventana."""
    if t < ventanas[0][0]:
        raise ValueError(f"{t} es anterior a la cadena")
    inicio, fin, semilla, horas = next((v for v in ventanas if v[0] <= t <= v[1]), ventanas[-1])
    limite = min(t, fin)
    return semilla | (np.nan_to_num(horas, nan=np.inf) <= (limite - inicio).total_seconds() / 3600)


def persistencia(semilla: np.ndarray, previa: np.ndarray, dt_h: float, plazo_h: float,
                 grilla: p.Grilla) -> np.ndarray:
    """Extrapolación ingenua: la semilla crece en todas direcciones lo mismo que creció su radio
    equivalente entre la observación previa y ésta, escalado al plazo."""
    celda_m2 = grilla.celda_ha * 1e4
    r_ahora = math.sqrt(semilla.sum() * celda_m2 / math.pi)
    r_antes = math.sqrt(previa.sum() * celda_m2 / math.pi)
    radio_m = max(r_ahora - r_antes, 0.0) * plazo_h / dt_h if dt_h > 0 else 0.0
    if radio_m <= 0 or not semilla.any():
        return semilla.copy()
    poligonos = [shape(g) for g, _ in rasterio.features.shapes(
        semilla.astype("uint8"), mask=semilla, transform=grilla.transform)]
    crecido = unary_union(poligonos).buffer(radio_m)
    return rasterio.features.rasterize([(mapping(crecido), 1)], out_shape=semilla.shape,
                                       transform=grilla.transform, dtype="uint8").astype(bool)


def resumir(filas: list[dict], plazo_h: int, contra: str = "cadena") -> dict:
    """El resultado principal de P-24 (§2.4): por incendio, la media del Dice del crecimiento en
    los reinicios k ≥ 1 (la ventana 0 arranca en la ignición, igual que la cadena); entre
    incendios, la mediana del ΔDice contra `contra` y cuántos incendios mejoran."""
    por_incendio: dict[str, dict[str, list[float]]] = {}
    for f in filas:
        if f["n"] == 0:
            continue
        m = f["plazos"].get(str(plazo_h), {})
        if "p24" not in m or contra not in m:
            continue
        a, b = m["p24"]["cicatriz"]["dice"], m[contra]["cicatriz"]["dice"]
        if a is None or b is None:
            continue
        d = por_incendio.setdefault(f["incendio"], {"p24": [], contra: []})
        d["p24"].append(a)
        d[contra].append(b)
    medias = {inc: {k: float(np.mean(v)) for k, v in d.items()} for inc, d in por_incendio.items()}
    deltas = [m["p24"] - m[contra] for m in medias.values()]
    return {"plazo_h": plazo_h, "contra": contra, "incendios": medias,
            "mediana_delta": float(np.median(deltas)) if deltas else None,
            "mejoran": sum(x > 0 for x in deltas), "n": len(deltas)}
