"""Aritmética de la nota AE (scripts/diagnostico_cbh_z0.py), sin paquetes."""
import numpy as np
import pytest

from app.validation import copa
from scripts import diagnostico_cbh_z0 as dz


def test_cbh_umbral_invierte_van_wagner():
    cbh = np.array([0.5, 1.5, 6.0])
    assert dz.cbh_umbral(copa.intensidad_critica(cbh)) == pytest.approx(cbh)


def test_fraccion_copa_es_estricta_como_diagnosticar_copa():
    umbral = np.array([0.4, 1.5, 2.0, 3.0])
    assert dz.fraccion_copa(umbral, 1.5) == 0.5          # 1,5 no inicia: flin > I0, no ≥
    assert dz.fraccion_copa(umbral, np.array([0.0, 1.0, 3.0, 1.0])) == 0.75   # piso de 0,1 m
    assert np.isnan(dz.fraccion_copa(np.zeros(0), 1.0))


def test_razon_viento():
    assert dz.razon_viento(0.22) == 1.0
    assert dz.razon_viento(0.03) == pytest.approx(1.051, abs=1e-3)
    assert dz.razon_viento(0.5) == pytest.approx(0.959, abs=1e-3)
