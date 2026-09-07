"""Uniform-value raster writers shared by the preparation pipeline and the playground.

ELMFIRE takes every input as a raster on the computational grid, so a "constant" input
(a spread-rate adjustment of 1.0, a synthetic flat slope) is written as a raster whose
cells all carry the same value. Both the real pipeline and the synthetic scenarios of
PLAYGROUND-SENSIBILIDAD.md need that, so it lives here rather than in either of them.
"""
from pathlib import Path

import numpy as np
import rasterio


def write_uniform_float(profile: dict, output: Path, value: float) -> Path:
    """Float32 raster whose cells all hold `value` (ws, wd, m1, m10, m100, adj, phi)."""
    return _write(profile, output, value, "float32", nodata=None)


def write_uniform_int16(profile: dict, output: Path, value: int) -> Path:
    """Int16 raster whose cells all hold `value` (dem, slp, asp, fbfm40, cc, ch, cbh, cbd).

    Values are written as ELMFIRE expects them on disk: `ch`/`cbh` pre-scaled to 10×metres
    and `cbd` to 100×kg/m³. Scaling is the caller's job — see
    .claude/skills/elmfire/references/interface-gotchas.md.
    """
    return _write(profile, output, value, "int16", nodata=None)


def write_uniform_from_reference(reference: Path, output: Path, value: float) -> Path:
    """Float32 uniform raster matching an existing raster's grid."""
    with rasterio.open(reference) as src:
        profile = src.meta.copy()
    return write_uniform_float(profile, output, value)


def _write(profile: dict, output: Path, value: float, dtype: str, nodata: float | None) -> Path:
    out = dict(profile)
    out.update(driver="GTiff", dtype=dtype, count=1, nodata=nodata)
    output.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output, "w", **out) as dst:
        dst.write(np.full((out["height"], out["width"]), value, dtype=dtype), 1)
    return output
