"""Nota AC: ¿la agrupación de la app operativa de `main` elige las mismas detecciones que la
semilla conexa del benchmark (`pronostico-v7`)? Sin ELMFIRE.

    PYTHONPATH=<este checkout> uv run python <este checkout>/scripts/diagnostico_semilla_app.py

desde un checkout con `data/` (lee los paquetes). `agrupar` sale del código de `main` en
`COMMIT_MAIN`, no de una copia. Escribe AC-semilla-app.json en
benchmarks/diagnosticos/e2e/datos/.
"""
import ast
import subprocess
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from pyproj import Transformer

from app.elmfire.builder import perimeter_reconstruction as pr
from app.validation import almacen
from app.validation import definiciones as d
from app.validation import puntuacion as p

COMMIT_MAIN = "81637c3"
CASOS = ["cholila-2015", "los-alerces-2016", "los-alerces-2023", "epuyen-2025",
         "los-alerces-2024", "puerto-patriada-2026"]
SALTO_M, HISTORIA = 3000.0, timedelta(days=7)
DATOS = Path(__file__).resolve().parents[1] / "benchmarks/diagnosticos/e2e/datos"
SALIDA = DATOS / "AC-semilla-app.json"


def agrupar_de_main(crs: str):
    """`agrupar` tal como está en main, con sus constantes, y la proyección de main."""
    fuente = subprocess.run(["git", "show", f"{COMMIT_MAIN}:app/operativo/servicio.py"],
                            check=True, capture_output=True, text=True).stdout
    arbol = ast.parse(fuente)
    ns = {"Deteccion": object, "Transformer": Transformer,
          "_a_utm": lambda: Transformer.from_crs("EPSG:4326", crs, always_xy=True)}
    for nodo in arbol.body:
        destino = getattr(nodo, "targets", [None])[0]
        nombre = getattr(nodo, "name", None) or getattr(destino, "id", None)
        if nombre in ("RADIO_GRUPO_M", "VENTANA_GRUPO_H", "agrupar"):
            exec(ast.get_source_segment(fuente, nodo), ns)
    assert ns["RADIO_GRUPO_M"] == SALTO_M
    return ns["agrupar"]


def elegir_grupo(grupos: list[set[int]], b: set[int]) -> set[int]:
    """El grupo de la app que el usuario elegiría: el de más detecciones en común con B."""
    return max(grupos, key=lambda g: len(g & b), default=set())


def jaccard(a, b) -> float:
    if a.is_empty and b.is_empty:
        return 1.0
    return a.intersection(b).area / a.union(b).area


def reinicios(caso_id: str, agrupar) -> list[dict]:
    caso = d.Caso.cargar(f"{caso_id}/pronostico-v7")
    paq = caso.paquete()
    grilla = p.Grilla(almacen.abrir(paq["comunes"]["dem.tif"]))
    tr = Transformer.from_crs("EPSG:4326", str(grilla.crs), always_xy=True)
    df = pd.read_csv(almacen.abrir(paq["comunes"]["firms.csv"]), parse_dates=["acq_datetime"])
    xy = list(zip(*tr.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())))
    s = caso.datos["semilla_inicial"]
    ancla = [tr.transform(s["lon"], s["lat"])]
    filas = []
    for n, v in enumerate(caso.ventanas):
        if n == 0:
            continue
        hasta = (df["acq_datetime"] <= v.inicio).to_numpy()
        idx = [i for i in range(len(df)) if hasta[i]]
        keep = pr.connected_to_anchors([xy[i] for i in idx], ancla, SALTO_M)
        b = {i for i, k in zip(idx, keep) if k}
        app = [i for i in idx if df["acq_datetime"].iloc[i] > v.inicio - HISTORIA]
        dets = [SimpleNamespace(i=i, t=df["acq_datetime"].iloc[i].to_pydatetime(),
                                lon=df["longitude"].iloc[i], lat=df["latitude"].iloc[i])
                for i in app]
        grupos = [{x.i for x in g} for g in agrupar(dets)]
        a = elegir_grupo(grupos, b)
        pa = pr.reconstruct_burn_polygon([xy[i] for i in sorted(a)]) if a else None
        pb = pr.reconstruct_burn_polygon([xy[i] for i in sorted(b)]) if b else None
        filas.append({"caso": caso_id, "n": n, "inicio": v.inicio, "detecciones": len(idx),
                      "b": len(b), "a": len(a), "solo_a": len(a - b), "solo_b": len(b - a),
                      "ha_b": pb.area / 1e4 if pb else 0.0, "ha_a": pa.area / 1e4 if pa else 0.0,
                      "jaccard": jaccard(pa, pb) if pa and pb else float(pa is pb)})
    return filas


def main() -> None:
    agrupar = agrupar_de_main("EPSG:32719")   # settings.aoi_crs_processing de main
    df = pd.DataFrame([f for c in CASOS for f in reinicios(c, agrupar)])
    SALIDA.write_text(df.round(4).to_json(orient="records", date_format="iso", indent=1))
    print(df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"\nreinicios: {len(df)}; A = B en {(df.solo_a + df.solo_b == 0).sum()}; "
          f"Jaccard mínimo {df.jaccard.min():.4f}")


if __name__ == "__main__":
    main()
