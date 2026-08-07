"""Schemas de consulta de auditoría (admin-only).

Lectura de `logs.auditoria` para la vista de administrador. La escritura la hace
`app.services.auditoria_service`; aquí solo se expone la consulta filtrable.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditoriaItem(BaseModel):
    id: int
    usuario_id: UUID | None = None
    usuario_nombre: str | None = None
    accion: str
    detalle: dict | None = None
    ip: str | None = None
    user_agent: str | None = None
    creado_en: datetime


class AuditoriaListado(BaseModel):
    items: list[AuditoriaItem]
    total: int
    page: int
    size: int


class AccionCatalogo(BaseModel):
    """Una acción distinta presente en el log, para poblar el filtro del front."""

    accion: str
    total: int
