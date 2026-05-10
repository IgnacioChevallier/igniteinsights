from datetime import datetime

from pydantic import BaseModel
from shapely.geometry import Point


class FireDetectionNormalized(BaseModel):
    geom: object  # shapely Point — converted to WKB before DB insert
    bright_ti4: float
    frp: float
    confidence: str
    acq_datetime: datetime
    satellite: str
    daynight: str

    model_config = {"arbitrary_types_allowed": True}
