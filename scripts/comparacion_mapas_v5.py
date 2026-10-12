"""Comparación de los tres mapas de combustible sobre el benchmark v5.

Ver docs/resultados/COMPARACION-MAPAS-V5.md.

Lee las iteraciones de los protocolos `-v5m` (el paquete v5 más los mapas de WorldCover y
MapBiomas) y escribe en Markdown: Dice, sesgo y forma por incendio y por mapa; diferencias
apareadas con test de signos; el día 1; y dónde se diferencian, por grupo de combustible de
CCS-BAP dentro de la cicatriz.

    uv run python scripts/comparacion_mapas_v5.py [--recetas final|base]
    uv run python scripts/comparacion_mapas_v5.py --modelo modelo-v0
"""
import argparse
import json
import sys
from math import comb
from pathlib import Path
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
CASOS_COMPARACION = {
    "los-alerces-2023/calibracion-v6-h54":
        "los-alerces-2023/calibracion-v6m2-h54",
}


def caso_comparacion(base: str) -> str:
    if base in CASOS_COMPARACION:
        return CASOS_COMPARACION[base]
    incendio, protocolo = base.split("/")
    return f"{incendio}/{protocolo.replace('v6', 'v6m', 1)}"


def casos(modelo_id: str | None = None) -> list[dict]:
    """Los casos base y sus gemelos con los tres mapas."""
    particion = json.loads((d.RAIZ / "particion.json").read_text())
    filas = []
    if modelo_id:
        modelo = d.Modelo.cargar(modelo_id)
        modelo.validar()
        for conjunto, fuentes in modelo.conjuntos.items():
            for clima, ids in fuentes.items():
                for base in ids:
                    filas.append({
                        "base": base,
                        "id": caso_comparacion(base),
                        "conjunto": conjunto,
                        "clima": clima,
                        "limite": base in particion["limites"],
                    })
        return filas
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


def cota_inferior(difs: list[float], alfa: float = 0.05) -> tuple[float, float, float | None]:
    """Hodges-Lehmann y su cota inferior unilateral exacta (Wilcoxon de rangos con signo):
    la c+1-ésima media de Walsh, con c el mayor valor tal que P(T <= c) <= alfa. Devuelve
    (estimador, nivel exacto alcanzado, cota); la cota es None si n es tan chico que ningún
    c cumple."""
    n = len(difs)
    cuentas = [1]  # cuentas[t]: asignaciones de signo con T = t bajo H0
    for r in range(1, n + 1):
        cuentas = [a + (cuentas[i - r] if i >= r else 0)
                   for i, a in enumerate(cuentas + [0] * r)]
    acum = c = 0
    while acum + cuentas[c] <= alfa * 2 ** n:
        acum += cuentas[c]
        c += 1
    walsh = sorted((a + b) / 2 for i, a in enumerate(difs) for b in difs[i:])
    return median(walsh), 1 - acum / 2 ** n, walsh[c - 1] if c else None


def _f(v, nd=3) -> str:
    return "—" if v is None else f"{v:.{nd}f}".replace(".", ",")


def _arranco(manifiesto: dict) -> bool:
    return any(n.startswith("time_of_arrival") for n in manifiesto["ventanas"][0]["salidas"])


