"""Viento de superficie consistente con el terreno: un atlas de WindNinja por caso.

El GFS de 0,25° no resuelve los valles: el frente observado avanza 40–100° más al sur que el
empuje del GFS en cinco de seis incendios (RESULTADOS-CSS-BAP, H4). WindNinja (USFS Missoula
Fire Sciences Lab, dominio público) ajusta un campo de viento inicial al terreno conservando
la masa. Para ese solver la salida es lineal en la velocidad inicial, así que alcanza con
correrlo una vez por dirección a velocidad unitaria (el "atlas", la técnica de FSPro/FlamMap).
En la corrida, cada celda y cada hora toman la velocidad y la dirección del GFS e interpolan
el atlas entre las dos direcciones vecinas.

- `atlas(dem, …)` corre WindNinja en Docker (`tools/windninja`) y devuelve, por dirección,
  las componentes (u, v) del viento a 20 pies por unidad de viento a 10 m.
- `aplicar(velocidad_10m, direccion, u, v)` es la interpolación, sin I/O.
"""
import subprocess
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

IMAGEN = "windninja-cli:3.12.2"
DIRECCIONES = 16
VELOCIDAD_MPH = 10.0   # la del cálculo; se divide para volver a "por unidad"


def aplicar(velocidad_10m: np.ndarray, direccion: np.ndarray,
            u: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Velocidad (misma unidad que la entrada) y dirección de origen (grados) a 20 pies.

    `velocidad_10m`, `direccion`: (bandas, filas, cols), el viento del GFS a 10 m y de dónde
    viene. `u`, `v`: (direcciones, filas, cols), el atlas: componentes hacia el este y el norte
    de la salida por unidad de entrada, para entradas desde 0°, 360/n°, …
    """
    n = u.shape[0]
    paso = 360.0 / n
    x = (direccion % 360.0) / paso
    k0 = np.floor(x).astype(int) % n
    k1 = (k0 + 1) % n
    w = (x - np.floor(x)).astype("float32")
    filas, cols = np.indices(u.shape[1:])
    ue = (1 - w) * u[k0, filas, cols] + w * u[k1, filas, cols]
    ve = (1 - w) * v[k0, filas, cols] + w * v[k1, filas, cols]
    velocidad = velocidad_10m * np.hypot(ue, ve)
    desde = (np.degrees(np.arctan2(-ue, -ve)) + 360.0) % 360.0
    return velocidad.astype("float32"), desde.astype("float32")


def atlas(dem: Path, trabajo: Path, resolucion_m: float = 90.0, vegetacion: str = "brush",
          direcciones: int = DIRECCIONES) -> tuple[np.ndarray, np.ndarray, dict]:
    """Corre WindNinja una vez por dirección sobre `dem` y devuelve (u, v, perfil) en su malla.

    `trabajo` tiene que estar bajo un directorio que Docker pueda montar (el repo lo está).
    """
    trabajo.mkdir(parents=True, exist_ok=True)
    (trabajo / "dem.tif").write_bytes(Path(dem).read_bytes())
    u, v, perfil = [], [], None
    for k in range(direcciones):
        d = k * 360.0 / direcciones
        salida = trabajo / f"d{k:02d}"
        salida.mkdir(exist_ok=True)
        (salida / "wn.cfg").write_text(f"""num_threads = 2
elevation_file = /data/dem.tif
initialization_method = domainAverageInitialization
input_speed = {VELOCIDAD_MPH}
input_speed_units = mph
input_direction = {d}
input_wind_height = 10.0
units_input_wind_height = m
output_wind_height = 20.0
units_output_wind_height = ft
vegetation = {vegetacion}
mesh_resolution = {resolucion_m}
units_mesh_resolution = m
output_path = /data/d{k:02d}
write_ascii_output = true
ascii_out_resolution = {resolucion_m}
units_ascii_out_resolution = m
write_goog_output = false
write_shapefile_output = false
write_farsite_atm = false
""")
        r = subprocess.run(["docker", "run", "--rm", "-v", f"{trabajo.resolve()}:/data", IMAGEN,
                            f"/data/d{k:02d}/wn.cfg"], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"WindNinja falló en {d}°: {r.stderr[-2000:]}")
        vel = next(salida.glob("*_vel.asc"))
        ang = next(salida.glob("*_ang.asc"))
        with rasterio.open(vel) as a, rasterio.open(ang) as b, rasterio.open(dem) as ref:
            rapidez, desde = a.read(1) / VELOCIDAD_MPH, b.read(1)
            perfil = perfil or (a.profile | {"crs": ref.crs})
        u.append(-rapidez * np.sin(np.radians(desde)))
        v.append(-rapidez * np.cos(np.radians(desde)))
    assert perfil is not None   # direcciones >= 1
    return np.stack(u).astype("float32"), np.stack(v).astype("float32"), perfil


def guardar(u: np.ndarray, v: np.ndarray, perfil: dict, destino: Path) -> tuple[Path, Path]:
    """Dos GeoTIFF de `direcciones` bandas cada uno, en la malla de WindNinja."""
    rutas = []
    for nombre, datos in (("atlas_u.tif", u), ("atlas_v.tif", v)):
        ruta = destino / nombre
        with rasterio.open(ruta, "w", driver="GTiff", height=datos.shape[1],
                           width=datos.shape[2], count=datos.shape[0], dtype="float32",
                           crs=perfil["crs"], transform=perfil["transform"]) as dst:
            dst.write(datos)
        rutas.append(ruta)
    return rutas[0], rutas[1]


def a_la_grilla(ruta: Path, referencia: Path) -> np.ndarray:
    """Un atlas guardado, llevado a la grilla de la corrida (bilineal)."""
    with rasterio.open(referencia) as ref:
        forma, transform, crs = (ref.height, ref.width), ref.transform, ref.crs
    with rasterio.open(ruta) as src:
        salida = np.empty((src.count, *forma), dtype="float32")
        for b in range(src.count):
            reproject(rasterio.band(src, b + 1), salida[b], src_transform=src.transform,
                      src_crs=src.crs, dst_transform=transform, dst_crs=crs,
                      resampling=Resampling.bilinear)
    return salida
