"""Correr, reconstruir y puntuar una iteración (receta × caso), ventana por ventana.

Todo pasa por el almacén: ELMFIRE lee un directorio materializado desde hashes y lo que
escribe se guarda por hash. El manifiesto de la iteración (en git) es la única fuente de
verdad sobre qué se corrió; con él y el almacén cualquier ventana se re-ejecuta byte a
byte (`verificar`).

Semilla de la ventana n > 0, según la receta:
- `prediccion`: lo que la ventana n-1 dio por quemado (su semilla más donde llegó el
  fuego). Mide el error acumulado del modelo corriendo solo.
- `observacion`: FIRMS hasta el inicio de la ventana, del paquete del caso. Mide la
  habilidad a 24 h, como el harness A.
"""
import asyncio
import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import rasterio

from app.elmfire.builder import (
    fuels_builder,
    ignition_builder,
    namelist_writer,
    weather_builder,
)
from app.elmfire.runner.client import ELMFIRERunnerClient
from app.elmfire.runner.schemas import SimulationRequest
from app.validation import almacen, humedad, viento
from app.validation import puntuacion as p
from app.validation.definiciones import (
    Caso,
    Receta,
    cargar_manifiesto,
    exigir_receta_intacta,
    ruta_iteracion,
)

ELMFIRE_VERSION = "2025.0212"
TRABAJO = Path("data/benchmark/trabajo")
VISTAS = Path("data/benchmark/vistas")
CONTENEDOR = Path("/app")   # el runner monta ./data en /app/data
# Lo que ELMFIRE lee del paquete. Las referencias del paquete no son insumos del modelo.
ESTATICOS = ("dem.tif", "slp.tif", "asp.tif", "adj.tif", "cc.tif", "ch.tif", "cbh.tif",
             "cbd.tif", "ws.tif", "wd.tif", "m1.tif", "m10.tif", "m100.tif",
             "fuel_models.csv")
# Códigos del ráster de confusión, los mismos que ya dibuja el dashboard.
NADA, SEMILLA, ACIERTO, PREDICHO_SIN_OBS, OBS_SIN_PREDECIR, EXCLUIDO = range(6)


def git_estado() -> dict:
    """Commit y si hay cambios sin commitear en el código que produce los números."""
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    sucio = subprocess.run(["git", "status", "--porcelain", "--", "app", "scripts"],
                           capture_output=True, text=True)
    return {"sha": sha.stdout.strip(), "sucio": bool(sucio.stdout.strip())}


def _leer(sha: str) -> np.ndarray:
    with rasterio.open(almacen.abrir(sha)) as src:
        return src.read(1)


def _toa(salidas: dict[str, str]) -> str:
    nombres = sorted(n for n in salidas if n.startswith("time_of_arrival") and n.endswith(".tif"))
    if not nombres:
        raise RuntimeError("la corrida no dejó time_of_arrival")
    return salidas[nombres[-1]]


def _quemado(ventana: dict) -> np.ndarray:
    """Lo que la ventana da por quemado al terminar: su semilla más donde llegó el fuego."""
    return (_leer(ventana["insumos"]["phi.tif"]) < 0) | (_leer(_toa(ventana["salidas"])) > 0)


def _rutas(caso: Caso, receta: Receta, n: int) -> tuple[Path, Path]:
    raiz = TRABAJO / caso.id / receta.id / f"v{n}"
    return raiz / "insumos", raiz / "salidas"


def _contenedor(ruta: Path) -> str:
    return str(CONTENEDOR / ruta)


def _normalizar_namelist(texto: str, insumos: Path, salidas: Path) -> str:
    return (texto.replace(_contenedor(insumos), "{INSUMOS}")
                 .replace(_contenedor(salidas), "{SALIDAS}"))


