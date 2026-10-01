"""Comparación de los tres mapas de combustible sobre el benchmark v5 (COMPARACION-MAPAS-V5.md).

Lee las iteraciones de los protocolos `-v5m` (el paquete v5 más los mapas de WorldCover y
MapBiomas) y escribe en Markdown: Dice, sesgo y forma por incendio y por mapa; diferencias
apareadas con test de signos; el día 1; y dónde se diferencian, por grupo de combustible de
CCS-BAP dentro de la cicatriz.

    uv run python scripts/comparacion_mapas_v5.py [--recetas final|base]
"""
import argparse
import json
from math import comb
from statistics import mean, median

import numpy as np
import rasterio

from app.validation import cadena
from app.validation import definiciones as d

RECETAS = {
    "final": {"CCS-BAP": "lw-100-001", "WorldCover": "lw-100-worldcover-001",
              "MapBiomas": "lw-100-mapbiomas-001"},
    "base": {"CCS-BAP": "base-001", "WorldCover": "fuels-worldcover-002",
             "MapBiomas": "fuels-mapbiomas-001"},
}
GRUPOS = {"GR": (101, 109), "GS": (121, 124), "SH": (141, 149), "TU": (161, 165),
          "TL": (181, 189), "NB": (91, 99)}


def casos() -> list[dict]:
    """Los casos v5 de la partición, con su gemelo v5m."""
    particion = json.loads((d.RAIZ / "particion.json").read_text())
    filas = []
    for conjunto in ("calibracion", "prueba"):
        for clima, ids in particion[conjunto].items():
            for base in ids:
                incendio, proto = base.split("/")
                filas.append({"base": base, "id": f"{incendio}/{proto.replace('v5', 'v5m', 1)}",
                              "conjunto": conjunto, "clima": clima,
                              "limite": base in particion["limites"]})
    return filas


def signos(difs: list[float]) -> tuple[int, int, int, float]:
    """Gana, pierde, empata (|d| < 0,005) y p bilateral exacto del test de signos."""
    g = sum(x >= 0.005 for x in difs)
    p_ = sum(x <= -0.005 for x in difs)
    n = g + p_
    pv = min(1.0, 2 * sum(comb(n, k) for k in range(min(g, p_) + 1)) / 2 ** n) if n else 1.0
    return g, p_, len(difs) - n, pv


def _f(v, nd=3) -> str:
    return "—" if v is None else f"{v:.{nd}f}".replace(".", ",")


def _arranco(manifiesto: dict) -> bool:
    return any(n.startswith("time_of_arrival") for n in manifiesto["ventanas"][0]["salidas"])


def metricas(caso_id: str, recetas: dict) -> dict:
    salida = {}
    for mapa, receta in recetas.items():
        m = d.cargar_metricas(caso_id, receta)
        manifiesto = d.cargar_manifiesto(caso_id, receta)
        if not m and manifiesto and not _arranco(manifiesto):
            # La semilla cae entera en combustible que no quema: ELMFIRE no deja TOA y
            # `correr` aborta. Lo predicho es nada: Dice 0, sesgo 0.
            salida[mapa] = {"dice": 0.0, "sesgo": 0.0, "alarma": True, "forma": 0.0,
                            "t": None, "alcanzada": False, "no_arranca": True,
                            "fuga": manifiesto["factores"].get("fuga_temporal", False),
                            "combustible": manifiesto["factores"]["combustible"],
                            "d1_firms": 0.0, "d1_sesgo_firms": 0.0, "d1_cicatriz_ha": 0.0}
            continue
        if not m:
            continue
        pr, v0 = m["principal"], m["ventanas"][0]
        salida[mapa] = {
            "dice": pr["dice"], "sesgo": pr["sesgo_area"], "alarma": pr["alarma_sesgo"],
            "forma": (pr.get("area_igualada") or {}).get("dice"),
            "t": (pr.get("area_igualada") or {}).get("hora"),
            "alcanzada": (pr.get("area_igualada") or {}).get("alcanzada"),
            "fuga": m["factores"].get("fuga_temporal", False),
            "combustible": m["factores"]["combustible"],
            "d1_firms": v0["firms"]["incremento"]["dice"],
            "d1_sesgo_firms": v0["firms"]["incremento"]["sesgo_area"],
            "d1_cicatriz_ha": v0["cicatriz"]["acumulado"]["predicho_ha"],
        }
    return salida


