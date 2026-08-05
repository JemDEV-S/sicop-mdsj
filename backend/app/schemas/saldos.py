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


class SemaforoContexto(BaseModel):
    """Contexto del semáforo temporal, para que la UI explique el color.

    El semáforo compara el avance devengado REAL contra el ESPERADO por el mes de
    corte del snapshot (no la fecha de hoy: los datos son de un backup). El
    `rezago = esperado − real` en puntos porcentuales decide el color.
    """

    color: str = "desconocido"          # verde | amarillo | rojo | desconocido
    esperado: float = 0                 # % que se esperaría al mes de corte
    real: float | None = None           # % devengado real de la meta
    rezago: float | None = None         # esperado − real (pp); negativo = adelantado
    mes_corte: int = 0                  # mes de datos del snapshot (MAX mes_eje)


class SaldoItem(BaseModel):
    """Saldo de una meta. La cifra presupuestal es SIEMPRE del SIAF/MEF.

    El presupuesto (PIM), la ejecución (certificado→comprometido→devengado→
    girado), los saldos entre fases y los % vienen del snapshot oficial MEF —
    el mismo número que ve el ciudadano. **El PIM SIGA NO se usa como cifra
    presupuestal** (discrepa del SIAF en el 75% de las metas); el SIGA solo
    aporta el detalle operativo por clasificador, que vive en el drill-down.

    - Cadena MEF: `pim_mef`, `certificado_mef`, `comprometido_mef`, `devengado_mef`,
      `girado_mef`. `null` si la meta no cruza con el snapshot.
    - Saldos entre fases: cuánto falta en cada tramo (por certificar/comprometer/
      devengar/pagar) y `saldo_por_ejecutar` (PIM − devengado, el número clave).
    - % por fase sobre el PIM: revela DÓNDE se estanca la ejecución.
    - `semaforo` + `semaforo_ctx`: color temporal (avance real vs. esperado).
    """

    sec_func: int
    nombre_meta: str | None = None
    act_proy: str | None = None
    filas_clasificador: int = 0  # cuántas líneas (clasificador×CC) agrega la meta

    # ── Cadena de ejecución oficial (SIAF/MEF). None si la meta no cruza. ──
    pim_mef: float | None = None
    certificado_mef: float | None = None
    comprometido_mef: float | None = None
    devengado_mef: float | None = None
    girado_mef: float | None = None

    # ── Saldos entre fases (dónde está detenido el gasto). ──
    saldo_por_certificar: float | None = None      # PIM − Certificado
    saldo_por_comprometer_mef: float | None = None  # Certificado − Comprometido
    saldo_por_devengar: float | None = None        # Comprometido − Devengado
    saldo_por_ejecutar: float | None = None        # PIM − Devengado (clave)
    saldo_por_pagar: float | None = None           # Devengado − Girado
    saldo_disponible_mef: float | None = None      # alias legado de saldo_por_ejecutar
    devengado_no_girado_mef: float | None = None   # = saldo_por_pagar

    # ── % de avance por fase sobre el PIM oficial. ──
    porcentaje_certificado: float | None = None
    porcentaje_comprometido: float | None = None
    porcentaje_devengado: float | None = None
    porcentaje_girado: float | None = None

    # ── Referencia operativa SIGA (NO presupuestal). Se conserva para el detalle;
    #    la tabla principal no la muestra como cifra de presupuesto. ──
    pim_siga: float = 0
    certificado_siga: float = 0
    comprometido_siga: float = 0
    saldo_disponible_siga: float = 0
    reservado_pedido: float = 0

    # Semáforo temporal.
    semaforo: str = "desconocido"
    semaforo_ctx: SemaforoContexto | None = None

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
    semaforo_ctx: SemaforoContexto | None = None


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


class ClasificadorDetalle(BaseModel):
    """Un clasificador de gasto dentro de una fuente (hoja del árbol).

    Detalle OPERATIVO del SIGA (qué se compra), NO presupuesto. `sin_pim=True`
    marca las líneas del plan sin techo activo — se muestran igual, no se ocultan.
    """

    codigo: str | None = None
    nombre: str | None = None
    pim: float = 0
    certificado: float = 0
    comprometido: float = 0
    saldo_disponible: float = 0
    saldo_por_comprometer: float = 0
    reservado_pedido: float = 0
    filas: int = 0
    sin_pim: bool = False


class FuenteDetalle(BaseModel):
    """Una fuente de financiamiento con sus clasificadores (nodo del árbol)."""

    fuente_codigo: str | None = None
    fuente_nombre: str | None = None
    pim: float = 0
    certificado: float = 0
    comprometido: float = 0
    saldo_disponible: float = 0
    n_clasificadores: int = 0
    clasificadores: list[ClasificadorDetalle] = []


class SaldoDetalleResponse(BaseModel):
    """Detalle drill-down de una meta: cabecera oficial + árbol operativo SIGA.

    - `cabecera`: la cadena de ejecución oficial (SIAF/MEF) de la meta.
    - `fuentes`: árbol Fuente → Clasificadores con el detalle operativo del SIGA
      (incluye todos los clasificadores, también los de PIM 0).
    """

    ano: int
    cabecera: SaldoItem
    fuentes: list[FuenteDetalle] = []


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
    semaforo_ctx: SemaforoContexto | None = None
    # Contexto temporal del avance (mes de corte del snapshot y % esperado).
    mes_corte: int = 0
    avance_esperado: float = 0
    metas_total: int = 0
    metas_criticas: int = 0
    top_metas_criticas: list[MetaCritica] = []
    mef: EjecucionMef | None = None
