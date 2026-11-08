from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings

# Los tres productos de cobertura que pueden alimentar fbfm40.tif. Vive acá y no en la
# capa de API porque `settings.fuels_source` es el default de todos ellos: tiparlo como
# `str` obligaba a cada punto de uso a convivir con un valor que el tipo no garantizaba.
# Como Literal, un valor mal escrito en .env falla al levantar en vez de al construir el
# ráster.
FuelsSource = Literal["ccsbap", "mapbiomas", "worldcover"]


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
    # False: api and runner share /app/data (docker-compose). True: they don't (Railway),
    # so the client uploads inputs_dir and downloads outputs_dir around each run.
    elmfire_runner_transfer_files: bool = False

    data_dir: str = "/app/data"
    raw_data_dir: str = "/app/data/raw"
    static_data_dir: str = "/app/data/static"
    elmfire_inputs_dir: str = "/app/data/elmfire/inputs"
    elmfire_outputs_dir: str = "/app/data/elmfire/outputs"

    # Union of the previous AOI and the Feb-2026 Los Alerces fire footprint, plus ~2 km of
    # margin so the front never reaches the domain edge. The validation dataset spans
    # lon -72.014..-71.201 and lat -42.818..-42.079 (../mask-dataset-gen/dataset/metadata.csv);
    # the old AOI stopped at -42.5 and only 70 of its 196 tiles were scorable.
    # ~7.8M cells at 30 m, up from ~2.0M. See docs/arquitectura.md §A0.
    # South edge moved from -42.90 to -43.20 on 2026-09-26 (IGN-26 §Benchmark): the 2023
    # Población Rosales scar reaches -42.95 and its ignition sat 2 km from the old edge, and
    # the old box left out the southern half of the park. North and west edges unchanged,
    # so crop offsets of earlier preparations stay valid.
    # North edge moved from -42.05 to -41.90 on 2026-09-28 (RESULTADOS-CSS-BAP §2): the Las
    # Golondrinas 2021 scar reaches -42.006 and both documented ignitions sit north of the old
    # edge. This one does shift the grid origin: preparations made before it keep their own
    # grid (the benchmark cases carry theirs), new ones start 0.15° further north.
    aoi_west: float = -72.05
    aoi_south: float = -43.20
    aoi_east: float = -71.15
    aoi_north: float = -41.90
    # Fuente de cobertura con la que se construye fbfm40.tif. Entra en la clave de
    # caché del ráster, así que cambiarla lo regenera en vez de servir el anterior.
    # "ccsbap"     → CCS-BAP CIEFAP 2017, nivel 3
    #                  (docs/crosswalk.md)
    # "mapbiomas"  → MapBiomas Argentina Col. 2 2024 (docs/crosswalk.md)
    # "worldcover" → ESA WorldCover 2021, el baseline de comparación (ETAPA-A §A7)
    fuels_source: FuelsSource = "ccsbap"
    # Recorte al AOI de la capa vectorial de CCS-BAP, derivado con
    # scripts/prepare_ccsbap_aoi.py. Vive bajo data/ porque es lo único que el
    # contenedor del runner y de la API tienen montado.
    ccsbap_vector_path: str = "/app/data/raw/ccsbap/ccsbap_2017_aoi.gpkg"
    mapbiomas_raster_path: str = "/app/data/raw/mapbiomas/mapbiomas_2024_aoi.tif"
    # Hansen GFC v1.13 lossyear (40S_080W, una tesela cubre el AOI): sin dosel donde
    # hubo pérdida antes del año de la simulación
    # (docs/crosswalk.md). Si falta, se sigue sin ella.
    hansen_lossyear_path: str = (
        "/app/data/raw/hansen/Hansen_GFC-2025-v1.13_lossyear_40S_080W.tif"
    )
    # Años con quema según otras fuentes (dNBR ∪ MCD64A1, scripts/anio_quema.py; máscara de
    # bits, bit i = 2001 + i): las quemas posteriores al último año de Hansen y las no
    # forestales (docs/resultados/pronostico/areas-quemadas.md). Si falta, sólo Hansen.
    otras_quemas_path: str = "/app/data/raw/cicatrices/otras_quemas_ext.tif"
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