def _preparar(caso: Caso, receta: Receta, n: int, previa: dict | None,
              insumos: Path, salidas: Path) -> dict[str, str]:
    """Arma los insumos de la ventana n y devuelve {nombre: sha}, ya en el almacén."""
    paquete = caso.paquete()
    archivos = paquete["comunes"] | paquete["ventanas"][n]
    combustible = f"fbfm40_{receta.combustible['fuente']}{receta.anio_combustible(caso)}.tif"
    if combustible not in archivos:
        raise FileNotFoundError(f"{caso.id} no empaquetó {combustible}")
    elegidos = {nombre: archivos[nombre] for nombre in ESTATICOS}
    elegidos["fbfm40.tif"] = archivos[combustible]
    modelo = receta.parametros.get("modelo_humedad")
    if modelo in ("fosberg", "altura") and not {"t2m_gfs.tif", "rh_gfs.tif"} <= set(archivos):
        raise FileNotFoundError(f"{caso.id} no empaquetó el clima crudo: definir "
                                "`clima_crudo` en el caso")
    if modelo == "retardo":
        for nombre in ("m1.tif", "m10.tif", "m100.tif"):
            alternativo = nombre.replace(".tif", "_retardo.tif")
            if alternativo not in archivos:
                raise FileNotFoundError(f"{caso.id} no empaquetó {alternativo}: definir "
                                        "`humedad_retardo_h` en el caso")
            elegidos[nombre] = archivos[alternativo]
    if previa is None or receta.semilla == "observacion":
        elegidos["phi.tif"] = archivos["phi.tif"]
    shutil.rmtree(insumos, ignore_errors=True)   # nada de una preparación anterior
    almacen.materializar(elegidos, insumos)

    if previa is not None and receta.semilla == "prediccion":
        ignition_builder.build_ignition_from_mask(_quemado(previa), insumos / "dem.tif", insumos)
    par = receta.parametros
    if modelo in ("fosberg", "altura"):
        _humedad_con_criterio(modelo, archivos, insumos, caso.ventanas[n].inicio,
                              float(np.mean(caso.datos["caja_wgs84"][::2])))
    if "reasignar_combustible" in par:
        # Diagnóstico de un hallazgo del crosswalk (nunca receta candidata: el crosswalk es el
        # aporte de la tesis y no se calibra). {"188": 165} modela las plantaciones TL8 como TU5.
        _reescribir(insumos / "fbfm40.tif",
                    lambda a: reasignar(a, par["reasignar_combustible"]))
    if par.get("dosel_coherente"):
        # Diagnóstico (auditoría física): el combustible sale de CCS-BAP y el dosel de Hansen 2000
        # + ETH 2020, y en el matorral quemado se contradicen. Con dosel, ELMFIRE le da al SH el
        # WAF de un bosque cerrado (~0,08 en vez de 0,46). Como LANDFIRE, sin dosel donde el
        # combustible no es forestal.
        with rasterio.open(insumos / "fbfm40.tif") as src:
            sin_dosel = no_forestal(src.read(1))
        for nombre in ("cc.tif", "ch.tif", "cbh.tif", "cbd.tif"):
            _reescribir(insumos / nombre, lambda a: np.where(sin_dosel, 0, a))
    if "combustible_perdida_reciente" in par:
        # docs/crosswalk/DECISIONES-MODELO-V0 §3: una quema de 0-1 año es ceniza, fustes en
        # pie y rebrote incipiente (Tiribelli et al. 2019; LANDFIRE FDist): casi no se
        # mapa (2013/2017) todavía le da el combustible del bosque. {"anios": n, "codigo": c}
        # pone c donde Hansen marca pérdida en los n años antes del incendio.
        if "lossyear.tif" not in archivos:
            raise FileNotFoundError(f"{caso.id} no empaquetó lossyear.tif (protocolo -x2)")
        cfg = par["combustible_perdida_reciente"]
        with rasterio.open(almacen.abrir(archivos["lossyear.tif"])) as src:
            reciente = perdida_previa(src.read(1), caso.anio_fuego,
                                      desde=caso.anio_fuego - cfg["anios"])
        _reescribir(insumos / "fbfm40.tif", lambda a: np.where(reciente, cfg["codigo"], a))
    if par.get("combustible_por_edad_quema"):
        # docs/resultados/LO-YA-QUEMADO-PROPUESTA §4 y §6 (protocolo LYQ-1): la misma regla que
        # la preparación de la app, sobre las quemas de Hansen posteriores al mapa del caso.
        if "lossyear.tif" not in archivos:
            raise FileNotFoundError(f"{caso.id} no empaquetó lossyear.tif (protocolo -p)")
        with rasterio.open(almacen.abrir(archivos["lossyear.tif"])) as src:
            anio_quema = src.read(1)
        anio_mapa = receta.anio_combustible(caso)
        _reescribir(insumos / "fbfm40.tif", lambda a: fuels_builder.reassign_burns_by_age(
            a[0], anio_quema, caso.anio_fuego, anio_mapa)[np.newaxis])
    if par.get("dosel_sin_perdida_previa"):
        # docs/crosswalk/DECISIONES-MODELO-V0 §3: el dosel es Hansen 2000 + ETH 2020 y los
        # dos siguen viendo bosque en las quemas de 2015 (fustes en pie). Sin dosel donde
        # pérdida antes del año del incendio (nunca ese año: sería ver la propia cicatriz).
        if "lossyear.tif" not in archivos:
            raise FileNotFoundError(f"{caso.id} no empaquetó lossyear.tif (protocolo -x2)")
        with rasterio.open(almacen.abrir(archivos["lossyear.tif"])) as src:
            quemado = perdida_previa(src.read(1), caso.anio_fuego)
        for nombre in ("cc.tif", "ch.tif", "cbh.tif", "cbd.tif"):
            _reescribir(insumos / nombre, lambda a: np.where(quemado, 0, a))
    if {"sin_dosel", "cbh_por_combustible", "cbd_por_combustible"} & set(par):
        with rasterio.open(insumos / "fbfm40.tif") as src:
            codigos = src.read(1)
    if "sin_dosel" in par:
        # docs/crosswalk/DECISIONES-MODELO-V0 §1 (c): el dosel se ignora sólo en las clases
        # declaradas.
        sin = en_codigos(codigos, par["sin_dosel"])
        for nombre in ("cc.tif", "ch.tif", "cbh.tif", "cbd.tif"):
            _reescribir(insumos / nombre, lambda a: np.where(sin, 0, a))
    if "cbh_por_combustible" in par:
        # docs/crosswalk/DECISIONES-MODELO-V0 §2: CBH por tipo de bosque en vez de
        # CH × (0,2 + 0,3 CC).
        _reescribir(insumos / "cbh.tif",
                    lambda a: por_combustible(codigos, a, par["cbh_por_combustible"], 10))
    if "cbd_por_combustible" in par:
        # Ídem para la densidad de copa (p. ej. 0,16 kg/m³ medido en pino, Paritsis et al.
        # 2018); 0 apaga la copa de esa clase sin tocar el viento bajo dosel.
        _reescribir(insumos / "cbd.tif",
                    lambda a: por_combustible(codigos, a, par["cbd_por_combustible"], 100))
    if "adj" in par:
        _reescribir(insumos / "adj.tif", lambda a: np.full_like(a, par["adj"]))
    if "adj_grupos" in par:
        with rasterio.open(insumos / "fbfm40.tif") as src:
            codigos = src.read(1)
        factor = factor_por_grupo(codigos, par["adj_grupos"])
        _reescribir(insumos / "adj.tif", lambda a: a * factor)
    if "humedad_m1_delta" in par:
        _reescribir(insumos / "m1.tif",
                    lambda a: np.clip(a + par["humedad_m1_delta"], 1.0, 40.0))
    if "cbh_factor" in par:   # diagnóstico: el CBH derivado (canopy_builder) hace imposible la copa
        _reescribir(insumos / "cbh.tif",
                    lambda a: np.where(a > 0, np.maximum(np.round(a * par["cbh_factor"]), 1), a))
    if par.get("aspecto_mas_180"):
        # Diagnóstico del bug de convención de raster_aligner (asp cuesta arriba, cuando
        # ELMFIRE espera la dirección hacia la que mira la ladera): da vuelta el ráster.
        _reescribir(insumos / "asp.tif",
                    lambda a: np.where(a >= 0, (a.astype("int32") + 180) % 360, a))
    if par.get("viento_atlas"):
        if not {"atlas_u.tif", "atlas_v.tif"} <= set(archivos):
            raise FileNotFoundError(f"{caso.id} no empaquetó el atlas de viento: definir "
                                    "`viento_atlas` en el caso")
        _viento_del_atlas(archivos, insumos)
    if par.get("viento_diurno"):
        # AUDITORIA-FISICA loop M: el viento de cada hora con los flujos de ladera de WindNinja
        # (empaquetador `viento_diurno`), en lugar del GFS/ERA5 uniforme o del atlas.
        # "direccion" / "velocidad": sólo una de las dos; la otra sigue siendo la del GFS/ERA5.
        if not {"wn_u.tif", "wn_v.tif"} <= set(archivos):
            raise FileNotFoundError(f"{caso.id} no empaquetó el viento diurno (protocolo -d)")
        dem = insumos / "dem.tif"
        este = viento.a_la_grilla(almacen.abrir(archivos["wn_u.tif"]), dem, rellenar=True)
        norte = viento.a_la_grilla(almacen.abrir(archivos["wn_v.tif"]), dem, rellenar=True)
        with rasterio.open(insumos / "ws.tif") as src:
            if src.count != este.shape[0]:
                raise ValueError(f"el viento diurno trae {este.shape[0]} horas y la ventana "
                                 f"{src.count}")
        if par["viento_diurno"] != "direccion":
            _reescribir(insumos / "ws.tif", lambda a: np.hypot(este, norte))
        if par["viento_diurno"] != "velocidad":
            _reescribir(insumos / "wd.tif",
                        lambda a: (np.degrees(np.arctan2(-este, -norte)) + 360.0) % 360.0)
    if par.get("z0_desde_dosel"):
        with rasterio.open(insumos / "ch.tif") as src:
            ch_m = np.where(src.read(1) > 0, src.read(1) / 10.0, 0.0)   # 10 × m (LANDFIRE)
        factor = factor_rugosidad(ch_m)
        _reescribir(insumos / "ws.tif", lambda a: a * factor)
    if "rotacion_viento" in par:   # grados en sentido horario sobre la dirección de origen
        _reescribir(insumos / "wd.tif", lambda a: (a + par["rotacion_viento"]) % 360.0)
    if "factor_viento" in par:
        _reescribir(insumos / "ws.tif", lambda a: a * par["factor_viento"])
    if "humedad_muerta_delta" in par:
        # Mismo rango que weather_builder.derive_moisture.
        for nombre in ("m1.tif", "m10.tif", "m100.tif"):
            _reescribir(insumos / nombre,
                        lambda a: np.clip(a + par["humedad_muerta_delta"], 1.0, 40.0))

    # Al final, después de las perillas que vuelven a envolver el ángulo (rotacion_viento,
    # viento_atlas): ELMFIRE interpola wd por el camino corto (hallazgo 3 de la auditoría).
    _reescribir(insumos / "wd.tif", weather_builder.wd_for_elmfire)

    v = caso.ventanas[n]
    kwargs = HUMEDAD_VIVA_BASE | {k: val for k, val in receta.parametros.items()
                                  if k not in RASTERS_TRANSFORMADOS}
    namelist_writer.write_namelist(
        insumos.resolve(), salidas.resolve(), simulation_hours=v.horas,
        output_path=insumos / "elmfire.data", simulation_tstart_s=v.tstart_s, **kwargs,
    )
    texto = (insumos / "elmfire.data").read_text()
    texto = (texto.replace(str(insumos.resolve()), _contenedor(insumos))
                  .replace(str(salidas.resolve()), _contenedor(salidas)))
    (insumos / "elmfire.data").write_text(texto)
    nombres = [*ESTATICOS, "fbfm40.tif", "phi.tif", "elmfire.data"]
    return {nombre: almacen.guardar(insumos / nombre) for nombre in sorted(nombres)}


