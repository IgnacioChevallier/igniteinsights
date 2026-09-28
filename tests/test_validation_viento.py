"""Interpolación del atlas de viento (app/validation/viento.py)."""
import numpy as np
import pytest

from app.validation import viento


def _atlas(salida_desde):
    """Atlas de 16 direcciones sobre una celda: para cada entrada, la dirección de salida."""
    d = np.arange(16) * 22.5
    desde = np.array([salida_desde(x) for x in d])
    u = (-0.9 * np.sin(np.radians(desde)))[:, None, None]
    v = (-0.9 * np.cos(np.radians(desde)))[:, None, None]
    return u.astype("float32"), v.astype("float32")


@pytest.mark.parametrize("entrada", [0.0, 22.5, 100.0, 270.0, 355.0])
def test_terreno_plano_conserva_la_direccion(entrada):
    u, v = _atlas(lambda x: x)
    vel, desde = viento.aplicar(np.full((1, 1, 1), 10.0), np.full((1, 1, 1), entrada), u, v)
    assert desde[0, 0, 0] == pytest.approx(entrada % 360, abs=0.5)
    assert 8.8 <= vel[0, 0, 0] <= 9.0 + 1e-4   # entre direcciones la cuerda achica <2 %


def test_un_valle_norte_sur_encauza():
    u, v = _atlas(lambda x: 0.0 if np.cos(np.radians(x)) >= 0 else 180.0)
    _, desde = viento.aplicar(np.full((1, 1, 1), 10.0), np.full((1, 1, 1), 300.0), u, v)
    assert min(desde[0, 0, 0], 360.0 - desde[0, 0, 0]) < 0.5   # del norte, a lo largo del valle
