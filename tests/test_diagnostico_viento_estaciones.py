"""Aritmética de la puerta meteorológica (scripts/diagnostico_viento_estaciones.py), sintética."""
from datetime import UTC, datetime

import numpy as np
import pytest

from scripts import diagnostico_viento_estaciones as dv


def test_viento_estaciones_sinteticos():
    # SYNOP: nudos (iw 4), m/s (iw 1, descartado), NIL, calma, variable y rapidez ≥ 99
    texto = "\n".join([
        "87800,2024,01,26,00,00,AAXX 26004 87800 11980 63619 10284=",
        "87800,2024,01,26,01,00,AAXX 26014 87800 NIL=",
        "87800,2024,01,26,02,00,AAXX 26021 87800 11980 62705 10284=",
        "87800,2024,01,26,03,00,AAXX 26034 87800 11980 60000 10284=",
        "87800,2024,01,26,04,00,AAXX 26044 87800 11980 69905 10284=",
        "87800,2024,01,26,05,00,AAXX 26054 87800 11980 63699 00105 10284=",
    ])
    df = dv.parsear_synop(texto).set_index("t")
    t = lambda h: datetime(2024, 1, 26, h, tzinfo=UTC)  # noqa: E731
    assert len(df) == 4 and t(1) not in df.index and t(2) not in df.index
    assert df.loc[t(0), "dir"] == 0.0   # dd 36 → 360° → 0°
    assert df.loc[t(0), "vel"] == pytest.approx(19 * dv.KT_MS)
    assert np.isnan(df.loc[t(3), "dir"]) and df.loc[t(3), "vel"] == 0.0
    assert np.isnan(df.loc[t(4), "dir"])
    assert df.loc[t(5), "vel"] == pytest.approx(105 * dv.KT_MS)

    # ángulos: el camino corto a través del norte
    assert dv.dif_angular(np.array([10.0, 350.0, 180.0]),
                          np.array([350.0, 10.0, 0.0])).tolist() == [20.0, -20.0, -180.0]

    # u/v ida y vuelta, convención "desde"
    u, v = dv.uv(np.array([5.0]), np.array([270.0]))   # del oeste: sopla hacia el este
    assert u[0] == pytest.approx(5.0) and v[0] == pytest.approx(0.0, abs=1e-9)
    vel, dir_ = dv.vel_dir(u, v)
    assert vel[0] == pytest.approx(5.0) and dir_[0] == pytest.approx(270.0)

    # bilineal exacta en un campo lineal; índices desde el centro de la celda
    a = np.add.outer(np.arange(4.0) * 10, np.arange(5.0))   # a[f, c] = 10 f + c
    assert dv.bilineal(a, 1.25, 2.5) == pytest.approx(15.0)
    assert dv.fila_col(dv.Affine(1, 0, 0, 0, -1, 0), 0.5, -0.5) == (0.0, 0.0)

    # ciclo: el más reciente con plazo ≥ 1 que exista
    c0, c6 = datetime(2024, 1, 26, 0, tzinfo=UTC), datetime(2024, 1, 26, 6, tzinfo=UTC)
    plazos = {c0: set(range(73)), c6: set(range(73))}
    assert dv.elegir_ciclo(t(6), plazos) == (c0, 6)
    assert dv.elegir_ciclo(t(7), plazos) == (c6, 1)
    assert dv.elegir_ciclo(t(7), {c0: set(range(73)), c6: {0, 2}}) == (c0, 7)

    # métricas y criterio: WRF sin error frente a un GFS girado 30° y a 0,6×
    obs_d, obs_v = np.array([200.0, 250.0, 300.0, 10.0]), np.array([4.0, 6.0, 8.0, 6.0])
    gfs = dv.metricas(obs_d, obs_v, (obs_d + 30) % 360, obs_v * 0.6)
    assert gfs["err_ang_mediano"] == pytest.approx(30.0)
    assert gfs["desvio_dir_circular"] == pytest.approx(30.0)
    assert gfs["sesgo_vel"] == pytest.approx(-2.4) and gfs["cociente_vel"] == pytest.approx(0.6)
    wrf = dv.metricas(obs_d, obs_v, obs_d, obs_v)
    assert dv.pasa_estacion(gfs, wrf) and not dv.pasa_estacion(wrf, gfs)
    casi = dv.metricas(obs_d, obs_v, (obs_d + 25) % 360, obs_v * 0.7)   # 5° y 25 % de mejora
    assert not dv.pasa_estacion(gfs, casi)