# La humedad viva de base del benchmark (la de base-001: LH 30 %, LW 110 %), fija acá y no
# heredada del default de la app: así una receta sin LW sigue siendo la misma receta aunque la
# app cambie su default (pasó a LW 100 % el 2026-09-30, la receta calibrada).
HUMEDAD_VIVA_BASE = {"lh_moisture_pct": 30.0, "lw_moisture_pct": 110.0}
# Perillas que no son kwargs del namelist sino transformaciones de un ráster de entrada.
RASTERS_TRANSFORMADOS = {"adj", "adj_grupos", "factor_viento", "humedad_muerta_delta",
                         "humedad_m1_delta", "modelo_humedad", "rotacion_viento",
                         "z0_desde_dosel", "aspecto_mas_180", "cbh_factor", "viento_atlas",
                         "reasignar_combustible", "dosel_coherente", "sin_dosel",
                         "cbh_por_combustible", "cbd_por_combustible",
                         "dosel_sin_perdida_previa", "combustible_perdida_reciente",
                         "combustible_por_edad_quema", "viento_diurno"}
# Códigos FBFM40 de cada grupo de Scott y Burgan (2005), para el ADJ por grupo.
GRUPOS_COMBUSTIBLE = {"GR": (101, 109), "GS": (121, 124), "SH": (141, 149),
                      "TU": (161, 165), "TL": (181, 189), "SB": (201, 204)}


