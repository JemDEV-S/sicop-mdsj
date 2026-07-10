"""Schemas de proveedores y contratos (HU-07, HU-19, HU-20)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


def _to_str(v):
    if v is None:
        return None
    if isinstance(v, (int, Decimal, float)):
        return str(int(v))
    return str(v).strip()


def _to_date(v):
    if isinstance(v, datetime):
        return v.date()
    return v


class ProveedorPublicoItem(BaseModel):
    ruc: str | None = None
    nombre: str | None = None
    tipo_persona: str | None = None
    giro: str | None = None
    flag_mype: str | None = None
    flag_rnp: str | None = None
    flag_consorcio: str | None = None
    monto_acumulado: float | None = None
    nro_ordenes: int = 0


class ProveedorInternoItem(ProveedorPublicoItem):
    email: str | None = None
    telefonos: str | None = None
    direccion: str | None = None
    nro_rnp: str | None = None


class ProveedoresListado(BaseModel):
    items: list[ProveedorPublicoItem]
    total: int
    page: int
    size: int


class ProveedoresListadoInterno(BaseModel):
    items: list[ProveedorInternoItem]
    total: int
    page: int
    size: int


class OrdenProveedor(BaseModel):
    ano_eje: int
    nro_orden: int
    tipo_bien: str
    exp_siaf: str | None = None
    estado: str | None = None
    estado_siaf: str | None = None
    total_fact_soles: float | None = None
    concepto: str | None = None
    fecha_orden: date | None = None

    @field_validator("tipo_bien", "exp_siaf", "estado", "estado_siaf", mode="before")
    @classmethod
    def _coerce(cls, v):
        return _to_str(v)

    @field_validator("fecha_orden", mode="before")
    @classmethod
    def _fecha(cls, v):
        return _to_date(v)


class ContratoItem(BaseModel):
    ano_eje: int
    sec_ejec: str
    tipo_contrato: str | None = None
    nro_contrato: int
    sec_contrato: int
    tipo_bien: str | None = None
    proveedor_ruc: str | None = None
    proveedor_nombre: str | None = None
    fecha_inicial: date | None = None
    fecha_final: date | None = None
    fecha_cese: date | None = None
    valor_soles: float | None = None
    objeto: str | None = None
    tipo_compra: str | None = None
    modal_compra: str | None = None
    id_proceso: str | None = None
    id_contrato: str | None = None
    nro_documento: str | None = None
    estado: str | None = None
    flag_snp: str | None = None

    @field_validator("sec_ejec", "proveedor_ruc", "tipo_bien", "tipo_contrato", mode="before")
    @classmethod
    def _coerce(cls, v):
        return _to_str(v)

    @field_validator("fecha_inicial", "fecha_final", "fecha_cese", mode="before")
    @classmethod
    def _fecha(cls, v):
        return _to_date(v)


class ContratosListado(BaseModel):
    items: list[ContratoItem]
    total: int
    page: int
    size: int


class ContratoPorVencerItem(BaseModel):
    ano_eje: int
    nro_contrato: int
    sec_contrato: int
    tipo_contrato: str | None = None
    tipo_bien: str | None = None
    proveedor_ruc: str | None = None
    proveedor_nombre: str | None = None
    fecha_inicial: date | None = None
    fecha_final: date | None = None
    valor_soles: float | None = None
    objeto: str | None = None
    estado: str | None = None
    dias_restantes: int | None = None

    @field_validator("tipo_bien", "tipo_contrato", "proveedor_ruc", mode="before")
    @classmethod
    def _coerce(cls, v):
        return _to_str(v)

    @field_validator("fecha_inicial", "fecha_final", mode="before")
    @classmethod
    def _fecha(cls, v):
        return _to_date(v)
