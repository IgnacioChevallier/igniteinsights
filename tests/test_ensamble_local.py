"""El circuito del ensamble local: exportar → correr → registrar (scripts/ensamble_*.py)."""
import base64
import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin


def _script(nombre: str):
    ruta = Path(__file__).parents[1] / "scripts" / f"{nombre}.py"
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


def _contrato(validos: int) -> dict:
    return {"layer": {"id": "ensemble_agreement"},
            "metadata": {"valid_members": validos, "expected_members": 31},
            "thresholds": [{"value": 0.5}]}


def test_registrar_valida_el_contrato():
    validar = _script("ensamble_registrar").validar
    assert validar(_contrato(31))["valid_members"] == 31
    with pytest.raises(ValueError, match="mínimo"):
        validar(_contrato(10))
    with pytest.raises(ValueError, match="layer.id"):
        validar({**_contrato(31), "layer": {"id": "isochrones"}})
    with pytest.raises(ValueError, match="umbrales"):
        validar({**_contrato(31), "thresholds": []})


def test_paquete_lleva_la_ventana_y_los_insumos(tmp_path):
    pasada = datetime(2026, 1, 5, 19, 20, tzinfo=UTC)
    p = SimpleNamespace(id="p1", simulacion_id="s1", nombre="Patriada", modo="demo",
                        pasada=pasada, ciclo_gfs=datetime(2026, 1, 5, 18, tzinfo=UTC))
    (tmp_path / "phi.tif").write_bytes(b"phi")
    (tmp_path / "fbfm40.tif").write_bytes(b"fbfm")
    paq = _script("ensamble_exportar").paquete(p, [-71.6, -42.2, -71.4, -42.0], tmp_path)
    assert paq["t0"] == "2026-01-05T19:00:00+00:00"
    assert paq["tstart_s"] == 1200.0
    assert {n: base64.b64decode(b) for n, b in paq["insumos_b64"].items()} == {
        "fbfm40.tif": b"fbfm", "phi.tif": b"phi"}


def _tif(path: Path, x0: float) -> Path:
    with rasterio.open(path, "w", driver="GTiff", height=4, width=4, count=1, dtype="float32",
                       crs="EPSG:32719", transform=from_origin(x0, 5300000, 30, 30)) as dst:
        dst.write(np.zeros((1, 4, 4), dtype="float32"))
    return path


def test_local_aborta_si_los_estaticos_caen_en_otra_grilla(tmp_path):
    misma_grilla = _script("ensamble_local").misma_grilla
    dem = _tif(tmp_path / "dem.tif", 500000)
    misma_grilla(dem, _tif(tmp_path / "phi.tif", 500000))
    with pytest.raises(ValueError, match="no coincide"):
        misma_grilla(dem, _tif(tmp_path / "otro.tif", 500030))