def _viento_del_atlas(archivos: dict[str, str], insumos: Path) -> None:
    """Reemplaza ws/wd por el viento del GFS ajustado al terreno con el atlas de WindNinja.
    ws.tif trae el viento a 20 pies con el perfil logarítmico de weather_builder: se vuelve a
    10 m y el atlas hace su propio paso a 20 pies sobre el terreno."""
    from app.elmfire.builder.weather_builder import wind_height_factor

    dem = insumos / "dem.tif"
    u = viento.a_la_grilla(almacen.abrir(archivos["atlas_u.tif"]), dem)
    v = viento.a_la_grilla(almacen.abrir(archivos["atlas_v.tif"]), dem)
    with rasterio.open(insumos / "ws.tif") as a, rasterio.open(insumos / "wd.tif") as b:
        ws, wd = a.read(), b.read()
    velocidad, desde = viento.aplicar(ws / wind_height_factor(), wd, u, v)
    _reescribir(insumos / "ws.tif", lambda a: velocidad)
    _reescribir(insumos / "wd.tif", lambda a: desde)


def factor_rugosidad(ch_m: np.ndarray) -> np.ndarray:
    """Cuánto cambia el viento a 20 pies si la rugosidad sale del dosel y no del escalar.

    weather_builder baja el viento de 10 m a 20 pies con un perfil logarítmico y z0 = 0,22 m
    para todo el dominio (PENDING_PARAMETERS §1.4). Acá z0 = 0,13 × altura del dosel (regla
    clásica de Tanner y Pelton para vegetación), con piso de 0,03 m (pastizal), y se devuelve
    el cociente entre los dos perfiles, por celda.
    """
    from app.elmfire.builder.weather_builder import wind_height_factor

    z0 = np.clip(0.13 * ch_m, 0.03, 0.9 * 6.096)   # el log-perfil exige z0 < 20 pies
    arriba = np.log(6.096 / z0) / np.log(10.0 / z0)
    return (arriba / wind_height_factor()).astype("float32")


def no_forestal(codigos: np.ndarray) -> np.ndarray:
    """Celdas con combustible de pastizal, pastizal-arbustal o arbustal (GR, GS, SH): los
    grupos de Scott y Burgan sin dosel arbóreo."""
    return (codigos >= GRUPOS_COMBUSTIBLE["GR"][0]) & (codigos <= GRUPOS_COMBUSTIBLE["SH"][1])


def perdida_previa(lossyear: np.ndarray, anio_fuego: int, desde: int = 2001) -> np.ndarray:
    """Hansen GFC lossyear (0 = sin pérdida, n = 2000 + n) con pérdida entre `desde` y el año
    anterior al incendio."""
    return (lossyear >= max(desde - 2000, 1)) & (lossyear <= anio_fuego - 1 - 2000)


