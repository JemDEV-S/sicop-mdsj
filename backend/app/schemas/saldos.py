"""Schemas de saldos presupuestales (HU-15, HU-16)."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, field_validator


def _to_str(v):
    if v is None:
        return None
    if isinstance(v, (int, Decimal, float)):
        return str(int(v))
    return str(v).strip()


class SaldoItem(BaseModel):
    sec_func: int
    nombre_meta: str | None = None
    act_proy: str | None = None
    clasificador: str | None = None
    fuente_financ: str | None = None
    centro_costo: str | None = None
    centro_costo_nombre: str | None = None
    pia: float = 0
    pim: float = 0
    certificado: float = 0
    comprometido_anual: float = 0
    comprometido_mensual: float = 0
    devengado: float = 0
    saldo_disponible: float = 0
    reservado_pedido: float = 0
    porcentaje_devengado: float = 0
    semaforo: str = "desconocido"

    @field_validator(
        "act_proy", "clasificador", "fuente_financ", "centro_costo",
        mode="before"
    )
    @classmethod
    def _coerce(cls, v):
        return _to_str(v)


class SaldosListadoResponse(BaseModel):
    items: list[SaldoItem]
    total: int
    page: int
    size: int


class MetaRezagadaItem(BaseModel):
    sec_func: int
    nombre_meta: str | None = None
    act_proy: str | None = None
    pim: float = 0
    devengado: float = 0
    porcentaje_devengado: float = 0
    semaforo: str = "rojo"

    @field_validator("act_proy", mode="before")
    @classmethod
    def _coerce(cls, v):
        return _to_str(v)


class MetaCritica(BaseModel):
    """Meta priorizada en el resumen del dashboard: alto PIM + bajo % devengado."""

    sec_func: int
    nombre_meta: str | None = None
    pim: float = 0
    devengado: float = 0
    porcentaje_devengado: float = 0
    semaforo: str = "desconocido"


class SaldosResumenResponse(BaseModel):
    """Totales agregados de saldos para el dashboard de bienvenida (T-44).

    Se calcula sobre el mismo universo que `/interno/saldos` (SIG_TECHO_PRESUPUESTO
    filtrado por año + CC del usuario, con `PPTO_MODIF > 0`). El semáforo se
    aplica al % devengado global usando `sistema.umbrales_alertas.saldo_bajo`.
    """

    ano: int
    pia: float = 0
    pim: float = 0
    certificado: float = 0
    comprometido: float = 0
    devengado: float = 0
    saldo_disponible: float = 0
    reservado_pedido: float = 0
    porcentaje_devengado: float = 0
    semaforo: str = "desconocido"
    metas_total: int = 0
    metas_criticas: int = 0
    top_metas_criticas: list[MetaCritica] = []