def donde(caso_id: str, recetas: dict) -> dict:
    """Por grupo de CCS-BAP: ha observadas en la cicatriz y ha acertadas / sobrantes de cada
    mapa en la última ventana; y la fracción de la cicatriz donde cada mapa es igual a
    WorldCover (ahí no se puede diferenciar del baseline)."""
    caso = d.Caso.cargar(caso_id)
    comunes = caso.paquete()["comunes"]
    mapas = {n.removeprefix("fbfm40_").removesuffix(".tif"): cadena._leer(s)
             for n, s in comunes.items() if n.startswith("fbfm40_")}
    ccs = next(v for k, v in mapas.items() if k.startswith("ccsbap"))
    wc = next(v for k, v in mapas.items() if k.startswith("worldcover"))
    grupo = np.full(ccs.shape, "", dtype="<U2")
    for g, (a, b) in GRUPOS.items():
        grupo[(ccs >= a) & (ccs <= b)] = g
    salida: dict = {"grupos": {}, "igual_a_wc": {}}
    confusiones = {}
    for mapa, receta in recetas.items():
        manifiesto = d.cargar_manifiesto(caso_id, receta)
        n = len(manifiesto["ventanas"]) - 1 if manifiesto else 0
        ruta = cadena.VISTAS / caso_id / receta / f"v{n}" / "confusion.tif"
        if ruta.exists():
            with rasterio.open(ruta) as src:
                confusiones[mapa] = src.read(1)
            ha = abs(src.transform.a) ** 2 / 1e4
    una = next(iter(confusiones.values()))
    # Lo observado (cicatriz fuera de la semilla y de la exclusión) es igual en los tres.
    obs = (una == cadena.ACIERTO) | (una == cadena.OBS_SIN_PREDECIR)
    for mapa, receta in recetas.items():
        manifiesto = d.cargar_manifiesto(caso_id, receta)
        assert manifiesto, f"{caso_id} sin {receta}"
        conf = confusiones.get(mapa, np.where(obs, cadena.OBS_SIN_PREDECIR, cadena.NADA))
        propio = next(v for k, v in mapas.items()
                      if k == manifiesto["factores"]["combustible"])
        salida["igual_a_wc"][mapa] = float((propio[obs] == wc[obs]).mean()) if obs.any() else None
        for g in GRUPOS:
            en = grupo == g
            fila = salida["grupos"].setdefault(g, {"obs_ha": float((obs & en).sum() * ha)})
            fila[mapa] = {"tp_ha": float(((conf == cadena.ACIERTO) & en).sum() * ha),
                          "fp_ha": float(((conf == cadena.PREDICHO_SIN_OBS) & en).sum() * ha)}
    return salida


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recetas", choices=RECETAS, default="final")
    args = ap.parse_args()
    recetas = RECETAS[args.recetas]
    filas = casos()
    for f in filas:
        f["m"] = metricas(f["id"], recetas)
    completos = [f for f in filas if len(f["m"]) == 3]
    print(f"## Recetas `{args.recetas}`: {', '.join(recetas.values())}\n")
    print(f"{len(completos)} de {len(filas)} incendios con los tres mapas.\n")

    print("| Incendio | Conjunto | Clima | " + " | ".join(
        f"{m} Dice / sesgo / forma" for m in recetas) + " |")
    print("|---|---|---|" + "---|" * len(recetas))
    for f in filas:
        celdas = []
        for mapa in recetas:
            x = f["m"].get(mapa)
            if not x:
                celdas.append("—")
                continue
            marca = (" ⚠" if x["alarma"] else "") + (" ‡" if x["fuga"] else "")
            celdas.append(f"{_f(x['dice'])} / {_f(x['sesgo'], 2)} / {_f(x['forma'])}{marca}"
                          f" ({x['combustible']})")
        nombre = f["base"].split("/")[0] + (" (límite)" if f["limite"] else "")
        print(f"| {nombre} | {f['conjunto']} | {f['clima'].upper()} | " + " | ".join(celdas) + " |")

    def bloque(titulo: str, sel: list[dict]) -> None:
        print(f"\n**{titulo}** ({len(sel)} incendios)\n")
        print("| | Media Dice | Mediana Dice | Media forma |")
        print("|---|---|---|---|")
        for mapa in recetas:
            dices = [f["m"][mapa]["dice"] for f in sel]
            formas = [f["m"][mapa]["forma"] for f in sel if f["m"][mapa]["forma"] is not None]
            print(f"| {mapa} | {_f(mean(dices))} | {_f(median(dices))} | "
                  f"{_f(mean(formas)) if formas else '—'} |")
        print("\n| CCS-BAP contra | Métrica | Gana / pierde / empata | p (signos) | "
              "Δ media | Δ mediana | Δ por incendio |")
        print("|---|---|---|---|---|---|---|")
        for otro in [m for m in recetas if m != "CCS-BAP"]:
            for metrica in ("dice", "forma"):
                difs = [f["m"]["CCS-BAP"][metrica] - f["m"][otro][metrica] for f in sel
                        if f["m"]["CCS-BAP"][metrica] is not None
                        and f["m"][otro][metrica] is not None]
                if not difs:
                    continue
                g, p_, e, pv = signos(difs)
                print(f"| {otro} | {metrica} | {g} / {p_} / {e} | {_f(pv)} | "
                      f"{_f(mean(difs), 3)} | {_f(median(difs), 3)} | "
                      + " ".join(f"{x:+.3f}".replace(".", ",") for x in difs) + " |")

    sin_limite = [f for f in completos if not f["limite"]]
    bloque("Todos (sin el límite)", sin_limite)
    bloque("Calibración (sin el límite)", [f for f in sin_limite if f["conjunto"] == "calibracion"])
    bloque("Prueba", [f for f in sin_limite if f["conjunto"] == "prueba"])
    bloque("GFS (sin el límite)", [f for f in sin_limite if f["clima"] == "gfs"])
    bloque("ERA5", [f for f in sin_limite if f["clima"] == "era5"])
    bloque("Sin fuga temporal de WorldCover (sin el límite)",
           [f for f in sin_limite if not f["m"]["WorldCover"]["fuga"]])
    bloque("Con fuga temporal de WorldCover",
           [f for f in sin_limite if f["m"]["WorldCover"]["fuga"]])

    print("\n### Día 1 (ventana 0): Dice y sesgo contra el incremento FIRMS; ha predichas\n")
    print("| Incendio | " + " | ".join(f"{m}" for m in recetas) + " |")
    print("|---|" + "---|" * len(recetas))
    for f in completos:
        print(f"| {f['base'].split('/')[0]} | " + " | ".join(
            f"{_f(f['m'][m]['d1_firms'])} / {_f(f['m'][m]['d1_sesgo_firms'], 2)} / "
            f"{f['m'][m]['d1_cicatriz_ha']:,.0f} ha".replace(",", ".") for m in recetas) + " |")
    for otro in [m for m in recetas if m != "CCS-BAP"]:
        difs = [f["m"]["CCS-BAP"]["d1_firms"] - f["m"][otro]["d1_firms"] for f in sin_limite]
        g, p_, e, pv = signos(difs)
        print(f"\nDía 1, CCS-BAP contra {otro} (sin el límite): gana {g}, pierde {p_}, "
              f"empata {e}, p = {_f(pv)}, Δ media {_f(mean(difs))}")

    print("\n### Dónde: por grupo de CCS-BAP dentro de la cicatriz (última ventana, ha)\n")
    total: dict = {}
    print("| Incendio | % cicatriz igual a WorldCover (" + ", ".join(recetas) + ") |")
    print("|---|---|")
    for f in completos:
        dd = donde(f["id"], recetas)
        print(f"| {f['base'].split('/')[0]} | " + " / ".join(
            _f(100 * dd["igual_a_wc"][m], 0) for m in recetas) + " |")
        for g, fila in dd["grupos"].items():
            t = total.setdefault(g, {"obs_ha": 0.0})
            t["obs_ha"] += fila["obs_ha"]
            for m in recetas:
                for k in ("tp_ha", "fp_ha"):
                    t.setdefault(m, {"tp_ha": 0.0, "fp_ha": 0.0})[k] += fila[m][k]
    print("\nSuma de los incendios con los tres mapas (aciertos / sobrantes en ha):\n")
    print("| Grupo CCS-BAP | Observado | " + " | ".join(recetas) + " |")
    print("|---|---|" + "---|" * len(recetas))
    for g, t in total.items():
        print(f"| {g} | {t['obs_ha']:,.0f} | ".replace(",", ".") + " | ".join(
            f"{t[m]['tp_ha']:,.0f} / {t[m]['fp_ha']:,.0f}".replace(",", ".")
            for m in recetas) + " |")


if __name__ == "__main__":
    main()
