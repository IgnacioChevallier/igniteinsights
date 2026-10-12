"""Prueba de la premisa de lo ya quemado (docs/resultados/LO-YA-QUEMADO-PROPUESTA.md §6, punto 3).

¿Las cicatrices jóvenes frenan al fuego y las de 6-15 años lo atraen? Sólo con MODIS MCD64A1, por
temporada de incendios (julio-junio: un fuego de diciembre a enero es una sola temporada), en la
grilla nativa (~463 m) de la caja extendida del benchmark. Sin ELMFIRE y sin las cicatrices de
referencia del benchmark: los incendios de prueba se sacan con su máscara dNBR dilatada una celda.

Para cada temporada T y tramo de edad k, con F = quemado en T y P_k = celdas cuya última quema
anterior tiene edad en k:

- reincendio relativo = Σ_T |F ∩ P_k| / Σ_T |P_k| · |F| / |celdas|: lo que ardió de la cicatriz
  contra lo esperado con la tasa de esa temporada. > 1, la cicatriz arde más que el resto; < 1,
  menos;
- borde = |anillo ∩ P_k| / (|anillo ∩ P_k| + |F ∩ P_k|), con el anillo de una celda alrededor de
  F, contra el mismo cociente con todas las celdas: más alto, el fuego llega y no entra.

Se suma sobre las temporadas 2006-2026, y aparte sin 2026 (la temporada de Patriada, que pesa
mucho y es un caso de calibración). Hipótesis fijadas antes: 1-2 años, reincendio < 1;
6-15 años, reincendio > 1.

Necesita `earthengine-api`: se corre con el venv de ../mask-dataset-gen.

    ../mask-dataset-gen/.venv/bin/python scripts/premisa_lo_ya_quemado.py
"""
import json
import urllib.request
from pathlib import Path

import ee
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

PROYECTO = "ee-nachochevallier"
AOI = (-72.18, -43.24, -71.04, -41.86)   # la de scripts/exportar_mcd64a1.py
TEMPORADAS = range(2002, 2027)           # temporada T = julio de T-1 a junio de T
PILA = Path("data/raw/mcd64a1/mcd64a1_temporadas_aoi.tif")
DATASET = Path("../mask-dataset-gen")
RUN_VIGENTE = {"los-alerces-2023": "event-filter-002"}
TRAMOS = [(1, 2, "1-2"), (3, 5, "3-5"), (6, 15, "6-15")]


def bajar_pila() -> None:
    ee.Initialize(project=PROYECTO)
    coleccion = ee.ImageCollection("MODIS/061/MCD64A1")
    proyeccion = coleccion.first().projection()
    bandas = []
    for t in TEMPORADAS:
        quemado = (coleccion.filterDate(f"{t - 1}-07-01", f"{t}-07-01")
                   .map(lambda img: img.select("BurnDate").gt(0)).max().unmask(0))
        bandas.append(quemado.toByte().rename(f"t{t}"))
    imagen = ee.Image.cat(bandas).reproject(proyeccion)
    url = imagen.getDownloadURL({"region": ee.Geometry.Rectangle(list(AOI)),
                                 "crs": proyeccion.crs().getInfo(),
                                 "crs_transform": proyeccion.getInfo()["transform"],
                                 "format": "GEO_TIFF"})
    PILA.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, PILA)


def mascaras_prueba(perfil) -> dict[int, np.ndarray]:
    """Huella de cada incendio de prueba en la grilla MODIS, por temporada, dilatada una celda."""
    prueba = json.loads(Path("benchmarks/particion.json").read_text())["prueba"]
    eventos = {c.split("/")[0] for casos in prueba.values() for c in casos}
    huellas: dict[int, np.ndarray] = {}
    for nombre in sorted(eventos):
        evento = json.loads((DATASET / "config" / "incendios" / f"{nombre}.json").read_text())
        anio, mes = int(evento["fire_start_date"][:4]), int(evento["fire_start_date"][5:7])
        temporada = anio + 1 if mes >= 7 else anio
        run = DATASET / "dataset" / nombre / "runs" / RUN_VIGENTE.get(nombre, "event-filter-001")
        huella = huellas.setdefault(temporada, np.zeros((perfil["height"], perfil["width"]), bool))
        for tile in sorted((run / "mascaras").glob("*.tif")):
            with rasterio.open(tile) as src:
                destino = np.zeros(huella.shape, np.uint8)
                reproject(src.read(1), destino, src_transform=src.transform, src_crs=src.crs,
                          dst_transform=perfil["transform"], dst_crs=perfil["crs"],
                          resampling=Resampling.max)
            huella |= destino > 0
    return {t: dilatar(h) for t, h in huellas.items()}


def dilatar(m: np.ndarray) -> np.ndarray:
    d = m.copy()
    d[1:] |= m[:-1]
    d[:-1] |= m[1:]
    d[:, 1:] |= m[:, :-1]
    d[:, :-1] |= m[:, 1:]
    return d


def resumir(pila, prueba, hasta: int) -> None:
    ultima = np.zeros(pila.shape[1:], np.int16)   # temporada de la última quema (0 = ninguna)
    obs = {et: 0 for _, _, et in TRAMOS}
    esp = {et: 0.0 for _, _, et in TRAMOS}
    borde = {et: [0, 0] for _, _, et in TRAMOS}
    base = [0, 0]
    for i, t in enumerate(TEMPORADAS):
        fuego = pila[i] & ~prueba[t] if t in prueba else pila[i]
        if 2006 <= t <= hasta and fuego.any():
            anillo = dilatar(fuego) & ~fuego
            base[0] += int(anillo.sum())
            base[1] += int(fuego.sum())
            edad = np.where(ultima > 0, t - ultima, 0)
            for desde, h, et in TRAMOS:
                cicatriz = (edad >= desde) & (edad <= h)
                obs[et] += int((fuego & cicatriz).sum())
                esp[et] += float(cicatriz.sum() * fuego.mean())
                borde[et][0] += int((anillo & cicatriz).sum())
                borde[et][1] += int((fuego & cicatriz).sum())
        ultima[pila[i]] = t   # la prueba también quema: su cicatriz cuenta para después
    print(f"temporadas 2006-{hasta}: {base[1]} celdas quemadas (~{base[1] * 21.47:.0f} ha), "
          f"borde de base {base[0] / (base[0] + base[1]):.2f}")
    for _, _, et in TRAMOS:
        tocado = sum(borde[et])
        en_borde = borde[et][0] / tocado if tocado else float("nan")
        print(f"  edad {et:>4}: reincendio relativo {obs[et] / esp[et]:.2f} ({obs[et]} celdas, "
              f"{esp[et]:.1f} esperadas), borde {en_borde:.2f}")


if __name__ == "__main__":
    if not PILA.exists():
        bajar_pila()
    with rasterio.open(PILA) as src:
        pila = src.read().astype(bool)
        perfil = src.profile
    prueba = mascaras_prueba(perfil)
    resumir(pila, prueba, TEMPORADAS[-1])
    resumir(pila, prueba, TEMPORADAS[-1] - 1)
