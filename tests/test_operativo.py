"""Modo operativo: incendios y ciclo GFS disponible (docs/dashboard-producto.md)."""
from datetime import UTC, datetime, timedelta

from app.operativo import servicio as s
from app.validation import pronostico

T = datetime(2026, 1, 5, 19, 0, tzinfo=UTC)


def det(lon: float, lat: float, horas: float = 0.0) -> s.Deteccion:
    return s.Deteccion(lon, lat, T + timedelta(hours=horas))


def test_detecciones_a_menos_de_3_km_son_un_incendio_y_a_mas_dos():
    # 0,02° de latitud ≈ 2,2 km: encadenadas; 0,1° ≈ 11 km: otro incendio.
    grupos = s.agrupar([det(-71.53, -42.14), det(-71.53, -42.16), det(-71.53, -42.18),
                        det(-71.53, -42.28)])
    assert sorted(len(g) for g in grupos) == [1, 3]


def test_un_incendio_sin_detecciones_en_24_h_no_esta_activo():
    viejo = [det(-71.53, -42.14, -30)]
    nuevo = [det(-71.40, -42.50, -2), det(-71.40, -42.51, -1)]
    activos = s.incendios_activos(viejo + nuevo, T)
    assert [len(i.detecciones) for i in activos] == [2]
    assert activos[0].nombre == "Cerca de Cholila · desde 05-01"


def test_el_nombre_sale_de_la_primera_deteccion_y_no_cambia_con_las_nuevas():
    primera = [det(-71.535, -42.148)]
    antes = s.incendios_activos(primera, T)[0].nombre
    despues = s.incendios_activos(primera + [det(-71.55, -42.17, 12)], T + timedelta(hours=12))
    assert antes == despues[0].nombre == "Cerca de Puerto Patriada · desde 05-01"


def test_el_id_sale_de_la_primera_deteccion_y_es_estable():
    primera = [det(-71.535, -42.148)]
    antes = s.incendios_activos(primera, T)[0]
    despues = s.incendios_activos(primera + [det(-71.55, -42.17, 12)], T + timedelta(hours=12))[0]
    assert antes.id == despues.id
    assert antes.id.startswith("f-")


def test_focos_cercanos_separados_por_mas_de_24_h_no_se_unen():
    grupos = s.agrupar([det(-71.535, -42.148, -30), det(-71.535, -42.148, 0)])
    assert sorted(len(g) for g in grupos) == [1, 1]


def test_el_ciclo_es_el_publicado_cuando_la_pasada_se_ve_en_firms():
    # Pasada 19:20 → visible 22:20 → el 18z (completo ~22:00) ya está; el 00z del 6 todavía no.
    assert pronostico.ciclo_disponible(T.replace(minute=20)) == T.replace(hour=18)
    # Pasada 06:44 → visible 09:44 → el 06z recién a las 10:00: queda el 00z.
    assert (pronostico.ciclo_disponible(datetime(2026, 1, 6, 6, 44, tzinfo=UTC))
            == datetime(2026, 1, 6, 0, tzinfo=UTC))


def test_la_proxima_pasada_es_la_siguiente_hora_tipica():
    assert s.proxima_pasada(T) == datetime(2026, 1, 6, 5, 30, tzinfo=UTC)
    assert s.proxima_pasada(T.replace(hour=10)) == T


def test_el_corte_de_la_demo_vale_solo_en_demo_y_fija_la_primera_deteccion(monkeypatch):
    """tick y estado agrupan con el mismo corte: si no, el id del incendio difiere y el panel
    no encuentra los pronósticos de la demo (quedaba en "el pronóstico se está calculando")."""
    import asyncio
    from types import SimpleNamespace

    vieja, nueva = det(-71.5, -42.1, -20), det(-71.5, -42.1, 0)

    async def aoi(session):
        return SimpleNamespace(id=1)

    async def fuegos(session, since, aoi_id, until):
        return [{"properties": {"longitude": d.lon, "latitude": d.lat,
                                "acq_datetime": d.t.isoformat()}}
                for d in (vieja, nueva) if since <= d.t < until]

    monkeypatch.setattr(s.repository, "get_or_create_default_aoi", aoi)
    monkeypatch.setattr(s.repository, "get_active_fires", fuegos)
    op = SimpleNamespace(demo_desde=T - timedelta(hours=1))
    ahora = T + timedelta(hours=pronostico.LATENCIA_FIRMS_H)

    def primera(modo: str) -> datetime:
        dets = asyncio.run(s.detecciones_visibles(None, ahora, s.desde_de(op, modo)))
        return min(d.t for d in dets)

    assert primera("demo") == nueva.t
    assert primera("vivo") == vieja.t


