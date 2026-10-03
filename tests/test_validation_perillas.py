"""Perillas de receta que transforman rásters que ELMFIRE ya lee (app/validation/cadena.py)."""
from datetime import UTC, datetime

import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.validation import almacen, cadena

UTM = "EPSG:32719"
GRILLA = from_origin(300000, 5300000, 30, 30)   # ~ -42,4 / -71,4


def _escribir(ruta, datos, transform=GRILLA, crs=UTM, dtype="float32"):
    datos = np.asarray(datos, dtype=dtype)
    datos = datos[None] if datos.ndim == 2 else datos
    with rasterio.open(ruta, "w", driver="GTiff", height=datos.shape[1], width=datos.shape[2],
                       count=datos.shape[0], dtype=dtype, crs=crs, transform=transform) as dst:
        dst.write(datos)


def _insumos(tmp_path, monkeypatch):
    monkeypatch.setattr(almacen, "_raiz", lambda: tmp_path / "objetos")
    ins = tmp_path / "insumos"
    ins.mkdir()
    for nombre, valor in (("dem", 400.0), ("slp", 0.0), ("asp", 0.0), ("cc", 0.0)):
        _escribir(ins / f"{nombre}.tif", np.full((4, 4), valor))
    for nombre in ("m1", "m10", "m100"):
        _escribir(ins / f"{nombre}.tif", np.full((3, 4, 4), 9.0))
    grueso = from_origin(-72.0, -42.0, 0.25, 0.25)
    archivos = {}
    for nombre, valor, bandas in (("t2m_gfs", 293.15, 3), ("rh_gfs", 40.0, 3),
                                  ("orog_gfs", 1000.0, 1)):
        ruta = tmp_path / f"{nombre}.tif"
        _escribir(ruta, np.full((bandas, 4, 4), valor), grueso, "EPSG:4326")
        archivos[f"{nombre}.tif"] = almacen.guardar(ruta)
    return ins, archivos


def _leer(ruta):
    with rasterio.open(ruta) as src:
        return src.read()


def test_altura_600_m_abajo_seca_los_tres(tmp_path, monkeypatch):
    ins, archivos = _insumos(tmp_path, monkeypatch)
    cadena._humedad_con_criterio("altura", archivos, ins,
                                 datetime(2025, 1, 15, 18, tzinfo=UTC), -71.4)
    m1, m10, m100 = (_leer(ins / f"{n}.tif") for n in ("m1", "m10", "m100"))
    # 20 °C y 40 % a 1.000 m → 23,9 °C y ~31 % a 400 m: Nelson ~5,5 %
    assert 4.5 < m1.mean() < 6.5
    assert np.allclose(m10 - m1, 2.0) and np.allclose(m100 - m1, 5.0)


def test_fosberg_cambia_solo_m1(tmp_path, monkeypatch):
    ins, archivos = _insumos(tmp_path, monkeypatch)
    cadena._humedad_con_criterio("fosberg", archivos, ins,
                                 datetime(2025, 1, 15, 18, tzinfo=UTC), -71.4)
    assert not np.allclose(_leer(ins / "m1.tif"), 9.0)
    assert np.allclose(_leer(ins / "m10.tif"), 9.0)


def test_adj_por_grupo_de_combustible():
    codigos = np.array([[102, 144, 165, 186, 98]])
    factor = cadena.factor_por_grupo(codigos, {"SH": 1.5, "TL": 0.75})
    assert factor.tolist() == [[1.0, 1.5, 1.0, 0.75, 1.0]]


def test_rotar_el_viento_da_la_vuelta(tmp_path):
    ruta = tmp_path / "wd.tif"
    _escribir(ruta, np.array([[[350.0, 10.0]]]))
    cadena._reescribir(ruta, lambda a: (a + 45.0) % 360.0)
    assert _leer(ruta).ravel().tolist() == [35.0, 55.0]


