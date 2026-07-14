"""Ampliar ejecucion_presupuestal con nombres de jerarquia (rubro, subgenerica, especifica) para narrativa ciudadana

Revision ID: a1b2c3d4e5f6
Revises: 36ad7695cdfb
Create Date: 2026-07-14 10:00:00

Contexto:
    La API MEF devuelve nombres para rubro, subgenerica, subgenerica_det,
    especifica y especifica_det. Hasta ahora solo guardabamos codigos, lo
    que fuerza al frontend a mostrar "5.1.11.15" en vez de "Otros servicios".

    Tambien agregamos `finalidad` (codigo distintivo de meta segun MEF) y
    `categoria_gasto_nombre` para mostrar "Gasto Corriente" en vez de "5".

    La vista `siaf.v_ejecucion_normalizada` se recrea exponiendo todos los
    nuevos campos + rubro/programa_ppto que estaban en la tabla base pero
    no en la vista.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "0004_inversiones_alta_prioridad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Nuevas columnas
    op.add_column(
        "ejecucion_presupuestal",
        sa.Column("finalidad", sa.String(length=10), nullable=True),
        schema="siaf",
    )
    op.add_column(
        "ejecucion_presupuestal",
        sa.Column("categoria_gasto_nombre", sa.String(length=120), nullable=True),
        schema="siaf",
    )
    op.add_column(
        "ejecucion_presupuestal",
        sa.Column("subgenerica_nombre", sa.String(length=120), nullable=True),
        schema="siaf",
    )
    op.add_column(
        "ejecucion_presupuestal",
        sa.Column("subgenerica_det", sa.String(length=4), nullable=True),
        schema="siaf",
    )
    op.add_column(
        "ejecucion_presupuestal",
        sa.Column("subgenerica_det_nombre", sa.String(length=120), nullable=True),
        schema="siaf",
    )
    op.add_column(
        "ejecucion_presupuestal",
        sa.Column("especifica_nombre", sa.String(length=120), nullable=True),
        schema="siaf",
    )
    op.add_column(
        "ejecucion_presupuestal",
        sa.Column("especifica_det_nombre", sa.String(length=120), nullable=True),
        schema="siaf",
    )
    op.add_column(
        "ejecucion_presupuestal",
        sa.Column("rubro_nombre", sa.String(length=120), nullable=True),
        schema="siaf",
    )

    # 2) Recrear vista normalizada con la jerarquia completa
    op.execute("DROP VIEW IF EXISTS siaf.v_ejecucion_normalizada")
    op.execute(
        """
        CREATE VIEW siaf.v_ejecucion_normalizada AS
        SELECT
            e.id, e.ano_eje, e.mes_eje, e.sec_ejec, e.sec_func,
            COALESCE(m.meta,   e.meta,          '(sin codigo)')       AS meta_codigo,
            COALESCE(m.nombre, e.meta_nombre,   'Meta desconocida')   AS meta_nombre,
            m.tipo_meta,
            COALESCE(m.act_proy, e.producto_proyecto)                 AS producto_proyecto,
            e.producto_proyecto_nombre,
            COALESCE(f.codigo, e.funcion)                             AS funcion_codigo,
            COALESCE(f.nombre, e.funcion_nombre, 'Funcion desconocida') AS funcion_nombre,
            e.programa_ppto, e.programa_ppto_nombre,
            e.finalidad,
            COALESCE(ff.codigo, e.fuente_financiamiento)              AS fuente_codigo,
            COALESCE(ff.nombre, e.fuente_financiamiento_nombre)       AS fuente_nombre,
            e.rubro, e.rubro_nombre,
            e.generica, e.generica_nombre,
            e.subgenerica, e.subgenerica_nombre,
            e.subgenerica_det, e.subgenerica_det_nombre,
            e.especifica, e.especifica_nombre,
            e.especifica_det, e.especifica_det_nombre,
            e.categoria_gasto, e.categoria_gasto_nombre,
            e.monto_pia, e.monto_pim, e.monto_certificado,
            e.monto_comprometido_anual, e.monto_comprometido,
            e.monto_devengado, e.monto_girado,
            e.sincronizado_en,
            (m.sec_func IS NULL) AS es_huerfano
        FROM siaf.ejecucion_presupuestal e
        LEFT JOIN ref.metas m                    ON m.sec_func = e.sec_func
        LEFT JOIN ref.funciones f                ON f.codigo = e.funcion
        LEFT JOIN ref.fuentes_financiamiento ff  ON ff.codigo = e.fuente_financiamiento
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS siaf.v_ejecucion_normalizada")
    op.execute(
        """
        CREATE VIEW siaf.v_ejecucion_normalizada AS
        SELECT
            e.id, e.ano_eje, e.mes_eje, e.sec_ejec, e.sec_func,
            COALESCE(m.meta,   e.meta,          '(sin codigo)')       AS meta_codigo,
            COALESCE(m.nombre, e.meta_nombre,   'Meta desconocida')   AS meta_nombre,
            m.tipo_meta,
            COALESCE(m.act_proy, e.producto_proyecto)                 AS producto_proyecto,
            COALESCE(f.codigo, e.funcion)                             AS funcion_codigo,
            COALESCE(f.nombre, e.funcion_nombre, 'Funcion desconocida') AS funcion_nombre,
            COALESCE(ff.codigo, e.fuente_financiamiento)              AS fuente_codigo,
            COALESCE(ff.nombre, e.fuente_financiamiento_nombre)       AS fuente_nombre,
            e.generica, e.generica_nombre, e.especifica, e.especifica_det,
            e.categoria_gasto,
            e.monto_pia, e.monto_pim, e.monto_certificado,
            e.monto_comprometido_anual, e.monto_comprometido,
            e.monto_devengado, e.monto_girado,
            e.sincronizado_en,
            (m.sec_func IS NULL) AS es_huerfano
        FROM siaf.ejecucion_presupuestal e
        LEFT JOIN ref.metas m                    ON m.sec_func = e.sec_func
        LEFT JOIN ref.funciones f                ON f.codigo = e.funcion
        LEFT JOIN ref.fuentes_financiamiento ff  ON ff.codigo = e.fuente_financiamiento
        """
    )

    op.drop_column("ejecucion_presupuestal", "rubro_nombre", schema="siaf")
    op.drop_column("ejecucion_presupuestal", "especifica_det_nombre", schema="siaf")
    op.drop_column("ejecucion_presupuestal", "especifica_nombre", schema="siaf")
    op.drop_column("ejecucion_presupuestal", "subgenerica_det_nombre", schema="siaf")
    op.drop_column("ejecucion_presupuestal", "subgenerica_det", schema="siaf")
    op.drop_column("ejecucion_presupuestal", "subgenerica_nombre", schema="siaf")
    op.drop_column("ejecucion_presupuestal", "categoria_gasto_nombre", schema="siaf")
    op.drop_column("ejecucion_presupuestal", "finalidad", schema="siaf")
