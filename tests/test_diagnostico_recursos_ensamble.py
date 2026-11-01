"""Nota AD: lectura de la memoria de `docker stats`."""
import pytest

from scripts import diagnostico_recursos_ensamble as dr


def test_mib_convierte_las_unidades_de_docker_stats():
    assert dr.mib("47.3MiB") == pytest.approx(47.3)
    assert dr.mib("1.456GiB ") == pytest.approx(1490.944)
    assert dr.mib("512KiB") == pytest.approx(0.5)