def en_codigos(codigos: np.ndarray, claves) -> np.ndarray:
    """Celdas cuyo código FBFM40 está en `claves`: códigos ("148") o grupos ("SH")."""
    m = np.zeros(codigos.shape, dtype=bool)
    for clave in claves:
        if clave in GRUPOS_COMBUSTIBLE:
            desde, hasta = GRUPOS_COMBUSTIBLE[clave]
            m |= (codigos >= desde) & (codigos <= hasta)
        else:
            m |= codigos == int(clave)
    return m


def por_combustible(codigos: np.ndarray, capa: np.ndarray, tabla: dict,
                    escala: float) -> np.ndarray:
    """Valor por código o grupo FBFM40 (en unidades físicas; `escala` es la codificación de
    ELMFIRE: 10 para cbh en m, 100 para cbd en kg/m³), sólo donde ya hay copa (capa > 0); un
    código pisa a su grupo. El resto queda como lo derivó canopy_builder."""
    salida = capa.copy()
    hay_copa = capa > 0
    for clave in sorted(tabla, key=lambda k: k in GRUPOS_COMBUSTIBLE, reverse=True):
        m = hay_copa & en_codigos(codigos, [clave])
        salida[m] = round(tabla[clave] * escala)
    return salida


def reasignar(codigos: np.ndarray, cambios: dict) -> np.ndarray:
    """Cambia cada código FBFM40 de `cambios` ({"188": 165}) por su reemplazo."""
    cambios = {int(k): int(v) for k, v in cambios.items()}
    return np.select([codigos == k for k in cambios], list(cambios.values()), codigos)


def factor_por_grupo(codigos: np.ndarray, grupos: dict[str, float]) -> np.ndarray:
    """ADJ por grupo de combustible (GR/GS/SH/TU/TL/SB); 1 donde no se declara."""
    factor = np.ones(codigos.shape, dtype="float32")
    for grupo, valor in grupos.items():
        desde, hasta = GRUPOS_COMBUSTIBLE[grupo]
        factor[(codigos >= desde) & (codigos <= hasta)] = valor
    return factor


def _humedad_con_criterio(modelo: str, archivos: dict[str, str], insumos: Path,
                          inicio, lon: float) -> None:
    """Reemplaza m1 (y con `altura` también m10/m100) desde el clima crudo del GFS del
    paquete: T y HR a 0,25° y el terreno del modelo, llevados a la grilla de la corrida."""
    from app.elmfire.builder.weather_builder import _nelson_emc, _read_aligned

    dem = insumos / "dem.tif"
    t_k = _read_aligned(almacen.abrir(archivos["t2m_gfs.tif"]), dem)
    hr = np.clip(_read_aligned(almacen.abrir(archivos["rh_gfs.tif"]), dem), 0, 100)
    with rasterio.open(dem) as src:
        altura = src.read(1).astype("float32")
    desnivel = altura - _read_aligned(almacen.abrir(archivos["orog_gfs.tif"]), dem)[0]
    if modelo == "altura":
        t_k, hr = humedad.a_la_altura(t_k, hr, desnivel)
        emc = _nelson_emc((t_k - 273.15) * 9 / 5 + 32, hr)
        for nombre, extra in (("m1.tif", 0.0), ("m10.tif", 2.0), ("m100.tif", 5.0)):
            _reescribir(insumos / nombre, lambda a, e=extra: np.clip(emc + e, 1.0, 40.0))
        return
    with rasterio.open(insumos / "slp.tif") as s1, rasterio.open(insumos / "asp.tif") as s2, \
            rasterio.open(insumos / "cc.tif") as s3:
        pendiente, orientacion, cc = (s.read(1).astype("float32") for s in (s1, s2, s3))
    m1 = humedad.fosberg(t_k, hr, humedad.tiempos_de_bandas(inicio, t_k.shape[0]), lon,
                         pendiente, orientacion, cc, desnivel)
    _reescribir(insumos / "m1.tif", lambda a: np.clip(m1, 1.0, 40.0))


def _reescribir(ruta: Path, transformar) -> None:
    """Aplica `transformar` a todas las bandas. El archivo es un hardlink de sólo lectura al
    almacén: se desvincula y se escribe uno nuevo, nunca se pisa el objeto."""
    with rasterio.open(ruta) as src:
        perfil, datos = src.profile, src.read()
    ruta.unlink()
    predictor = 3 if perfil["dtype"].startswith("float") else 2
    comprimir = {"compress": "deflate", "predictor": predictor}
    with rasterio.open(ruta, "w", **(perfil | comprimir)) as dst:
        dst.write(transformar(datos).astype(perfil["dtype"]))


def _ejecutar(insumos_sha: dict[str, str], horas: int, insumos: Path, salidas: Path,
              ) -> dict[str, str]:
    """Materializa exactamente esos insumos, corre ELMFIRE y guarda todo lo que escribió."""
    if salidas.exists():
        for viejo in salidas.iterdir():
            viejo.unlink()
    salidas.mkdir(parents=True, exist_ok=True)
    almacen.materializar(insumos_sha, insumos)
    asyncio.run(ELMFIRERunnerClient().run_simulation(SimulationRequest(
        elmfire_data_path=_contenedor(insumos / "elmfire.data"),
        inputs_dir=_contenedor(insumos), outputs_dir=_contenedor(salidas),
        simulation_hours=horas,
    )))
    return almacen.guardar_dir(salidas)


