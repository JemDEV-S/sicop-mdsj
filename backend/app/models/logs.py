"""Schema `logs` — auditoría de acciones + estado de sincronizaciones.

Ver `Docs/actividad-3-arquitectura-tecnica.md` §3.6.
"""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import BIGINT, INET, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP

from app.database import Base
from app.models.enums import EstadoSync

SCHEMA = "logs"


class Auditoria(Base):
    __tablename__ = "auditoria"
    __table_args__ = (
        Index(
            "ix_auditoria_usuario_creado",
            "usuario_id",
            "creado_en",
            postgresql_ops={"creado_en": "DESC"},
        ),
        Index(
            "ix_auditoria_accion_creado",
            "accion",
            "creado_en",
            postgresql_ops={"creado_en": "DESC"},
        ),
        Index(
            "ix_auditoria_detalle_gin",
            "detalle",
            postgresql_using="gin",
            postgresql_ops={"detalle": "jsonb_path_ops"},
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    usuario_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.usuarios.id")
    )
    accion: Mapped[str] = mapped_column(String(50), nullable=False)
    detalle: Mapped[dict | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class Sincronizacion(Base):
    __tablename__ = "sincronizacion"
    __table_args__ = (
        Index(
            "ix_sincronizacion_job_inicio",
            "job",
            "inicio",
            postgresql_ops={"inicio": "DESC"},
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    job: Mapped[str] = mapped_column(String(50), nullable=False)
    inicio: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    fin: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    estado: Mapped[EstadoSync] = mapped_column(
        sa.Enum(EstadoSync, name="estado_sync", create_type=False),
        nullable=False,
        server_default=text("'en_curso'::estado_sync"),
    )
    registros_procesados: Mapped[int | None] = mapped_column(Integer)
    error_mensaje: Mapped[str | None] = mapped_column(Text)
