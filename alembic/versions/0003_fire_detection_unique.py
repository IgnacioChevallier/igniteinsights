"""Deduplicate fire_detections and add natural-key unique constraint

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-06

"""
from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Re-ingestions of overlapping FIRMS windows stored each detection multiple
    # times; keep one row per (geom, acq_datetime, satellite) before constraining.
    op.execute(
        """
        DELETE FROM fire_detections a
        USING fire_detections b
        WHERE a.ctid > b.ctid
          AND a.geom = b.geom
          AND a.acq_datetime = b.acq_datetime
          AND a.satellite IS NOT DISTINCT FROM b.satellite
        """
    )
    op.execute(
        """
        ALTER TABLE fire_detections
        ADD CONSTRAINT uq_fire_detection_natural_key
        UNIQUE NULLS NOT DISTINCT (geom, acq_datetime, satellite)
        """
    )


def downgrade() -> None:
    # Deleted duplicate rows are not restored.
    op.drop_constraint(
        "uq_fire_detection_natural_key", "fire_detections", type_="unique"
    )
