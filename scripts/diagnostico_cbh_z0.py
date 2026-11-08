"""Nota AE: ¿el rango plausible del CBH nativo o de z0 mueve algo material? SIN correr ELMFIRE.

Diseño y criterios en benchmarks/diagnosticos/e2e/notas/AE-cbh-z0-sensibilidad.md §1–§2. Toma
las celdas del día 1 de `benchmark.py copa` (bosque TU/TL con dosel, quemado y visto en la
ventana 0) y, por celda, la intensidad de Rothermel máxima antes de verse con el WAF de ELMFIRE.
Como el WAF no depende del CBH, de ahí sale el CBH umbral de Van Wagner y la curva de iniciación
para cualquier CBH. Para z0, el viento a 20 ft se escala por el cociente de
`weather_builder.wind_height_factor`. Sólo incendios de calibración.

    uv run python scripts/diagnostico_cbh_z0.py

Escribe benchmarks/diagnosticos/e2e/datos/AE_cbh_z0.json.
"""
import csv
import json

import numpy as np
import pandas as pd
import rasterio

from app.elmfire.builder import perimeter_reconstruction
from app.elmfire.builder.weather_builder import wind_height_factor
from app.validation import almacen, cadena, copa
from app.validation import definiciones as d
from app.validation import puntuacion as p
from scripts import benchmark as bm
from scripts import diagnostico_error as de

CASOS = ("los-alerces-2023/calibracion-v6-h54", "epuyen-2025/calibracion-v6",
         "los-alerces-2024/calibracion-v6", "puerto-patriada-2026/calibracion-v6",
         "los-alerces-2016/calibracion-era5-v6", "cholila-2015/calibracion-era5-v6")
RECETA = "lw-100-001"
# Rangos de §1, fijados antes de calcular: (valor v6, mínimo, máximo) en m.
RANGOS_CBH = {"TL6": (6.0, 3.0, 10.0), "TL5": (4.0, 1.5, 8.0), "TU5": (1.5, 0.5, 3.0),
              "TU3": (1.5, 0.5, 3.0), "TL2": (1.0, 0.5, 2.0)}
CURVA_CBH = tuple(np.round(np.arange(0.5, 10.01, 0.5), 1))
Z0_RANGO = (0.03, 0.5)
Z0_REFERENCIA = (1.0, 2.6)   # bosque: doble conteo con el WAF, no rango


def cbh_umbral(i_max: np.ndarray, fmc: float = copa.HUMEDAD_FOLIAR) -> np.ndarray:
    """CBH por debajo del cual Van Wagner enciende la copa con intensidad `i_max` (kW/m): la
    inversa de `copa.intensidad_critica`."""
    return np.asarray(i_max, dtype="float64") ** (2 / 3) / (0.01 * (460.0 + 26.0 * fmc))


def fraccion_copa(umbral: np.ndarray, cbh) -> float:
    """Fracción de celdas que inician copa con ese CBH (escalar o por celda)."""
    umbral = np.asarray(umbral)
    if umbral.size == 0:
        return float("nan")
    return float(np.mean(umbral > np.maximum(np.asarray(cbh, dtype="float64"), 0.1)))


def razon_viento(z0: float) -> float:
    """Cuánto cambia el viento a 20 ft (y a media llama) con `z0` en vez del de weather_builder."""
    return wind_height_factor(z0=z0) / wind_height_factor()


def celdas_dia1(caso_id: str, escalas: tuple[float, ...]) -> dict:
    """Por celda del día 1: clase, CBH v6, WAF y, por escala de viento, la intensidad máxima antes
    de verse; con escala 1, el viento a media llama (mph) en la hora de esa intensidad. Misma
    selección y misma física que `benchmark.diagnosticar_copa`."""
    caso, receta = d.Caso.cargar(caso_id), d.Receta.cargar(RECETA)
    paquete = caso.paquete()
    comunes = paquete["comunes"]
    dem = almacen.abrir(comunes["dem.tif"])
    fbfm = cadena._leer(comunes[f"fbfm40_{receta.combustible['fuente']}"
                                f"{receta.anio_combustible(caso)}.tif"])
    cc = cadena._leer(comunes["cc.tif"]) / 100.0
    ch, cbh = cadena._leer(comunes["ch.tif"]) / 10.0, cadena._leer(comunes["cbh.tif"]) / 10.0
    con_dosel = ((cc >= 0.15) & (ch >= 2.0) & (cbh > 0) & (cadena._leer(comunes["cbd.tif"]) > 0)
                 & np.isin(fbfm, [*range(161, 166), *range(181, 190)]))
    cicatriz = cadena._leer(comunes["cicatriz.tif"]).astype(bool)
    df = pd.read_csv(almacen.abrir(comunes["firms.csv"]), parse_dates=["acq_datetime"])
    v = caso.ventanas[0]
    vistas = bm._horas_por_pasada(df, v.inicio, caso.ventanas[-1].fin, dem,
                                  perimeter_reconstruction.VIIRS_PIXEL_M)
    celdas = con_dosel & cicatriz & (vistas > 0) & (vistas <= v.horas)
    with open(almacen.abrir(comunes["fuel_models.csv"])) as fh:
        modelos = {int(r[0]): r for r in csv.reader(fh) if r}
    viva = cadena.HUMEDAD_VIVA_BASE | receta.parametros
    lh, lw = viva["lh_moisture_pct"] / 100, viva["lw_moisture_pct"] / 100
    clima = {}
    for nom in ("ws", "m1", "m10", "m100"):
        with rasterio.open(almacen.abrir(paquete["ventanas"][0][f"{nom}.tif"])) as src:
            clima[nom] = src.read()
    filas = []
    for codigo in np.unique(fbfm[celdas]):
        fila = modelos.get(int(codigo))
        if fila is None or float(fila[3]) + float(fila[4]) <= 0:
            continue
        sel = celdas & (fbfm == codigo)
        waf = copa.waf_elmfire(cc[sel], ch[sel], float(fila[11]))
        antes = vistas[sel]
        i_max = {s: np.zeros(sel.sum()) for s in escalas}
        u_mf = np.zeros(sel.sum())
        for b in range(clima["ws"].shape[0]):
            ya = b <= antes + 1
            ws = clima["ws"][b][sel]
            for s in escalas:
                _, flin = copa.rothermel(fila, clima["m1"][b][sel] / 100,
                                         clima["m10"][b][sel] / 100, clima["m100"][b][sel] / 100,
                                         lh, lw, ws * s * waf * 88.0)
                flin = np.where(ya, flin, 0.0)
                if s == 1.0:
                    u_mf = np.where(flin > i_max[s], ws * waf, u_mf)
                i_max[s] = np.maximum(i_max[s], flin)
        filas.append({"clase": fila[1], "cbh": cbh[sel], "waf": waf, "u_mf": u_mf,
                      "i_max": i_max})
    return {"caso": caso_id, "celda_ha": p.Grilla(dem).celda_ha, "filas": filas}


