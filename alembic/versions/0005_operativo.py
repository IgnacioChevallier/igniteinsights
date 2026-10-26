"""Modo operativo: estado global (demo / vivo) y pronósticos por pasada

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Una sola fila: el modo que ven todos los clientes y el reloj de la demostración.
    op.create_table(
        "operativo",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("modo", sa.Text, nullable=False, server_default="demo"),
        sa.Column("reloj", sa.TIMESTAMP(timezone=True)),
        sa.Column("calcular_ensamble", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("actualizado_en", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="ck_operativo_una_fila"),
        sa.CheckConstraint("modo IN ('demo', 'vivo')", name="ck_operativo_modo"),
    )
    op.execute("INSERT INTO operativo (id) VALUES (1)")

    op.create_table(
        "pronosticos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("modo", sa.Text, nullable=False),
        sa.Column("incendio_id", sa.Text, nullable=False),
        sa.Column("nombre", sa.Text, nullable=False),
        sa.Column("pasada", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("disponible", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ciclo_gfs", sa.TIMESTAMP(timezone=True)),
        sa.Column("estado", sa.Text, nullable=False),
        sa.Column("error", sa.Text),
        sa.Column("simulacion_id", UUID(as_uuid=True), sa.ForeignKey("simulation_runs.id")),
        sa.Column("caja", Geometry("POLYGON", srid=4326)),
        sa.Column("creado_en", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        # Un tick repetido no vuelve a correr la misma pasada del mismo incendio.
        sa.UniqueConstraint("modo", "incendio_id", "pasada", name="uq_pronostico_pasada"),
    )
    op.create_index("idx_pronosticos_disponible", "pronosticos", ["modo", "disponible"])


def downgrade() -> None:
    op.drop_table("pronosticos")
    op.drop_table("operativo")
