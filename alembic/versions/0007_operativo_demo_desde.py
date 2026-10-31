"""Operativo: corte de detecciones de la demo

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-31

`tick` y `estado` tienen que agrupar las mismas detecciones: el id de un incendio sale de su
primera detección. Antes el corte vivía sólo en el script de precarga y el panel no encontraba
los pronósticos de la demo.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("operativo", sa.Column("demo_desde", sa.TIMESTAMP(timezone=True)))


def downgrade() -> None:
    op.drop_column("operativo", "demo_desde")
