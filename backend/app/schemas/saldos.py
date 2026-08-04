"""Schemas de saldos presupuestales (HU-15, HU-16)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


def _to_str(v):
    if v is None:
        return None
    if isinstance(v, (int, Decimal, float)):
        return str(int(v))
    return str(v).strip()


class SaldoItem(BaseModel):
    """Saldo de una meta: SIGA operativo (fases previas) + devengado MEF real.

    Modelo dual (Iteración 2):
      - Bloque SIGA (`pim`, `certificado`, `comprometido_*`, `saldo_disponible`,
        `reservado_pedido`): lo asignado/comprometido a nivel meta según el
        SIGA, filtrado por CC. Son fases PREVIAS al devengado.
      - Bloque MEF (`*_mef`): el número oficial que ve el ciudadano. El
        `devengado_mef` es el devengado REAL; `null` si la meta no cruza con el
        snapshot MEF.
      - `porcentaje_devengado` y `semaforo` se calculan sobre el devengado MEF.
    """

    sec_func: int
    nombre_meta: str | None = None
    act_proy: str | None = None
    filas_clasificador: int = 0  # cuántas filas (clasificador×CC) agrega la meta

    # Bloque SIGA operativo (fases previas — NO son devengado)
    pia: float = 0
    pim: float = 0
    certificado: float = 0
    comprometido_anual: float = 0
    comprometido_mensual: float = 0
    saldo_disponible: float = 0
    reservado_pedido: float = 0

    # Bloque MEF (oficial). None si la meta no está en el snapshot MEF.
    pim_mef: float | None = None
    certificado_mef: float | None = None
    comprometido_mef: float | None = None
    devengado_mef: float | None = None
    girado_mef: float | None = None
    saldo_disponible_mef: float | None = None

    # % y semáforo sobre el devengado MEF real (None si la meta no cruza).
    porcentaje_devengado: float | None = None
    semaforo: str = "desconocido"

    @field_validator("act_proy", mode="before")
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
    """Meta priorizada en el resumen del dashboard: alto PIM + bajo % devengado.

    `devengado` y `porcentaje_devengado` son el devengado REAL del MEF.
    """

    sec_func: int
    nombre_meta: str | None = None
    pim: float = 0
    devengado: float = 0
    porcentaje_devengado: float = 0
    semaforo: str = "desconocido"


class EjecucionMef(BaseModel):
    """Snapshot oficial MEF (portal ciudadano). Sin filtro por CC.

    - PIA/PIM: fila maestra `mes_eje = 0` de la API MEF.
    - Certificado/Comprometido/Devengado/Girado: suma de flujos `mes_eje > 0`.
    - `sincronizado_en`: momento del último sync desde la API MEF (job de sync).
    """
    pia: float = 0
    pim: float = 0
    certificado: float = 0
    comprometido: float = 0
    devengado: float = 0
    girado: float = 0
    saldo_disponible: float = 0
    porcentaje_devengado: float = 0
    sincronizado_en: datetime | None = None


class SaldosResumenResponse(BaseModel):
    """Totales agregados de saldos para el dashboard de bienvenida (T-44).

    Contiene dos bloques de datos:

    1. **Campos planos SIGA (pia, pim, certificado, comprometido, ...):** vienen
       del SIGA (`SIG_TECHO_PRESUPUESTO`), excluyendo las filas sin `SEC_FUNC`
       (techo del pliego no desagregado a metas). Filtrado por CC del usuario.
       Son fases PREVIAS al devengado — aquí no hay un "devengado" SIGA.

    2. **Bloque `mef`:** snapshot oficial del portal MEF, restringido a las metas
       visibles del usuario (Iteración 2: ya NO se oculta a decisores/CC). Trae
       el devengado REAL. Es el número que ve el ciudadano.

    `porcentaje_devengado` y `semaforo` globales se calculan sobre el devengado
    real del bloque MEF. `top_metas_criticas` son las de menor % devengado real.
    """

    ano: int
    # Bloque SIGA operativo (fases previas)
    pia: float = 0
    pim: float = 0
    certificado: float = 0
    comprometido: float = 0
    saldo_disponible: float = 0
    reservado_pedido: float = 0
    # % y semáforo globales sobre el devengado MEF real
    porcentaje_devengado: float = 0
    semaforo: str = "desconocido"
    metas_total: int = 0
    metas_criticas: int = 0
    top_metas_criticas: list[MetaCritica] = []
    mef: EjecucionMef | None = None
