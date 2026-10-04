"""Crea los casos de comparación de mapas condicionados a un modelo promovido.

Cada caso nuevo copia la definición del caso congelado y empaqueta su contenido byte a byte,
sumando los rásters WorldCover y MapBiomas ya preparados para la misma grilla. El dosel y todos
los demás insumos siguen siendo los del modelo: entre recetas sólo cambia ``fbfm40.tif``.

    uv run python scripts/preparar_comparacion_mapas_modelo.py modelo-v0
"""
import argparse
import json

from app.validation import definiciones as d


def _protocolo_mapas(protocolo: str, marca: str = "v6m") -> str:
    if "v6" not in protocolo:
        raise ValueError(f"{protocolo}: se esperaba un protocolo v6")
    return protocolo.replace("v6", marca, 1)


def _antecedente_v5m(protocolo: str) -> str:
    return protocolo.replace("v6", "v5m", 1)


def preparar(modelo_id: str, caso_elegido: str | None = None, marca: str = "v6m") -> list[str]:
    modelo = d.Modelo.cargar(modelo_id)
    modelo.validar()
    creados = []
    for caso_id in modelo.casos:
        if caso_elegido and caso_id != caso_elegido:
            continue
        incendio, protocolo = caso_id.split("/")
        base_path = d.RAIZ / "casos" / incendio / f"{protocolo}.json"
        datos = json.loads(base_path.read_text())

        antecedente = d.RAIZ / "casos" / incendio / f"{_antecedente_v5m(protocolo)}.json"
        mapas_v5m = json.loads(antecedente.read_text())["empaquetado"]["mapas"]
        comparadores = {
            nombre: ruta
            for nombre, ruta in mapas_v5m.items()
            if "worldcover" in nombre or "mapbiomas" in nombre
        }
        if len(comparadores) != 2:
            raise ValueError(f"{antecedente}: se esperaban WorldCover y MapBiomas")

        nuevo_protocolo = _protocolo_mapas(protocolo, marca)
        nuevo_id = f"{incendio}/{nuevo_protocolo}"
        datos["descripcion"] = (
            f"Comparación final de mapas condicionada a {modelo.id}: paquete de `{caso_id}` "
            "byte a byte más WorldCover y MapBiomas. El dosel permanece congelado y entre "
            "recetas sólo cambia fbfm40.tif. " + datos["descripcion"]
        )
        datos["empaquetado"] = {
            "tipo": "ampliar_mapas",
            "base": caso_id,
            "mapas": comparadores,
        }
        destino = d.RAIZ / "casos" / incendio / f"{nuevo_protocolo}.json"
        contenido = json.dumps(datos, indent=2, ensure_ascii=False) + "\n"
        if destino.exists() and destino.read_text() != contenido:
            raise FileExistsError(f"{destino} ya existe con otro contenido")
        destino.write_text(contenido)
        creados.append(nuevo_id)
        print(nuevo_id)
    return creados


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("modelo")
    ap.add_argument("--caso")
    ap.add_argument("--marca", default="v6m")
    args = ap.parse_args()
    preparar(args.modelo, args.caso, args.marca)


if __name__ == "__main__":
    main()
