from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"

    firms_map_key: str = ""
    opentopography_api_key: str = ""

    database_url: str = "postgresql+asyncpg://igniteinsights:igniteinsights@localhost:5432/igniteinsights"

    elmfire_runner_url: str = "http://localhost:8001"
    elmfire_runner_timeout: int = 300

    data_dir: str = "/app/data"
    raw_data_dir: str = "/app/data/raw"
    processed_data_dir: str = "/app/data/processed"
    elmfire_inputs_dir: str = "/app/data/elmfire/inputs"
    elmfire_outputs_dir: str = "/app/data/elmfire/outputs"

    aoi_west: float = -72.0
    aoi_south: float = -42.9
    aoi_east: float = -71.5
    aoi_north: float = -42.5
    aoi_crs_processing: str = "EPSG:32719"
    aoi_crs_output: str = "EPSG:4326"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
