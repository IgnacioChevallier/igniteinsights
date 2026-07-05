"""Add valid_time to raster_assets

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-05

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "raster_assets",
        sa.Column("valid_time", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_raster_assets_valid_time", "raster_assets", ["valid_time"]
    )


def downgrade() -> None:
    op.drop_index("idx_raster_assets_valid_time", table_name="raster_assets")
    op.drop_column("raster_assets", "valid_time")
