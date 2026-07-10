"""Schemas del buzon ciudadano (HU-24)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ObservacionCreate(BaseModel):
    nombre: str | None = Field(default=None, max_length=150)
    email: str | None = Field(default=None, max_length=150)
    texto: str = Field(min_length=10, max_length=2000)
    captcha_token: str | None = None

    @field_validator("email")
    @classmethod
    def _email_basico(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        # Validacion minima — el campo es opcional y no lo usamos para autenticar.
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("email invalido")
        return v


class ObservacionResponse(BaseModel):
    id: UUID
    codigo_unico_obra: str
    estado: str
    creado_en: datetime


class ObservacionAdminItem(BaseModel):
    id: UUID
    codigo_unico_obra: str
    nombre_ciudadano: str | None
    email_ciudadano: str | None
    texto: str
    estado: str
    creado_en: datetime
    revisado_en: datetime | None
    respuesta_interna: str | None


class ObservacionUpdate(BaseModel):
    estado: str = Field(pattern="^(pendiente|leida|respondida|spam)$")
    respuesta_interna: str | None = Field(default=None, max_length=2000)
