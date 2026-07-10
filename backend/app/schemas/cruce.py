"""Schemas del cruce SIAF-SIGA (HU-12, HU-13)."""

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


class OrdenCruceItem(BaseModel):
    ano_eje: int
    sec_ejec: str
    nro_orden: int
    tipo_bien: str
    exp_siaf: str | None = None
    exp_siga: str | None = None
    estado: str | None = None
    estado_siaf: str | None = None
    total_fact_soles: float | None = None
    concepto: str | None = None
    fecha_orden: date | None = None
    nro_contrato: int | None = None
    ano_contrato: int | None = None
    sec_contrato: int | None = None
    proveedor_ruc: str | None = None
    proveedor_nombre: str | None = None

    @field_validator(
        "sec_ejec", "exp_siaf", "exp_siga", "estado", "estado_siaf",
        "proveedor_ruc", mode="before"
    )
    @classmethod
    def _coerce(cls, v):
        return _to_str(v)

    @field_validator("fecha_orden", mode="before")
    @classmethod
    def _fecha(cls, v):
        return _to_date(v)


class AfectacionItem(BaseModel):
    nro_orden: int
    tipo_bien: str
    sec_func: int
    clasificador: str | None = None
    fuente_financ: str | None = None
    exp_siaf: str | None = None
    valor_soles: float | None = None
    nombre_meta: str | None = None
    act_proy: str | None = None
    funcion: str | None = None

    @field_validator("tipo_bien", "clasificador", "fuente_financ", "exp_siaf", "act_proy", "funcion", mode="before")
    @classmethod
    def _coerce(cls, v):
        return _to_str(v)


class PedidoOrigenItem(BaseModel):
    nro_pedido: int
    tipo_bien: str
    centro_costo: str | None = None
    sec_func: int | None = None
    fecha_pedido: date | None = None
    estado_pedido: str | None = None
    motivo: str | None = None
    solicitante: str | None = None
    nro_orden: int | None = None

    @field_validator("tipo_bien", "centro_costo", "estado_pedido", mode="before")
    @classmethod
    def _coerce(cls, v):
        return _to_str(v)

    @field_validator("fecha_pedido", mode="before")
    @classmethod
    def _fecha(cls, v):
        return _to_date(v)


class ConformidadItem(BaseModel):
    nro_orden: int | None = None
    ano_orden: int | None = None
    tipo_bien: str | None = None
    fecha_movimto: date | None = None
    indi_confor: str | None = None
    estado_deveng: str | None = None
    exp_siaf: str | None = None
    responsable: str | None = None
    observacion: str | None = None

    @field_validator("tipo_bien", "indi_confor", "estado_deveng", "exp_siaf", mode="before")
    @classmethod
    def _coerce(cls, v):
        return _to_str(v)

    @field_validator("fecha_movimto", mode="before")
    @classmethod
    def _fecha(cls, v):
        return _to_date(v)


class CruceExpedienteResponse(BaseModel):
    exp_siaf: str
    ano: int
    ordenes: list[OrdenCruceItem]
    afectacion_presupuestal: list[AfectacionItem]
    pedidos_origen: list[PedidoOrigenItem]
    conformidades: list[ConformidadItem]


class MetaCabecera(BaseModel):
    sec_func: int
    ano_eje: int
    meta: str | None = None
    nombre: str | None = None
    act_proy: str | None = None
    funcion: str | None = None
    programa: str | None = None
    finalidad: str | None = None

    @field_validator("meta", "act_proy", "funcion", "programa", "finalidad", mode="before")
    @classmethod
    def _coerce(cls, v):
        return _to_str(v)


class PresupuestoMeta(BaseModel):
    pia: float = 0
    pim: float = 0
    certificado: float = 0
    devengado: float = 0
    saldo_disponible: float = 0


class CertificacionItem(BaseModel):
    nro_certifica: int | None = None
    clasificador: str | None = None
    valor_soles: float | None = None
    fecha_reg: date | None = None

    @field_validator("clasificador", mode="before")
    @classmethod
    def _coerce(cls, v):
        return _to_str(v)

    @field_validator("fecha_reg", mode="before")
    @classmethod
    def _fecha(cls, v):
        return _to_date(v)


class ConsolidadoMetaResponse(BaseModel):
    meta: MetaCabecera
    presupuesto: PresupuestoMeta
    ordenes: list[OrdenCruceItem]
    pedidos: list[PedidoOrigenItem]
    certificaciones: list[CertificacionItem]
