"""inversiones: agregar campos alta prioridad Invierte.pe

Revision ID: 0004_inversiones_alta_prioridad
Revises: 36ad7695cdfb
Create Date: 2026-07-13

Campos nuevos: pia_anio_actual, num_habitantes_benef, registrado_pmi,
pmi_anio_1..4, ult_fec_decla_estim.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_inversiones_alta_prioridad"
down_revision: str | Sequence[str] | None = "36ad7695cdfb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "inversiones",
        sa.Column("pia_anio_actual", sa.Numeric(18, 2), nullable=True),
        schema="siaf",
    )
    op.add_column(
        "inversiones",
        sa.Column("num_habitantes_benef", sa.Integer, nullable=True),
        schema="siaf",
    )
    op.add_column(
        "inversiones",
        sa.Column("registrado_pmi", sa.CHAR(2), nullable=True),
        schema="siaf",
    )
    op.add_column(
        "inversiones",
        sa.Column("pmi_anio_1", sa.Numeric(18, 2), nullable=True),
        schema="siaf",
    )
    op.add_column(
        "inversiones",
        sa.Column("pmi_anio_2", sa.Numeric(18, 2), nullable=True),
        schema="siaf",
    )
    op.add_column(
        "inversiones",
        sa.Column("pmi_anio_3", sa.Numeric(18, 2), nullable=True),
        schema="siaf",
    )
    op.add_column(
        "inversiones",
        sa.Column("pmi_anio_4", sa.Numeric(18, 2), nullable=True),
        schema="siaf",
    )
    op.add_column(
        "inversiones",
        sa.Column("ult_fec_decla_estim", sa.Date, nullable=True),
        schema="siaf",
    )


def downgrade() -> None:
    for col in [
        "ult_fec_decla_estim",
        "pmi_anio_4",
        "pmi_anio_3",
        "pmi_anio_2",
        "pmi_anio_1",
        "registrado_pmi",
        "num_habitantes_benef",
        "pia_anio_actual",
    ]:
        op.drop_column("inversiones", col, schema="siaf")
