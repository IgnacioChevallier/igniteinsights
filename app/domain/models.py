import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class AreaOfInterest(Base):
    __tablename__ = "areas_of_interest"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    geom = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    crs_processing: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    ingestion_runs: Mapped[list["IngestionRun"]] = relationship(back_populates="aoi")
    simulation_runs: Mapped[list["SimulationRun"]] = relationship(back_populates="aoi")


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    ingestion_runs: Mapped[list["IngestionRun"]] = relationship(back_populates="data_source")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False
    )
    aoi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("areas_of_interest.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)  # pending|running|success|failed
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    data_source: Mapped["DataSource"] = relationship(back_populates="ingestion_runs")
    aoi: Mapped["AreaOfInterest"] = relationship(back_populates="ingestion_runs")
    fire_detections: Mapped[list["FireDetection"]] = relationship(back_populates="ingestion_run")
    raster_assets: Mapped[list["RasterAsset"]] = relationship(back_populates="ingestion_run")


class FireDetection(Base):
    __tablename__ = "fire_detections"
    __table_args__ = (
        # Natural key of one VIIRS detection — re-ingesting an overlapping FIRMS
        # window must not duplicate rows (inserts use ON CONFLICT DO NOTHING).
        UniqueConstraint(
            "geom",
            "acq_datetime",
            "satellite",
            name="uq_fire_detection_natural_key",
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_runs.id"), nullable=False
    )
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    bright_ti4: Mapped[float | None] = mapped_column(Float)
    frp: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[str | None] = mapped_column(Text)
    acq_datetime: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    satellite: Mapped[str | None] = mapped_column(Text)
    daynight: Mapped[str | None] = mapped_column(Text)

    ingestion_run: Mapped["IngestionRun"] = relationship(back_populates="fire_detections")


class RasterAsset(Base):
    __tablename__ = "raster_assets"
    __table_args__ = (
        UniqueConstraint("ingestion_run_id", "asset_type", name="uq_raster_run_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_runs.id")
    )
    asset_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    crs: Mapped[str | None] = mapped_column(Text)
    resolution_m: Mapped[float | None] = mapped_column(Float)
    bbox = mapped_column(Geometry("POLYGON", srid=4326))
    band_count: Mapped[int | None] = mapped_column(Integer)
    dtype: Mapped[str | None] = mapped_column(Text)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    valid_time: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    ingestion_run: Mapped["IngestionRun | None"] = relationship(back_populates="raster_assets")


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    aoi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("areas_of_interest.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    horizon_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    ignition_datetime: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    elmfire_config: Mapped[dict | None] = mapped_column(JSONB)
    output_dir: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)

    aoi: Mapped["AreaOfInterest"] = relationship(back_populates="simulation_runs")
    outputs: Mapped[list["SimulationOutput"]] = relationship(back_populates="simulation")


class SimulationOutput(Base):
    __tablename__ = "simulation_outputs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    simulation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_runs.id"), nullable=False
    )
    output_type: Mapped[str] = mapped_column(Text, nullable=False)
    geom = mapped_column(Geometry("MULTIPOLYGON", srid=4326))
    file_path: Mapped[str | None] = mapped_column(Text)
    valid_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    simulation: Mapped["SimulationRun"] = relationship(back_populates="outputs")


class Operativo(Base):
    """El modo que ven todos los clientes (`demo` con `reloj` congelado, o `vivo`)."""

    __tablename__ = "operativo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    modo: Mapped[str] = mapped_column(Text, nullable=False, default="demo")
    reloj: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    calcular_ensamble: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Corte de la demo: detecciones anteriores no agrupan ni siembran (scripts/demo_operativo.py).
    demo_desde: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    actualizado_en: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Pronostico(Base):
    """Una ventana P-24 de un incendio: la pasada VIIRS que la siembra y cuándo se pudo ver."""

    __tablename__ = "pronosticos"
    __table_args__ = (
        UniqueConstraint("modo", "incendio_id", "pasada", name="uq_pronostico_pasada"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    modo: Mapped[str] = mapped_column(Text, nullable=False)
    incendio_id: Mapped[str] = mapped_column(Text, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    pasada: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    disponible: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    ciclo_gfs: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    estado: Mapped[str] = mapped_column(Text, nullable=False)  # corriendo|listo|fallido
    error: Mapped[str | None] = mapped_column(Text)
    simulacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_runs.id")
    )
    caja = mapped_column(Geometry("POLYGON", srid=4326))
    creado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
