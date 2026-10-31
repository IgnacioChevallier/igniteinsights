"""Nombre del resumen de `benchmark.py pronostico` en benchmarks/diagnosticos/."""
from scripts import benchmark


def test_un_protocolo_conserva_el_nombre():
    ruta = benchmark._ruta_resumen(
        ["epuyen-2025/pronostico-v7", "los-alerces-2024/pronostico-v7"],
        "lw-100-obs-001", "cadena", 12)
    assert ruta.name == "pronostico-v7-lw-100-obs-001-cadena-12h.json"


def test_protocolos_mezclados_no_pisan_el_de_uno_solo():
    mezclados = benchmark._ruta_resumen(
        ["el-turbio-2025/pronostico-ciclo-v7", "epuyen-2019/pronostico-v7"],
        "lw-100-obs-001", "cadena", 12)
    solo = benchmark._ruta_resumen(
        ["el-turbio-2025/pronostico-ciclo-v7"], "lw-100-obs-001", "cadena", 12)
    assert mezclados != solo
    assert "pronostico-ciclo-v7" in mezclados.name and "pronostico-v7" in mezclados.name
