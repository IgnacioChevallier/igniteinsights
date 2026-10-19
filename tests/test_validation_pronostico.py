"""Protocolo P-24 y diagnóstico de copa (docs/resultados/DIA-1-PROPUESTA.md §2 y §4)."""
import csv
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

from app.validation import copa, pronostico
from app.validation import puntuacion as p

T0 = datetime(2025, 1, 15, 14, tzinfo=UTC)
HA = 0.09


def test_pasadas_toma_la_ultima_deteccion_de_cada_una():
    tiempos = pd.Series(pd.to_datetime([
        "2025-01-15 18:10", "2025-01-15 18:12", "2025-01-15 19:50",   # una pasada (< 2 h)
        "2025-01-16 05:30"], utc=True))
    assert pronostico.pasadas(tiempos) == [pd.Timestamp("2025-01-15 19:50", tz="UTC"),
                                           pd.Timestamp("2025-01-16 05:30", tz="UTC")]


def test_una_ventana_con_minutos_pide_una_banda_mas():
    v = pronostico.ventana_desde(T0 + timedelta(hours=4, minutes=30))
    assert v["t0"] == (T0 + timedelta(hours=4)).isoformat() and v["tstart_s"] == 1800
    assert pronostico.bandas_necesarias(24, 0) == 25
    assert pronostico.bandas_necesarias(24, 1800) == 26


def test_la_hora_de_borde_es_de_la_ventana_siguiente():
    desfases, horas = [0, 24, 48], [24, 24, 6]
    assert pronostico.hora_en_base(23, desfases, horas) == (0, 23)
    assert pronostico.hora_en_base(24, desfases, horas) == (1, 0)
    assert pronostico.hora_en_base(54, desfases, horas) == (2, 6)
    with pytest.raises(ValueError):
        pronostico.hora_en_base(55, desfases, horas)


def test_lo_no_visto_y_la_semilla_no_cuentan():
    semilla = np.array([1, 0, 0, 0, 0], dtype=bool)
    cicatriz = np.array([1, 1, 1, 0, 0], dtype=bool)
    vistas = np.array([-1, 5, 30, np.inf, np.inf])      # la celda 2 se ve recién a las 30 h
    pred = np.array([1, 1, 1, 1, 0], dtype=bool)
    m = pronostico.puntuar(pred, semilla, cicatriz, np.zeros(5, bool), vistas,
                           np.full(5, -1.0), 24, HA)["cicatriz"]
    # acierto en 1; la 2 (no vista a 24 h) se excluye; la 3 (fuera de la cicatriz) es error
    assert (m["tp"], m["fp"], m["fn"]) == (1, 1, 0)


def test_el_anillo_ya_visto_al_reiniciar_no_cuenta():
    semilla = np.array([1, 0, 0, 0], dtype=bool)
    cicatriz = np.array([1, 1, 1, 0], dtype=bool)
    vistas = np.array([-1, 0, 5, np.inf])     # la celda 1 ya estaba vista al reiniciar
    pred = np.array([1, 1, 0, 0], dtype=bool)
    m = pronostico.puntuar(pred, semilla, cicatriz, np.zeros(4, bool), vistas,
                           np.full(4, -1.0), 12, HA)["cicatriz"]
    # la 1 no es acierto ni error; la 2, vista a las 5 h y no predicha, es un falso negativo
    assert (m["tp"], m["fp"], m["fn"]) == (0, 0, 1)


def test_la_cadena_a_una_hora_dada():
    semilla = np.array([1, 0, 0], dtype=bool)
    horas = np.array([0.0, 10.0, np.nan])
    ventanas = [(T0, T0 + timedelta(hours=24), semilla, horas)]
    assert pronostico.quemado_en(ventanas, T0 + timedelta(hours=5)).tolist() == [1, 0, 0]
    assert pronostico.quemado_en(ventanas, T0 + timedelta(hours=12)).tolist() == [1, 1, 0]
    assert pronostico.quemado_en(ventanas, T0 + timedelta(hours=99)).tolist() == [1, 1, 0]


def test_la_persistencia_crece_lo_que_crecio_el_radio(tmp_path):
    ruta = tmp_path / "dem.tif"
    with rasterio.open(ruta, "w", driver="GTiff", height=41, width=41, count=1, dtype="float32",
                       crs="EPSG:32719", transform=from_origin(0, 1230, 30, 30)) as dst:
        dst.write(np.zeros((1, 41, 41), dtype="float32"))
    grilla = p.Grilla(ruta)
    previa = np.zeros((41, 41), dtype=bool)
    previa[20, 20] = True
    semilla = np.zeros((41, 41), dtype=bool)
    semilla[18:23, 18:23] = True
    crecido = pronostico.persistencia(semilla, previa, dt_h=12, plazo_h=24, grilla=grilla)
    assert (crecido & semilla).sum() == semilla.sum()
    assert crecido.sum() > 3 * semilla.sum()
    assert not pronostico.persistencia(semilla, semilla, 12, 24, grilla)[0, 0]


def test_resumen_ignora_la_ventana_de_la_ignicion():
    def fila(inc, n, a, b):
        return {"incendio": inc, "n": n, "plazos": {"24": {
            "p24": {"cicatriz": {"dice": a}}, "cadena": {"cicatriz": {"dice": b}}}}}
    r = pronostico.resumir([fila("x", 0, 0.0, 0.9), fila("x", 1, 0.5, 0.3),
                            fila("y", 1, 0.2, 0.4)], 24)
    assert r["n"] == 2 and r["mejoran"] == 1
    assert r["mediana_delta"] == pytest.approx(0.0)


def test_cfis_y_van_wagner_publicados():
    # Van Wagner con CBH 1,5 m y humedad foliar de 90 %: los ~270 kW/m de DECISIONES-MODELO-V0 §5
    assert copa.intensidad_critica(1.5) == pytest.approx(272.2, abs=0.5)
    # Tabla 4 de Cruz et al. (2004): logit a mano
    g = 4.236 + 0.357 * 20 - 0.710 * 4 - 1.856 - 0.331 * 9
    assert copa.prob_cfis(20, 4, 1.5, 9) == pytest.approx(1 / (1 + np.exp(-g)))
    assert copa.prob_cfis(20, 4, 0.5, 9) < copa.prob_cfis(20, 4, 2.5, 9)


def test_rothermel_responde_al_viento_y_a_la_humedad():
    filas = {r[1]: r for r in csv.reader(open("app/elmfire/fuel_models.csv"))}
    tl8 = filas["TL8"]
    lento, _ = copa.rothermel(tl8, 0.06, 0.08, 0.10, 0.3, 1.0, 88.0)
    rapido, _ = copa.rothermel(tl8, 0.06, 0.08, 0.10, 0.3, 1.0, 880.0)
    humedo, _ = copa.rothermel(tl8, 0.20, 0.22, 0.24, 0.3, 1.0, 88.0)
    assert rapido > 3 * lento and humedo < lento
    # bajo un pinar cerrado el viento a media llama es ~el 9 % del de 20 pies
    assert copa.waf_elmfire(0.8, 15, 0.3) == pytest.approx(0.086, abs=0.01)
