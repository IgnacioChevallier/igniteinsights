"""Dead-fuel moisture with drying history: each class lags the EMC by its own time-lag."""
import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.elmfire.builder import weather_builder as wb


def _series(path, values):
    """A 2×2 GFS-like series, one band per hour, same value everywhere."""
    with rasterio.open(path, "w", driver="GTiff", height=2, width=2, count=len(values),
                       dtype="float32", crs="EPSG:4326",
                       transform=from_origin(-72.0, -42.0, 0.25, 0.25)) as dst:
        dst.write(np.stack([np.full((2, 2), v, dtype="float32") for v in values]))
    return path


def _media(path, banda):
    with rasterio.open(path) as src:
        return float(src.read(banda).mean())


def test_timelag(tmp_path):
    ref = _series(tmp_path / "ref.tif", [0.0])
    horas = 400
    t2m = _series(tmp_path / "t2m.tif", [300.0] * horas)          # ~80 °F
    # 300 h húmedas (RH 80 %) y después 100 h secas (RH 15 %).
    rh = _series(tmp_path / "rh.tif", [80.0] * 300 + [15.0] * 100)
    m1, m10, m100 = wb.derive_moisture_timelag(t2m, rh, ref, tmp_path / "out", skip_bands=290)

    emc_humeda = float(wb._nelson_emc(np.array([80.6]), np.array([80.0]))[0])
    emc_seca = float(wb._nelson_emc(np.array([80.6]), np.array([15.0]))[0])
    # Antes del cambio, tras 290 h de spin-up constante, las tres clases están en equilibrio.
    for m in (m1, m10, m100):
        assert abs(_media(m, 1) - emc_humeda) < 0.2
    # 10 h después del secado: m1 ya lo siguió, m100 casi no se movió.
    banda = 300 - 290 + 10 + 1
    assert abs(_media(m1, banda) - emc_seca) < 0.1
    assert _media(m10, banda) > emc_seca + 0.3 * (emc_humeda - emc_seca)
    assert _media(m100, banda) > emc_seca + 0.85 * (emc_humeda - emc_seca)
