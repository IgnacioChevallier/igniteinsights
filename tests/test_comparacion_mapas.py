import importlib.util
import itertools
import random

spec = importlib.util.spec_from_file_location("cm", "scripts/comparacion_mapas_v5.py")
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)


def _p_valor(d: list[float], th: float) -> float:
    """Wilcoxon exacto unilateral (mediana > th), por enumeración."""
    x = [v - th for v in d]
    orden = sorted(range(len(x)), key=lambda i: abs(x[i]))
    t = sum(r + 1 for r, i in enumerate(orden) if x[i] > 0)
    dist = [sum(r + 1 for r, s in enumerate(sg) if s)
            for sg in itertools.product([0, 1], repeat=len(x))]
    return sum(v >= t for v in dist) / 2 ** len(x)


def test_cota_inferior_invierte_wilcoxon_exacto():
    assert abs(cm.cota_inferior([1, 2, 3, 4, 5, 6])[1] - 61 / 64) < 1e-12
    assert abs(cm.cota_inferior(list(range(1, 11)))[1] - (1 - 43 / 1024)) < 1e-12
    assert cm.cota_inferior([1, 2, 3, 4])[2] is None
    rng = random.Random(1)
    for _ in range(20):
        d = [rng.gauss(0, 1) for _ in range(rng.choice([6, 8, 10]))]
        cota = cm.cota_inferior(d)[2]
        assert _p_valor(d, cota - 1e-9) <= 0.05 < _p_valor(d, cota + 1e-9)
