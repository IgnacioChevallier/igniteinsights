"""Humedad del combustible fino con criterio (app/validation/humedad.py)."""
from datetime import UTC, datetime

import numpy as np
import pytest

from app.validation import humedad as h

LON = -71.5   # la hora solar es UTC − 4,77 h


def _una_celda(**kw):
    base = {"pendiente_grados": np.array([[0.0]]), "orientacion_grados": np.array([[0.0]]),
            "cc_pct": np.array([[0.0]]), "desnivel_m": np.array([[0.0]])}
    return base | kw


def _utc(solar_h: float, mes: int = 1) -> datetime:
    return datetime(2025, mes, 15, int((solar_h - LON / 15) % 24), 0, tzinfo=UTC)


def test_verano_austral_es_el_verano_boreal_de_la_tabla():
    assert h._grupo_meses_sur(1) == 0 and h._grupo_meses_sur(12) == 0
    assert h._grupo_meses_sur(7) == 2
    assert h._grupo_meses_sur(3) == 1


def test_siesta_de_enero_en_ladera_norte_expuesta():
    """80 °F y 37 % → referencia 5 %. Enero, ladera norte (la del sol en el hemisferio sur),
    plana, sin dosel, a nivel, 14 h solar → corrección 0 (fila "sur" de may-jul)."""
    t = np.full((1, 1, 1), (80 - 32) * 5 / 9 + 273.15)
    hr = np.full((1, 1, 1), 37.0)
    m1 = h.fosberg(t, hr, [_utc(14.5)], LON, **_una_celda())
    assert m1[0, 0, 0] == pytest.approx(5.0)


def test_sombra_ladera_sur_y_noche_humedecen():
    t = np.full((1, 1, 1), (80 - 32) * 5 / 9 + 273.15)
    hr = np.full((1, 1, 1), 37.0)
    expuesta = h.fosberg(t, hr, [_utc(14.5)], LON, **_una_celda())[0, 0, 0]
    sombra = h.fosberg(t, hr, [_utc(14.5)], LON, **_una_celda(cc_pct=np.array([[80.0]])))
    sur = h.fosberg(t, hr, [_utc(14.5)], LON,
                    **_una_celda(orientacion_grados=np.array([[180.0]]),
                                 pendiente_grados=np.array([[30.0]])))
    noche = h.fosberg(t, hr, [_utc(2.0)], LON, **_una_celda())
    assert sombra[0, 0, 0] > expuesta
    assert sur[0, 0, 0] > expuesta
    assert noche[0, 0, 0] == pytest.approx(5 + 5)   # sombreada, última franja, a nivel


def test_sitio_bajo_la_estacion_es_mas_seco():
    t = np.full((1, 1, 1), 290.0)
    hr = np.full((1, 1, 1), 40.0)
    nivel = h.fosberg(t, hr, [_utc(9.0)], LON, **_una_celda())
    abajo = h.fosberg(t, hr, [_utc(9.0)], LON, **_una_celda(desnivel_m=np.array([[-600.0]])))
    assert abajo[0, 0, 0] < nivel[0, 0, 0]


def test_bajar_1000_m_calienta_65_y_seca_con_el_mismo_rocio():
    t, hr = np.array([290.0]), np.array([50.0])
    t2, hr2 = h.a_la_altura(t, hr, np.array([-1000.0]))
    assert t2[0] == pytest.approx(296.5)
    assert hr2[0] < 50
    e1 = 0.5 * h._es(t - 273.15)
    e2 = hr2 / 100 * h._es(t2 - 273.15)
    assert e2[0] == pytest.approx(e1[0])
