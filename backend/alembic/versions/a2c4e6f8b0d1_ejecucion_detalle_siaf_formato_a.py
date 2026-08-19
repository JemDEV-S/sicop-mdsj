"""siaf.ejecucion_detalle_siaf: detalle por documento del SIAF (Formato A).

Revision ID: a2c4e6f8b0d1
Revises: f4a1b2c3d5e7
Create Date: 2026-08-19

Contexto:
    La API MEF publica ejecucion agregada por sec_func/mes (max 8 columnas,
    sin detalle de documento). El reporte "Formato A" del Modulo Administrativo
    SIAF si trae el detalle por DOCUMENTO/expediente: fase (C/D/G/P/R),
    proveedor con RUC, clasificador completo y fechas por fase.

    Esta tabla recibe ese Excel (carga PROVISIONAL via endpoint de admin) para
    complementar los reportes internos. NO es fuente de totales de presupuesto:
    los montos autoritativos siguen viniendo de `ejecucion_presupuestal`
    (API MEF). Ver CLAUDE.md RN §3 y memoria feedback-mef-unica-fuente-presupuesto.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a2c4e6f8b0d1"
down_revision: str | Sequence[str] | None = "f4a1b2c3d5e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ejecucion_detalle_siaf",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("expediente", sa.String(length=20), nullable=False),
        sa.Column("ano_eje", sa.SmallInteger(), nullable=False),
        sa.Column("sec_ejec", sa.String(length=10), nullable=True),
        sa.Column("ciclo", sa.String(length=2), nullable=True),
        sa.Column("fase", sa.String(length=2), nullable=True),
        sa.Column("fase_nombre", sa.String(length=20), nullable=True),
        sa.Column("sub_reg", sa.String(length=8), nullable=True),
        sa.Column("correlativo", sa.String(length=8), nullable=True),
        sa.Column("secuencia_padre", sa.String(length=8), nullable=True),
        sa.Column("origen", sa.String(length=4), nullable=True),
        sa.Column("tipo_op", sa.String(length=4), nullable=True),
        sa.Column("mod_compra", sa.String(length=4), nullable=True),
        sa.Column("producto_proyecto", sa.String(length=20), nullable=True),
        sa.Column("funcion", sa.String(length=6), nullable=True),
        sa.Column("meta", sa.String(length=10), nullable=True),
        sa.Column("sec_func", sa.BigInteger(), nullable=True),
        sa.Column("clasificador", sa.String(length=30), nullable=True),
        sa.Column("rubro", sa.String(length=4), nullable=True),
        sa.Column("rubro_nombre", sa.String(length=160), nullable=True),
        sa.Column("tipo_financ", sa.String(length=120), nullable=True),
        sa.Column("cod_doc", sa.String(length=6), nullable=True),
        sa.Column("num_doc", sa.String(length=60), nullable=True),
        sa.Column("fecha_doc", sa.Date(), nullable=True),
        sa.Column("tipo_giro", sa.String(length=4), nullable=True),
        sa.Column("tipo_prov", sa.String(length=4), nullable=True),
        sa.Column("proveedor_ruc", sa.String(length=20), nullable=True),
        sa.Column("proveedor_nombre", sa.Text(), nullable=True),
        sa.Column(
            "monto_origen",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "monto_soles",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("fecha_aprobacion", sa.Date(), nullable=True),
        sa.Column("fecha_proceso", sa.Date(), nullable=True),
        sa.Column("sec_est", sa.String(length=4), nullable=True),
        sa.Column("est_registro", sa.String(length=4), nullable=True),
        sa.Column("certificado", sa.String(length=20), nullable=True),
        sa.Column("certificado_secuencia", sa.String(length=8), nullable=True),
        sa.Column("origen_archivo", sa.Text(), nullable=True),
        sa.Column(
            "cargado_en",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="siaf",
    )
    op.create_index(
        "ix_ejec_det_ano_exp",
        "ejecucion_detalle_siaf",
        ["ano_eje", "expediente"],
        schema="siaf",
    )
    op.create_index(
        "ix_ejec_det_ano_sec_func",
        "ejecucion_detalle_siaf",
        ["ano_eje", "sec_func"],
        schema="siaf",
    )
    op.create_index(
        "ix_ejec_det_ano_fase",
        "ejecucion_detalle_siaf",
        ["ano_eje", "fase"],
        schema="siaf",
    )
    op.create_index(
        "ix_ejec_det_proveedor",
        "ejecucion_detalle_siaf",
        ["proveedor_ruc"],
        schema="siaf",
    )
    op.create_index(
        "ix_ejec_det_clasificador",
        "ejecucion_detalle_siaf",
        ["ano_eje", "clasificador"],
        schema="siaf",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ejec_det_clasificador", "ejecucion_detalle_siaf", schema="siaf"
    )
    op.drop_index(
        "ix_ejec_det_proveedor", "ejecucion_detalle_siaf", schema="siaf"
    )
    op.drop_index("ix_ejec_det_ano_fase", "ejecucion_detalle_siaf", schema="siaf")
    op.drop_index(
        "ix_ejec_det_ano_sec_func", "ejecucion_detalle_siaf", schema="siaf"
    )
    op.drop_index("ix_ejec_det_ano_exp", "ejecucion_detalle_siaf", schema="siaf")
    op.drop_table("ejecucion_detalle_siaf", schema="siaf")
