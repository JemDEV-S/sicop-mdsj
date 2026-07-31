"""Schema siga.*: snapshot incremental del pipeline SIGA en PostgreSQL.

Revision ID: d1a2b3c4e5f7
Revises: c8d2e3f4a5b6
Create Date: 2026-07-31

Guia Pipeline v2 §01. Deja de consultar SIGA en caliente: los jobs de sync
pueblan estas tablas y el kanban/detalle leen de aqui (milisegundos, cero
carga a SIGA).

Reglas de diseno (§01 y principio 8 del 00-resumen):
    - Una tabla dueña por dato. NO se copian montos MEF (viven en siaf.*) ni
      catalogos de metas/CC (viven en ref.*). Las vistas juntan por JOIN.
    - PK natural = la PK real de SIGA, para que el UPSERT incremental sea por
      clave y el barrido de reconciliacion pueda comparar conteos 1:1.
    - Solo las columnas que el pipeline usa. Los nombres se conservan en
      snake_case; los tipos se ajustan a Postgres (numeric->bigint/numeric,
      datetime->timestamp, varchar->text/varchar acotado).

Los nombres de columna se validaron contra INFORMATION_SCHEMA de SIGA_300687
(2026-07-31): SIG_MOVIM_CONFOR_SERVICIO usa ANO_ORDEN + glosa (minuscula);
SIG_SEGUIMIENTO usa NRO_ORIGEN/FECHA_TRANSACCION/ESTADO_TRANSACCION y NRO_PEDIDO
es varchar; SIG_CUADRO_MODIFICADO_CMN no tiene FECHA_REG (recarga completa).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d1a2b3c4e5f7"
down_revision: str | None = "c8d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _col_registro() -> list[sa.Column]:
    """Columnas de control comunes a todo snapshot: cuando se sincronizo."""
    return [
        sa.Column(
            "sincronizado_en",
            sa.TIMESTAMP(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    ]


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS siga")

    # ─── Control de sincronizacion incremental ───────────────────────────
    # Una fila por tabla SIGA sincronizada: el watermark (max FECHA_REG visto)
    # deja que cada corrida traiga solo lo nuevo, y el conteo permite el
    # barrido de reconciliacion nocturno (§01.2).
    op.create_table(
        "sync_watermarks",
        sa.Column("tabla", sa.String(80), primary_key=True),
        sa.Column("ano_eje", sa.SmallInteger, primary_key=True),
        sa.Column("ultima_fecha", sa.TIMESTAMP(timezone=False)),
        sa.Column("ultima_corrida", sa.TIMESTAMP(timezone=False)),
        sa.Column("filas", sa.Integer, nullable=False, server_default="0"),
        schema="sistema",
    )

    # ═══════════════════════════════════════════════════════════════════
    # siga.* — snapshot del pipeline
    # ═══════════════════════════════════════════════════════════════════

    # ── pedidos: cabecera (SIG_PEDIDOS) ──────────────────────────────────
    op.create_table(
        "pedidos",
        sa.Column("ano_eje", sa.SmallInteger, primary_key=True),
        sa.Column("sec_ejec", sa.BigInteger, primary_key=True),
        sa.Column("tipo_bien", sa.String(1), primary_key=True),
        sa.Column("tipo_pedido", sa.String(2), primary_key=True),
        sa.Column("nro_pedido", sa.Integer, primary_key=True),
        sa.Column("centro_costo", sa.String(20), index=True),
        sa.Column("sec_func", sa.BigInteger),
        sa.Column("estado", sa.String(2)),
        sa.Column("act_proy", sa.String(40)),
        sa.Column("fecha_pedido", sa.TIMESTAMP(timezone=False)),
        sa.Column("fecha_aprob", sa.TIMESTAMP(timezone=False)),
        sa.Column("fecha_atenc", sa.TIMESTAMP(timezone=False)),
        sa.Column("motivo", sa.Text),
        sa.Column("solicitante", sa.String(150)),
        sa.Column("fuente_financ", sa.String(60)),
        sa.Column("fecha_reg", sa.TIMESTAMP(timezone=False)),
        *_col_registro(),
        schema="siga",
    )

    # ── pedido_items: grano item (SIG_DETALLE_PEDIDOS) ───────────────────
    # Es la tabla grande (8k/año) que amerita watermark. Guarda el composite
    # (item + clasificador + valor) y las llaves de programacion/pecosa.
    op.create_table(
        "pedido_items",
        sa.Column("ano_eje", sa.SmallInteger, primary_key=True),
        sa.Column("sec_ejec", sa.BigInteger, primary_key=True),
        sa.Column("tipo_bien", sa.String(1), primary_key=True),
        sa.Column("tipo_pedido", sa.String(2), primary_key=True),
        sa.Column("nro_pedido", sa.Integer, primary_key=True),
        sa.Column("secuencia", sa.Integer, primary_key=True),
        sa.Column("sec_cua_mod_sal", sa.BigInteger, index=True),
        sa.Column("nro_orden_declarado", sa.Integer),
        sa.Column("nro_pecosa", sa.Integer),
        sa.Column("clasificador", sa.String(20)),
        sa.Column("grupo_bien", sa.String(10)),
        sa.Column("clase_bien", sa.String(10)),
        sa.Column("familia_bien", sa.String(10)),
        sa.Column("item_bien", sa.String(10)),
        sa.Column("cant_solicitada", sa.Numeric(18, 4)),
        sa.Column("cant_aprobada", sa.Numeric(18, 4)),
        sa.Column("cant_atendida", sa.Numeric(18, 4)),
        sa.Column("precio_unit", sa.Numeric(18, 6)),
        # Monto ya normalizado en el job: VALOR_TOTAL o cant*precio (VALOR_TOTAL
        # viene 0 en el 100% de servicios). Ver principio del §01.
        sa.Column("valor_soles", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("estado_confor", sa.String(2)),
        sa.Column("fecha_reg", sa.TIMESTAMP(timezone=False)),
        *_col_registro(),
        schema="siga",
    )

    # ── bolsas: puente SEC_CUA_MOD_SAL <-> CCMN (SIG_CUADRO_MODIFICADO_CMN) ─
    # Sin FECHA_REG en origen: recarga completa por año. Es el puente donde
    # nace la ambiguedad; una bolsa puede tener N CCMN candidatos.
    op.create_table(
        "bolsas",
        sa.Column("ano_eje", sa.SmallInteger, primary_key=True),
        sa.Column("sec_ejec", sa.BigInteger, primary_key=True),
        sa.Column("tipo_bien", sa.String(1), primary_key=True),
        sa.Column("sec_cua_mod_sal", sa.BigInteger, primary_key=True, index=True),
        sa.Column("tipo_consolid", sa.String(2), primary_key=True),
        sa.Column("nro_consolid", sa.BigInteger, primary_key=True, index=True),
        *_col_registro(),
        schema="siga",
    )

    # ── expedientes_ccmn: cabecera CCMN (SIG_PAAC_CONSOLIDADO) + cotizacion +
    #    cuadro de adquisicion, aplanados a una fila por CCMN. ────────────
    op.create_table(
        "expedientes_ccmn",
        sa.Column("ano_eje", sa.SmallInteger, primary_key=True),
        sa.Column("sec_ejec", sa.BigInteger, primary_key=True),
        sa.Column("tipo_bien", sa.String(1), primary_key=True),
        sa.Column("tipo_consolid", sa.String(2), primary_key=True),
        sa.Column("nro_consolid", sa.BigInteger, primary_key=True, index=True),
        sa.Column("nro_est_mdo", sa.BigInteger),
        sa.Column("nro_certifica", sa.BigInteger),
        sa.Column("valor_plan", sa.Numeric(18, 2)),
        sa.Column("fecha_cons", sa.TIMESTAMP(timezone=False)),
        # Cotizacion (SIG_SOLICITUD_COTIZACION.FECHA_REG mas antigua del CCMN).
        sa.Column("fecha_cotizacion", sa.TIMESTAMP(timezone=False)),
        # Cuadro de adquisicion (SIG_CUADRO_ADQUISICION por NRO_CONS_PAAC).
        sa.Column("sec_cuadro", sa.BigInteger),
        sa.Column("fecha_cuadro", sa.TIMESTAMP(timezone=False)),
        sa.Column("fecha_reg", sa.TIMESTAMP(timezone=False)),
        *_col_registro(),
        schema="siga",
    )

    # ── ordenes: SIG_ORDEN_ADQUISICION + SIG_ORDEN_PRESUPUESTO (llaves de
    #    cruce MEF) + CCMN via SIG_CERTIFICACION_FASE. ────────────────────
    op.create_table(
        "ordenes",
        sa.Column("ano_eje", sa.SmallInteger, primary_key=True),
        sa.Column("sec_ejec", sa.BigInteger, primary_key=True),
        sa.Column("tipo_bien", sa.String(1), primary_key=True),
        sa.Column("nro_orden", sa.Integer, primary_key=True),
        sa.Column("sec_cuadro", sa.BigInteger, index=True),
        # CCMN del que sale la orden (cadena dura via cuadro de adquisicion).
        sa.Column("nro_consolid", sa.BigInteger, index=True),
        sa.Column("nro_certifica", sa.BigInteger),
        sa.Column("exp_siga", sa.BigInteger),
        sa.Column("exp_siaf", sa.BigInteger),
        # Llaves de cruce orden -> MEF (SIG_ORDEN_PRESUPUESTO, 100% pobladas).
        sa.Column("sec_func", sa.BigInteger, index=True),
        sa.Column("clasificador", sa.String(20)),
        sa.Column("mes_cale", sa.String(2)),
        sa.Column("proveedor", sa.BigInteger),
        sa.Column("proveedor_nombre", sa.String(200)),
        sa.Column("proveedor_ruc", sa.String(15)),
        sa.Column("concepto", sa.Text),
        sa.Column("total_fact_soles", sa.Numeric(18, 2)),
        sa.Column("estado", sa.String(2)),
        sa.Column("estado_siaf", sa.String(2)),
        sa.Column("fecha_orden", sa.TIMESTAMP(timezone=False)),
        sa.Column("fecha_reg", sa.TIMESTAMP(timezone=False)),
        *_col_registro(),
        schema="siga",
    )

    # ── certificaciones: SIG_CERTIFICACION_FASE — CCMN<->orden en duro +
    #    CCP SIAF + fecha de certificacion por fase. ──────────────────────
    op.create_table(
        "certificaciones",
        sa.Column("ano_eje", sa.SmallInteger, primary_key=True),
        sa.Column("sec_ejec", sa.BigInteger, primary_key=True),
        sa.Column("nro_certifica", sa.BigInteger, primary_key=True),
        sa.Column("secuencia_fase", sa.Integer, primary_key=True),
        sa.Column("nro_consolid", sa.BigInteger, index=True),
        sa.Column("nro_orden", sa.Integer, index=True),
        sa.Column("nro_certifica_siaf", sa.BigInteger),
        sa.Column("tipo_bien", sa.String(1)),
        sa.Column("valor_soles", sa.Numeric(18, 2)),
        sa.Column("fecha_reg", sa.TIMESTAMP(timezone=False)),
        *_col_registro(),
        schema="siga",
    )

    # ── compromisos: SIG_EXP_SIGA_DOCU — interfase SIAF (compromiso) +
    #    tipo de operacion (DV = devengado en el expediente para bienes). ──
    op.create_table(
        "compromisos",
        sa.Column("ano_eje", sa.SmallInteger, primary_key=True),
        sa.Column("sec_ejec", sa.BigInteger, primary_key=True),
        sa.Column("exp_siga", sa.BigInteger, primary_key=True, index=True),
        sa.Column("exp_siga_doc", sa.BigInteger, primary_key=True),
        sa.Column("tipo_operacion", sa.String(4)),
        sa.Column("exp_siaf", sa.BigInteger),
        sa.Column("fecha_interfase", sa.TIMESTAMP(timezone=False)),
        sa.Column("fecha_documento", sa.TIMESTAMP(timezone=False)),
        sa.Column("fecha_reg", sa.TIMESTAMP(timezone=False)),
        *_col_registro(),
        schema="siga",
    )

    # ── conformidades: SIG_MOVIM_CONFOR_SERVICIO — fin real del servicio y
    #    su estado de devengado (caso 232/S). Clave para el cierre S. ──────
    op.create_table(
        "conformidades",
        sa.Column("ano_orden", sa.SmallInteger, primary_key=True),
        sa.Column("sec_ejec", sa.BigInteger, primary_key=True),
        sa.Column("tipo_bien", sa.String(1), primary_key=True),
        sa.Column("nro_orden", sa.Integer, primary_key=True, index=True),
        sa.Column("nro_movimto", sa.BigInteger, primary_key=True),
        sa.Column("indi_confor", sa.String(2)),
        sa.Column("estado_deveng", sa.String(2)),
        sa.Column("expediente_siaf", sa.BigInteger),
        sa.Column("secuencia_siaf", sa.BigInteger),
        sa.Column("proveedor_nombre", sa.String(200)),
        sa.Column("responsable", sa.String(150)),
        sa.Column("glosa", sa.Text),
        sa.Column("observacion", sa.Text),
        sa.Column("fecha_movimto", sa.TIMESTAMP(timezone=False)),
        sa.Column("fecha_reg", sa.TIMESTAMP(timezone=False)),
        *_col_registro(),
        schema="siga",
    )

    # ── movimientos_almacen: SIG_MOVIM_ALMACEN — I/R/S por orden/pecosa. ──
    op.create_table(
        "movimientos_almacen",
        sa.Column("ano_eje", sa.SmallInteger, primary_key=True),
        sa.Column("sec_ejec", sa.BigInteger, primary_key=True),
        sa.Column("tipo_bien", sa.String(1), primary_key=True),
        # NRO_MOVIMTO se repite entre tipos (I/R/S comparten el mismo numero por
        # orden): tipo_movimto y tipo_transac forman parte de la PK real.
        sa.Column("tipo_movimto", sa.String(1), primary_key=True, index=True),
        sa.Column("tipo_transac", sa.Integer, primary_key=True),
        sa.Column("nro_movimto", sa.BigInteger, primary_key=True),
        sa.Column("nro_orden", sa.Integer, index=True),
        sa.Column("nro_pecosa", sa.Integer),
        sa.Column("nro_guia", sa.String(40)),
        sa.Column("fecha_movimto", sa.TIMESTAMP(timezone=False)),
        sa.Column("fecha_reg", sa.TIMESTAMP(timezone=False)),
        *_col_registro(),
        schema="siga",
    )

    # ── seguimiento_estados: SIG_SEGUIMIENTO + _ESTADO — timeline real por
    #    documento (VB, aprobado, denegado, anulado). Tabla grande (16k/año)
    #    -> watermark por FECHA_ESTADO. ───────────────────────────────────
    op.create_table(
        "seguimiento_estados",
        sa.Column("ano_eje", sa.SmallInteger, primary_key=True),
        sa.Column("sec_ejec", sa.BigInteger, primary_key=True),
        sa.Column("tipo_transaccion", sa.Integer, primary_key=True),
        sa.Column("nro_origen", sa.BigInteger, primary_key=True),
        sa.Column("sec_estado", sa.BigInteger, primary_key=True),
        sa.Column("tipo_bien", sa.String(1)),
        sa.Column("tipo_pedido", sa.String(2)),
        sa.Column("nro_pedido", sa.String(20), index=True),
        sa.Column("nro_consolid", sa.BigInteger),
        sa.Column("centro_costo", sa.String(20)),
        sa.Column("estado_seguimiento", sa.String(2)),
        sa.Column("cuser_id", sa.String(40)),
        sa.Column("fecha_estado", sa.TIMESTAMP(timezone=False)),
        sa.Column("fecha_reg", sa.TIMESTAMP(timezone=False)),
        *_col_registro(),
        schema="siga",
    )

    # ── catalogo_estados: SIG_TRANSACCION_ESTADO — traducir estados a texto. ─
    op.create_table(
        "catalogo_estados",
        sa.Column("cod_maestro", sa.String(30), primary_key=True),
        sa.Column("cod_detalle", sa.Integer, primary_key=True),
        # Un mismo (maestro, detalle) tiene N estados (0..7, A/P...): la PK real
        # de SIG_TRANSACCION_ESTADO incluye ESTADO.
        sa.Column("estado", sa.String(2), primary_key=True),
        sa.Column("nombre", sa.String(200)),
        *_col_registro(),
        schema="siga",
    )


def downgrade() -> None:
    for tabla in (
        "catalogo_estados",
        "seguimiento_estados",
        "movimientos_almacen",
        "conformidades",
        "compromisos",
        "certificaciones",
        "ordenes",
        "expedientes_ccmn",
        "bolsas",
        "pedido_items",
        "pedidos",
    ):
        op.drop_table(tabla, schema="siga")
    op.drop_table("sync_watermarks", schema="sistema")
    op.execute("DROP SCHEMA IF EXISTS siga CASCADE")
