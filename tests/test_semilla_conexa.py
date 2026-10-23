"""Filtro de semilla conexa (`semilla_inicial.filtro_conexo_m`, T-semilla §2.2), sintético."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from app.elmfire.builder.perimeter_reconstruction import connected_to_anchors
from app.validation import puntuacion as p
from scripts import benchmark


def test_conexas_a_la_ignicion():
    frente = [(x, 0.0) for x in np.arange(0, 12000, 2500)]   # cadena de saltos de 2,5 km
    ajeno = [(30000.0, 0.0), (31000.0, 0.0)]                  # otro incendio a 18 km
    puntos = frente + ajeno
    assert connected_to_anchors(puntos, [(0.0, 3000.0)], 3000.0) == [True] * 5 + [False] * 2
    # saltos cortos: quedan sólo las dos a ≤ 5 km del ancla
    assert connected_to_anchors(puntos, [(0.0, 3000.0)], 2000.0) == [True] * 2 + [False] * 5
    assert connected_to_anchors(puntos, [(0.0, 9000.0)], 3000.0) == [False] * 7   # ancla lejos
    assert connected_to_anchors([], [(0.0, 0.0)], 3000.0) == []


def test_el_benchmark_siembra_solo_con_las_conexas(tmp_path):
    dem = tmp_path / "dem.tif"
    with rasterio.open(dem, "w", driver="GTiff", height=10, width=10, count=1, dtype="float32",
                       crs="EPSG:32719", transform=from_origin(500000, 5300000, 30, 30)) as dst:
        dst.write(np.zeros((1, 10, 10), dtype="float32"))
    grilla = p.Grilla(dem)
    puntos = [(-71.90, -42.48), (-71.89, -42.48), (-71.50, -42.48)]   # el último, a ~33 km
    semilla = {"tipo": "punto", "lon": -71.90, "lat": -42.48}
    assert benchmark._semilla_conexa(puntos, semilla, grilla) == puntos   # sin filtro: todo
    semilla["filtro_conexo_m"] = 3000
    assert benchmark._semilla_conexa(puntos, semilla, grilla) == puntos[:2]
    with pytest.raises(ValueError):
        benchmark._semilla_conexa(puntos, {"tipo": "firms", "filtro_conexo_m": 3000}, grilla)
