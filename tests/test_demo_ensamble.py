"""La elección de pasos del ensamble de la demo (scripts/demo_ensamble.py)."""
from scripts.demo_ensamble import elegir


def test_la_primera_pasada_mas_las_dos_que_mas_crecen_en_orden():
    # La primera no compite aunque crezca poco; una sin estadísticas (4) no entra.
    crecimiento = {0: 5.0, 1: 300.0, 2: 10.0, 3: 900.0, 5: 120.0}
    assert elegir([0, 1, 2, 3, 4, 5], crecimiento) == [0, 1, 3]
