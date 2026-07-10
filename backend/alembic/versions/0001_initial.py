"""Initial schema: 5 schemas, extensiones, 8 ENUMs, 20 tablas, 2 vistas.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-09

Ver `Docs/actividad-3-arquitectura-tecnica.md` §3.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SCHEMAS = ["auth", "ref", "siaf", "sistema", "logs"]

ENUMS = {
    "estado_usuario": ("activo", "inactivo", "bloqueado"),
    "estado_observacion": ("pendiente", "leida", "respondida", "spam"),
    "estado_sync": ("en_curso", "exito", "error"),
    "tipo_documento_obra": (
        "foto",
        "expediente_tecnico",
        "contrato",
        "f8",
        "f9",
        "otro",
    ),
    "tipo_entidad_anotacion": ("pedido", "orden", "meta", "obra", "contrato"),
    "tipo_entidad_alerta": ("pedido", "contrato", "meta"),
    "direccion_semaforo": ("mayor", "menor"),
    "codigo_rol": ("ciudadano", "operativo", "decisor", "admin"),
}


def upgrade() -> None:
    # ─── Extensiones ──────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "ltree"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "btree_gin"')

    # ─── Schemas ──────────────────────────────────────────────────
    for schema in SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    # ─── ENUMs (globales, sin schema) ─────────────────────────────
    for enum_name, values in ENUMS.items():
        values_sql = ", ".join(f"'{v}'" for v in values)
        op.execute(f"CREATE TYPE {enum_name} AS ENUM ({values_sql})")

    # ═══════════════════════════════════════════════════════════════
    # ref.* (primero porque auth.usuarios_centros_costo lo referencia)
    # ═══════════════════════════════════════════════════════════════

    op.create_table(
        "fuentes_financiamiento",
        sa.Column("codigo", sa.String(2), primary_key=True),
        sa.Column("nombre", sa.String(80), nullable=False),
        schema="ref",
    )

    op.create_table(
        "rubros",
        sa.Column("codigo", sa.String(2), primary_key=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column(
            "fuente_financ_codigo",
            sa.String(2),
            sa.ForeignKey("ref.fuentes_financiamiento.codigo"),
        ),
        schema="ref",
    )

    op.create_table(
        "funciones",
        sa.Column("codigo", sa.String(4), primary_key=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        schema="ref",
    )

    op.create_table(
        "programas_presupuestales",
        sa.Column("codigo", sa.String(4), primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        schema="ref",
    )

    op.create_table(
        "centros_costo",
        sa.Column("codigo", sa.String(15), primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("abreviado", sa.String(60)),
        sa.Column(
            "centro_padre",
            sa.String(15),
            sa.ForeignKey("ref.centros_costo.codigo"),
        ),
        # ltree: se crea como Text y se convierte al tipo ltree tras crear la tabla.
        sa.Column("ruta", sa.Text, nullable=False),
        sa.Column("nivel", sa.SmallInteger, nullable=False),
        sa.Column("sede", sa.SmallInteger),
        sa.Column("tipo_dependencia", sa.CHAR(1)),
        sa.Column("nro_personal", sa.SmallInteger),
        sa.Column("flag_cn", sa.Boolean),
        sa.Column("flag_presupuesto", sa.Boolean),
        sa.Column("flag_ppr", sa.Boolean),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "sincronizado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="ref",
    )
    # Convertir ruta a tipo ltree real
    op.execute("ALTER TABLE ref.centros_costo ALTER COLUMN ruta TYPE ltree USING ruta::ltree")
    op.execute(
        "CREATE INDEX ix_centros_costo_ruta_gist ON ref.centros_costo USING GIST (ruta)"
    )
    op.create_index(
        "ix_centros_costo_centro_padre", "centros_costo", ["centro_padre"], schema="ref"
    )
    op.create_index(
        "ix_centros_costo_activo",
        "centros_costo",
        ["activo"],
        schema="ref",
        postgresql_where=sa.text("activo"),
    )

    op.create_table(
        "metas",
        sa.Column("sec_func", sa.BigInteger, primary_key=True),
        sa.Column("ano_eje", sa.SmallInteger, nullable=False),
        sa.Column("meta", sa.String(5), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("funcion", sa.String(2)),
        sa.Column("programa", sa.String(3)),
        sa.Column("sub_programa", sa.String(4)),
        sa.Column("act_proy", sa.String(7)),
        sa.Column("componente", sa.String(7)),
        sa.Column("finalidad", sa.String(10)),
        sa.Column("tipo_meta", sa.String(20), nullable=False),
        sa.Column("unidad_med", sa.String(3)),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "sincronizado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="ref",
    )
    op.create_index("ix_metas_ano_tipo", "metas", ["ano_eje", "tipo_meta"], schema="ref")
    op.create_index("ix_metas_act_proy", "metas", ["act_proy"], schema="ref")
    op.create_index("ix_metas_funcion", "metas", ["funcion"], schema="ref")
    op.create_index("ix_metas_programa", "metas", ["programa"], schema="ref")

    op.create_table(
        "metas_centro_costo",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "sec_func", sa.BigInteger, sa.ForeignKey("ref.metas.sec_func"), nullable=False
        ),
        sa.Column(
            "centro_costo",
            sa.String(15),
            sa.ForeignKey("ref.centros_costo.codigo"),
            nullable=False,
        ),
        sa.Column("secuencia", sa.SmallInteger, nullable=False),
        sa.Column("fuente_financ", sa.String(2)),
        sa.Column("tipo_recurso", sa.String(2)),
        sa.Column("porc_techo", sa.Numeric(8, 4)),
        sa.Column(
            "sincronizado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "sec_func", "centro_costo", "secuencia", name="uq_meta_cc_secuencia"
        ),
        schema="ref",
    )
    op.create_index(
        "ix_meta_cc_cc_sec_func",
        "metas_centro_costo",
        ["centro_costo", "sec_func"],
        schema="ref",
    )

    # ═══════════════════════════════════════════════════════════════
    # auth.*
    # ═══════════════════════════════════════════════════════════════

    op.create_table(
        "roles",
        sa.Column("id", sa.SmallInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "codigo",
            postgresql.ENUM(name="codigo_rol", create_type=False),
            unique=True,
            nullable=False,
        ),
        sa.Column("nombre", sa.String(80), nullable=False),
        schema="auth",
    )

    op.create_table(
        "usuarios",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("usuario", sa.String(60), unique=True, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("nombre_completo", sa.String(150), nullable=False),
        sa.Column("email", sa.String(150)),
        sa.Column(
            "rol_id",
            sa.SmallInteger,
            sa.ForeignKey("auth.roles.id"),
            nullable=False,
        ),
        sa.Column(
            "estado",
            postgresql.ENUM(name="estado_usuario", create_type=False),
            nullable=False,
            server_default=sa.text("'activo'::estado_usuario"),
        ),
        sa.Column(
            "intentos_fallidos",
            sa.SmallInteger,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("bloqueado_hasta", sa.TIMESTAMP(timezone=True)),
        sa.Column(
            "debe_cambiar_password",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "creado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "actualizado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="auth",
    )
    op.create_index(
        "ix_usuarios_email",
        "usuarios",
        ["email"],
        schema="auth",
        postgresql_where=sa.text("email IS NOT NULL"),
    )
    op.create_index("ix_usuarios_rol_id", "usuarios", ["rol_id"], schema="auth")

    op.create_table(
        "usuarios_centros_costo",
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.usuarios.id"),
            primary_key=True,
        ),
        sa.Column(
            "centro_costo",
            sa.String(15),
            sa.ForeignKey("ref.centros_costo.codigo"),
            primary_key=True,
        ),
        sa.Column(
            "es_raiz_jerarquia",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "creado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="auth",
    )

    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.usuarios.id"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.Text, nullable=False),
        sa.Column("expira_en", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "revocado",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "creado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("user_agent", sa.Text),
        sa.Column("ip_origen", postgresql.INET),
        schema="auth",
    )
    op.create_index(
        "ix_refresh_usuario_revocado",
        "refresh_tokens",
        ["usuario_id", "revocado"],
        schema="auth",
    )
    op.create_index(
        "ix_refresh_expira_en", "refresh_tokens", ["expira_en"], schema="auth"
    )

    # ═══════════════════════════════════════════════════════════════
    # siaf.*
    # ═══════════════════════════════════════════════════════════════

    op.create_table(
        "ejecucion_presupuestal",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("ano_eje", sa.SmallInteger, nullable=False),
        sa.Column("mes_eje", sa.SmallInteger, nullable=False),
        sa.Column("sec_ejec", sa.String(10), nullable=False),
        sa.Column("sec_func", sa.BigInteger, nullable=False),
        sa.Column("producto_proyecto", sa.String(20)),
        sa.Column("producto_proyecto_nombre", sa.Text),
        sa.Column("tipo_act_proy", sa.CHAR(1)),
        sa.Column("meta", sa.String(10)),
        sa.Column("meta_nombre", sa.Text),
        sa.Column("funcion", sa.String(4)),
        sa.Column("funcion_nombre", sa.String(120)),
        sa.Column("programa_ppto", sa.String(10)),
        sa.Column("programa_ppto_nombre", sa.Text),
        sa.Column("categoria_gasto", sa.CHAR(1)),
        sa.Column("generica", sa.String(4)),
        sa.Column("generica_nombre", sa.String(120)),
        sa.Column("subgenerica", sa.String(4)),
        sa.Column("especifica", sa.String(4)),
        sa.Column("especifica_det", sa.String(4)),
        sa.Column("fuente_financiamiento", sa.String(4)),
        sa.Column("fuente_financiamiento_nombre", sa.String(120)),
        sa.Column("rubro", sa.String(4)),
        sa.Column(
            "monto_pia", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "monto_pim", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "monto_certificado",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "monto_comprometido_anual",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "monto_comprometido",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "monto_devengado",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "monto_girado",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "sincronizado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="siaf",
    )
    op.create_index(
        "ix_ejec_ano_mes_sec_func",
        "ejecucion_presupuestal",
        ["ano_eje", "mes_eje", "sec_func"],
        schema="siaf",
    )
    op.create_index(
        "ix_ejec_ano_producto",
        "ejecucion_presupuestal",
        ["ano_eje", "producto_proyecto"],
        schema="siaf",
    )
    op.create_index(
        "ix_ejec_ano_mes_funcion",
        "ejecucion_presupuestal",
        ["ano_eje", "mes_eje", "funcion"],
        schema="siaf",
    )
    op.create_index(
        "ix_ejec_ano_mes_fuente",
        "ejecucion_presupuestal",
        ["ano_eje", "mes_eje", "fuente_financiamiento"],
        schema="siaf",
    )
    op.create_index(
        "ix_ejec_sec_func", "ejecucion_presupuestal", ["sec_func"], schema="siaf"
    )

    op.create_table(
        "inversiones",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("codigo_unico", sa.String(20)),
        sa.Column("nombre_inversion", sa.Text),
        sa.Column("tipo_inversion", sa.String(40)),
        sa.Column("marco", sa.String(20)),
        sa.Column("estado", sa.String(20)),
        sa.Column("situacion", sa.String(30)),
        sa.Column("anio_proceso", sa.SmallInteger),
        sa.Column("sec_ejec", sa.String(10)),
        sa.Column("avance_fisico", sa.Numeric(6, 2)),
        sa.Column("avance_ejecucion", sa.Numeric(6, 2)),
        sa.Column("tiene_avan_fisico", sa.CHAR(2)),
        sa.Column("pim_anio_actual", sa.Numeric(18, 2)),
        sa.Column("dev_anio_actual", sa.Numeric(18, 2)),
        sa.Column("deven_acumul_anio_ant", sa.Numeric(18, 2)),
        sa.Column("comprom_anual_anio_actual", sa.Numeric(18, 2)),
        sa.Column("certif_anio_actual", sa.Numeric(18, 2)),
        sa.Column("costo_actualizado", sa.Numeric(18, 2)),
        sa.Column("monto_viable", sa.Numeric(18, 2)),
        sa.Column("saldo_ejecutar", sa.Numeric(18, 2)),
        sa.Column("tiene_f8", sa.CHAR(2)),
        sa.Column("etapa_f8", sa.String(50)),
        sa.Column("tiene_f9", sa.CHAR(2)),
        sa.Column("tiene_f12b", sa.CHAR(2)),
        sa.Column("informe_cierre", sa.CHAR(2)),
        sa.Column("expediente_tecnico", sa.CHAR(2)),
        sa.Column("des_modalidad", sa.String(40)),
        sa.Column("des_tipologia", sa.String(80)),
        sa.Column("funcion", sa.String(80)),
        sa.Column("programa", sa.String(80)),
        sa.Column("fec_ini_ejecucion", sa.Date),
        sa.Column("fec_fin_ejecucion", sa.Date),
        sa.Column("fec_ini_ejec_fisica", sa.Date),
        sa.Column("fec_fin_ejec_fisica", sa.Date),
        sa.Column("fecha_viabilidad", sa.Date),
        sa.Column("primer_devengado", sa.Date),
        sa.Column("ultimo_devengado", sa.Date),
        sa.Column("latitud", sa.Numeric(10, 7)),
        sa.Column("longitud", sa.Numeric(10, 7)),
        sa.Column("ubigeo", sa.String(6)),
        sa.Column("departamento", sa.String(60)),
        sa.Column("provincia", sa.String(60)),
        sa.Column("distrito", sa.String(60)),
        sa.Column("nombre_uei", sa.Text),
        sa.Column("nombre_uf", sa.Text),
        sa.Column("nombre_opmi", sa.Text),
        sa.Column(
            "sincronizado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="siaf",
    )
    op.create_index(
        "ux_inversiones_codigo_unico",
        "inversiones",
        ["codigo_unico"],
        schema="siaf",
        unique=True,
    )
    op.create_index(
        "ix_inversiones_lat_lng",
        "inversiones",
        ["latitud", "longitud"],
        schema="siaf",
        postgresql_where=sa.text("latitud IS NOT NULL"),
    )
    op.create_index(
        "ix_inversiones_tipologia", "inversiones", ["des_tipologia"], schema="siaf"
    )
    op.create_index("ix_inversiones_funcion", "inversiones", ["funcion"], schema="siaf")
    op.create_index(
        "ix_inversiones_sec_ejec_estado",
        "inversiones",
        ["sec_ejec", "estado"],
        schema="siaf",
        postgresql_where=sa.text("sec_ejec IS NOT NULL"),
    )

    # Vista normalizada consumida por el frontend
    op.execute(
        """
        CREATE VIEW siaf.v_ejecucion_normalizada AS
        SELECT
            e.id, e.ano_eje, e.mes_eje, e.sec_ejec, e.sec_func,
            COALESCE(m.meta,   e.meta,          '(sin código)')       AS meta_codigo,
            COALESCE(m.nombre, e.meta_nombre,   'Meta desconocida')   AS meta_nombre,
            m.tipo_meta,
            COALESCE(m.act_proy, e.producto_proyecto)                 AS producto_proyecto,
            COALESCE(f.codigo, e.funcion)                             AS funcion_codigo,
            COALESCE(f.nombre, e.funcion_nombre, 'Función desconocida') AS funcion_nombre,
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

    # Vista de auditoría de huérfanos
    op.execute(
        """
        CREATE VIEW siaf.v_ejecucion_huerfana AS
        SELECT
            e.ano_eje, e.mes_eje, e.sec_func, e.meta, e.meta_nombre,
            e.producto_proyecto, e.producto_proyecto_nombre,
            e.monto_pim, e.monto_devengado, e.sincronizado_en
        FROM siaf.ejecucion_presupuestal e
        LEFT JOIN ref.metas m ON m.sec_func = e.sec_func
        WHERE m.sec_func IS NULL
        """
    )

    # ═══════════════════════════════════════════════════════════════
    # sistema.*
    # ═══════════════════════════════════════════════════════════════

    op.create_table(
        "umbrales_semaforos",
        sa.Column("id", sa.SmallInteger, primary_key=True, autoincrement=True),
        sa.Column("modulo", sa.String(50), nullable=False),
        sa.Column("metrica", sa.String(50), nullable=False),
        sa.Column("umbral_verde", sa.Numeric(6, 2), nullable=False),
        sa.Column("umbral_amarillo", sa.Numeric(6, 2), nullable=False),
        sa.Column(
            "direccion",
            postgresql.ENUM(name="direccion_semaforo", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "actualizado_por",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.usuarios.id"),
        ),
        sa.Column(
            "actualizado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("modulo", "metrica", name="uq_umbral_modulo_metrica"),
        schema="sistema",
    )

    op.create_table(
        "umbrales_alertas",
        sa.Column("id", sa.SmallInteger, primary_key=True, autoincrement=True),
        sa.Column("codigo_alerta", sa.String(50), unique=True, nullable=False),
        sa.Column("parametros", postgresql.JSONB, nullable=False),
        sa.Column(
            "actualizado_por",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.usuarios.id"),
        ),
        sa.Column(
            "actualizado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="sistema",
    )

    op.create_table(
        "alertas_revisadas",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.usuarios.id"),
            nullable=False,
        ),
        sa.Column("codigo_alerta", sa.String(50), nullable=False),
        sa.Column(
            "entidad_tipo",
            postgresql.ENUM(name="tipo_entidad_alerta", create_type=False),
            nullable=False,
        ),
        sa.Column("entidad_id", sa.String(50), nullable=False),
        sa.Column(
            "revisado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("comentario", sa.Text),
        sa.UniqueConstraint(
            "usuario_id",
            "codigo_alerta",
            "entidad_id",
            name="uq_alerta_revisada_usuario_codigo_entidad",
        ),
        schema="sistema",
    )

    op.create_table(
        "anotaciones_internas",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "entidad_tipo",
            postgresql.ENUM(name="tipo_entidad_anotacion", create_type=False),
            nullable=False,
        ),
        sa.Column("entidad_id", sa.String(50), nullable=False),
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.usuarios.id"),
            nullable=False,
        ),
        sa.Column("texto", sa.Text, nullable=False),
        sa.Column(
            "creado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="sistema",
    )
    op.execute(
        "CREATE INDEX ix_anotacion_entidad_creado "
        "ON sistema.anotaciones_internas (entidad_tipo, entidad_id, creado_en DESC)"
    )

    op.create_table(
        "observaciones_ciudadanas",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("codigo_unico_obra", sa.String(20), nullable=False),
        sa.Column("nombre_ciudadano", sa.String(150)),
        sa.Column("email_ciudadano", sa.String(150)),
        sa.Column("texto", sa.Text, nullable=False),
        sa.Column(
            "estado",
            postgresql.ENUM(name="estado_observacion", create_type=False),
            nullable=False,
            server_default=sa.text("'pendiente'::estado_observacion"),
        ),
        sa.Column(
            "revisado_por",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.usuarios.id"),
        ),
        sa.Column("revisado_en", sa.TIMESTAMP(timezone=True)),
        sa.Column("respuesta_interna", sa.Text),
        sa.Column("ip_origen", postgresql.INET),
        sa.Column("captcha_score", sa.Numeric(3, 2)),
        sa.Column(
            "creado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="sistema",
    )
    op.execute(
        "CREATE INDEX ix_observacion_obra_creado "
        "ON sistema.observaciones_ciudadanas (codigo_unico_obra, creado_en DESC)"
    )
    op.execute(
        "CREATE INDEX ix_observacion_estado "
        "ON sistema.observaciones_ciudadanas (estado) "
        "WHERE estado = 'pendiente'"
    )

    op.create_table(
        "documentos_obra",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("codigo_unico_obra", sa.String(20), nullable=False),
        sa.Column(
            "tipo",
            postgresql.ENUM(name="tipo_documento_obra", create_type=False),
            nullable=False,
        ),
        sa.Column("nombre_original", sa.String(255), nullable=False),
        sa.Column("ruta_relativa", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(80), nullable=False),
        sa.Column("tamano_bytes", sa.Integer, nullable=False),
        sa.Column(
            "subido_por",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.usuarios.id"),
            nullable=False,
        ),
        sa.Column(
            "subido_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "publicado",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        schema="sistema",
    )
    op.create_index(
        "ix_documento_obra_tipo_publicado",
        "documentos_obra",
        ["codigo_unico_obra", "tipo"],
        schema="sistema",
        postgresql_where=sa.text("publicado"),
    )
    op.create_index(
        "ix_documento_subido_por", "documentos_obra", ["subido_por"], schema="sistema"
    )

    # ═══════════════════════════════════════════════════════════════
    # logs.*
    # ═══════════════════════════════════════════════════════════════

    op.create_table(
        "auditoria",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.usuarios.id"),
        ),
        sa.Column("accion", sa.String(50), nullable=False),
        sa.Column("detalle", postgresql.JSONB),
        sa.Column("ip", postgresql.INET),
        sa.Column("user_agent", sa.Text),
        sa.Column(
            "creado_en",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="logs",
    )
    op.execute(
        "CREATE INDEX ix_auditoria_usuario_creado "
        "ON logs.auditoria (usuario_id, creado_en DESC)"
    )
    op.execute(
        "CREATE INDEX ix_auditoria_accion_creado "
        "ON logs.auditoria (accion, creado_en DESC)"
    )
    op.execute(
        "CREATE INDEX ix_auditoria_detalle_gin "
        "ON logs.auditoria USING gin (detalle jsonb_path_ops)"
    )

    op.create_table(
        "sincronizacion",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("job", sa.String(50), nullable=False),
        sa.Column(
            "inicio",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("fin", sa.TIMESTAMP(timezone=True)),
        sa.Column(
            "estado",
            postgresql.ENUM(name="estado_sync", create_type=False),
            nullable=False,
            server_default=sa.text("'en_curso'::estado_sync"),
        ),
        sa.Column("registros_procesados", sa.Integer),
        sa.Column("error_mensaje", sa.Text),
        schema="logs",
    )
    op.execute(
        "CREATE INDEX ix_sincronizacion_job_inicio "
        "ON logs.sincronizacion (job, inicio DESC)"
    )


def downgrade() -> None:
    # Vistas primero
    op.execute("DROP VIEW IF EXISTS siaf.v_ejecucion_huerfana")
    op.execute("DROP VIEW IF EXISTS siaf.v_ejecucion_normalizada")

    # Tablas en orden inverso
    op.drop_table("sincronizacion", schema="logs")
    op.drop_table("auditoria", schema="logs")

    op.drop_table("documentos_obra", schema="sistema")
    op.drop_table("observaciones_ciudadanas", schema="sistema")
    op.drop_table("anotaciones_internas", schema="sistema")
    op.drop_table("alertas_revisadas", schema="sistema")
    op.drop_table("umbrales_alertas", schema="sistema")
    op.drop_table("umbrales_semaforos", schema="sistema")

    op.drop_table("inversiones", schema="siaf")
    op.drop_table("ejecucion_presupuestal", schema="siaf")

    op.drop_table("refresh_tokens", schema="auth")
    op.drop_table("usuarios_centros_costo", schema="auth")
    op.drop_table("usuarios", schema="auth")
    op.drop_table("roles", schema="auth")

    op.drop_table("metas_centro_costo", schema="ref")
    op.drop_table("metas", schema="ref")
    op.drop_table("centros_costo", schema="ref")
    op.drop_table("programas_presupuestales", schema="ref")
    op.drop_table("funciones", schema="ref")
    op.drop_table("rubros", schema="ref")
    op.drop_table("fuentes_financiamiento", schema="ref")

    # ENUMs (después de las tablas)
    for enum_name in ENUMS:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

    # Schemas (después de todo)
    for schema in reversed(SCHEMAS):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