def _unir(filas: list[dict], clave: str, s: float | None = None) -> np.ndarray:
    partes = [f[clave][s] if s is not None else f[clave] for f in filas]
    return np.concatenate(partes) if partes else np.zeros(0)


def resumir(celdas: dict, escalas: dict[str, float]) -> dict:
    filas = celdas["filas"]
    umbral = cbh_umbral(_unir(filas, "i_max", 1.0))
    cbh_v6 = _unir(filas, "cbh")
    clases = np.concatenate([[f["clase"]] * len(f["cbh"]) for f in filas]) if filas else np.zeros(0)
    base = fraccion_copa(umbral, cbh_v6)

    def con_cbh(reemplazos: dict[str, float]) -> float:
        cbh = cbh_v6.copy()
        for clase, valor in reemplazos.items():
            cbh[clases == clase] = valor
        return fraccion_copa(umbral, cbh)

    por_clase = {}
    for f in filas:
        u = cbh_umbral(f["i_max"][1.0])
        rango = RANGOS_CBH.get(f["clase"])
        por_clase[f["clase"]] = {
            "ha": float(len(u) * celdas["celda_ha"]),
            "cbh_v6": float(np.median(f["cbh"])),
            "waf": float(np.median(f["waf"])),
            "u_media_llama_mph": float(np.median(f["u_mf"])),
            "cbh_umbral_p50_p90": [float(np.percentile(u, 50)), float(np.percentile(u, 90))],
            "copa_v6": fraccion_copa(u, f["cbh"]),
            "curva": {str(c): fraccion_copa(u, c) for c in CURVA_CBH},
            **({"total_en_min": con_cbh({f["clase"]: rango[1]}),
                "total_en_max": con_cbh({f["clase"]: rango[2]})} if rango else {}),
        }
    presentes = {c: r for c, r in RANGOS_CBH.items() if c in por_clase}
    i1 = _unir(filas, "i_max", 1.0)
    viento = {}
    for nombre, s in escalas.items():
        i_s = _unir(filas, "i_max", s)
        viento[nombre] = {
            "escala": s,
            "copa": fraccion_copa(cbh_umbral(i_s), cbh_v6),
            "adj_equivalente": float(np.median(i_s[i1 > 0] / i1[i1 > 0])) if (i1 > 0).any()
            else None,
        }
    return {"caso": celdas["caso"], "con_dosel_ha": float(len(umbral) * celdas["celda_ha"]),
            "copa_v6": base,
            "todas_al_min": con_cbh({c: r[1] for c, r in presentes.items()}),
            "todas_al_max": con_cbh({c: r[2] for c, r in presentes.items()}),
            "por_clase": por_clase, "viento": viento}


def main() -> None:
    escalas = {f"z0={z}": razon_viento(z) for z in (*Z0_RANGO, *Z0_REFERENCIA)}
    resultados = []
    for caso_id in CASOS:
        r = resumir(celdas_dia1(caso_id, (1.0, *escalas.values())), escalas)
        control = json.loads((d.RAIZ / "diagnosticos" / "copa" /
                              f"{caso_id.split('/')[0]}.json").read_text())["dias"][0]
        r["control_van_wagner"] = control["van_wagner"]
        if abs(control["van_wagner"] - r["copa_v6"]) > 1e-9:
            raise SystemExit(f"{caso_id}: el control no coincide "
                             f"({r['copa_v6']} contra {control['van_wagner']})")
        resultados.append(r)
        print(f"{caso_id}: copa v6 {r['copa_v6']:.3f}, extremos {r['todas_al_min']:.3f} / "
              f"{r['todas_al_max']:.3f}; viento " + ", ".join(
                  f"{k} ×{v['escala']:.3f} → ADJ eq {v['adj_equivalente']:.3f}, "
                  f"copa {v['copa']:.3f}" for k, v in r["viento"].items()))
    salida = {"factor_20ft": {str(z): wind_height_factor(z0=z)
                              for z in (0.01, *Z0_RANGO, 0.1, 0.22, *Z0_REFERENCIA)},
              "rangos_cbh": RANGOS_CBH, "casos": resultados}
    de.SALIDA.mkdir(parents=True, exist_ok=True)
    (de.SALIDA / "AE_cbh_z0.json").write_text(json.dumps(salida, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
