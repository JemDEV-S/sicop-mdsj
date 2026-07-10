"""Schemas de anotaciones internas (HU-10 AC-10.4)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AnotacionCreate(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)


class AnotacionResponse(BaseModel):
    id: int
    entidad_tipo: str
    entidad_id: str
    usuario_id: UUID
    usuario_nombre: str | None = None
    texto: str
    creado_en: datetime
