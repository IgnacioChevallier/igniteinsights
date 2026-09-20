from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"

    firms_map_key: str = ""
    opentopography_api_key: str = ""

    database_url: str = "postgresql+asyncpg://igniteinsights:igniteinsights@localhost:5432/igniteinsights"

    # Forecast hours fetched per GFS cycle → one raster band each. Must cover the
    # simulation horizon: ELMFIRE holds the last band and freezes the weather beyond it
    # (see namelist_writer.validate_weather_coverage). GFS is hourly to f120, so 120 is
    # the ceiling for a single cycle; longer hindcasts need stitched cycles.
    gfs_forecast_hours: int = 24

    elmfire_runner_url: str = "http://localhost:8001"
    elmfire_runner_timeout: int = 300

    data_dir: str = "/app/data"
    raw_data_dir: str = "/app/data/raw"
    static_data_dir: str = "/app/data/static"
    elmfire_inputs_dir: str = "/app/data/elmfire/inputs"
    elmfire_outputs_dir: str = "/app/data/elmfire/outputs"

    # Union of the previous AOI and the Feb-2026 Los Alerces fire footprint, plus ~2 km of
    # margin so the front never reaches the domain edge. The validation dataset spans
    # lon -72.014..-71.201 and lat -42.818..-42.079 (../mask-dataset-gen/dataset/metadata.csv);
    # the old AOI stopped at -42.5 and only 70 of its 196 tiles were scorable.
    # ~7.8M cells at 30 m, up from ~2.0M. See ETAPA-A-BASELINE.md §A0.
    aoi_west: float = -72.05
    aoi_south: float = -42.90
    aoi_east: float = -71.15
    aoi_north: float = -42.05
    aoi_crs_processing: str = "EPSG:32719"
    aoi_crs_output: str = "EPSG:4326"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def resolve_data_path(path_str: str) -> Path:
    """Resolve a configured path, falling back to local ./data/ when running outside Docker."""
    p = Path(path_str)
    if p.exists():
        return p
    parts = p.parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "app" and parts[2] == "data":
        return Path.cwd() / "data" / Path(*parts[3:])
    return p
