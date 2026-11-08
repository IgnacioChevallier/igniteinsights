"""Convenciones de la interfaz con ELMFIRE 2025.0212 que encontró la auditoría física
(docs/resultados/modelo/auditoria.md). Cada una se verificó corriendo ELMFIRE en
scripts/pruebas_fisicas.py; estos tests fijan lo que el repo emite."""
import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.elmfire.builder import ignition_builder, namelist_writer
from app.elmfire.builder.weather_builder import _elmfire_blows_to, wd_for_elmfire


def _raster(path, data, dtype="float32"):
    data = np.asarray(data, dtype=dtype)
    data = data if data.ndim == 3 else data[None]
    with rasterio.open(path, "w", driver="GTiff", height=data.shape[1], width=data.shape[2],
                       count=data.shape[0], dtype=dtype, crs="EPSG:32719",
                       transform=from_origin(500000, 6000000, 30, 30)) as dst:
        dst.write(data)


def _elmfire_interpola(wd_lo, wd_hi, f):
    """INTERP_WD_RASTER de elmfire_subs.f90, transcrito."""
    to = _elmfire_blows_to(wd_lo) + f * (_elmfire_blows_to(wd_hi) - _elmfire_blows_to(wd_lo))
    salida = to + 180.0
    salida = np.where(salida > 360.0, salida - 360.0, salida)
    return np.where(salida < 0.0, salida + 360.0, salida)


def _dif(a, b):
    return np.abs((a - b + 180.0) % 360.0 - 180.0)


def test_phi_es_el_campo_mas_menos_uno_de_elmfire(tmp_path):
    """Hallazgo 2: con la distancia en metros el frente avanzaba a la mitad."""
    _raster(tmp_path / "dem.tif", np.zeros((9, 9)))
    mascara = np.zeros((9, 9), dtype=bool)
    mascara[3:6, 3:6] = True
    phi_path = ignition_builder.build_ignition_from_mask(mascara, tmp_path / "dem.tif", tmp_path)
    with rasterio.open(phi_path) as src:
        phi = src.read(1)
    assert (phi[mascara] == -1.0).all() and (phi[~mascara] == 1.0).all()


def test_sin_ignicion_nada_arranca_quemado(tmp_path):
    """Antes escribía -9999: ELMFIRE lo resetea a +1, pero `phi <= 0` (la regla de
    benchmark._mascara) daba el dominio entero por quemado."""
    _raster(tmp_path / "dem.tif", np.zeros((9, 9)))
    phi_path, _ = ignition_builder.build_ignition_layer([], tmp_path / "dem.tif", tmp_path)
    with rasterio.open(phi_path) as src:
        assert (src.read(1) == 1.0).all()


def test_el_namelist_declara_todas_las_bandas_del_clima(tmp_path):
    """Hallazgo 1: sin NUM_METEOROLOGY_TIMES, ELMFIRE usa la banda 0 toda la corrida."""
    _raster(tmp_path / "dem.tif", np.zeros((2, 2)))
    for nombre in namelist_writer.WEATHER_RASTERS:
        _raster(tmp_path / f"{nombre}.tif", np.zeros((25, 2, 2)))
    ruta, _, _ = namelist_writer.write_namelist(tmp_path, tmp_path / "out", simulation_hours=24,
                                                output_path=tmp_path / "elmfire.data")
    texto = ruta.read_text()
    assert "&MONTE_CARLO" in texto
    assert "NUM_METEOROLOGY_TIMES           = 25" in texto


def test_rasters_de_clima_con_distinta_serie_se_rechazan(tmp_path):
    _raster(tmp_path / "dem.tif", np.zeros((2, 2)))
    for nombre in namelist_writer.WEATHER_RASTERS:
        _raster(tmp_path / f"{nombre}.tif", np.zeros((25, 2, 2)))
    _raster(tmp_path / "m1.tif", np.zeros((24, 2, 2)))
    try:
        namelist_writer.write_namelist(tmp_path, tmp_path / "out", simulation_hours=6,
                                       output_path=tmp_path / "elmfire.data")
    except ValueError as exc:
        assert "m1.tif" in str(exc)
    else:
        raise AssertionError("una serie de humedad más corta que la del viento debía fallar")


def test_wd_cruda_del_sur_gira_por_el_norte_en_elmfire():
    """El bug, reproducido: 170° → 190° a mitad de la hora da viento del norte."""
    assert _dif(_elmfire_interpola(np.array(170.0), np.array(190.0), 0.5), 0.0) < 1


