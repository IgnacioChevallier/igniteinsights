"""Deduplicate areas_of_interest and make name unique

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-28

"""
from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # On a fresh DB, /ingestion/run starts every source in parallel and each one found
    # no AOI and created its own "Los Alerces" row; after that every lookup by name
    # raised MultipleResultsFound. Keep the oldest row per name and repoint references.
    op.execute(
        """
        CREATE TEMP TABLE aoi_dupes ON COMMIT DROP AS
        SELECT id, first_value(id) OVER (
            PARTITION BY name ORDER BY created_at, id
        ) AS keep_id
        FROM areas_of_interest
        """
    )
    for table in ("ingestion_runs", "simulation_runs"):
        op.execute(
            f"""
            UPDATE {table} t SET aoi_id = d.keep_id
            FROM aoi_dupes d
            WHERE t.aoi_id = d.id AND d.id <> d.keep_id
            """
        )
    op.execute(
        """
        DELETE FROM areas_of_interest a
        USING aoi_dupes d
        WHERE a.id = d.id AND d.id <> d.keep_id
        """
    )
    op.create_unique_constraint("uq_areas_of_interest_name", "areas_of_interest", ["name"])


def downgrade() -> None:
    # Deleted duplicate rows are not restored.
    op.drop_constraint("uq_areas_of_interest_name", "areas_of_interest", type_="unique")
