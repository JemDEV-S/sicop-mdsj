export interface PedidoCard {
  ano_eje: number;
  sec_ejec: string;
  nro_pedido: number;
  tipo_bien: string;
  centro_costo?: string | null;
  sec_func?: number | null;
  fecha_pedido?: string | null;
  fecha_aprob?: string | null;
  fecha_atenc?: string | null;
  motivo?: string | null;
  solicitante?: string | null;
  fuente_financ?: string | null;
  monto_total: number;
  items: number;
  tiene_orden: number;
  tiene_conformidad: number;
  esta_devengado: number;
  etapa: string;
  dias_en_etapa?: number | null;
  estancado: boolean;
}

export interface KanbanResponse {
  solicitado: PedidoCard[];
  con_orden: PedidoCard[];
  conformidad: PedidoCard[];
  devengado: PedidoCard[];
  cerrado: PedidoCard[];
}

export interface SaldoItem {
  sec_func: number;
  nombre_meta?: string | null;
  act_proy?: string | null;
  clasificador?: string | null;
  fuente_financ?: string | null;
  centro_costo?: string | null;
  centro_costo_nombre?: string | null;
  pia: number;
  pim: number;
  certificado: number;
  comprometido_anual: number;
  comprometido_mensual: number;
  devengado: number;
  saldo_disponible: number;
  reservado_pedido: number;
  porcentaje_devengado: number;
  semaforo: string;
}

export interface SaldosListadoResponse {
  items: SaldoItem[];
  total: number;
  page: number;
  size: number;
}


// ─── Tipos para Componentes (UI) ──────────────────────────────────
export interface AlertasResumen {
  pedidos_estancados: number;
  contratos_por_vencer: number;
  metas_rezagadas: number;
}

export interface PipelineResumen {
  solicitados: number;
  con_orden: number;
  conformidad: number;
  devengado: number;
  cerrado: number;
}

export interface SaldosResumen {
  saldo_disponible: number;
  pim_total: number;
  devengado_total: number;
  porcentaje_ejecucion: number;
  semaforo: 'ok' | 'alerta' | 'critico' | null;
}

export interface PedidoReciente {
  nro_pedido: string;
  monto: number;
  descripcion: string;
  estado: string;
  fecha: string | null;
}
