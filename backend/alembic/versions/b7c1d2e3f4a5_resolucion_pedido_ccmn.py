"""Resolucion manual pedido <-> CCMN (referencial, opcional, N:M)

Revision ID: b7c1d2e3f4a5
Revises: a1b2c3d4e5f6
Create Date: 2026-07-22 17:30:00

Contexto:
    SIGA no registra que CCMN corresponde a que pedido: logistica copia los
    datos del pedido a un CCMN nuevo y no los vincula (confirmado con un
    funcionario que ejecuta el proceso). Cuando la bolsa SEC_CUA_MOD_SAL
    agrupa varios pedidos hay N candidatos y ninguno es "el" del pedido.

    La cascada automatica ya resuelve el 95.5% de bienes y 88.7% de servicios
    (niveles unico/declarado/declarado_cert). Esta tabla cubre el resto:
    158 ambiguos + 4 conflictos que solo un humano puede decidir.

Decisiones de diseno (doc §5):
    - REFERENCIAL, no vinculante: el sistema funciona sin ninguna fila aqui.
      Si se borran todas, solo se pierde precision en los `ambiguo`.
    - N:M en ambas direcciones: un CCMN puede consolidar varios pedidos, y un
      pedido varios CCMN. Una fila POR PAR. El mismo CCMN en dos pedidos
      distintos ES VALIDO y no se advierte.
    - Nunca se borra, se REVOCA. `revocado_en` preserva el historial; el
      UNIQUE con NULLS NOT DISTINCT deja un solo par activo pero muchos
      revocados. (Requiere PG15+; el proyecto corre PG16.)
    - Llave del pedido = TIPO_BIEN + TIPO_PEDIDO + NRO_PEDIDO (doc §6):
      NRO_PEDIDO solo no es unico -- 446 colisiones en 2026.
    - Escribe en PostgreSQL, jamas en SIGA (regla 2 del proyecto).

    `sec_cua_mod_sal` (la bolsa) se guarda para auditar el contexto: permite
    detectar despues si SIGA agrego candidatos a la bolsa tras la resolucion
    (obsolescencia silenciosa, §5.1 / punto 9 del plan).

Ref: Docs/diagnostico-2026-07-20/refactorizacion-pipeline-pedido-ccmn.md §5
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resolucion_pedido_ccmn",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        # ── Identidad del pedido (llave real, doc §6) ────────────────────
        sa.Column("ano_eje", sa.SmallInteger, nullable=False),
        sa.Column(
            "sec_ejec", sa.Integer, nullable=False, server_default=sa.text("300687")
        ),
        sa.Column("tipo_bien", sa.CHAR(1), nullable=False),
        sa.Column("tipo_pedido", sa.String(2), nullable=False),
        sa.Column("nro_pedido", sa.Integer, nullable=False),
        # ── El CCMN asociado: UNA FILA POR CCMN (N:M) ────────────────────
        sa.Column("nro_consolid", sa.Integer, nullable=False),
        # Bolsa de la que salio el candidato, para auditar el contexto (§5.1).
        sa.Column("sec_cua_mod_sal", sa.Integer, nullable=False),
        sa.Column("nota", sa.Text),
        # ── Autoria y ciclo de vida ──────────────────────────────────────
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.usuarios.id"),
            nullable=False,
        ),
        sa.Column(
            "creado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("revocado_en", sa.TIMESTAMP(timezone=True)),
        sa.Column(
            "revocado_por",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.usuarios.id"),
        ),
        sa.CheckConstraint("tipo_bien IN ('B','S')", name="ck_resolucion_tipo_bien"),
        # Revocar exige ambos campos o ninguno: una revocacion sin autor no
        # es auditable, y un autor sin fecha deja la fila en un estado ambiguo.
        sa.CheckConstraint(
            "(revocado_en IS NULL) = (revocado_por IS NULL)",
            name="ck_resolucion_revocacion_completa",
        ),
        schema="sistema",
    )

    # Un solo par ACTIVO por (pedido, ccmn); muchos revocados conviviendo.
    # NULLS NOT DISTINCT hace que dos filas activas (revocado_en NULL) colisionen
    # -- sin esto, NULL != NULL y el UNIQUE no impediria duplicados activos.
    op.execute(
        """
        ALTER TABLE sistema.resolucion_pedido_ccmn
        ADD CONSTRAINT uq_par_activo UNIQUE NULLS NOT DISTINCT
            (ano_eje, sec_ejec, tipo_bien, tipo_pedido, nro_pedido,
             nro_consolid, revocado_en)
        """
    )

    # Lookup del pipeline: resolver los CCMN activos de un pedido. Es la via
    # caliente -- se consulta por cada pedido al armar el kanban.
    op.execute(
        """
        CREATE INDEX ix_resolucion_pedido_activa
        ON sistema.resolucion_pedido_ccmn
            (ano_eje, sec_ejec, tipo_bien, tipo_pedido, nro_pedido)
        WHERE revocado_en IS NULL
        """
    )

    # Direccion inversa: que pedidos se asociaron a un CCMN (vista de bolsa).
    op.execute(
        """
        CREATE INDEX ix_resolucion_ccmn_activa
        ON sistema.resolucion_pedido_ccmn (ano_eje, sec_ejec, nro_consolid)
        WHERE revocado_en IS NULL
        """
    )

    op.execute(
        "COMMENT ON TABLE sistema.resolucion_pedido_ccmn IS "
        "'Asociacion manual pedido<->CCMN. Referencial y opcional: el sistema "
        "funciona sin filas aqui. N:M en ambas direcciones. Nunca se borra, "
        "se revoca. Ver Docs/diagnostico-2026-07-20/"
        "refactorizacion-pipeline-pedido-ccmn.md §5'"
    )


def downgrade() -> None:
    op.drop_table("resolucion_pedido_ccmn", schema="sistema")