def _escribir_manifiesto(caso: Caso, receta: Receta, ventanas: list[dict]) -> dict:
    manifiesto = {
        "caso": caso.id, "caso_sha": caso.sha(),
        "receta": receta.id, "receta_sha": receta.sha(), "padre": receta.padre,
        "motivo": receta.motivo, "factores": receta.factores(caso),
        "elmfire": ELMFIRE_VERSION, "git": ventanas[-1]["git"],
        "ventanas": ventanas,
    }
    destino = ruta_iteracion(caso.id, receta.id)
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "manifiesto.json").write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False))
    return manifiesto


def correr(caso: Caso, receta: Receta) -> dict:
    """Corre las ventanas que falten. Reanudable: una ventana ya registrada con el mismo
    caso no se repite, porque la corrida completa lleva horas."""
    receta.validar(caso)
    exigir_receta_intacta(receta, caso)
    previo = cargar_manifiesto(caso.id, receta.id)
    hechas = previo["ventanas"] if previo and previo["caso_sha"] == caso.sha() else []
    semilla_en_metros = _leer(caso.paquete()["ventanas"][0]["phi.tif"]).max() > 1
    if len(hechas) < len(caso.ventanas) and semilla_en_metros:
        # phi en metros: un paquete anterior a la auditoría física (hallazgo 2). Correrlo
        # ahora mezclaría la semilla vieja con las ventanas encadenadas nuevas (±1).
        raise ValueError(f"{caso.id} se empaquetó antes de la auditoría física: "
                         "re-empaquetarlo como protocolo nuevo (-v4)")
    if receta.semilla == "prediccion":
        dems = {caso.paquete()["comunes"].get("dem.tif")}
        dems |= {v.get("dem.tif") for v in caso.paquete()["ventanas"] if "dem.tif" in v}
        if len(dems - {None}) > 1:
            raise ValueError(f"{caso.id}: una cadena `prediccion` exige la misma grilla en "
                             "todas las ventanas")

    for n, v in enumerate(caso.ventanas):
        if n < len(hechas):
            continue
        insumos, salidas = _rutas(caso, receta, n)
        previa = hechas[n - 1] if n else None
        estado = git_estado()
        print(f"  {caso.id} · {receta.id} · ventana {n} ({v.inicio:%Y-%m-%d %H:%M}, "
              f"{v.horas} h): corriendo …", flush=True)
        inicio = datetime.now(UTC)
        insumos_sha = _preparar(caso, receta, n, previa, insumos, salidas)
        salidas_sha = _ejecutar(insumos_sha, v.horas, insumos, salidas)
        hechas.append({
            "n": n, "t0": v.t0.isoformat(), "inicio": v.inicio.isoformat(), "horas": v.horas,
            "tstart_s": v.tstart_s,
            "semilla_desde": "caso" if n == 0 else
            ("ventana_anterior" if receta.semilla == "prediccion" else "firms"),
            "insumos": insumos_sha,
            "namelist_sha": hashlib.sha256(_normalizar_namelist(
                (insumos / "elmfire.data").read_text(), insumos, salidas).encode()).hexdigest(),
            "salidas": salidas_sha,
            "git": estado,
            "corrida": {"inicio": inicio.isoformat(), "minutos":
                        round((datetime.now(UTC) - inicio).total_seconds() / 60, 1)},
        })
        _escribir_manifiesto(caso, receta, hechas)   # tras cada ventana: un corte no pierde nada
    return _escribir_manifiesto(caso, receta, hechas)


def verificar(caso: Caso, receta: Receta) -> list[dict]:
    """Re-ejecuta cada ventana desde los insumos registrados y compara el TOA.

    Es la prueba de que el estado es inmutable y el modelo determinista: si un hash no
    coincide, el benchmark no sirve para comparar versiones.
    """
    manifiesto = cargar_manifiesto(caso.id, receta.id)
    if manifiesto is None:
        raise FileNotFoundError(f"{caso.id}/{receta.id} no corrió todavía")
    resultado = []
    for v in manifiesto["ventanas"]:
        insumos, salidas = _rutas(caso, receta, v["n"])
        nuevas = _ejecutar(v["insumos"], v["horas"], insumos, salidas)
        resultado.append({"n": v["n"], "toa_igual": _toa(nuevas) == _toa(v["salidas"])})
    return resultado


# ── puntuación ────────────────────────────────────────────────────────────────

def _opcional(archivos: dict[str, str], nombre: str) -> np.ndarray | None:
    return _leer(archivos[nombre]) if nombre in archivos else None


