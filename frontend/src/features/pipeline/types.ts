// Tipos específicos del feature pipeline — detalle de pedido y anotaciones.
// El kanban (widget + página T-45) sigue leyendo dashboard/types.ts.

import type { EtapaCodigo, Macrofase } from '../dashboard/types';

export interface ItemPedido {
  secuencia: number;
  grupo_bien: string | null;
  clase_bien: string | null;
  familia_bien: string | null;
  item_bien: string | null;
  cant_solicitada: number | null;
  cant_aprobada: number | null;
  cant_atendida: number | null;
  valor_total: number | null;
  clasificador: string | null;
  nro_orden_declarado: number | null;
  nro_pecosa: number | null;
  estado_ped: string | null;
  estado_atend: string | null;
  estado_confor: string | null;
  estado_compra: string | null;
  fecha_confor: string | null;
}

export interface OrdenAsociada {
  nro_orden: number;
  tipo_bien: string;
  exp_siaf: number | null;
  exp_siga: number | null;
  sec_cuadro: number | null;
  nro_certifica: number | null;
  estado: string | null;
  estado_siaf: string | null;
  total_fact_soles: number | null;
  concepto: string | null;
  fecha_orden: string | null;
  proveedor_nombre: string | null;
  proveedor_ruc: string | null;
  match_metodos: string | null;
}

export interface Cuadro {
  sec_cuadro: number;
  tipo_bien: string;
  estado: string | null;
  fecha_cuadro: string | null;
  fecha_autoriz: string | null;
  fecha_compra: string | null;
  valor_total: number | null;
}

export interface Certificacion {
  nro_certifica: number;
  nro_certifica_siaf: number | null;
  estado_certifica_siaf: string | null;
  fecha: string | null;
}

export interface Expediente {
  exp_siga: number;
  tipo_ppto: number | null;
  tipo_fase: string | null;
  exp_siaf: number | null;
  estado_siaf: string | null;
  fecha_exp_siga: string | null;
  fecha_documento: string | null;
  fecha_siaf: string | null;
}

export interface Conformidad {
  nro_orden: number | null;
  ano_orden: number | null;
  tipo_bien: string | null;
  fecha_movimto: string | null;
  indi_confor: string | null;
  proveedor: string | null;
  estado_deveng: string | null;
  exp_siaf: string | null;
  responsable: string | null;
  observacion: string | null;
}

export interface MovimientoAlmacen {
  nro_movimto: number;
  nro_orden: number | null;
  tipo_movimto: string | null;
  tipo_transac: number | null;
  tipo_ppto: number | null;
  fecha_movimto: string | null;
  nro_guia: string | null;
}

export interface TimelineEvento {
  etapa: EtapaCodigo;
  etapa_numero: number;
  etapa_label: string;
  macrofase: Macrofase;
  fecha: string | null;
  detalle: string | null;
  alcanzada: boolean;
}

export interface PedidoDetalle {
  ano_eje: number;
  sec_ejec: string;
  nro_pedido: number;
  tipo_bien: string;
  tipo_pedido: string | null;
  centro_costo: string | null;
  centro_costo_nombre: string | null;
  sec_func: number | null;
  act_proy: string | null;
  nombre_meta: string | null;
  estado_pedido: string | null;
  fecha_pedido: string | null;
  fecha_aprob: string | null;
  fecha_atenc: string | null;
  motivo: string | null;
  solicitante: string | null;
  fuente_financ: string | null;

  etapa_actual: EtapaCodigo;
  etapa_actual_numero: number;
  etapa_actual_label: string;
  macrofase_actual: Macrofase;
  macrofase_actual_label: string;

  items: ItemPedido[];
  ordenes: OrdenAsociada[];
  cuadros: Cuadro[];
  certificaciones: Certificacion[];
  expedientes: Expediente[];
  conformidades: Conformidad[];
  movimientos_almacen: MovimientoAlmacen[];
  timeline: TimelineEvento[];
}

// ─── Anotaciones internas (HU-10 AC-10.4) ────────────────────────────────

export type TipoEntidadAnotacion =
  | 'pedido'
  | 'orden'
  | 'meta'
  | 'obra'
  | 'contrato';

export interface Anotacion {
  id: number;
  entidad_tipo: TipoEntidadAnotacion;
  entidad_id: string;
  usuario_id: string;
  usuario_nombre: string | null;
  texto: string;
  creado_en: string;
}
