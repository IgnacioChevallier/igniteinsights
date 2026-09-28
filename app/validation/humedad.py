"""Humedad del combustible fino muerto con criterio: las alternativas al delta uniforme.

El m1 de base es la humedad de equilibrio de Nelson con la T y la HR del GFS de 0,25°, que
valen a la altura del terreno del modelo (~1.000 m en el AOI) y no a la de cada celda, sin
sol, sombra ni pendiente (PENDING_PARAMETERS §1.2). Dos correcciones, cada una una perilla
de receta (`modelo_humedad`), calculadas en la corrida desde el clima crudo del paquete:

- `altura`: Nelson con la temperatura llevada a la altura del DEM con el gradiente estándar
  (−6,5 °C/km) y el punto de rocío conservado, así que la HR también cambia.
- `fosberg`: las tablas de Rothermel (1983) / Fosberg que usan NFDRS y BehavePlus: humedad
  de referencia por T y HR, más una corrección por mes, sombra, orientación, pendiente, hora
  y altura relativa a la estación. Los valores son los de BehavePlus
  (`firelab/behave`, `src/behave/fineDeadFuelMoistureTool.cpp`), llevados al hemisferio sur.
"""
from datetime import datetime, timedelta

import numpy as np

GRADIENTE_K_POR_M = -0.0065
PIE_M = 0.3048

# Tabla A: humedad de referencia (%) por temperatura (filas, °F: 10-29, 30-49, 50-69, 70-89,
# 90-109, >109) y HR (columnas, de a 5 %: 0-4 … 95-99, 100).
_RFM = np.array([
    [1, 2, 2, 3, 4, 5, 5, 6, 7, 8, 8, 8, 9, 9, 10, 11, 12, 12, 13, 13, 14],
    [1, 2, 2, 3, 4, 5, 5, 6, 7, 7, 7, 8, 9, 9, 10, 10, 11, 12, 13, 13, 13],
    [1, 2, 2, 3, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 11, 12, 12, 12, 13],
    [1, 1, 2, 2, 3, 4, 5, 5, 6, 7, 7, 8, 8, 8, 9, 10, 10, 11, 12, 12, 13],
    [1, 1, 2, 2, 3, 4, 4, 5, 6, 7, 7, 8, 8, 8, 9, 10, 10, 11, 12, 12, 13],
    [1, 1, 2, 2, 3, 4, 4, 5, 6, 7, 7, 8, 8, 8, 9, 10, 10, 11, 12, 12, 12],
], dtype="float32")

# Tablas B, C y D: corrección (%). Filas, por grupo de meses del hemisferio norte
# (may-jul, feb-abr/ago-oct, nov-ene): 8 expuestas (orientación N, E, S, O × pendiente
# 0-30 %, 31+ %) y 4 sombreadas (N, E, S, O). Columnas: hora (08, 10, 12, 14, 16, 18-ocaso)
# × altura del sitio respecto de la estación (debajo 1.000-2.000 pies, a nivel, arriba).
_CORRECCION = np.array([
    # may-jun-jul, expuesto
    [2, 3, 4, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 2, 3, 4],
    [3, 4, 4, 1, 2, 2, 1, 1, 2, 1, 1, 2, 1, 2, 2, 3, 4, 4],
    [2, 2, 3, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 2, 3, 4, 4],
    [1, 2, 2, 0, 0, 1, 0, 0, 1, 1, 1, 2, 2, 3, 4, 4, 5, 6],
    [2, 3, 3, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 2, 3, 3],
    [2, 3, 3, 1, 1, 2, 0, 1, 1, 0, 1, 1, 1, 1, 2, 2, 3, 3],
    [2, 3, 4, 1, 1, 2, 0, 0, 1, 0, 0, 1, 0, 1, 1, 2, 3, 3],
    [4, 5, 6, 2, 3, 4, 1, 1, 2, 0, 0, 1, 0, 0, 1, 1, 2, 2],
    # may-jun-jul, sombreado
    [4, 5, 5, 3, 4, 5, 3, 3, 4, 3, 3, 4, 3, 4, 5, 4, 5, 5],
    [4, 4, 5, 3, 4, 5, 3, 3, 4, 3, 4, 4, 3, 4, 5, 4, 5, 6],
    [4, 4, 5, 3, 4, 5, 3, 3, 4, 3, 3, 4, 3, 4, 5, 4, 5, 5],
    [4, 5, 6, 3, 4, 5, 3, 3, 4, 3, 3, 4, 3, 4, 5, 4, 4, 5],
    # feb-mar-abr / ago-sep-oct, expuesto
    [3, 4, 5, 1, 2, 3, 1, 1, 2, 1, 1, 2, 1, 2, 3, 3, 4, 5],
    [3, 4, 5, 3, 3, 4, 2, 3, 4, 2, 3, 4, 3, 3, 4, 3, 4, 5],
    [3, 4, 5, 1, 2, 3, 1, 1, 1, 1, 1, 2, 1, 2, 3, 3, 4, 5],
    [3, 3, 4, 1, 1, 1, 1, 1, 1, 1, 2, 3, 3, 4, 5, 3, 4, 6],
    [3, 4, 5, 1, 2, 2, 1, 1, 1, 1, 1, 1, 1, 2, 3, 3, 4, 5],
    [3, 4, 5, 1, 2, 2, 0, 1, 1, 0, 1, 1, 1, 2, 2, 3, 4, 5],
    [3, 4, 5, 1, 2, 3, 1, 1, 1, 1, 1, 1, 1, 2, 3, 3, 4, 5],
    [4, 5, 6, 3, 4, 5, 1, 2, 3, 1, 1, 1, 1, 1, 1, 3, 3, 4],
    # feb-mar-abr / ago-sep-oct, sombreado
    [4, 5, 6, 4, 5, 5, 3, 4, 5, 3, 4, 5, 4, 5, 5, 4, 5, 6],
    [4, 5, 6, 3, 4, 5, 3, 4, 5, 3, 4, 5, 4, 5, 6, 4, 5, 6],
    [4, 5, 6, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 4, 5, 6],
    [4, 5, 6, 4, 5, 6, 3, 4, 5, 3, 4, 5, 3, 4, 5, 4, 5, 6],
    # nov-dic-ene, expuesto
    [4, 5, 6, 3, 4, 5, 2, 3, 4, 2, 3, 4, 3, 4, 5, 4, 5, 6],
    [4, 5, 6, 4, 5, 6, 4, 5, 6, 4, 5, 6, 4, 5, 6, 4, 5, 6],
    [4, 5, 6, 3, 4, 4, 2, 3, 3, 2, 3, 3, 3, 4, 5, 4, 5, 6],
    [4, 5, 6, 2, 3, 4, 2, 2, 3, 3, 4, 4, 4, 5, 6, 4, 5, 6],
    [4, 5, 6, 3, 4, 5, 2, 3, 3, 2, 2, 3, 3, 4, 4, 4, 5, 6],
    [4, 5, 6, 2, 3, 3, 1, 1, 2, 1, 1, 2, 2, 3, 3, 4, 5, 6],
    [4, 5, 6, 3, 4, 5, 2, 3, 3, 2, 3, 3, 3, 4, 4, 4, 5, 6],
    [4, 5, 6, 4, 5, 6, 3, 4, 4, 2, 2, 3, 2, 3, 4, 4, 5, 6],
    # nov-dic-ene, sombreado
    *[[4, 5, 6] * 6] * 4,
], dtype="float32")
# Orientación en el orden de la tabla. En el hemisferio sur la ladera al sol mira al norte:
# se usa la fila "sur" de la tabla para una ladera norte, y al revés.
_N, _E, _S, _O = range(4)