def _ha(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


def control_reproducido(base_id: str, mapas_id: str, receta: str) -> bool:
    """El control del caso ampliado debe reproducir los TOA congelados byte a byte."""
    base = d.cargar_manifiesto(base_id, receta)
    mapas = d.cargar_manifiesto(mapas_id, receta)
    if not base or not mapas or len(base["ventanas"]) != len(mapas["ventanas"]):
        return False
    return all(
        cadena._toa(a["salidas"]) == cadena._toa(b["salidas"])
        for a, b in zip(base["ventanas"], mapas["ventanas"], strict=True)
    )


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
    mapa en la última ventana."""
    caso = d.Caso.cargar(caso_id)
    comunes = caso.paquete()["comunes"]
    mapas = {n.removeprefix("fbfm40_").removesuffix(".tif"): cadena._leer(s)
             for n, s in comunes.items() if n.startswith("fbfm40_")}
    ccs = next(v for k, v in mapas.items() if k.startswith("ccsbap"))
    grupo = np.full(ccs.shape, "", dtype="<U2")
    for g, (a, b) in GRUPOS.items():
        grupo[(ccs >= a) & (ccs <= b)] = g
    salida: dict = {"grupos": {}}
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
    for mapa in recetas:
        conf = confusiones.get(mapa, np.where(obs, cadena.OBS_SIN_PREDECIR, cadena.NADA))
        for g in GRUPOS:
            en = grupo == g
            fila = salida["grupos"].setdefault(g, {"obs_ha": float((obs & en).sum() * ha)})
            fila[mapa] = {"tp_ha": float(((conf == cadena.ACIERTO) & en).sum() * ha),
                          "fp_ha": float(((conf == cadena.PREDICHO_SIN_OBS) & en).sum() * ha)}
    return salida


def _dilatar(m: np.ndarray, r: int) -> np.ndarray:
    """Dilatación cuadrada de radio r celdas, separable con sumas acumuladas."""
    x = m.astype(np.int64)
    for eje in (0, 1):
        c = np.cumsum(np.pad(x, [(r + 1, r) if e == eje else (0, 0) for e in (0, 1)]), axis=eje)
        x = np.take(c, range(2 * r + 1, c.shape[eje]), axis=eje) - np.take(
            c, range(0, c.shape[eje] - 2 * r - 1), axis=eje)
    return x > 0


def fuga(caso_id: str) -> dict:
    """¿El mapa ve la cicatriz? Fracción de pastizal (GR) y de no combustible (NB) dentro de
    la cicatriz y en un anillo de 2 km alrededor. Un mapa posterior al fuego que la ve pone
    mucho más GR/NB adentro que afuera; uno anterior, más o menos lo mismo."""
    caso = d.Caso.cargar(caso_id)
    comunes = caso.paquete()["comunes"]
    cic = cadena._leer(comunes["cicatriz.tif"]).astype(bool)
    excl = cadena._leer(comunes["excluido.tif"]).astype(bool)
    anillo = _dilatar(cic, 67) & ~cic & ~excl
    dentro = cic & ~excl
    salida = {}
    for n, sha in comunes.items():
        if n.startswith("fbfm40_"):
            f = cadena._leer(sha)
            gr_nb = (f >= 91) & (f <= 109)
            salida[n.removeprefix("fbfm40_").removesuffix(".tif")] = (
                float(gr_nb[dentro].mean()), float(gr_nb[anillo].mean()))
    return salida


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recetas", choices=RECETAS, default="final")
    ap.add_argument("--modelo")
    ap.add_argument("--salida", type=Path)
    args = ap.parse_args()
    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = args.salida.open("w")
    recetas = RECETAS[args.recetas]
    filas = casos(args.modelo)
    if args.modelo:
        print(f"# Resultados de la comparación de mapas condicionada a {args.modelo}\n")
    for f in filas:
        f["m"] = metricas(f["id"], recetas)
    completos = [f for f in filas if len(f["m"]) == 3]
    print(f"## Recetas `{args.recetas}`: {', '.join(recetas.values())}\n")
    print(f"{len(completos)} de {len(filas)} incendios con los tres mapas.\n")
    controles = [control_reproducido(f["base"], f["id"], recetas["CCS-BAP"]) for f in filas]
    if not all(controles):
        malos = [f["base"] for f, ok in zip(filas, controles, strict=True) if not ok]
        raise RuntimeError(f"los controles CCS-BAP no reproducen modelo-v0: {malos}")
    print(f"Controles CCS-BAP reproducidos byte a byte: {sum(controles)}/{len(controles)}.\n")
    if args.modelo and CASOS_COMPARACION:
        print(
            "Los Alerces 2023 usa el protocolo `v6m2`: la primera corrida `v6m` se rechazó "
            "porque fue ejecutada durante una prueba de concurrencia MPI y no reprodujo el "
            "control. `v6m2` es la repetición limpia, íntegramente serial.\n"
        )

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
            f"{_ha(f['m'][m]['d1_cicatriz_ha'])} ha" for m in recetas) + " |")
    for otro in [m for m in recetas if m != "CCS-BAP"]:
        difs = [f["m"]["CCS-BAP"]["d1_firms"] - f["m"][otro]["d1_firms"] for f in sin_limite]
        g, p_, e, pv = signos(difs)
        print(f"\nDía 1, CCS-BAP contra {otro} (sin el límite): gana {g}, pierde {p_}, "
              f"empata {e}, p = {_f(pv)}, Δ media {_f(mean(difs))}")

    print("\n### ¿Cada mapa ve la cicatriz? % de GR + NB dentro / en el anillo de 2 km\n")
    print("| Incendio | Año del fuego | " + " | ".join(recetas) + " |")
    print("|---|---|" + "---|" * len(recetas))
    for f in filas:
        fu = fuga(f["id"])
        celdas = []
        for prefijo in ("ccsbap", "worldcover", "mapbiomas"):
            k = next(k for k in fu if k.startswith(prefijo))
            celdas.append(f"{_f(100 * fu[k][0], 0)} / {_f(100 * fu[k][1], 0)} ({k[len(prefijo):]})")
        anio = d.Caso.cargar(f["id"]).anio_fuego
        print(f"| {f['base'].split('/')[0]} | {anio} | " + " | ".join(celdas) + " |")

    print("\n### Dónde: por grupo de CCS-BAP dentro de la cicatriz (última ventana)\n")
    for titulo, sel in (("Sin fuga temporal (2021+, sin el límite)",
                         [f for f in sin_limite if not f["m"]["WorldCover"]["fuga"]]),
                        ("Con fuga temporal (2015-2019)",
                         [f for f in sin_limite if f["m"]["WorldCover"]["fuga"]])):
        total: dict = {}
        for f in sel:
            for g, fila in donde(f["id"], recetas)["grupos"].items():
                t = total.setdefault(g, {"obs_ha": 0.0})
                t["obs_ha"] += fila["obs_ha"]
                for m in recetas:
                    for k in ("tp_ha", "fp_ha"):
                        t.setdefault(m, {"tp_ha": 0.0, "fp_ha": 0.0})[k] += fila[m][k]
        print(f"\n{titulo}: aciertos / sobrantes en ha\n")
        print("| Grupo CCS-BAP | Observado | " + " | ".join(recetas) + " |")
        print("|---|---|" + "---|" * len(recetas))
        for g, t in total.items():
            print(f"| {g} | {_ha(t['obs_ha'])} | " + " | ".join(
                f"{_ha(t[m]['tp_ha'])} / {_ha(t[m]['fp_ha'])}" for m in recetas) + " |")

    calibracion = [f for f in sin_limite if f["conjunto"] == "calibracion"]
    prueba = [f for f in sin_limite if f["conjunto"] == "prueba"]
    sin_fuga = [f for f in sin_limite if not f["m"]["WorldCover"]["fuga"]]

    def media(sel: list[dict], mapa: str) -> float:
        return mean(f["m"][mapa]["dice"] for f in sel)

    # Margen: conservar al menos la mitad de lo que MapBiomas gana sobre el baseline
    # (WorldCover) donde la comparación es limpia; convención de no inferioridad (FDA M2).
    margen = (media(sin_fuga, "MapBiomas") - media(sin_fuga, "WorldCover")) / 2
    print("\n## No inferioridad frente a MapBiomas\n")
    print(
        "Δ = CCS-BAP − MapBiomas por incendio. Estimador de Hodges-Lehmann y cota inferior "
        "unilateral exacta al 95 % (Wilcoxon de rangos con signo). CCS-BAP es no inferior "
        f"si la cota supera −{_f(margen)}: la mitad de la ventaja media de MapBiomas sobre "
        f"WorldCover en los casos sin fuga ({_f(media(sin_fuga, 'MapBiomas'))} − "
        f"{_f(media(sin_fuga, 'WorldCover'))}). El margen se fijó después de ver las "
        "diferencias por incendio; por eso la cota se lee también por sí misma: su valor "
        "absoluto es el margen más chico que los datos sostienen, sin depender de esa "
        "elección.\n"
    )
    print("| Conjunto | Métrica | n | Δ HL | Cota inferior | Nivel exacto | No inferior |")
    print("|---|---|---|---|---|---|---|")
    cotas = {}
    for titulo, sel in (("Sin fuga (6)", sin_fuga), ("Todos sin el límite", sin_limite),
                        ("Calibración", calibracion), ("Prueba", prueba)):
        for metrica in ("dice", "forma"):
            difs = [f["m"]["CCS-BAP"][metrica] - f["m"]["MapBiomas"][metrica] for f in sel
                    if f["m"]["CCS-BAP"][metrica] is not None
                    and f["m"]["MapBiomas"][metrica] is not None]
            hl, nivel, cota = cota_inferior(difs)
            cotas[titulo, metrica] = cota
            veredicto = "n insuficiente" if cota is None else ("sí" if cota > -margen else "no")
            print(f"| {titulo} | {metrica} | {len(difs)} | {_f(hl)} | {_f(cota)} | "
                  f"{_f(100 * nivel, 1) if cota is not None else '—'} % | {veredicto} |")
    sin_el_turbio = [f["m"]["CCS-BAP"]["dice"] - f["m"]["MapBiomas"]["dice"] for f in sin_fuga
                     if not f["base"].startswith("el-turbio")]
    print(
        f"\nSensibilidad: sin El Turbio, la cota de Dice en los casos sin fuga pasa a "
        f"{_f(cota_inferior(sin_el_turbio)[2])} (n = {len(sin_el_turbio)}).\n"
    )

    print("\n## Conclusión\n")
    print(
        f"En los seis casos sin fuga temporal, CCS-BAP obtiene Dice medio "
        f"{_f(media(sin_fuga, 'CCS-BAP'))}, frente a "
        f"{_f(media(sin_fuga, 'WorldCover'))} de WorldCover y "
        f"{_f(media(sin_fuga, 'MapBiomas'))} de MapBiomas. Supera a WorldCover en 5/6 "
        "incendios y a MapBiomas en 4/6, con un empate. La dirección favorece claramente a "
        "CCS-BAP frente a WorldCover, pero la muestra es demasiado pequeña para significación "
        "en el test de signos (p = 0,219). Frente a MapBiomas, la ventaja es pequeña y tampoco "
        "concluyente (p = 0,375).\n"
    )
    print(
        f"En calibración, CCS-BAP conserva la mayor media "
        f"({_f(media(calibracion, 'CCS-BAP'))} contra "
        f"{_f(media(calibracion, 'WorldCover'))} y "
        f"{_f(media(calibracion, 'MapBiomas'))}). En prueba ocurre lo contrario: "
        f"{_f(media(prueba, 'CCS-BAP'))} contra "
        f"{_f(media(prueba, 'WorldCover'))} y {_f(media(prueba, 'MapBiomas'))}. "
        "El Turbio explica buena parte de esa inversión. Como el holdout no puede usarse para "
        "elegir el mapa después de observarlo, el resultado no cambia modelo-v0.\n"
    )
    print(
        "Cierre: WorldCover queda descartado como fuente principal; además de la fuga temporal "
        "en 2015–2019, falla fuertemente en la mayoría de los casos posteriores. CCS-BAP sigue "
        "siendo el mapa de modelo-v0. MapBiomas queda como el comparador competitivo: no hay "
        "evidencia suficiente para afirmar que CCS-BAP lo supera de forma general. Un eventual "
        "cambio exige un modelo-v1 predefinido y datos independientes nuevos, no otro ajuste "
        "sobre estos once incendios."
    )
    print(
        f"\nNo inferioridad: con 95 % de confianza, CCS-BAP no pierde contra MapBiomas más de "
        f"{_f(-cotas['Sin fuga (6)', 'dice'])} de Dice en los casos sin fuga "
        f"({_f(-cotas['Todos sin el límite', 'dice'])} con los diez), dentro del margen de "
        f"{_f(margen)}. La afirmación que se sostiene es \"no inferior a MapBiomas\", no "
        "\"equivalente\": la cota depende casi entera de El Turbio, y una pérdida de hasta "
        "0,1 de Dice no es despreciable. El conjunto de prueba (4) es demasiado chico para "
        "una cota exacta al 95 %."
    )

if __name__ == "__main__":
    main()