def puntuar(caso: Caso, receta: Receta) -> dict:
    """Métricas por ventana y la principal de la iteración, más las vistas del dashboard.

    - Contra FIRMS, el **incremento** de cada ventana: lo nuevo que predijo contra las
      detecciones nuevas, excluyendo lo que el modelo ya daba por quemado al empezar.
      Recall fiable, precisión como cota (un hueco del satélite no es un falso positivo).
    - Contra la cicatriz, lo **acumulado**: con semilla `prediccion`, todo lo que el
      modelo quemó desde la semilla del caso. Con `observacion` sólo el anillo de la
      ventana, porque la semilla observada coincide con la cicatriz por construcción.
    """
    manifiesto = cargar_manifiesto(caso.id, receta.id)
    if manifiesto is None:
        raise FileNotFoundError(f"{caso.id}/{receta.id} no corrió todavía")
    paquete = caso.paquete()
    vistas = VISTAS / caso.id / receta.id
    vistas.mkdir(parents=True, exist_ok=True)
    semilla_caso = None
    por_ventana, lineas = [], []
    for v, ventana in zip(caso.ventanas, manifiesto["ventanas"]):
        n = ventana["n"]
        archivos = paquete["comunes"] | paquete["ventanas"][n]
        grilla = p.Grilla(almacen.abrir(archivos["dem.tif"]))
        semilla = _leer(ventana["insumos"]["phi.tif"]) < 0
        if semilla_caso is None:
            semilla_caso = semilla
        toa = _leer(_toa(ventana["salidas"]))
        horas = p.horas_relativas(toa, v.tstart_s)
        quemado = semilla | (toa > 0)
        incremento = quemado & ~semilla
        fila = {"n": n, "inicio": v.inicio.isoformat(), "horas": v.horas,
                "semilla_ha": float(semilla.sum() * grilla.celda_ha),
                "predicho_ha": float(incremento.sum() * grilla.celda_ha)}

        firms = _opcional(archivos, "ref_firms.tif")
        if firms is not None:
            firms = firms.astype(bool)
            fila["firms"] = {"incremento": p.metricas(incremento, firms, grilla.celda_ha,
                                                      excluir=semilla)}
            alcance = _opcional(archivos, "alcance.tif")
            if alcance is not None:
                fila["firms"]["incremento_cercano"] = p.metricas(
                    incremento, firms, grilla.celda_ha, excluir=semilla | ~alcance.astype(bool))
            det = _opcional(archivos, "ref_firms_horas.tif")
            if det is not None:
                fila["llegada"] = p.error_llegada(horas, np.where(det >= 0, det, np.nan))

        cicatriz = _opcional(archivos, "cicatriz.tif")
        ya = semilla_caso if receta.semilla == "prediccion" else semilla
        if cicatriz is not None:
            excluido = _leer(archivos["excluido.tif"]).astype(bool)
            pred, ref = quemado & ~ya, cicatriz.astype(bool) & ~ya
            fila["cicatriz"] = {"acumulado": p.metricas(pred, ref, grilla.celda_ha, excluido)}
            bandas = _opcional(archivos, "bandas_pct.tif")   # un bit por banda
            if bandas is not None:
                nombres = paquete["origen"].get("bandas_pct", [])
                fila["cicatriz"]["bandas"] = {
                    nombre: p.metricas(pred, ref, grilla.celda_ha,
                                       excluido | ((bandas & (1 << bit)) == 0))
                    for bit, nombre in enumerate(nombres)}
            _confusion(pred, ref, ya, excluido, grilla, vistas / f"v{n}" / "confusion.tif")
        elif firms is not None:
            _confusion(incremento, firms, semilla, np.zeros_like(semilla), grilla,
                       vistas / f"v{n}" / "confusion.tif")
        por_ventana.append(fila)
        _llegada(np.where(semilla, np.nan, horas), grilla, vistas / f"v{n}" / "llegada.tif")
        lineas.append(((v.inicio - caso.ventanas[0].inicio).total_seconds() / 3600,
                       horas, semilla, grilla))

    metricas = {"caso": caso.id, "receta": receta.id, "factores": manifiesto["factores"],
                "ventanas": por_ventana, "agregado_firms": _agregar(por_ventana)}
    metricas["principal"] = _principal(por_ventana, receta.semilla, metricas["agregado_firms"])
    cosido = _linea_de_tiempo(lineas, vistas / "linea_tiempo.tif")
    ultimos = paquete["comunes"] | paquete["ventanas"][-1]
    if (cosido is not None and semilla_caso is not None and receta.semilla == "prediccion"
            and "cicatriz.tif" in ultimos
            and metricas["principal"]):
        excluido = _leer(ultimos["excluido.tif"]).astype(bool) | semilla_caso
        metricas["principal"]["area_igualada"] = p.area_igualada(
            np.where(semilla_caso, np.nan, cosido), _leer(ultimos["cicatriz.tif"]).astype(bool),
            lineas[0][3].celda_ha, excluido)
    destino = ruta_iteracion(caso.id, receta.id) / "metricas.json"
    destino.write_text(json.dumps(metricas, indent=2, ensure_ascii=False))
    return metricas