def _grupo_meses_sur(mes: int) -> int:
    """El mes austral llevado a su equivalente boreal de insolación (+6 meses)."""
    boreal = (mes + 5) % 12 + 1
    return 0 if boreal in (5, 6, 7) else 2 if boreal in (11, 12, 1) else 1


def fosberg(t_k: np.ndarray, hr: np.ndarray, tiempos: list[datetime], lon: float,
            pendiente_grados: np.ndarray, orientacion_grados: np.ndarray, cc_pct: np.ndarray,
            desnivel_m: np.ndarray) -> np.ndarray:
    """m1 (%) por las tablas de Fosberg, banda por banda.

    `t_k`, `hr`: (bandas, filas, columnas) en la grilla, a la altura de la estación (el
    terreno del GFS). `tiempos`: hora UTC de cada banda. `desnivel_m`: DEM menos terreno del
    GFS. La hora de la tabla es la solar local (UTC + lon/15). De noche, donde las tablas
    no llegan, se usa la corrección sombreada de la última franja (18 h-ocaso): el
    combustible sin sol se comporta como a la sombra.
    """
    t_f = (t_k - 273.15) * 9 / 5 + 32
    fila_t = np.clip(((t_f - 10) // 20).astype(int), 0, 5)
    col_hr = np.clip((np.clip(hr, 0, 100) // 5).astype(int), 0, 20)
    rfm = _RFM[fila_t, col_hr]

    pendiente = (np.tan(np.radians(pendiente_grados)) * 100 > 30).astype(int)
    a = orientacion_grados % 360
    orient = np.select([(a >= 45) & (a < 135), (a >= 135) & (a < 225), (a >= 225) & (a < 315)],
                       [_E, _N, _O], default=_S)   # ladera norte → fila "sur"
    sombra = cc_pct >= 50
    altura = np.select([desnivel_m < -1000 * PIE_M, desnivel_m > 1000 * PIE_M], [0, 2], default=1)
    fila_expuesta = pendiente + 2 * orient
    fila_sombra = 8 + orient

    salida = np.empty_like(rfm)
    for b, t in enumerate(tiempos):
        hora = (t.hour + t.minute / 60 + lon / 15) % 24
        base = 12 * _grupo_meses_sur(t.month)
        if 8 <= hora < 20:
            franja = min(int((hora - 8) // 2), 5)
            fila = base + np.where(sombra, fila_sombra, fila_expuesta)
        else:
            franja = 5
            fila = base + fila_sombra
        salida[b] = rfm[b] + _CORRECCION[fila, altura + 3 * franja]
    return salida


def a_la_altura(t_k: np.ndarray, hr: np.ndarray, desnivel_m: np.ndarray,
                ) -> tuple[np.ndarray, np.ndarray]:
    """T y HR llevadas `desnivel_m` más arriba (negativo: más abajo) con el gradiente
    estándar, conservando el punto de rocío (Magnus)."""
    t_c = t_k - 273.15
    e = np.clip(hr, 1, 100) / 100 * _es(t_c)
    t_nueva = t_c + GRADIENTE_K_POR_M * desnivel_m
    return t_nueva + 273.15, np.clip(100 * e / _es(t_nueva), 1, 100)


def _es(t_c: np.ndarray) -> np.ndarray:
    return 6.112 * np.exp(17.62 * t_c / (243.12 + t_c))


def tiempos_de_bandas(inicio: datetime, bandas: int) -> list[datetime]:
    return [inicio + timedelta(hours=h) for h in range(bandas)]
