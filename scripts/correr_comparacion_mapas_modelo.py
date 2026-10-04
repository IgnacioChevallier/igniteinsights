"""Ejecuta en serie la comparación de mapas de un modelo promovido.

ELMFIRE usa MPI y el runner local no admite varias simulaciones simultáneas de forma estable.
Este comando recorre un caso por vez y es reanudable a nivel de ventana.

    uv run python scripts/correr_comparacion_mapas_modelo.py modelo-v0
"""
import argparse
import os

# El .env usa el nombre del servicio dentro de Docker; este comando corre desde el host.
os.environ.setdefault("ELMFIRE_RUNNER_URL", "http://localhost:8001")

from app.validation import cadena
from app.validation import definiciones as d

RECETAS = ("lw-100-001", "lw-100-worldcover-001", "lw-100-mapbiomas-001")
CASOS_COMPARACION = {
    "los-alerces-2023/calibracion-v6-h54":
        "los-alerces-2023/calibracion-v6m2-h54",
}


def _caso_mapas(caso_id: str) -> str:
    if caso_id in CASOS_COMPARACION:
        return CASOS_COMPARACION[caso_id]
    incendio, protocolo = caso_id.split("/")
    return f"{incendio}/{protocolo.replace('v6', 'v6m', 1)}"


def correr(modelo_id: str) -> None:
    modelo = d.Modelo.cargar(modelo_id)
    modelo.validar()
    for base_id in modelo.casos:
        caso = d.Caso.cargar(_caso_mapas(base_id))
        for receta_id in RECETAS:
            receta = d.Receta.cargar(receta_id)
            try:
                cadena.correr(caso, receta)
                cadena.puntuar(caso, receta)
            except RuntimeError as exc:
                if "no dejó time_of_arrival" not in str(exc):
                    raise
                print(
                    f"{caso.id}/{receta.id}: no arranca; predicción nula",
                    flush=True,
                )
        print(f"{caso.id}: comparación completa", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("modelo")
    args = ap.parse_args()
    correr(args.modelo)


if __name__ == "__main__":
    main()
