"""Deteccion de resoluciones manuales obsoletas (§5.1)

Revision ID: c8d2e3f4a5b6
Revises: b7c1d2e3f4a5
Create Date: 2026-07-24 10:00:00

Contexto:
    Riesgo conocido (§5.1 del doc de refactorizacion): si SIGA agrega un CCMN
    a la bolsa DESPUES de una resolucion manual, la resolucion sigue ahi sin
    avisar. El funcionario asocio pensando que habia 3 candidatos, y ahora hay
    4 — puede que el nuevo sea el correcto y nadie lo note.

    Se guarda la foto de los candidatos AL MOMENTO de resolver, y un job (punto
    9 del plan) la compara contra los candidatos actuales de la bolsa. Si
    cambiaron, marca la resolucion para revision — nunca la revoca sola: quitar
    el juicio de un humano sin avisar seria el mismo fallo silencioso que este
    trabajo evita.

    En el punto 5 esa foto se guardaba solo en logs.auditoria. Auditoria es
    append-only y consultarla por cada resolucion es fragil; la foto vive ahora
    en la propia fila, que es donde el job la necesita.

Ref: Docs/diagnostico-2026-07-20/refactorizacion-pipeline-pedido-ccmn.md §5.1
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c8d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b7c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Foto de los candidatos de la bolsa cuando se creo la resolucion. El job
    # compara contra los actuales; si difieren, la bolsa cambio.
    op.add_column(
        "resolucion_pedido_ccmn",
        sa.Column(
            "candidatos_al_crear",
            postgresql.ARRAY(sa.Integer),
            nullable=False,
            server_default="{}",
        ),
        schema="sistema",
    )
    # Cuando el job detecta que la bolsa cambio, sella aqui la fecha. NULL =
    # vigente. Se muestra en la UI como aviso, no revoca la resolucion.
    op.add_column(
        "resolucion_pedido_ccmn",
        sa.Column(
            "revision_pendiente_desde",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        schema="sistema",
    )
    # Candidatos que el job vio la ultima vez que marco para revision. Deja
    # ver QUE cambio (aparecio el CCMN 2999), no solo que algo cambio.
    op.add_column(
        "resolucion_pedido_ccmn",
        sa.Column(
            "candidatos_en_revision",
            postgresql.ARRAY(sa.Integer),
            nullable=True,
        ),
        schema="sistema",
    )

    # Solo las activas pendientes de revision — es lo que la UI lista arriba.
    op.execute(
        """
        CREATE INDEX ix_resolucion_revision_pendiente
        ON sistema.resolucion_pedido_ccmn (ano_eje, sec_ejec)
        WHERE revocado_en IS NULL AND revision_pendiente_desde IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_resolucion_revision_pendiente",
        table_name="resolucion_pedido_ccmn",
        schema="sistema",
    )
    for col in ("candidatos_en_revision", "revision_pendiente_desde",
                "candidatos_al_crear"):
        op.drop_column("resolucion_pedido_ccmn", col, schema="sistema")
