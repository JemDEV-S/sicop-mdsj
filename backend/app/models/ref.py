"""Schema `ref` — dimensiones espejadas de SIGA + catálogos MEF.

Ver `Docs/actividad-3-arquitectura-tecnica.md` §3.3.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP

from app.database import Base

SCHEMA = "ref"


class CentroCosto(Base):
    __tablename__ = "centros_costo"
    __table_args__ = (
        Index("ix_centros_costo_ruta_gist", "ruta", postgresql_using="gist"),
        Index("ix_centros_costo_centro_padre", "centro_padre"),
        Index("ix_centros_costo_activo", "activo", postgresql_where="activo"),
        {"schema": SCHEMA},
    )

    codigo: Mapped[str] = mapped_column(String(15), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    abreviado: Mapped[str | None] = mapped_column(String(60))
    centro_padre: Mapped[str | None] = mapped_column(
        String(15), ForeignKey(f"{SCHEMA}.centros_costo.codigo")
    )
    # ltree — se declara como Text para no depender de sqlalchemy_utils.
    # El tipo real ltree se aplica desde la migración con USING CAST.
    ruta: Mapped[str] = mapped_column(Text, nullable=False)
    nivel: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sede: Mapped[int | None] = mapped_column(SmallInteger)
    tipo_dependencia: Mapped[str | None] = mapped_column(String(1))
    nro_personal: Mapped[int | None] = mapped_column(SmallInteger)
    flag_cn: Mapped[bool | None] = mapped_column(Boolean)
    flag_presupuesto: Mapped[bool | None] = mapped_column(Boolean)
    flag_ppr: Mapped[bool | None] = mapped_column(Boolean)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sincronizado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class Meta(Base):
    __tablename__ = "metas"
    __table_args__ = (
        Index("ix_metas_ano_tipo", "ano_eje", "tipo_meta"),
        Index("ix_metas_act_proy", "act_proy"),
        Index("ix_metas_funcion", "funcion"),
        Index("ix_metas_programa", "programa"),
        {"schema": SCHEMA},
    )

    sec_func: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    ano_eje: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    meta: Mapped[str] = mapped_column(String(5), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    funcion: Mapped[str | None] = mapped_column(String(2))
    programa: Mapped[str | None] = mapped_column(String(3))
    sub_programa: Mapped[str | None] = mapped_column(String(4))
    act_proy: Mapped[str | None] = mapped_column(String(7))
    componente: Mapped[str | None] = mapped_column(String(7))
    finalidad: Mapped[str | None] = mapped_column(String(10))
    tipo_meta: Mapped[str] = mapped_column(String(20), nullable=False)
    unidad_med: Mapped[str | None] = mapped_column(String(3))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sincronizado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class MetaCentroCosto(Base):
    __tablename__ = "metas_centro_costo"
    __table_args__ = (
        UniqueConstraint("sec_func", "centro_costo", "secuencia", name="uq_meta_cc_secuencia"),
        Index("ix_meta_cc_cc_sec_func", "centro_costo", "sec_func"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    sec_func: Mapped[int] = mapped_column(
        BIGINT, ForeignKey(f"{SCHEMA}.metas.sec_func"), nullable=False
    )
    centro_costo: Mapped[str] = mapped_column(
        String(15), ForeignKey(f"{SCHEMA}.centros_costo.codigo"), nullable=False
    )
    secuencia: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    fuente_financ: Mapped[str | None] = mapped_column(String(2))
    tipo_recurso: Mapped[str | None] = mapped_column(String(2))
    porc_techo: Mapped[float | None] = mapped_column(Numeric(8, 4))
    sincronizado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class FuenteFinanciamiento(Base):
    __tablename__ = "fuentes_financiamiento"
    __table_args__ = ({"schema": SCHEMA},)

    codigo: Mapped[str] = mapped_column(String(2), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)


class Rubro(Base):
    __tablename__ = "rubros"
    __table_args__ = ({"schema": SCHEMA},)

    codigo: Mapped[str] = mapped_column(String(2), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    fuente_financ_codigo: Mapped[str | None] = mapped_column(
        String(2), ForeignKey(f"{SCHEMA}.fuentes_financiamiento.codigo")
    )


class Funcion(Base):
    __tablename__ = "funciones"
    __table_args__ = ({"schema": SCHEMA},)

    codigo: Mapped[str] = mapped_column(String(4), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)


class ProgramaPresupuestal(Base):
    __tablename__ = "programas_presupuestales"
    __table_args__ = ({"schema": SCHEMA},)

    codigo: Mapped[str] = mapped_column(String(4), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