# Lo que la principal copia de la confusión al horizonte (o del agregado FIRMS).
METRICAS_PRINCIPALES = ("dice", "iou", "precision", "recall", "tp", "fp", "fn")


def principal_completa(metricas: dict) -> dict | None:
    """La principal con IoU, precisión, recall y tp/fp/fn. Las iteraciones puntuadas antes de
    que la principal los copiara los tienen igual en su ventana (o en el agregado FIRMS)."""
    pr = metricas.get("principal")
    if not pr or all(k in pr for k in METRICAS_PRINCIPALES):
        return pr
    if pr["referencia"] == "cicatriz":
        m = metricas["ventanas"][pr["ventana"]]["cicatriz"]["acumulado"]
    else:
        m = metricas["agregado_firms"]["incremento"]
    return {**{k: m.get(k) for k in METRICAS_PRINCIPALES}, **pr}


def _principal(filas: list[dict], semilla: str, agregado: dict | None) -> dict | None:
    """Dice de la última ventana contra la cicatriz, si la cadena corre sola.

    Con semilla `observacion` la cicatriz no sirve de referencia principal: la semilla FIRMS
    de la última ventana ya la cubre casi entera y lo que queda para puntuar es un anillo
    angosto (§12.1). Ahí manda el agregado contra las detecciones nuevas de cada ventana.
    Por eso la principal sólo es comparable entre recetas con la misma política de semilla.
    """
    ultima = filas[-1]
    if semilla == "prediccion" and "cicatriz" in ultima:
        m = ultima["cicatriz"]["acumulado"]
        return {"referencia": "cicatriz", "ventana": ultima["n"],
                **{k: m[k] for k in METRICAS_PRINCIPALES},
                "sesgo_area": m["sesgo_area"], "alarma_sesgo": m["alarma_sesgo"]}
    if agregado and "incremento" in agregado:
        m = agregado["incremento"]
        return {"referencia": "firms", "ventana": None,
                **{k: m[k] for k in METRICAS_PRINCIPALES},
                "sesgo_area": None, "alarma_sesgo": False}
    return None


def _agregar(filas: list[dict]) -> dict | None:
    """Suma de las confusiones por ventana contra FIRMS (el agregado del harness A)."""
    conjunto = [f["firms"] for f in filas if "firms" in f]
    if not conjunto:
        return None
    salida = {}
    for clave in ("incremento", "incremento_cercano"):
        ms = [f[clave] for f in conjunto if clave in f]
        if not ms:
            continue
        tp, fp, fn = (sum(m[k] for m in ms) for k in ("tp", "fp", "fn"))
        salida[clave] = {
            "tp": tp, "fp": fp, "fn": fn, "tp_ha": sum(m["tp_ha"] for m in ms),
            "recall": tp / (tp + fn) if tp + fn else None,
            "precision": tp / (tp + fp) if tp + fp else None,
            "iou": tp / (tp + fp + fn) if tp + fp + fn else None,
            "dice": 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None,
        }
    return salida


def _confusion(pred, ref, ya, excluido, grilla: p.Grilla, destino: Path) -> None:
    codigos = np.full(pred.shape, NADA, dtype="uint8")
    codigos[pred & ref] = ACIERTO
    codigos[pred & ~ref] = PREDICHO_SIN_OBS
    codigos[~pred & ref] = OBS_SIN_PREDECIR
    codigos[excluido] = EXCLUIDO
    codigos[ya] = SEMILLA
    destino.parent.mkdir(parents=True, exist_ok=True)
    perfil = grilla.perfil | {"dtype": "uint8", "count": 1, "nodata": None, "compress": "deflate"}
    with rasterio.open(destino, "w", **perfil) as dst:
        dst.write(codigos, 1)


def _llegada(horas: np.ndarray, grilla: p.Grilla, destino: Path) -> None:
    """Segundos de llegada en el formato del TOA de ELMFIRE (> 0 = quemado), para que el
    dashboard lo polígonice con el mismo código que el mapa. La semilla queda afuera: el
    visor la dibuja aparte, como el perímetro de ignición."""
    segundos = np.where(np.isnan(horas), -1.0, horas * 3600.0)
    perfil = grilla.perfil | {"dtype": "float32", "count": 1, "nodata": -1.0, "compress": "deflate"}
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".tif", dir=destino.parent, delete=False) as tmp:
        with rasterio.open(tmp.name, "w", **perfil) as dst:
            dst.write(segundos.astype("float32"), 1)
    Path(tmp.name).replace(destino)


def _linea_de_tiempo(lineas: list, destino: Path) -> np.ndarray | None:
    """Toda la cadena en una sola línea de tiempo, en segundos desde el inicio del caso.
    Sólo si todas las ventanas comparten grilla: con recortes distintos (el harness A) el
    visor dibuja ventana por ventana."""
    grillas = {(g.transform, g.shape) for *_, g in lineas}
    if len(grillas) != 1:
        destino.unlink(missing_ok=True)
        return None
    cosido = p.coser([(desfase, horas, semilla) for desfase, horas, semilla, _ in lineas])
    _llegada(cosido, lineas[0][3], destino)
    return cosido