def test_el_id_no_depende_del_orden_de_las_filas_cuando_la_primera_hora_empata():
    # Un pase trae varias detecciones con la misma hora y la consulta no ordena.
    grupo = [det(-71.535, -42.148), det(-71.534, -42.150), det(-71.536, -42.146)]
    ids = {s.incendios_activos(g, T)[0].id for g in (grupo, grupo[::-1], grupo[1:] + grupo[:1])}
    assert len(ids) == 1


def test_el_pronostico_dice_si_tiene_ensamble(monkeypatch, tmp_path):
    """El cliente ofrece la capa de acuerdo sólo donde existe el JSON (no en todas las pasadas)."""
    from types import SimpleNamespace

    monkeypatch.setattr(s.settings, "elmfire_outputs_dir", str(tmp_path))
    inc = s.incendios_activos([det(-71.535, -42.148)], T)[0]
    con, sin = (SimpleNamespace(id=n, simulacion_id=None, pasada=T, disponible=T, ciclo_gfs=None)
                for n in ("a", "b"))
    s.salidas_de("a").mkdir()
    (s.salidas_de("a") / "ensemble_agreement.json").write_text("{}")
    assert s._incendio_json(inc, con, None)["pronostico"]["ensamble"] is True
    assert s._incendio_json(inc, sin, None)["pronostico"]["ensamble"] is False


def test_el_miembro_gefs_que_no_cubre_la_grilla_falla_en_vez_de_inventar_clima(tmp_path):
    """Patriada 05-01: el recorte GEFS sin margen (1×2 celdas de 0,25°) no llegaba a la mitad sur
    de la caja; reproject rellenaba con el nodata -9999 y salía viento de 27.530 mph y m1 = 1 %
    en el 70 % de la grilla (docs/resultados/ENSAMBLE-DEMO-DIAGNOSTICO.md)."""
    import numpy as np
    import pytest
    import rasterio
    from rasterio.transform import from_origin

    from app.operativo.ensamble import _preparar_miembro

    base, fuente = tmp_path / "base", tmp_path / "fuente"
    base.mkdir()
    fuente.mkdir()
    with rasterio.open(base / "dem.tif", "w", driver="GTiff", width=40, height=40, count=1,
                       dtype="float32", crs="EPSG:4326",
                       transform=from_origin(-71.75, -42.0, 0.01, 0.01)) as dst:
        dst.write(np.zeros((1, 40, 40), "float32"))
    # Una fila de celdas GEFS que cubre sólo la mitad norte del DEM (-42,0 … -42,4).
    for nombre, valor in (("u10", 3.0), ("v10", 0.0), ("t2m", 290.0), ("rh", 40.0)):
        with rasterio.open(fuente / f"{nombre}.tif", "w", driver="GTiff", width=2, height=1,
                           count=2, dtype="float32", nodata=-9999.0, crs="EPSG:4326",
                           transform=from_origin(-71.875, -41.875, 0.25, 0.25)) as dst:
            dst.write(np.full((2, 1, 2), valor, "float32"))
    with pytest.raises(RuntimeError, match="no cubre"):
        _preparar_miembro(base, fuente, tmp_path / "miembro")


def test_en_vivo_una_pasada_del_racimo_ya_pronosticado_no_corre_y_en_demo_si():
    def p(horas: float, estado: str = "listo") -> s.Pronostico:
        return s.Pronostico(pasada=T + timedelta(hours=horas), estado=estado)

    ultima = T + timedelta(hours=2)   # NOAA-21 dos horas después de una SNPP ya pronosticada
    assert not s.a_pronosticar([p(0)], ultima, "vivo")
    assert s.a_pronosticar([p(0)], ultima, "demo")
    assert s.a_pronosticar([p(0, "fallido")], ultima, "vivo")      # el fallido se reintenta
    assert s.a_pronosticar([p(-12)], ultima, "vivo")               # el racimo anterior no cuenta
    assert not s.a_pronosticar([p(2, "corriendo")], ultima, "demo")
