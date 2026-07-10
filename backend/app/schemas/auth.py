"""Schemas Pydantic del dominio de autenticación."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    usuario: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_en_segundos: int
    debe_cambiar_password: bool = False


class CambiarPasswordRequest(BaseModel):
    password_actual: str = Field(min_length=1)
    password_nueva: str = Field(min_length=8, max_length=128)


class MeResponse(BaseModel):
    id: UUID
    usuario: str
    nombre_completo: str
    email: str | None
    rol: str
    centros_costo: list[str]
    debe_cambiar_password: bool
