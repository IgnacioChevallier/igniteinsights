"""Paso 4 de Scott & Burgan: contrastar las asignaciones de arbustal contra la quema A4.

Scott & Burgan (2005, pp. 8-9) cierran su procedimiento con un filtro de rechazo: elegido
un modelo, hay que mirar su comportamiento predicho y descartarlo si contradice lo
observado. Hasta ahora ese paso se aplicaba con la escala adjetiva publicada, medida en un
escenario de referencia (D2L2) que no es el nuestro. La PT-37 §3.3-3.4 da algo mejor: una
quema experimental con meteorología medida.

Cada candidato se corre en el playground bajo ESAS condiciones, en terreno plano, y se
compara contra lo observado: 80 m/min de propagación y 3 a 4 m de llama.

    uv run python scripts/paso4_quema_a4.py
"""
import json
import shutil
import urllib.request
from pathlib import Path

import numpy as np
import rasterio

from app.elmfire.builder import fuels_builder, namelist_writer
from app.elmfire.builder.fuels_builder import fuel_model_info
from app.playground.builder import build_scenario_inputs
from app.playground.metrics import ros_adjective, scenario_metrics
from app.playground.schemas import Scenario

RUNNER = "http://localhost:8001/simulate"
INPUTS = Path("data/elmfire/inputs")
OUTPUTS = Path("data/elmfire/outputs")

# Condiciones medidas de la quema, PT-37 §3.3 (Cerro Jones, 14-09-2011, 16:00)
# La quema se hizo con viento sostenido de 24 km/h y ráfagas de 51 km/h, y el frente
# recorrió 40 m en 30 s: los 80 m/min observados son el pico bajo ráfaga, no un promedio
# horario. Se corre cada candidato en las dos condiciones y el resultado se lee como
# horquilla, que es la comparación honesta contra un dato de una sola quema.
VIENTOS_MPH = {"sostenido": 14.9, "ráfaga": 31.7}
M1_PCT = 8.0             # de FFMC 92,7 por la conversión de Van Wagner: 147(101-F)/(59,5+F)
LW_PCT = 82.0            # humedad foliar medida en espino negro, la especie dominante
LH_PCT = 30.0            # pasto 100 % curado: transferencia dinámica completa a muerto
ROS_OBSERVADA_M_H = 4800.0   # 80 m/min en régimen
LLAMA_OBSERVADA_M = (3.0, 4.0)

CANDIDATOS = {
    148: "SH8 · asignado a ñire bajo y lenga achaparrada",
    144: "SH4 · asignado a arbustal nativo y matorral mixto",
    149: "SH9 · descartado por carga, se verifica",
    123: "GS3 · asignado a estepa arbustiva y remanente de disturbio",
    145: "SH5 · el del baseline, clima seco (control)",
}


def byram_flame_m(fli_kw_m: float) -> float:
    """Byram (1959): L = 0,0775 · I^0,46, con I en kW/m."""
    return 0.0775 * float(fli_kw_m) ** 0.46