def test_rugosidad_del_dosel():
    f = cadena.factor_rugosidad(np.array([0.0, 1.7, 20.0]))
    assert f[0] > 1.0                      # pastizal (z0 0,03) frena menos que 0,22 m
    assert abs(f[1] - 1.0) < 0.01          # 1,7 m de dosel ≈ el escalar de hoy
    assert 0.6 < f[2] < 0.8                # bosque de 20 m: z0 2,6 m, bastante menos viento


def test_reasignar_combustible():
    codigos = np.array([[188, 144, 188, 98]])
    assert cadena.reasignar(codigos, {"188": 165}).tolist() == [[165, 144, 165, 98]]


def test_dosel_coherente_solo_en_combustibles_no_forestales():
    codigos = np.array([[102, 123, 144, 165, 188, 98]])
    assert cadena.no_forestal(codigos).tolist() == [[True, True, True, False, False, False]]


def test_sin_dosel_por_codigo_o_grupo():
    codigos = np.array([[102, 144, 148, 165, 188]])
    assert cadena.en_codigos(codigos, ["148"]).tolist() == [[False, False, True, False, False]]
    assert cadena.en_codigos(codigos, ["SH", "188"]).tolist() == [[False, True, True, False, True]]


def test_cbh_por_combustible_solo_donde_hay_copa_y_el_codigo_pisa_al_grupo():
    codigos = np.array([[165, 165, 188, 186, 144]])
    cbh = np.array([[60, 0, 80, 70, -9999]], dtype=np.int16)
    salida = cadena.por_combustible(codigos, cbh, {"TU": 1.5, "TL": 4.0, "188": 2.0}, 10)
    assert salida.tolist() == [[15, 0, 20, 40, -9999]]
    cbd = np.array([[5, 0, 7, 4, 3]], dtype=np.int16)
    assert cadena.por_combustible(codigos, cbd, {"188": 0.16, "SH": 0}, 100).tolist() == [
        [5, 0, 16, 4, 0]]


def test_variante_crosswalk_solo_la_clase_y_su_codigo_y_la_altura():
    import importlib.util
    spec = importlib.util.spec_from_file_location("vc", "scripts/variante_crosswalk.py")
    vc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vc)
    fuel = np.array([[148, 148, 144, 148]], dtype=np.int16)
    clase = np.array([[True, True, True, False]])
    viejo = np.where(clase, 148, 0)
    dem = np.array([[1400, 900, 1400, 1400]])
    salida = vc.aplicar(fuel, clase, viejo, dem, {"a": 143, "altura_min": 1300})
    assert salida.tolist() == [[143, 148, 144, 148]]


def test_variante_hereda_los_anios_del_producto():
    from app.validation import definiciones
    assert definiciones.anios_publicados("ccsbap-l1") == definiciones.ANIOS_COMBUSTIBLE["ccsbap"]


def test_principal_completa_lee_iou_precision_y_recall_de_la_ventana():
    vieja = {"principal": {"referencia": "cicatriz", "ventana": 1, "dice": 0.5,
                           "sesgo_area": 1.0, "alarma_sesgo": False},
             "ventanas": [{}, {"cicatriz": {"acumulado": {
                 "dice": 0.5, "iou": 1 / 3, "precision": 0.5, "recall": 0.5,
                 "tp": 10, "fp": 10, "fn": 10}}}]}
    pr = cadena.principal_completa(vieja)
    assert (pr["iou"], pr["precision"], pr["recall"], pr["tp"]) == (1 / 3, 0.5, 0.5, 10)
    assert pr["dice"] == 0.5 and pr["ventana"] == 1


def test_perdida_previa_excluye_el_anio_del_incendio():
    ly = np.array([[0, 14, 15, 24, 25]])
    assert cadena.perdida_previa(ly, 2025).tolist() == [[False, True, True, True, False]]
    assert cadena.perdida_previa(ly, 2015).tolist() == [[False, True, False, False, False]]
