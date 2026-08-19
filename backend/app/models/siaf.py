"""Schema `siaf` — snapshots del MEF (ejecución + Invierte.pe).

Ver `Docs/actividad-3-arquitectura-tecnica.md` §3.4.
Las vistas `v_ejecucion_normalizada` y `v_ejecucion_huerfana` se crean
con `op.execute` en la migración inicial.
"""

from datetime import date, datetime

from sqlalchemy import CHAR, Date, Index, Numeric, SmallInteger, String, Text, func, text
from sqlalchemy.dialects.postgresql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP

from app.database import Base

SCHEMA = "siaf"


class EjecucionPresupuestal(Base):
    __tablename__ = "ejecucion_presupuestal"
    __table_args__ = (
        Index("ix_ejec_ano_mes_sec_func", "ano_eje", "mes_eje", "sec_func"),
        Index("ix_ejec_ano_producto", "ano_eje", "producto_proyecto"),
        Index("ix_ejec_ano_mes_funcion", "ano_eje", "mes_eje", "funcion"),
        Index("ix_ejec_ano_mes_fuente", "ano_eje", "mes_eje", "fuente_financiamiento"),
        Index("ix_ejec_sec_func", "sec_func"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    ano_eje: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    mes_eje: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sec_ejec: Mapped[str] = mapped_column(String(10), nullable=False)
    sec_func: Mapped[int] = mapped_column(BIGINT, nullable=False)
    producto_proyecto: Mapped[str | None] = mapped_column(String(20))
    producto_proyecto_nombre: Mapped[str | None] = mapped_column(Text)
    tipo_act_proy: Mapped[str | None] = mapped_column(CHAR(1))
    meta: Mapped[str | None] = mapped_column(String(10))
    meta_nombre: Mapped[str | None] = mapped_column(Text)
    funcion: Mapped[str | None] = mapped_column(String(4))
    funcion_nombre: Mapped[str | None] = mapped_column(String(120))
    programa_ppto: Mapped[str | None] = mapped_column(String(10))
    programa_ppto_nombre: Mapped[str | None] = mapped_column(Text)
    finalidad: Mapped[str | None] = mapped_column(String(10))
    categoria_gasto: Mapped[str | None] = mapped_column(CHAR(1))
    categoria_gasto_nombre: Mapped[str | None] = mapped_column(String(120))
    generica: Mapped[str | None] = mapped_column(String(4))
    generica_nombre: Mapped[str | None] = mapped_column(String(120))
    subgenerica: Mapped[str | None] = mapped_column(String(4))
    subgenerica_nombre: Mapped[str | None] = mapped_column(String(120))
    subgenerica_det: Mapped[str | None] = mapped_column(String(4))
    subgenerica_det_nombre: Mapped[str | None] = mapped_column(String(120))
    especifica: Mapped[str | None] = mapped_column(String(4))
    especifica_nombre: Mapped[str | None] = mapped_column(String(120))
    especifica_det: Mapped[str | None] = mapped_column(String(4))
    especifica_det_nombre: Mapped[str | None] = mapped_column(String(120))
    fuente_financiamiento: Mapped[str | None] = mapped_column(String(4))
    fuente_financiamiento_nombre: Mapped[str | None] = mapped_column(String(120))
    rubro: Mapped[str | None] = mapped_column(String(4))
    rubro_nombre: Mapped[str | None] = mapped_column(String(120))

    monto_pia: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    monto_pim: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    monto_certificado: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    monto_comprometido_anual: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    monto_comprometido: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    monto_devengado: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    monto_girado: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )

    sincronizado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class EjecucionDetalleSiaf(Base):
    """Detalle a nivel de DOCUMENTO del SIAF (reporte "Formato A").

    Carga PROVISIONAL desde el Excel del Modulo Administrativo (subido por un
    admin). Complementa `ejecucion_presupuestal` (que viene agregada por
    sec_func/mes desde la API MEF) con lo que la API no publica: expediente,
    fase (C/D/G/P/R) con su documento, proveedor (RUC + razon social),
    clasificador completo y fechas por fase.

    Regla anti-inflado: esta tabla NO es fuente de totales de presupuesto. Los
    montos autoritativos siguen siendo del SIAF/MEF via `ejecucion_presupuestal`
    (ver memoria `feedback-mef-unica-fuente-presupuesto`). Aqui los montos son
    por documento y llevan signo (las rectificaciones se netean).
    """

    __tablename__ = "ejecucion_detalle_siaf"
    __table_args__ = (
        Index("ix_ejec_det_ano_exp", "ano_eje", "expediente"),
        Index("ix_ejec_det_ano_sec_func", "ano_eje", "sec_func"),
        Index("ix_ejec_det_ano_fase", "ano_eje", "fase"),
        Index("ix_ejec_det_proveedor", "proveedor_ruc"),
        Index("ix_ejec_det_clasificador", "ano_eje", "clasificador"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)

    # Identidad del documento-fase.
    expediente: Mapped[str] = mapped_column(String(20), nullable=False)
    ano_eje: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sec_ejec: Mapped[str | None] = mapped_column(String(10))
    ciclo: Mapped[str | None] = mapped_column(String(2))
    fase: Mapped[str | None] = mapped_column(String(2))
    fase_nombre: Mapped[str | None] = mapped_column(String(20))
    sub_reg: Mapped[str | None] = mapped_column(String(8))
    correlativo: Mapped[str | None] = mapped_column(String(8))
    secuencia_padre: Mapped[str | None] = mapped_column(String(8))
    origen: Mapped[str | None] = mapped_column(String(4))

    tipo_op: Mapped[str | None] = mapped_column(String(4))
    mod_compra: Mapped[str | None] = mapped_column(String(4))

    # Cadena programatica / clasificador.
    producto_proyecto: Mapped[str | None] = mapped_column(String(20))
    funcion: Mapped[str | None] = mapped_column(String(6))
    meta: Mapped[str | None] = mapped_column(String(10))
    sec_func: Mapped[int | None] = mapped_column(BIGINT)
    clasificador: Mapped[str | None] = mapped_column(String(30))

    # Fuente de financiamiento.
    rubro: Mapped[str | None] = mapped_column(String(4))
    rubro_nombre: Mapped[str | None] = mapped_column(String(160))
    tipo_financ: Mapped[str | None] = mapped_column(String(120))

    # Documento sustento.
    cod_doc: Mapped[str | None] = mapped_column(String(6))
    num_doc: Mapped[str | None] = mapped_column(String(60))
    fecha_doc: Mapped[date | None] = mapped_column(Date)
    tipo_giro: Mapped[str | None] = mapped_column(String(4))

    # Proveedor / beneficiario.
    tipo_prov: Mapped[str | None] = mapped_column(String(4))
    proveedor_ruc: Mapped[str | None] = mapped_column(String(20))
    proveedor_nombre: Mapped[str | None] = mapped_column(Text)

    # Montos (por documento, con signo).
    monto_origen: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    monto_soles: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )

    # Fechas por fase y estado del registro.
    fecha_aprobacion: Mapped[date | None] = mapped_column(Date)
    fecha_proceso: Mapped[date | None] = mapped_column(Date)
    sec_est: Mapped[str | None] = mapped_column(String(4))
    est_registro: Mapped[str | None] = mapped_column(String(4))
    certificado: Mapped[str | None] = mapped_column(String(20))
    certificado_secuencia: Mapped[str | None] = mapped_column(String(8))

    # Procedencia de la carga (provisional): archivo + momento.
    origen_archivo: Mapped[str | None] = mapped_column(Text)
    cargado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class Inversion(Base):
    __tablename__ = "inversiones"
    __table_args__ = (
        Index("ux_inversiones_codigo_unico", "codigo_unico", unique=True),
        Index(
            "ix_inversiones_lat_lng",
            "latitud",
            "longitud",
            postgresql_where=text("latitud IS NOT NULL"),
        ),
        Index("ix_inversiones_tipologia", "des_tipologia"),
        Index("ix_inversiones_funcion", "funcion"),
        Index(
            "ix_inversiones_sec_ejec_estado",
            "sec_ejec",
            "estado",
            postgresql_where=text("sec_ejec IS NOT NULL"),
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    codigo_unico: Mapped[str | None] = mapped_column(String(20))
    nombre_inversion: Mapped[str | None] = mapped_column(Text)
    tipo_inversion: Mapped[str | None] = mapped_column(String(40))
    marco: Mapped[str | None] = mapped_column(String(20))
    estado: Mapped[str | None] = mapped_column(String(20))
    situacion: Mapped[str | None] = mapped_column(String(30))
    anio_proceso: Mapped[int | None] = mapped_column(SmallInteger)
    sec_ejec: Mapped[str | None] = mapped_column(String(10))
    avance_fisico: Mapped[float | None] = mapped_column(Numeric(6, 2))
    avance_ejecucion: Mapped[float | None] = mapped_column(Numeric(6, 2))
    tiene_avan_fisico: Mapped[str | None] = mapped_column(CHAR(2))
    pim_anio_actual: Mapped[float | None] = mapped_column(Numeric(18, 2))
    dev_anio_actual: Mapped[float | None] = mapped_column(Numeric(18, 2))
    deven_acumul_anio_ant: Mapped[float | None] = mapped_column(Numeric(18, 2))
    comprom_anual_anio_actual: Mapped[float | None] = mapped_column(Numeric(18, 2))
    certif_anio_actual: Mapped[float | None] = mapped_column(Numeric(18, 2))
    costo_actualizado: Mapped[float | None] = mapped_column(Numeric(18, 2))
    monto_viable: Mapped[float | None] = mapped_column(Numeric(18, 2))
    saldo_ejecutar: Mapped[float | None] = mapped_column(Numeric(18, 2))
    tiene_f8: Mapped[str | None] = mapped_column(CHAR(2))
    etapa_f8: Mapped[str | None] = mapped_column(String(150))
    tiene_f9: Mapped[str | None] = mapped_column(CHAR(2))
    tiene_f12b: Mapped[str | None] = mapped_column(CHAR(2))
    informe_cierre: Mapped[str | None] = mapped_column(CHAR(2))
    expediente_tecnico: Mapped[str | None] = mapped_column(CHAR(2))
    des_modalidad: Mapped[str | None] = mapped_column(String(150))
    des_tipologia: Mapped[str | None] = mapped_column(String(150))
    funcion: Mapped[str | None] = mapped_column(String(150))
    programa: Mapped[str | None] = mapped_column(String(150))
    fec_ini_ejecucion: Mapped[date | None] = mapped_column(Date)
    fec_fin_ejecucion: Mapped[date | None] = mapped_column(Date)
    fec_ini_ejec_fisica: Mapped[date | None] = mapped_column(Date)
    fec_fin_ejec_fisica: Mapped[date | None] = mapped_column(Date)
    fecha_viabilidad: Mapped[date | None] = mapped_column(Date)
    primer_devengado: Mapped[date | None] = mapped_column(Date)
    ultimo_devengado: Mapped[date | None] = mapped_column(Date)
    latitud: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitud: Mapped[float | None] = mapped_column(Numeric(10, 7))
    ubigeo: Mapped[str | None] = mapped_column(String(6))
    departamento: Mapped[str | None] = mapped_column(String(60))
    provincia: Mapped[str | None] = mapped_column(String(60))
    distrito: Mapped[str | None] = mapped_column(String(60))
    nombre_uei: Mapped[str | None] = mapped_column(Text)
    nombre_uf: Mapped[str | None] = mapped_column(Text)
    nombre_opmi: Mapped[str | None] = mapped_column(Text)
    sincronizado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
