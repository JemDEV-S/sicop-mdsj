"""Schemas de gestión de usuarios — admin-only (HU-17 · T-08/T-54).

CRUD de usuarios + asignación de centros de costo. Reutiliza `CentroCostoBreve`
de `schemas.auth`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.enums import CodigoRol, EstadoUsuario
from app.schemas.auth import CentroCostoBreve


class CentroAsignado(CentroCostoBreve):
    """CC asignado a un usuario, con el flag de cabeza de jerarquía (decisor)."""

    es_raiz_jerarquia: bool = False


class UsuarioItem(BaseModel):
    """Fila del listado de usuarios."""

    id: UUID
    usuario: str
    nombre_completo: str
    dni: str | None = None
    email: str | None = None
    rol: CodigoRol
    estado: EstadoUsuario
    debe_cambiar_password: bool
    nro_centros: int
    creado_en: datetime


class UsuarioDetalle(UsuarioItem):
    """Detalle de un usuario, con sus CC asignados."""

    centros: list[CentroAsignado] = Field(default_factory=list)


class UsuariosListado(BaseModel):
    items: list[UsuarioItem]
    total: int
    page: int
    size: int


def _validar_dni(v: str) -> str:
    v = v.strip()
    if not v.isdigit():
        raise ValueError("el DNI debe contener solo dígitos")
    if not (8 <= len(v) <= 12):
        raise ValueError("el DNI debe tener entre 8 y 12 dígitos")
    return v


class UsuarioCrear(BaseModel):
    usuario: str = Field(min_length=3, max_length=60)
    nombre_completo: str = Field(min_length=1, max_length=150)
    dni: str = Field(description="DNI del usuario; es su contraseña inicial.")
    rol: CodigoRol
    email: str | None = Field(default=None, max_length=150)

    @field_validator("dni")
    @classmethod
    def _dni(cls, v: str) -> str:
        return _validar_dni(v)

    @field_validator("usuario")
    @classmethod
    def _usuario(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("rol")
    @classmethod
    def _rol_no_ciudadano(cls, v: CodigoRol) -> CodigoRol:
        if v == CodigoRol.ciudadano:
            raise ValueError("el rol 'ciudadano' no se asigna a usuarios internos")
        return v


class UsuarioActualizar(BaseModel):
    """Edición parcial. `None` = no cambiar ese campo."""

    nombre_completo: str | None = Field(default=None, min_length=1, max_length=150)
    email: str | None = Field(default=None, max_length=150)
    rol: CodigoRol | None = None
    estado: EstadoUsuario | None = None

    @field_validator("rol")
    @classmethod
    def _rol_no_ciudadano(cls, v: CodigoRol | None) -> CodigoRol | None:
        if v == CodigoRol.ciudadano:
            raise ValueError("el rol 'ciudadano' no se asigna a usuarios internos")
        return v


class AsignacionCentroCrear(BaseModel):
    centro_costo: str = Field(min_length=1, max_length=15)
    es_raiz_jerarquia: bool = False


class ResetPasswordResponse(BaseModel):
    """Resultado de resetear la contraseña al DNI del usuario."""

    ok: bool
    mensaje: str
