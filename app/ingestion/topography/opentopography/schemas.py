from pydantic import BaseModel


class BoundingBox(BaseModel):
    west: float
    south: float
    east: float
    north: float


class DEMDownloadRequest(BaseModel):
    dem_type: str = "COP30"
    bbox: BoundingBox
    output_format: str = "GTiff"


class DEMMetadata(BaseModel):
    file_path: str
    crs: str
    resolution_m: float
    band_count: int
    dtype: str
    file_size_bytes: int
    bbox: BoundingBox
