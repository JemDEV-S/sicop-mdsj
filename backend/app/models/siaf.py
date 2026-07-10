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
    categoria_gasto: Mapped[str | None] = mapped_column(CHAR(1))
    generica: Mapped[str | None] = mapped_column(String(4))
    generica_nombre: Mapped[str | None] = mapped_column(String(120))
    subgenerica: Mapped[str | None] = mapped_column(String(4))
    especifica: Mapped[str | None] = mapped_column(String(4))
    especifica_det: Mapped[str | None] = mapped_column(String(4))
    fuente_financiamiento: Mapped[str | None] = mapped_column(String(4))
    fuente_financiamiento_nombre: Mapped[str | None] = mapped_column(String(120))
    rubro: Mapped[str | None] = mapped_column(String(4))

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
    etapa_f8: Mapped[str | None] = mapped_column(String(50))
    tiene_f9: Mapped[str | None] = mapped_column(CHAR(2))
    tiene_f12b: Mapped[str | None] = mapped_column(CHAR(2))
    informe_cierre: Mapped[str | None] = mapped_column(CHAR(2))
    expediente_tecnico: Mapped[str | None] = mapped_column(CHAR(2))
    des_modalidad: Mapped[str | None] = mapped_column(String(40))
    des_tipologia: Mapped[str | None] = mapped_column(String(80))
    funcion: Mapped[str | None] = mapped_column(String(80))
    programa: Mapped[str | None] = mapped_column(String(80))
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
