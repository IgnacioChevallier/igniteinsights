"""Nota AD: CPU/RAM del runner y latencia de un backtest GEFS, a partir de los logs de la corrida.

    uv run python scripts/diagnostico_recursos_ensamble.py

desde un checkout con `data/`. Lee `data/ensemble-poc/medicion-recursos/` (log con hora UTC por
línea y `docker stats` del contenedor del runner) y compara los hashes de TOA y de los mapas de
acuerdo contra el backtest consolidado. Escribe AD-recursos-ensamble.json en
benchmarks/diagnosticos/e2e/datos/.
"""
import csv
import hashlib
import json
import re
import statistics
from datetime import datetime
from pathlib import Path

MED = Path("data/ensemble-poc/medicion-recursos")
NUEVO = MED / "los-alerces-2023-w01"
REF = Path("data/ensemble-poc/backtest-lote-a/los-alerces-2023-w01")
VM_MIB = 7.753 * 1024
SALIDA = (Path(__file__).resolve().parents[1]
          / "benchmarks/diagnosticos/e2e/datos/AD-recursos-ensamble.json")
UNIDADES = {"KiB": 1 / 1024, "MiB": 1, "GiB": 1024, "kB": 1 / 1024, "MB": 1, "GB": 1024}


def mib(texto: str) -> float:
    """'1.456GiB' → 1490,9. La memoria usada de `docker stats`."""
    valor, unidad = re.match(r"([\d.]+)\s*([KMG]i?B)", texto.strip()).groups()
    return float(valor) * UNIDADES[unidad]


def _hora(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def main() -> None:
    toa = {r: {t["member"]: t["toa_sha256"]
               for t in json.loads((r / "integrity.json").read_text())["toa"]}
           for r in (NUEVO, REF)}
    geo = [f"{h}/{f.name}" for h in ("h12", "h24")
           for f in (REF / "agreement" / h).glob("*.geojson")]

    def sha(raiz: Path, g: str) -> str:
        return hashlib.sha256((raiz / "agreement" / g).read_bytes()).hexdigest()

    geo_iguales = sum(sha(REF, g) == sha(NUEVO, g) for g in geo)

    lineas = [ln for ln in (MED / "corrida.log").read_text().splitlines() if ln[:4].isdigit()]
    fin = _hora(lineas[-1][:20])
    pasos = [(_hora(ln[:20]), m.group(2) or m.group(1)) for ln in lineas
             if " + " in ln[:24] and (m := re.search(r"/scripts/([a-z_]+)\.py ?([a-z-]*)", ln))]
    inicio = pasos[0][0]
    pared = (fin - inicio).total_seconds()
    etapas: dict[str, float] = {}
    for i, (t, etapa) in enumerate(pasos):
        siguiente = pasos[i + 1][0] if i + 1 < len(pasos) else fin
        etapas[etapa] = etapas.get(etapa, 0.0) + (siguiente - t).total_seconds()

    muestras = [(_hora(t), float(c.rstrip("%")), mib(m.split("/")[0]))
                for t, c, m in csv.reader((MED / "docker-stats.csv").open())]
    reposo = statistics.median(m for t, _, m in muestras if t < inicio)
    pico = max(m for _, _, m in muestras)
    cpu_s = sum(c / 100 * (muestras[i + 1][0] - t).total_seconds()
                for i, (t, c, _) in enumerate(muestras[:-1]) if inicio <= t <= fin)
    miembros = [json.loads(p.read_text())["wall_seconds"]
                for p in (NUEVO / "runs").glob("*/run-metrics.json")]

    resultado = {
        "control": {"toa_iguales": sum(toa[NUEVO].get(k) == v for k, v in toa[REF].items()),
                    "toa_total": len(toa[REF]), "geojson_iguales": geo_iguales,
                    "geojson_total": len(geo)},
        "pared_min": round(pared / 60, 1),
        "etapas_min": {k: round(v / 60, 1) for k, v in etapas.items()},
        "etapas_fraccion": {k: round(v / pared, 3) for k, v in etapas.items()},
        "elmfire_suma_s": round(sum(miembros)),
        "elmfire_mediana_s": round(statistics.median(miembros), 1),
        "elmfire_fraccion": round(sum(miembros) / pared, 3),
        "ram_reposo_mib": round(reposo), "ram_pico_mib": round(pico),
        "ram_pico_sobre_reposo_mib": round(pico - reposo),
        "paralelos_en_vm": int((VM_MIB - reposo) // (pico - reposo)),
        "cpu_s_contenedor": round(cpu_s),
        "muestras": len(muestras),
    }
    SALIDA.write_text(json.dumps(resultado, indent=1, ensure_ascii=False))
    print(json.dumps(resultado, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
