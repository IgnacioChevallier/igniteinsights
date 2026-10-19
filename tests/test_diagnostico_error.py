"""Aritmética del diagnóstico de error (scripts/diagnostico_error.py) con rásters sintéticos."""
import math

import numpy as np
import pytest

from scripts import diagnostico_error as de


def cuadrado(f: int, c: int, lado: int = 20, forma=(200, 200)) -> np.ndarray:
    m = np.zeros(forma, dtype=bool)
    m[f:f + lado, c:c + lado] = True
    return m


def test_diagnostico_sinteticos():
    ref, desplazado = cuadrado(90, 90), cuadrado(90, 100)   # corrido 10 celdas al este
    todo = np.ones(ref.shape, dtype=bool)

    # FSS: 1 si coinciden; el corrimiento se perdona al crecer la ventana
    assert de.fss(ref, ref, todo, 1) == pytest.approx(1.0)
    f1, f33 = de.fss(desplazado, ref, todo, 1), de.fss(desplazado, ref, todo, 33)
    assert f1 == pytest.approx(0.5) and f33 > 0.8

    # distancia de perímetro: dos cuadrados corridos 10 celdas de 30 m -> ~300 m en los lados E/O
    dist = de.distancia_perimetro(desplazado, ref, np.zeros_like(ref), 30.0)
    assert 100 < dist["assd_m"] < 400 and dist["hd95_m"] == pytest.approx(300, abs=35)

    # eje: la semilla al centro, el crecimiento al este -> rumbo 90°, distancia 20 celdas
    semilla = cuadrado(99, 99, 2)
    rumbo, metros = de.eje(semilla, cuadrado(99, 119, 2), 30.0)
    assert rumbo == pytest.approx(90) and metros == pytest.approx(600)
    assert de.dif_angulo(10, 350) == pytest.approx(20)

    # ADJ offline: r_obs/r_sim = 1,5 -> ADJ 1,5; con r_sim = 0 satura en 4
    adj, sat = de.adj_k(100.0, 144.0, 169.0)   # r_sim = 2, r_obs = 3 -> 1,5
    assert adj == pytest.approx(1.5) and not sat
    assert de.adj_k(100.0, 100.0, 400.0) == (4.0, True)
    g = de.crecimiento_con_adj(100.0, 44.0, 1.5)   # radio 2 -> 3: área (10+3)² − 100 = 69
    assert g == pytest.approx(69.0)
    assert de.crecimiento_con_adj(100.0, 44.0, 1.0) == pytest.approx(44.0)

    # ROS empírica: frente en x = 0, detección nueva a 1.200 m, 10 h después -> 2 m/min
    prev = np.array([[0.0, 0.0], [0.0, 375.0]])
    nuevos = np.array([[1200.0, 0.0], [100.0, 0.0], [90_000.0, 0.0]])
    r = de.ros_empirica(prev, nuevos, np.array([10.0, 10.0, 10.0]))
    assert list(r["i"]) == [0]   # la 2.ª es el mismo píxel; la 3.ª, un salto
    assert r["ros_obs_m_min"][0] == pytest.approx(1200 / 600)

    # autocorrelación: serie perfectamente persistente
    c = de.correlacion([0.0, 1.0, 2.0, 3.0], [0.1, 1.1, 2.1, 3.1])
    assert c["pearson"] == pytest.approx(1.0) and c["mismo_signo"] == pytest.approx(0.75)
    assert math.isfinite(de.fss_util(ref, todo))


def elipse(a: float, b: float, rumbo: float = 90.0, forma=(300, 300)) -> np.ndarray:
    """Elipse llena con semieje `a` sobre el rumbo `rumbo` (grados desde el norte) y `b` al lado."""
    f, c = np.mgrid[0:forma[0], 0:forma[1]]
    dx, dy = c - forma[1] / 2, forma[0] / 2 - f
    t = math.radians(rumbo)
    u, v = dx * math.sin(t) + dy * math.cos(t), dx * math.cos(t) - dy * math.sin(t)
    return (u / a) ** 2 + (v / b) ** 2 <= 1


def test_f7_elongacion_y_s1():
    # elipse conocida: semiejes 60 y 30 -> elongación 2; eje E-O = 90°, NNE-SSO = 22,5°
    e = de.elongacion(elipse(60, 30))
    assert e["elong"] == pytest.approx(2.0, abs=0.05) and e["eje"] == pytest.approx(90, abs=1)
    assert e["elong_lo"] < 2.0 < e["elong_hi"]
    assert de.elongacion(elipse(60, 30, 22.5))["eje"] == pytest.approx(22.5, abs=1.5)
    # círculo: elongación ~1, el eje no se informa (pero queda el crudo)
    r = de.elongacion(elipse(40, 40))
    assert r["elong"] < de.ELONG_MIN_EJE and math.isnan(r["eje"])
    # componente mayor: se queda con el disco grande y descarta el chico
    m = elipse(40, 40)
    m[5:10, 5:10] = True
    mayor = de.componente_mayor(m)
    assert mayor.sum() == elipse(40, 40).sum() and not mayor[5:10, 5:10].any()

    # S1: semilla al centro; el modelo crece al este más (1,5x el área) que lo observado
    forma, todo = (100, 100), np.ones((100, 100), dtype=bool)
    sem = cuadrado(45, 45, 10, forma)
    obs = cuadrado(45, 45, 20, forma)       # cicatriz: 20x20 con la semilla adentro
    pred_horas = np.full(forma, np.nan)
    pred_horas[45:55, 55:75] = 6.0          # 10x20 al este, a las 6 h
    pred_horas[45:55, 35:45] = 10.0
    vistas = np.where(obs & ~sem, 3.0, 99.0)
    f = de.s1_reinicio(sem, pred_horas, vistas, obs, ~todo, 12, 0.09, 30.0)
    # referencia: 300 celdas (cicatriz 400 - semilla 100); predicho 300 (10x20 + 10x10 se solapa)
    assert f["obs_ha"] == pytest.approx(0.09 * 300)
    assert 0 < f["dice"] < 1 and f["t_star_alcanzada"] in (True, False)
    assert 0 <= f["abs_dif_angulo"] <= 180


def test_dispersion_viento():
    n = 31
    u = np.full((n, 3, 3), -5.0)    # viento del este (dirección 90°), 5 m/s, sin dispersión
    v = np.zeros((n, 3, 3))
    sd, cv, vel = de.dispersion_viento(u, v)
    assert sd == pytest.approx(0, abs=1e-3) and cv == pytest.approx(0) and vel == pytest.approx(5)
    # direcciones uniformes en ±20° alrededor de 90°: desvío circular ≈ desvío lineal (~11,5°)
    ang = np.radians(90 + np.linspace(-20, 20, n))[:, None, None] * np.ones((n, 3, 3))
    sd, cv, _ = de.dispersion_viento(-5 * np.sin(ang), -5 * np.cos(ang))
    assert sd == pytest.approx(11.9, abs=1.0) and cv == pytest.approx(0, abs=1e-6)
    # rapidez ±20 % con la misma dirección: cv ≈ 0,12
    k = np.linspace(0.8, 1.2, n)[:, None, None] * np.ones((n, 3, 3))
    assert de.dispersion_viento(-5 * k, 0 * k)[1] == pytest.approx(0.12, abs=0.01)
