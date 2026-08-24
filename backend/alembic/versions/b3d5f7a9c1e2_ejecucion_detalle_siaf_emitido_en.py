"""siaf.ejecucion_detalle_siaf: fecha de emision del reporte Formato A.

Revision ID: b3d5f7a9c1e2
Revises: a2c4e6f8b0d1
Create Date: 2026-08-19

Contexto:
    El Formato A trae en su cabecera la fecha/hora de emision del reporte. El
    mes de corte del Formato A puede diferir del snapshot MEF, asi que la UI
    debe rotular el dato con esa fecha (plan-trazabilidad-siaf-formato-a §2
    regla 6). El parser ya la extrae (`cabecera.emitido_en`); esta columna la
    persiste para poder mostrarla junto al detalle.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b3d5f7a9c1e2"
down_revision: str | Sequence[str] | None = "a2c4e6f8b0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ejecucion_detalle_siaf",
        sa.Column("emitido_en", sa.TIMESTAMP(timezone=True), nullable=True),
        schema="siaf",
    )


def downgrade() -> None:
    op.drop_column("ejecucion_detalle_siaf", "emitido_en", schema="siaf")
