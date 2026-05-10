import uuid
from datetime import datetime

from pydantic import BaseModel


class FireDetectionOut(BaseModel):
    id: uuid.UUID
    longitude: float
    latitude: float
    bright_ti4: float | None
    frp: float | None
    confidence: str | None
    acq_datetime: datetime
    satellite: str | None
    daynight: str | None

    model_config = {"from_attributes": True}


class IngestionRunOut(BaseModel):
    id: uuid.UUID
    data_source_id: uuid.UUID
    aoi_id: uuid.UUID
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}


class RasterAssetOut(BaseModel):
    id: uuid.UUID
    ingestion_run_id: uuid.UUID | None
    asset_type: str
    file_path: str
    crs: str | None
    resolution_m: float | None
    file_size_bytes: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SimulationRunOut(BaseModel):
    id: uuid.UUID
    aoi_id: uuid.UUID
    status: str
    horizon_hours: int
    ignition_datetime: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}
