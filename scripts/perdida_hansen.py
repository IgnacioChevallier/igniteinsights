"""Hansen GFC v1.13 `lossyear` en las grillas de los paquetes v5.

Ver docs/crosswalk.md.

Vecino más cercano (es una capa de años). Sale en data/static/canopy/ y entra a los
protocolos `-x2` como `lossyear.tif` por el empaquetador `ampliar_mapas`; la perilla
`dosel_sin_perdida_previa` lo usa.

    curl -o data/raw/hansen/Hansen_GFC-2025-v1.13_lossyear_40S_080W.tif \\
      https://storage.googleapis.com/earthenginepartners-hansen/GFC-2025-v1.13/Hansen_GFC-2025-v1.13_lossyear_40S_080W.tif
    uv run python scripts/perdida_hansen.py
"""
from pathlib import Path

from app.elmfire.builder.canopy_builder import reproject_canopy

CRUDO = Path("data/raw/hansen/Hansen_GFC-2025-v1.13_lossyear_40S_080W.tif")
GRILLAS = {"aoi": Path("data/elmfire/inputs/benchmark-aoi-asp3-v5/dem.tif"),
           "ext": Path("data/elmfire/inputs/benchmark-2026-09-28-asp3-v5/dem.tif")}

if __name__ == "__main__":
    for nombre, dem in GRILLAS.items():
        salida = Path(f"data/static/canopy/hansen_lossyear_v113_{nombre}.tif")
        reproject_canopy(CRUDO, dem, salida, resampling="nearest")
        print(salida)
