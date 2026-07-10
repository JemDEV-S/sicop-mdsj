"""Schemas del pipeline (HU-09, HU-10, HU-11)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class PedidoCard(BaseModel):
    """Tarjeta del kanban."""

    ano_eje: int
    sec_ejec: str
    nro_pedido: int
    tipo_bien: str
    centro_costo: str | None = None
    sec_func: int | None = None
    fecha_pedido: date | None = None
    fecha_aprob: date | None = None
    fecha_atenc: date | None = None
    motivo: str | None = None
    solicitante: str | None = None
    fuente_financ: str | None = None
    monto_total: float = 0
    items: int = 0
    tiene_orden: int = 0
    tiene_conformidad: int = 0
    esta_devengado: int = 0
    etapa: str
    dias_en_etapa: int | None = None
    estancado: bool = False

    model_config = {"populate_by_name": True}


class KanbanResponse(BaseModel):
    solicitado: list[PedidoCard]
    con_orden: list[PedidoCard]
    conformidad: list[PedidoCard]
    devengado: list[PedidoCard]
    cerrado: list[PedidoCard]


class ItemPedido(BaseModel):
    secuencia: int
    item_bien: str | None = None
    cant_solicitada: float | None = None
    cant_aprobada: float | None = None
    cant_atendida: float | None = None
    valor_total: float | None = None
    clasificador: str | None = None
    nro_orden: int | None = None
    estado_ped: str | None = None
    estado_atend: str | None = None
    estado_confor: str | None = None
    estado_compra: str | None = None
    fecha_confor: date | None = None


class OrdenAsociada(BaseModel):
    nro_orden: int
    tipo_bien: str
    exp_siaf: str | None = None
    exp_siga: str | None = None
    estado: str | None = None
    estado_siaf: str | None = None
    total_fact_soles: float | None = None
    concepto: str | None = None
    fecha_orden: date | None = None
    proveedor_nombre: str | None = None
    proveedor_ruc: str | None = None


class Conformidad(BaseModel):
    nro_orden: int | None = None
    ano_orden: int | None = None
    tipo_bien: str | None = None
    fecha_movimto: date | None = None
    indi_confor: str | None = None
    proveedor: str | None = None
    estado_deveng: str | None = None
    exp_siaf: str | None = None
    responsable: str | None = None
    observacion: str | None = None


class PedidoDetalleResponse(BaseModel):
    ano_eje: int
    sec_ejec: str
    nro_pedido: int
    tipo_bien: str
    tipo_pedido: str | None = None
    centro_costo: str | None = None
    centro_costo_nombre: str | None = None
    sec_func: int | None = None
    act_proy: str | None = None
    nombre_meta: str | None = None
    estado_pedido: str | None = None
    fecha_pedido: date | None = None
    fecha_aprob: date | None = None
    fecha_atenc: date | None = None
    motivo: str | None = None
    solicitante: str | None = None
    fuente_financ: str | None = None
    items: list[ItemPedido]
    ordenes: list[OrdenAsociada]
    conformidades: list[Conformidad]


class AnotacionCreate(BaseModel):
    texto: str


class AnotacionResponse(BaseModel):
    id: int
    entidad_tipo: str
    entidad_id: str
    usuario_id: str
    texto: str
    creado_en: datetime
