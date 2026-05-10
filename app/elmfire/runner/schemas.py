from pydantic import BaseModel


class SimulationRequest(BaseModel):
    elmfire_data_path: str
    inputs_dir: str
    outputs_dir: str
    simulation_hours: int = 3


class SimulationOutputPaths(BaseModel):
    isochrones_shp: str | None = None
    time_of_arrival_tif: str | None = None
    flame_length_tifs: list[str] = []


class SimulationResult(BaseModel):
    status: str
    run_id: str
    outputs: SimulationOutputPaths
