"""siga.ordenes.especificaciones: declaracion del pedido en el item.

Revision ID: e6f7a8b9c2d3
Revises: d5e6f7a8b9c2
Create Date: 2026-07-31

La orden nombra el pedido en su CONCEPTO o en las ESPECIFICACIONES del item.
751 ordenes 2026 lo dicen SOLO en especificaciones ("SEGUN PEDIDO DE SERVICIO
N°0069") — el CONCEPTO trae solo el objeto ("SERVICIO DE REFERENCISTA..."). El
kanban solo tenia el concepto en el snapshot, asi que no resolvia el puente
pedido<->CCMN de esos casos y discrepaba del detalle (caso 69/S: detalle
`declarado` en cierre, kanban `sin_ccmn` en cuadro de necesidades).

Se agrega la columna al snapshot (poblada por el extractor _ORDENES con el
primer item) y `_cargar_declaraciones` parsea concepto Y especificaciones.
Requiere re-sync de siga.ordenes.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e6f7a8b9c2d3"
down_revision: str | None = "d5e6f7a8b9c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ordenes",
        sa.Column("especificaciones", sa.Text),
        schema="siga",
    )


def downgrade() -> None:
    op.drop_column("ordenes", "especificaciones", schema="siga")
