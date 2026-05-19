from pydantic import BaseModel


class GFSCycleInfo(BaseModel):
    date: str        # YYYY-MM-DD
    cycle_hour: int  # 0, 6, 12, or 18
    fxx: int = 0     # forecast hour offset


class GFSVariableMetadata(BaseModel):
    variable: str    # e.g. "u10"
    asset_type: str  # e.g. "gfs_u10"
    file_path: str
    crs: str
    resolution_deg: float
    band_count: int
    dtype: str
    file_size_bytes: int
    cycle: str       # e.g. "2026051812"
    search_string: str
