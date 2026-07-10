"""Schema `sistema` — configuración + datos de negocio propios.

Ver `Docs/actividad-3-arquitectura-tecnica.md` §3.5.
"""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import BIGINT, INET, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP

from app.database import Base
from app.models.enums import (
    DireccionSemaforo,
    EstadoObservacion,
    TipoDocumentoObra,
    TipoEntidadAlerta,
    TipoEntidadAnotacion,
)

SCHEMA = "sistema"


class UmbralSemaforo(Base):
    __tablename__ = "umbrales_semaforos"
    __table_args__ = (
        UniqueConstraint("modulo", "metrica", name="uq_umbral_modulo_metrica"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    modulo: Mapped[str] = mapped_column(String(50), nullable=False)
    metrica: Mapped[str] = mapped_column(String(50), nullable=False)
    umbral_verde: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    umbral_amarillo: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    direccion: Mapped[DireccionSemaforo] = mapped_column(
        sa.Enum(DireccionSemaforo, name="direccion_semaforo", create_type=False),
        nullable=False,
    )
    actualizado_por: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.usuarios.id")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class UmbralAlerta(Base):
    __tablename__ = "umbrales_alertas"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    codigo_alerta: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    parametros: Mapped[dict] = mapped_column(JSONB, nullable=False)
    actualizado_por: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.usuarios.id")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class AlertaRevisada(Base):
    __tablename__ = "alertas_revisadas"
    __table_args__ = (
        UniqueConstraint(
            "usuario_id",
            "codigo_alerta",
            "entidad_id",
            name="uq_alerta_revisada_usuario_codigo_entidad",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.usuarios.id"), nullable=False
    )
    codigo_alerta: Mapped[str] = mapped_column(String(50), nullable=False)
    entidad_tipo: Mapped[TipoEntidadAlerta] = mapped_column(
        sa.Enum(TipoEntidadAlerta, name="tipo_entidad_alerta", create_type=False),
        nullable=False,
    )
    entidad_id: Mapped[str] = mapped_column(String(50), nullable=False)
    revisado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    comentario: Mapped[str | None] = mapped_column(Text)


class AnotacionInterna(Base):
    __tablename__ = "anotaciones_internas"
    __table_args__ = (
        Index(
            "ix_anotacion_entidad_creado",
            "entidad_tipo",
            "entidad_id",
            "creado_en",
            postgresql_ops={"creado_en": "DESC"},
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    entidad_tipo: Mapped[TipoEntidadAnotacion] = mapped_column(
        sa.Enum(TipoEntidadAnotacion, name="tipo_entidad_anotacion", create_type=False),
        nullable=False,
    )
    entidad_id: Mapped[str] = mapped_column(String(50), nullable=False)
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.usuarios.id"), nullable=False
    )
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class ObservacionCiudadana(Base):
    __tablename__ = "observaciones_ciudadanas"
    __table_args__ = (
        Index(
            "ix_observacion_obra_creado",
            "codigo_unico_obra",
            "creado_en",
            postgresql_ops={"creado_en": "DESC"},
        ),
        Index(
            "ix_observacion_estado",
            "estado",
            postgresql_where=text("estado = 'pendiente'"),
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    codigo_unico_obra: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre_ciudadano: Mapped[str | None] = mapped_column(String(150))
    email_ciudadano: Mapped[str | None] = mapped_column(String(150))
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[EstadoObservacion] = mapped_column(
        sa.Enum(EstadoObservacion, name="estado_observacion", create_type=False),
        nullable=False,
        server_default=text("'pendiente'::estado_observacion"),
    )
    revisado_por: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.usuarios.id")
    )
    revisado_en: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    respuesta_interna: Mapped[str | None] = mapped_column(Text)
    ip_origen: Mapped[str | None] = mapped_column(INET)
    captcha_score: Mapped[float | None] = mapped_column(Numeric(3, 2))
    creado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class DocumentoObra(Base):
    __tablename__ = "documentos_obra"
    __table_args__ = (
        Index(
            "ix_documento_obra_tipo_publicado",
            "codigo_unico_obra",
            "tipo",
            postgresql_where=text("publicado"),
        ),
        Index("ix_documento_subido_por", "subido_por"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    codigo_unico_obra: Mapped[str] = mapped_column(String(20), nullable=False)
    tipo: Mapped[TipoDocumentoObra] = mapped_column(
        sa.Enum(TipoDocumentoObra, name="tipo_documento_obra", create_type=False),
        nullable=False,
    )
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    ruta_relativa: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(80), nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    subido_por: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.usuarios.id"), nullable=False
    )
    subido_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    publicado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
