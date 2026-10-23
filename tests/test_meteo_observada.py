"""Reemplazo de la meteorología por lo medido (`empaquetado.meteo_observada`), sintético."""
from datetime import UTC, datetime

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from app.elmfire.builder import weather_builder
from scripts import benchmark

T0 = datetime(2021, 3, 9, 18, tzinfo=UTC)


def _escribir(ruta, datos):
    with rasterio.open(ruta, "w", driver="GTiff", height=4, width=5, count=datos.shape[0],
                       dtype="float32", crs="EPSG:32719",
                       transform=from_origin(500000, 5300000, 30, 30)) as dst:
        dst.write(datos.astype("float32"))
    return ruta


def _leer(ruta):
    with rasterio.open(ruta) as src:
        return src.read()


@pytest.fixture
def ventana(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    lleno = np.ones((3, 4, 5))
    archivos = {"ws.tif": _escribir(base / "ws.tif", 8.0 * lleno),
                "wd.tif": _escribir(base / "wd.tif", -71.0 * lleno),   # 289°, desenrollado
                "t2m_gfs.tif": _escribir(base / "t2m_gfs.tif", 285.6 * lleno),
                "rh_gfs.tif": _escribir(base / "rh_gfs.tif", 61.0 * lleno)}
    dem = _escribir(base / "dem.tif", lleno[:1])
    salida = tmp_path / "salida"
    salida.mkdir()
    return archivos, dem, salida


def test_solo_viento_pisa_su_banda(ventana):
    archivos, dem, salida = ventana
    serie = [{"t": "2021-03-09T19:00:00+00:00", "ws10_kt": 29, "wd": 360}]
    nuevos = benchmark._meteo_en_ventana(archivos, dem, T0, serie, salida)
    assert set(nuevos) == {"ws.tif", "wd.tif"}   # la humedad queda la del GFS
    ws, wd = _leer(nuevos["ws.tif"]), _leer(nuevos["wd.tif"])
    assert np.allclose(ws[1], 29.0, atol=0.1)    # 29 kt a 10 m ≈ 29 mph a 20 ft
    assert np.allclose(ws[[0, 2]], 8.0)
    assert np.allclose(np.mod(wd, 360), [[[289]], [[0]], [[289]]])


def test_humedad_regenera_m1_m10_m100(ventana):
    archivos, dem, salida = ventana
    serie = [{"t": "2021-03-09T20:00:00+00:00", "t2m_c": 23.9, "hr_pct": 27.0}]
    nuevos = benchmark._meteo_en_ventana(archivos, dem, T0, serie, salida)
    assert {"m1.tif", "m10.tif", "m100.tif", "t2m_gfs.tif", "rh_gfs.tif"} == set(nuevos)
    m1, m100 = _leer(nuevos["m1.tif"]), _leer(nuevos["m100.tif"])
    sin_cambios = weather_builder.derive_moisture(archivos["t2m_gfs.tif"],
                                                  archivos["rh_gfs.tif"], dem,
                                                  salida / "gfs")
    assert np.allclose(m1[2], 5.44, atol=0.01)   # EMC de Nelson a 23,9 °C y 27 %
    assert np.allclose(m100[2], m1[2] + 5.0)
    assert np.array_equal(m1[:2], _leer(sin_cambios[0])[:2])


def test_hora_fuera_de_la_ventana(ventana):
    archivos, dem, salida = ventana
    for t in ("2021-03-09T21:00:00+00:00", "2021-03-09T18:30:00+00:00"):
        with pytest.raises(ValueError):
            benchmark._meteo_en_ventana(archivos, dem, T0, [{"t": t, "ws10_kt": 29}], salida)


def test_alarga_la_ventana_con_horas_medidas_completas(ventana):
    archivos, dem, salida = ventana
    completa = {"ws10_kt": 29, "wd": 303, "t2m_c": 23.9, "hr_pct": 27.5}
    serie = [{"t": f"2021-03-09T{h}:00:00+00:00", **completa} for h in (21, 22)]
    nuevos = benchmark._meteo_en_ventana(archivos, dem, T0, serie, salida, bandas=5)
    ws, m1 = _leer(nuevos["ws.tif"]), _leer(nuevos["m1.tif"])
    assert ws.shape[0] == m1.shape[0] == 5
    assert np.allclose(ws[:3], 8.0) and np.allclose(ws[3:], 29.0, atol=0.1)
    assert np.allclose(np.mod(_leer(nuevos["wd.tif"])[3:], 360), 303)


def test_alargar_sin_las_cuatro_variables_es_un_error(ventana):
    archivos, dem, salida = ventana
    serie = [{"t": "2021-03-09T21:00:00+00:00", "ws10_kt": 29}]
    with pytest.raises(ValueError, match="fuera del GFS"):
        benchmark._meteo_en_ventana(archivos, dem, T0, serie, salida, bandas=4)
