"""Aritmética del benchmark.

Si esto falla, ningún número de docs/resultados/modelo/validacion.md vale.
"""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from app.validation import puntuacion as p

HA = 0.09


def test_confusion_conocida():
    pred = np.array([1, 1, 1, 0, 0, 0], dtype=bool)
    ref = np.array([1, 1, 0, 1, 0, 0], dtype=bool)
    m = p.metricas(pred, ref, HA)
    assert (m["tp"], m["fp"], m["fn"]) == (2, 1, 1)
    assert m["iou"] == pytest.approx(2 / 4)
    assert m["dice"] == pytest.approx(4 / 6)
    assert m["sesgo_area"] == pytest.approx(1.0)
    assert m["tp_ha"] == pytest.approx(2 * HA)
    assert not m["alarma_sesgo"]


def test_la_exclusion_no_cuenta():
    pred = np.array([1, 1, 1, 0], dtype=bool)
    ref = np.array([1, 0, 0, 1], dtype=bool)
    excluir = np.array([0, 1, 1, 1], dtype=bool)
    m = p.metricas(pred, ref, HA, excluir)
    assert (m["tp"], m["fp"], m["fn"]) == (1, 0, 0)
    assert m["dice"] == 1.0


def test_la_referencia_como_prediccion_da_uno():
    ref = np.random.default_rng(0).random((50, 50)) > 0.7
    m = p.metricas(ref, ref, HA)
    assert m["dice"] == m["iou"] == m["recall"] == m["precision"] == m["sesgo_area"] == 1.0


def test_sobre_propagar_dispara_la_alarma():
    """Recall 1 quemando 458× la referencia no es un buen resultado (RESULTADOS §6)."""
    pred = np.ones(100, dtype=bool)
    ref = np.zeros(100, dtype=bool)
    ref[:10] = True
    m = p.metricas(pred, ref, HA)
    assert m["recall"] == 1.0
    assert m["sesgo_area"] == pytest.approx(10.0)
    assert m["alarma_sesgo"]


def test_toa_absoluto_a_horas_relativas():
    toa = np.array([-9999.0, 6360.0, 6360.0 + 7200.0])
    h = p.horas_relativas(toa, tstart_s=6360.0)
    assert np.isnan(h[0])
    assert h[1] == 0.0 and h[2] == 2.0


def test_coser_respeta_la_primera_llegada():
    semilla0 = np.array([1, 0, 0, 0], dtype=bool)
    h0 = np.array([0.0, 5.0, np.nan, np.nan])      # ventana 0 quema la celda 1 a las 5 h
    semilla1 = np.array([1, 1, 0, 1], dtype=bool)  # FIRMS siembra la 3, que nadie alcanzó
    h1 = np.array([0.0, 0.0, 3.0, 0.0])
    cosido = p.coser([(0.0, h0, semilla0), (24.0, h1, semilla1)])
    assert cosido[0] == 0.0
    assert cosido[1] == 5.0      # la ventana 1 no puede atrasar lo que ya ardía
    assert cosido[2] == 27.0
    assert cosido[3] == 24.0     # sembrada por observación: aparece al empezar la ventana


def test_error_llegada_con_signo():
    pred = np.array([10.0, 20.0, np.nan, np.nan])
    det = np.array([12.0, 18.0, 5.0, np.nan])
    e = p.error_llegada(pred, det)
    assert e["detecciones"] == 3
    assert e["mediana_h"] == pytest.approx(0.0)       # -2 y +2
    assert e["nunca_alcanzadas"] == pytest.approx(1 / 3)


def _tif(ruta, arr, transform, crs="EPSG:32719"):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(ruta, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1],
                       count=1, dtype="uint8", crs=crs, transform=transform) as dst:
        dst.write(arr.astype("uint8"), 1)


def test_cicatriz_formato_nuevo_excluye_lo_no_atribuido(tmp_path):
    t = from_origin(500000.0, 5300000.0, 30.0, 30.0)
    _tif(tmp_path / "grilla.tif", np.zeros((4, 4)), t)
    mascara = np.zeros((4, 4))
    mascara[0, :2] = 1
    no_conf = np.zeros((4, 4))
    no_conf[3, 3] = 1
    valida = np.ones((4, 4))
    valida[2, 0] = 0
    run = tmp_path / "run"
    _tif(run / "mascaras" / "t.tif", mascara, t)
    _tif(run / "cambio_no_confirmado" / "t.tif", no_conf, t)
    _tif(run / "calidad" / "observacion_valida" / "t.tif", valida, t)

    positivo, excluido = p.cargar_cicatriz(run, p.Grilla(tmp_path / "grilla.tif"))
    assert positivo.sum() == 2
    assert excluido[3, 3] and excluido[2, 0]
    assert excluido.sum() == 2


def test_cicatriz_legacy_usa_la_huella_del_tile(tmp_path):
    t = from_origin(500000.0, 5300000.0, 30.0, 30.0)
    _tif(tmp_path / "grilla.tif", np.zeros((4, 4)), t)
    run = tmp_path / "run"
    _tif(run / "mascaras" / "t.tif", np.ones((2, 2)), t)   # cubre sólo la esquina

    positivo, excluido = p.cargar_cicatriz(run, p.Grilla(tmp_path / "grilla.tif"))
    assert positivo.sum() == 4
    assert excluido.sum() == 12


def test_area_igualada_corta_donde_las_areas_coinciden():
    horas = np.array([1.0, 2.0, 3.0, 4.0, np.nan, np.nan])
    ref = np.array([1, 1, 0, 0, 1, 0], dtype=bool)          # 3 celdas observadas
    r = p.area_igualada(horas, ref, HA, np.zeros(6, dtype=bool))
    assert r["alcanzada"] and r["hora"] == 3.0              # la tercera celda llega a las 3 h
    assert r["dice"] == pytest.approx(2 * 2 / (2 * 2 + 1 + 1))


def test_area_igualada_no_alcanzada_usa_el_final():
    horas = np.array([1.0, np.nan, np.nan])
    ref = np.array([1, 1, 1], dtype=bool)
    r = p.area_igualada(horas, ref, HA, np.zeros(3, dtype=bool))
    assert not r["alcanzada"] and r["hora"] == 1.0


def test_distancia_a_la_mascara():
    m = np.zeros((20, 20), dtype=bool)
    m[10, 15] = True
    assert p.distancia_a(m, 10, 15, 30.0) == 0.0
    assert p.distancia_a(m, 10, 12, 30.0) == pytest.approx(90.0)
    assert p.distancia_a(m, 13, 11, 30.0) == pytest.approx(150.0)   # 3-4-5
    assert p.distancia_a(m, 0, 0, 30.0, radio_m=100.0) == float("inf")
    # profundidad: distancia a lo que NO es máscara desde adentro
    lleno = np.ones((9, 9), dtype=bool)
    lleno[0, :] = False
    assert p.distancia_a(~lleno, 4, 4, 30.0) == pytest.approx(120.0)
