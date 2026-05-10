"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-10

"""
from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "areas_of_interest",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(geometry_type="POLYGON", srid=4326),
            nullable=False,
        ),
        sa.Column("crs_processing", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "data_sources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("data_source_id", sa.UUID(), nullable=False),
        sa.Column("aoi_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["aoi_id"], ["areas_of_interest.id"]),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "fire_detections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ingestion_run_id", sa.UUID(), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326),
            nullable=False,
        ),
        sa.Column("bright_ti4", sa.Float(), nullable=True),
        sa.Column("frp", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Text(), nullable=True),
        sa.Column("acq_datetime", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("satellite", sa.Text(), nullable=True),
        sa.Column("daynight", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_fire_detections_geom", "fire_detections", ["geom"], postgresql_using="gist"
    )
    op.create_index("idx_fire_detections_acq", "fire_detections", ["acq_datetime"])

    op.create_table(
        "raster_assets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ingestion_run_id", sa.UUID(), nullable=True),
        sa.Column("asset_type", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("crs", sa.Text(), nullable=True),
        sa.Column("resolution_m", sa.Float(), nullable=True),
        sa.Column(
            "bbox",
            geoalchemy2.types.Geometry(geometry_type="POLYGON", srid=4326),
            nullable=True,
        ),
        sa.Column("band_count", sa.Integer(), nullable=True),
        sa.Column("dtype", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ingestion_run_id", "asset_type", name="uq_raster_run_type"),
    )

    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("aoi_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("horizon_hours", sa.Integer(), nullable=False),
        sa.Column("ignition_datetime", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("elmfire_config", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("output_dir", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["aoi_id"], ["areas_of_interest.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "simulation_outputs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("simulation_id", sa.UUID(), nullable=False),
        sa.Column("output_type", sa.Text(), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(geometry_type="MULTIPOLYGON", srid=4326),
            nullable=True,
        ),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("valid_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulation_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("simulation_outputs")
    op.drop_table("simulation_runs")
    op.drop_table("raster_assets")
    op.drop_index("idx_fire_detections_acq", table_name="fire_detections")
    op.drop_index("idx_fire_detections_geom", table_name="fire_detections")
    op.drop_table("fire_detections")
    op.drop_table("ingestion_runs")
    op.drop_table("data_sources")
    op.drop_table("areas_of_interest")