def correr(code: int, viento_mph: float, etiqueta: str) -> dict:
    nombre = f"paso4_{code}_{etiqueta.replace('á', 'a')}"
    inputs, outputs = (INPUTS / nombre).resolve(), (OUTPUTS / nombre).resolve()
    shutil.rmtree(inputs, ignore_errors=True)
    outputs.mkdir(parents=True, exist_ok=True)

    escenario = Scenario(
        name=nombre, fbfm40_code=code, slope_deg=0,
        wind_speed_mph=viento_mph, wind_direction_deg=0.0,
        m1_pct=M1_PCT, m10_pct=M1_PCT + 2, m100_pct=M1_PCT + 5,
        lh_moisture_pct=LH_PCT, lw_moisture_pct=LW_PCT,
        tstop_s=3600.0, domain_size_m=12000.0,
    )
    build_scenario_inputs(escenario, inputs)
    shutil.copy2(fuels_builder.FUEL_MODEL_TABLE, inputs / namelist_writer.FUEL_MODEL_FILE)
    # El endpoint de playground delega el namelist en run_simulation, que necesita base de
    # datos. Acá se escribe directo y después se reescriben los dos directorios a las rutas
    # del contenedor, que es lo único que el runner ve por el volumen compartido.
    elmfire_data, _, _ = namelist_writer.write_namelist(
        inputs, outputs, simulation_hours=escenario.horizon_hours,
        output_path=inputs / "elmfire.data", dtdump_s=escenario.dtdump_s,
        lh_moisture_pct=escenario.lh_moisture_pct, lw_moisture_pct=escenario.lw_moisture_pct,
    )
    texto = elmfire_data.read_text()
    texto = texto.replace(str(inputs.resolve()), f"/app/data/elmfire/inputs/{nombre}")
    texto = texto.replace(str(outputs.resolve()), f"/app/data/elmfire/outputs/{nombre}")
    elmfire_data.write_text(texto)

    cuerpo = json.dumps({
        "elmfire_data_path": f"/app/data/elmfire/inputs/{nombre}/elmfire.data",
        "inputs_dir": f"/app/data/elmfire/inputs/{nombre}",
        "outputs_dir": f"/app/data/elmfire/outputs/{nombre}",
        "simulation_hours": 1, "dtdump_s": 3600.0,
    }).encode()
    req = urllib.request.Request(RUNNER, data=cuerpo, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        json.load(r)

    toa = sorted(outputs.glob("time_of_arrival*.tif"))
    if not toa:
        return {"code": code, "ros": 0.0, "llama": 0.0, "fli": 0.0}
    m = scenario_metrics(toa[-1], 1)
    fli_files = sorted(outputs.glob("flin*.tif"))
    fli = 0.0
    if fli_files:
        with rasterio.open(fli_files[-1]) as src:
            v = src.read(1)
        quemado = v[v > 0]
        fli = float(np.median(quemado)) if quemado.size else 0.0
    return {
        "code": code,
        "ros": m["final"]["head_ros_m_per_h"],
        "clase": m["final"]["head_ros_class"],
        "fli": fli,
        "llama": byram_flame_m(fli) if fli else 0.0,
    }


def main() -> None:
    print(f"Observado en la quema A4: {ROS_OBSERVADA_M_H:,.0f} m/h "
          f"({ROS_OBSERVADA_M_H / 60:.0f} m/min, clase {ros_adjective(ROS_OBSERVADA_M_H)}) · "
          f"llama {LLAMA_OBSERVADA_M[0]:.0f}-{LLAMA_OBSERVADA_M[1]:.0f} m")
    print(f"Condiciones: m1 {M1_PCT}% · LW {LW_PCT}% · pendiente 0 · viento "
          + " y ".join(f"{v} mph ({k})" for k, v in VIENTOS_MPH.items()) + "\n")
    cab = f"{'Modelo':8s}"
    for etiqueta in VIENTOS_MPH:
        cab += f"{'ROS ' + etiqueta:>16s}{'llama':>8s}"
    print(cab + "   veredicto")

    for code, desc in CANDIDATOS.items():
        fila, llamas, ros_max = f"{fuel_model_info(code)['name']:8s}", [], 0.0
        for etiqueta, viento in VIENTOS_MPH.items():
            r = correr(code, viento, etiqueta)
            fila += f"{r['ros']:12,.0f} m/h{r['llama']:7.1f}m"
            llamas.append(r["llama"])
            ros_max = max(ros_max, r["ros"])
        # Compatible = la horquilla del modelo alcanza el orden de lo observado y la llama
        # cae dentro del rango medido, con tolerancia de un factor 2 en cada extremo.
        llama_ok = any(LLAMA_OBSERVADA_M[0] * 0.5 <= x <= LLAMA_OBSERVADA_M[1] * 2 for x in llamas)
        veredicto = ("compatible" if (llama_ok and ros_max >= ROS_OBSERVADA_M_H * 0.4)
                     else "por debajo de lo observado")
        print(fila + f"   {veredicto}")
        print(f"         └ {desc}")


if __name__ == "__main__":
    main()
