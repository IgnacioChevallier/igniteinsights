"""Scenario definition for the synthetic playground.

A scenario is a set of scalars and nothing else. Every ELMFIRE input becomes a uniform
raster over a square domain, so the only thing that varies between two runs is the
parameter under study — that is what makes the comparison attributable.

Almost no spatially-varying fields: a scenario with gradients stops being a controlled
base case and becomes the real AOI. See docs/historico/PLAYGROUND-SENSIBILIDAD.md §P1.

The single exception is `terrain`, which is itself one of the factors under study — "what
does an unburnable barrier do to the front?" is only answerable with a domain that has
one. It is therefore held to the same rule as every other factor: vary it between A and B
with everything else fixed, never alongside a second change.
"""
from typing import Literal

from pydantic import BaseModel, Field


class Scenario(BaseModel):
    name: str = Field(default="custom", max_length=80)
    description: str = Field(default="", max_length=500)

    # ── Domain ────────────────────────────────────────────────────────────────
    cellsize_m: float = Field(default=30.0, gt=0, le=500)
    domain_size_m: float = Field(default=12000.0, gt=0, le=60000)

    # ── Topography ────────────────────────────────────────────────────────────
    slope_deg: int = Field(default=0, ge=0, le=80)
    aspect_deg: int = Field(default=0, ge=0, lt=360, description="Downslope azimuth")
    elevation_m: int = Field(default=0, ge=-500, le=9000)

    # ── Fuel ──────────────────────────────────────────────────────────────────
    fbfm40_code: int = Field(default=102, description="Must exist in fuel_models.csv")
    terrain: Literal["uniform", "lake"] = Field(
        default="uniform",
        description=(
            "Layout of the fuel slab. 'uniform' is one fuel model everywhere. 'lake' cuts "
            "a circular patch of FBFM 98 (NB8, water) out of it, placed in the fire's "
            "path, so the run shows what an unburnable barrier does to the front."
        ),
    )

    # ── Canopy (ELMFIRE on-disk encoding is applied by the builder) ───────────
    cc_pct: int = Field(default=0, ge=0, le=100)
    ch_m: float = Field(default=0.0, ge=0, le=100)
    cbh_m: float = Field(default=0.0, ge=0, le=100)
    cbd_kg_m3: float = Field(default=0.0, ge=0, le=5)

    # ── Weather ───────────────────────────────────────────────────────────────
    wind_speed_mph: float = Field(default=0.0, ge=0, le=100)
    wind_direction_deg: float = Field(
        default=0.0, ge=0, lt=360,
        description=(
            "Direction the wind blows FROM, degrees from north (meteorological "
            "convention). Verified against ELMFIRE 2025.0212 elmfire_subs.f90:473, which "
            "computes the blowing-toward direction as WD + 180. So 0 = wind from the "
            "north and the fire elongates SOUTH."
        ),
    )
    m1_pct: float = Field(default=3.0, ge=1, le=60)
    m10_pct: float = Field(default=4.0, ge=1, le=60)
    m100_pct: float = Field(default=5.0, ge=1, le=60)
    lh_moisture_pct: float = Field(default=30.0, ge=1, le=300)
    lw_moisture_pct: float = Field(default=60.0, ge=1, le=300)

    # ── Run control ───────────────────────────────────────────────────────────
    tstop_s: float = Field(default=19800.0, gt=0, le=604800)
    dtdump_s: float = Field(default=3600.0, gt=0)
    adj: float = Field(default=1.0, gt=0, le=10)

    # ── Ignition ──────────────────────────────────────────────────────────────
    ignition_radius_m: float = Field(default=60.0, gt=0, le=5000)

    @property
    def horizon_hours(self) -> int:
        """Whole hours, rounded up: the namelist writer takes an int."""
        return max(1, -(-int(self.tstop_s) // 3600))
