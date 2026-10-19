"""Aritmética del frente 1 (scripts/diagnostico_metrica.py) con rásters sintéticos."""
import numpy as np
import pandas as pd

from app.validation import puntuacion as p
from scripts import diagnostico_metrica as dm


def test_variantes_de_exclusion():
    forma = (12, 12)
    exc = np.zeros(forma, bool)
    cic = np.zeros(forma, bool)
    cic[2:10, 2:10] = True
    cic[5:7, 5:7] = False         # isla (hueco interior de la cicatriz final)
    vistas = np.zeros(forma, bool)
    vistas[:, :6] = True          # lo visto: columnas 0-5 (la isla queda mitad vista)

    # el relleno ignora el fondo que llega al borde y toma el hueco interior
    lleno = dm.rellenar_huecos(cic)
    assert lleno[5, 5] and lleno[6, 6] and not lleno[0, 0]
    isl = dm.islas_no_vistas(cic, vistas)
    assert isl[5, 6] and isl[6, 6] and not isl[5, 5] and isl.sum() == 2

    # (a) corregida: sólo las islas no vistas; un FP lejos del fuego SIGUE puntuando
    c = dm.excluido_corregido(exc, cic, vistas)
    assert c[5, 6] and not c[0, 11] and not c[3, 3]
    # la descartada excluía ese FP lejano (premiaba sobre-propagar)
    assert dm.excluido_descartado(exc, cic, vistas)[0, 11]

    pred = np.ones(forma, bool)
    ref = cic & vistas
    antes = p.metricas(pred, ref, 1.0, exc | (cic & ~vistas))
    despues = p.metricas(pred, ref, 1.0, c | (cic & ~vistas))
    assert despues["tp"] == antes["tp"] and despues["fp"] == antes["fp"] - 2

    # (b) el anillo: visto al reiniciar (vistas_h <= 0) y fuera de la semilla se EXCLUYE
    semilla = np.zeros(forma, bool)
    semilla[0, 0] = True
    vistas_h = np.full(forma, np.inf)
    vistas_h[0, :3] = -1.0
    e = dm.excluido_estricto(exc, semilla, vistas_h)
    assert not e[0, 0] and e[0, 1] and e[0, 2] and not e[5, 5]
    # excluir saca la celda de TP, FP y FN por igual
    m = p.metricas(np.ones(forma, bool), np.zeros(forma, bool), 1.0, e)
    assert m["fp"] == forma[0] * forma[1] - int(e.sum())


def test_resumen_y_control():
    filas = pd.DataFrame({"receta": ["a", "a", "b", "b"], "caso": ["x", "y", "x", "y"],
                          "dice_oficial": [0.5, 0.3, 0.4, 0.4],
                          "dice_corregido": [0.5, 0.5, 0.7, 0.6]})
    r = dm.resumen_recetas(filas).set_index("receta")
    assert r.loc["a", "puesto_medio_oficial"] == 1 and r.loc["b", "puesto_medio_oficial"] == 2
    assert r.loc["b", "puesto_medio_corregido"] == 1   # el orden puede cambiar

    texto = ("P-24 contra cadena, 12 h (k ≥ 1): mediana ΔDice 0.168, mejora en 6 de 6 incendios\n"
             "P-24 contra persistencia, 24 h (k ≥ 1): mediana ΔDice -0.010, mejora en 2 de 6")
    assert dm.leer_control_p24(texto) == {("cadena", 12): (0.168, 6),
                                          ("persistencia", 24): (-0.01, 2)}
    assert dm.puesto({"a": 1.0, "b": 3.0}) == {"b": 1, "a": 2}
