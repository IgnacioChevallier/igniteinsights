from pydantic import BaseModel


class WorldCoverTile(BaseModel):
    tile_id: str  # e.g. "S45W072"
    url: str


class WorldCoverMetadata(BaseModel):
    file_path: str
    crs: str
    version: str
    year: str
    tiles_used: list[str]
    band_count: int
    dtype: str
    file_size_bytes: int
    resolution_m: float = 10.0
