from pydantic import BaseModel


class CanopyTile(BaseModel):
    tile_id: str
    url: str


class CanopyLayerMetadata(BaseModel):
    file_path: str
    crs: str
    band_count: int
    dtype: str
    file_size_bytes: int
    resolution_m: float
    source: str
    version: str
    tile_ids: list[str]
