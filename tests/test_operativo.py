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
