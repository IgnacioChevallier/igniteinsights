"""Domain-mean wind per hourly band, for the map's wind animation.

GFS is 0.25° — about 27 km — so an AOI of this size spans one or two source cells and the
wind really is close to uniform across it. That is what makes a single drifting-particle
field an honest picture of the real wind rather than a smoothing of something that varies:
each band carries its own `direction_consistency` so the claim stays checkable instead of
assumed. Measured on a real 24 h run it sits at 0.99 whenever the wind is above ~2 mph and
collapses only in the calm hours, where the direction of a 0.5 mph wind means nothing
anyway — which is why this is per band and not one number for the cube. A single minimum
made a well-behaved field look broken.

Reading the *inputs* rather than the raw GFS assets is deliberate: ws.tif/wd.tif are what
ELMFIRE was actually given, already reprojected and clipped, so the arrows on the map
cannot disagree with the wind the run was driven by.
"""
import logging
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform as warp_transform

logger = logging.getLogger(__name__)

# Spanish 8-point compass. A still screenshot has to be readable on its own: "hacia el SO"
# says in two characters what an animation cannot say once it stops moving.
_COMPASS = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]


def compass_point(azimuth_deg: float) -> str:
    return _COMPASS[int((azimuth_deg % 360.0) / 45.0 + 0.5) % 8]


def wind_bands(ws_path: Path, wd_path: Path) -> dict:
    """Per-band mean speed and blowing-to azimuth, plus the domain ring in EPSG:4326.

    One band at a time. Reading both cubes whole and promoting them to float64 allocated
    ~1.6 GB each, and the `u`/`v` components another four arrays of that size — about 13 GB
    of peak for a result that is two floats per hour. That did not raise, it killed the
    API process, which took the isochrone and ignition requests down with it and left the
    panel with nothing to draw. Nothing here ever needed more than one band at a time.
    """
    with rasterio.open(ws_path) as ws_src, rasterio.open(wd_path) as wd_src:
        if ws_src.crs is None:
            raise ValueError(f"{ws_path} has no CRS")
        if (ws_src.count, ws_src.shape) != (wd_src.count, wd_src.shape):
            raise ValueError(
                f"ws {(ws_src.count, *ws_src.shape)} and wd {(wd_src.count, *wd_src.shape)} "
                "are not on the same grid"
            )
        bounds, crs = ws_src.bounds, ws_src.crs

        bands: list[dict] = []
        for i in range(ws_src.count):
            ws = ws_src.read(i + 1, masked=True).astype("float64")
            wd = wd_src.read(i + 1, masked=True).astype("float64")

            # wd holds the direction the wind comes FROM (meteorological convention, the
            # same one ELMFIRE reads). The animation draws where it goes, so the unit
            # vector is negated.
            theta = np.radians(wd)
            speed = float(np.ma.mean(ws))
            mean_u = float(np.ma.mean(ws * -np.sin(theta)))
            mean_v = float(np.ma.mean(ws * -np.cos(theta)))
            if not math.isfinite(speed) or not math.isfinite(mean_u):
                continue
            # Scalar mean for the speed — what a station would read — and the vector mean
            # for the direction, which is the only correct way to average an angle.
            blows_to = math.degrees(math.atan2(mean_u, mean_v)) % 360.0
            bands.append({
                "hour": i,
                "speed_mph": round(speed, 2),
                "blows_to_deg": round(blows_to, 1),
                # Comma decimal, like every other number this UI shows.
                "label": (
                    f"viento {speed:.1f}".replace(".", ",")
                    + f" mph hacia el {compass_point(blows_to)}"
                ),
                # 1.0 = every cell points the same way; below ~0.9 this band's arrow is an
                # average rather than the wind. Calm hours land there and that is expected.
                "direction_consistency": round(math.hypot(mean_u, mean_v) / speed, 3)
                if speed > 0
                else 1.0,
            })

    xs = [bounds.left, bounds.right, bounds.right, bounds.left, bounds.left]
    ys = [bounds.top, bounds.top, bounds.bottom, bounds.bottom, bounds.top]
    lons, lats = warp_transform(crs, "EPSG:4326", xs, ys)

    logger.info("Wind field: %d bands from %s", len(bands), ws_path.name)
    return {
        "ring": [[lon, lat] for lon, lat in zip(lons, lats)],
        "bands": bands,
    }
