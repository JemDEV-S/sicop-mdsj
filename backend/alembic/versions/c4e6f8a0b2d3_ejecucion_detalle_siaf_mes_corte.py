"""siaf.ejecucion_detalle_siaf: mes_corte (carga acumulada multi-mes del Formato A).

Revision ID: c4e6f8a0b2d3
Revises: b3d5f7a9c1e2
Create Date: 2026-08-19

Contexto:
    El Formato A del Modulo Administrativo SIAF solo se exporta POR MES (el mes
    en curso viene acumulado hasta la fecha de emision). Para reconstruir el
    rastro completo del año hay que acumular varios meses: cada expediente
    avanza de fase entre meses (ej. exp 2049: Devengado en julio, Girado/Pagado
    en agosto). Verificado: las llaves documento-fase NO se repiten entre meses
    (el SIAF numera sub_reg/correlativo incrementalmente), asi que acumular =
    sumar, sin doble conteo.

    `mes_corte` (1-12, del PERIODO de la cabecera) permite el swap por (año, mes)
    en vez de por año: cada carga reemplaza SOLO su mes. Asi se carga el
    historico (ene-jul) una vez y el mes en curso a diario (cada foto reemplaza
    la anterior del mismo mes). Ver Docs/plan-trazabilidad-siaf-formato-a.md.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4e6f8a0b2d3"
down_revision: str | Sequence[str] | None = "b3d5f7a9c1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ejecucion_detalle_siaf",
        sa.Column("mes_corte", sa.SmallInteger(), nullable=True),
        schema="siaf",
    )
    op.create_index(
        "ix_ejec_det_ano_mes",
        "ejecucion_detalle_siaf",
        ["ano_eje", "mes_corte"],
        schema="siaf",
    )


def downgrade() -> None:
    op.drop_index("ix_ejec_det_ano_mes", "ejecucion_detalle_siaf", schema="siaf")
    op.drop_column("ejecucion_detalle_siaf", "mes_corte", schema="siaf")