def test_wd_for_elmfire_interpola_por_el_camino_corto():
    rng = np.random.default_rng(1)
    series = [np.array([170.0, 190.0] * 4), np.array([350.0, 10.0, 350.0]),
              np.array([0.0, 90.0, 180.0, 270.0, 0.0, 90.0]), rng.uniform(0, 360, 48),
              np.cumsum(rng.uniform(-60, 60, 72)) % 360]
    for serie in series:
        wd = wd_for_elmfire(serie[:, None, None])[:, 0, 0]
        assert np.allclose(np.mod(wd, 360.0), np.mod(serie, 360.0), atol=1e-3)
        for a, b, a0, b0 in zip(wd[:-1], wd[1:], serie[:-1], serie[1:]):
            for f in (0.25, 0.5, 0.75):
                got = _elmfire_interpola(np.array(a), np.array(b), f)
                # sobre el arco corto entre a0 y b0: a distancia f·Δ de a0
                paso = (b0 - a0 + 180.0) % 360.0 - 180.0
                assert _dif(got, a0 + f * paso) < 0.01, (a0, b0, f, got)


def test_wd_for_elmfire_es_idempotente():
    serie = np.array([170.0, 190.0, 200.0, 350.0, 20.0])[:, None, None]
    una = wd_for_elmfire(serie)
    assert np.allclose(wd_for_elmfire(una), una)


def _fila_que_lee_elmfire(filas_finas: int, clima_ancho: int) -> np.ndarray:
    """MAP_FINE_TO_COARSE de elmfire_subs.f90:296-297, transcrito para la misma celda: la
    fila (contada desde el sur) se acota con NCOLS del clima. Devuelve, por fila fina (desde
    el norte, como numpy), la fila del clima que ELMFIRE lee (también desde el norte)."""
    iy = filas_finas - np.arange(filas_finas)          # IY de cada fila, desde el sur
    irow = np.minimum(np.maximum(iy, 1), clima_ancho)  # el bug: COARSE%NCOLS, no NROWS
    return filas_finas - irow


def test_grilla_alta_el_clima_se_rellena_hasta_ser_cuadrado(tmp_path):
    """Hallazgo 5: con la grilla de clima más alta que ancha, la franja norte leía el clima
    de la fila NCOLS. write_namelist rellena al este y cada fila vuelve a leer la suya."""
    filas, cols = 7, 3
    _raster(tmp_path / "dem.tif", np.zeros((filas, cols)))
    clima = np.arange(2 * filas * cols, dtype="float32").reshape(2, filas, cols)
    for nombre in namelist_writer.WEATHER_RASTERS:
        _raster(tmp_path / f"{nombre}.tif", clima)
    assert (_fila_que_lee_elmfire(filas, cols) != np.arange(filas)).sum() == filas - cols
    # En cadena los insumos son hardlinks de sólo lectura al almacén: no se escribe a través.
    objeto = tmp_path / "objeto-del-almacen"
    objeto.hardlink_to(tmp_path / "ws.tif")
    objeto.chmod(0o444)

    for _ in range(2):   # re-escribir el namelist sobre los mismos insumos no cambia nada
        namelist_writer.write_namelist(tmp_path, tmp_path / "out", simulation_hours=1,
                                       output_path=tmp_path / "elmfire.data")
    for nombre in namelist_writer.WEATHER_RASTERS:
        with rasterio.open(tmp_path / f"{nombre}.tif") as src, \
                rasterio.open(tmp_path / "dem.tif") as dem:
            datos = src.read()
            assert src.shape == (filas, filas)
            # misma esquina y celda: ELMFIRE mapea igual cada celda del combustible
            assert (src.bounds.left, src.bounds.bottom) == (dem.bounds.left, dem.bounds.bottom)
            assert src.res == dem.res
        assert np.array_equal(datos[:, :, :cols], clima)
        assert np.array_equal(datos[:, :, cols:], np.repeat(clima[:, :, -1:], filas - cols, 2))
    assert np.array_equal(_fila_que_lee_elmfire(filas, filas), np.arange(filas))
    with rasterio.open(objeto) as src:
        assert src.shape == (filas, cols)


def test_grilla_ancha_el_clima_no_se_toca(tmp_path):
    _raster(tmp_path / "dem.tif", np.zeros((3, 5)))
    for nombre in namelist_writer.WEATHER_RASTERS:
        _raster(tmp_path / f"{nombre}.tif", np.ones((2, 3, 5)))
    antes = (tmp_path / "ws.tif").stat().st_mtime_ns
    namelist_writer.write_namelist(tmp_path, tmp_path / "out", simulation_hours=1,
                                   output_path=tmp_path / "elmfire.data")
    assert (tmp_path / "ws.tif").stat().st_mtime_ns == antes


def test_la_base_del_benchmark_no_hereda_el_lw_de_la_app():
    """base-001 es LW 110 %; la app pasó a 100 % (receta calibrada). Una receta sin LW no puede
    cambiar de significado porque cambie el default de la app."""
    from app.validation import cadena
    assert cadena.HUMEDAD_VIVA_BASE == {"lh_moisture_pct": 30.0, "lw_moisture_pct": 110.0}
    assert namelist_writer.DEFAULT_LW_MOISTURE_PCT == 100.0
