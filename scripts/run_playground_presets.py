"""Runs every playground preset and reports the comparison table.

Doubles as the end-to-end check for the playground: it exercises the builder, the
namelist, the runner and the metrics on all 15 scenarios, and flags any run that clipped
against the domain boundary or failed to spread.

    uv run python scripts/run_playground_presets.py [--api http://localhost:8000]
"""
import argparse
import json
import sys
import urllib.error
import urllib.request


def _post(url: str, payload: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _get(url: str, timeout: float) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--timeout", type=float, default=600.0)
    args = ap.parse_args()

    base = f"{args.api.rstrip('/')}/api/v1/playground"
    presets = _get(f"{base}/presets", args.timeout)["data"]["presets"]
    print(f"{len(presets)} presets\n")

    header = f"{'preset':<26} {'ha':>9} {'dist m':>8} {'dir':>6} {'asp':>5} {'ROS m/h':>8}  clase"
    print(header)
    print("-" * len(header))

    problems: list[str] = []
    results: dict[str, dict] = {}

    for preset in sorted(presets, key=lambda p: p["order"]):
        pid = preset["id"]
        try:
            run = _post(f"{base}/run", preset["scenario"], args.timeout)
            sim_id = run["data"]["simulation_id"]
            m = _get(f"{base}/{sim_id}/metrics", args.timeout)["data"]
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError) as exc:
            print(f"{pid:<26}  FALLÓ: {exc}")
            problems.append(f"{pid}: {exc}")
            continue

        f = m["final"]
        results[pid] = m
        flag = ""
        if m["reached_domain_edge"]:
            flag = "  ⚠ TOCÓ EL BORDE — recorte, no comparable"
            problems.append(f"{pid}: reached the domain edge")
        elif m["burned_cells"] == 0:
            flag = "  · sin propagación"

        print(
            f"{pid:<26} {f['burned_ha']:>9.1f} {f['max_distance_m']:>8.0f} "
            f"{str(f['head_direction_deg']):>6} {str(f['aspect_ratio']):>5} "
            f"{f['head_ros_m_per_h']:>8.1f}  {f['head_ros_class']}{flag}"
        )

    print()
    _check_expectations(results, problems)

    if problems:
        print("\nPROBLEMAS:")
        for p in problems:
            print(" -", p)
        return 1
    print("\nTodos los presets corrieron y cumplieron lo esperado.")
    return 0


def _check_expectations(r: dict, problems: list[str]) -> None:
    """The assertions the sequence exists to make. A preset table that runs but does not
    show the expected contrast is not a sensitivity experiment."""

    def area(pid: str) -> float:
        return r[pid]["final"]["burned_ha"] if pid in r else float("nan")

    def direction(pid: str) -> float | None:
        return r[pid]["final"]["head_direction_deg"] if pid in r else None

    checks: list[tuple[str, bool, str]] = []

    if "01-gr2-calma" in r and "02-gr2-viento-n15" in r:
        checks.append((
            "el viento acelera la propagación",
            area("02-gr2-viento-n15") > 5 * area("01-gr2-calma"),
            f"calma {area('01-gr2-calma')} ha vs viento {area('02-gr2-viento-n15')} ha",
        ))
    if direction("02-gr2-viento-n15") is not None:
        d = direction("02-gr2-viento-n15")
        checks.append((
            "viento del norte propaga hacia el sur",
            abs(d - 180.0) < 15.0,
            f"dirección medida {d}°, esperada ~180°",
        ))
    if direction("03-gr2-viento-ne15") is not None:
        d = direction("03-gr2-viento-ne15")
        checks.append((
            "viento del noreste propaga hacia el sudoeste",
            abs(d - 225.0) < 20.0,
            f"dirección medida {d}°, esperada ~225°",
        ))
    if "05-tl3-viento-n15" in r and "06-tu5-viento-n15" in r:
        checks.append((
            "TU5 (propuesta IGN-20) propaga más que TL3 (baseline)",
            area("06-tu5-viento-n15") > area("05-tl3-viento-n15"),
            f"TL3 {area('05-tl3-viento-n15')} ha vs TU5 {area('06-tu5-viento-n15')} ha",
        ))
    if "11a-gr3-curado" in r and "11b-gr3-verde" in r:
        checks.append((
            "ELMFIRE aplica la transferencia dinámica de carga (Scott & Burgan p. 4)",
            area("11b-gr3-verde") < 0.5 * area("11a-gr3-curado"),
            f"curado {area('11a-gr3-curado')} ha vs verde {area('11b-gr3-verde')} ha",
        ))
    if "02-gr2-viento-n15" in r and "10-gr2-humedad-alta" in r:
        checks.append((
            "la humedad del combustible muerto frena la propagación",
            area("10-gr2-humedad-alta") < area("02-gr2-viento-n15"),
            f"seco {area('02-gr2-viento-n15')} ha vs húmedo {area('10-gr2-humedad-alta')} ha",
        ))

    print("VERIFICACIONES")
    for name, ok, detail in checks:
        print(f"  {'OK  ' if ok else 'FALLA'} {name}\n        {detail}")
        if not ok:
            problems.append(f"expectativa no cumplida: {name} ({detail})")


if __name__ == "__main__":
    sys.exit(main())
