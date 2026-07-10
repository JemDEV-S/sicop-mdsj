"""Schema `auth` — usuarios, roles, tokens, permisos por CC.

Ver `Docs/actividad-3-arquitectura-tecnica.md` §3.2.
"""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, String, Text, func, text
from sqlalchemy.dialects.postgresql import INET, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP

from app.database import Base
from app.models.enums import CodigoRol, EstadoUsuario

SCHEMA = "auth"


class Rol(Base):
    __tablename__ = "roles"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[CodigoRol] = mapped_column(
        sa.Enum(CodigoRol, name="codigo_rol", schema=None, create_type=False),
        unique=True,
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        Index(
            "ix_usuarios_email",
            "email",
            postgresql_where=text("email IS NOT NULL"),
        ),
        Index("ix_usuarios_rol_id", "rol_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    usuario: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(150))
    rol_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey(f"{SCHEMA}.roles.id"), nullable=False
    )
    estado: Mapped[EstadoUsuario] = mapped_column(
        sa.Enum(EstadoUsuario, name="estado_usuario", schema=None, create_type=False),
        nullable=False,
        server_default=text("'activo'::estado_usuario"),
    )
    intentos_fallidos: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    debe_cambiar_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    creado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class UsuarioCentroCosto(Base):
    __tablename__ = "usuarios_centros_costo"
    __table_args__ = ({"schema": SCHEMA},)

    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.usuarios.id"), primary_key=True
    )
    centro_costo: Mapped[str] = mapped_column(
        String(15), ForeignKey("ref.centros_costo.codigo"), primary_key=True
    )
    es_raiz_jerarquia: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    creado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_usuario_revocado", "usuario_id", "revocado"),
        Index("ix_refresh_expira_en", "expira_en"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.usuarios.id"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expira_en: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    revocado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    creado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip_origen: Mapped[str | None] = mapped_column(INET)
