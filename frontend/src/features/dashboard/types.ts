/**
 * Tipos del Dashboard Interno (HU-22).
 *
 * Contrato inferido a partir del mockup textual de HU-22
 * (Docs/actividad-2-requerimientos-funcionales.md §9)
 * y los schemas Pydantic existentes del backend:
 *   - pipeline.py (PedidoCard, KanbanResponse)
 *   - saldos.py   (SaldoItem, SaldosListadoResponse)
 *
 * NOTA: Este contrato se validará E2E cuando el .bak de SIGA
 * esté disponible (ver bitácora: Bloqueador SIGA).
 */

// ─── Alerta Widget ──────────────────────────────────────────────────
export interface AlertasResumen {
  pedidos_estancados: number;
  contratos_por_vencer: number;
  metas_rezagadas: number;
}

// ─── Pipeline Widget ────────────────────────────────────────────────
export interface PipelineResumen {
  solicitados: number;
  con_orden: number;
  conformidad: number;
  devengado: number;
  cerrado: number;
}

// ─── Saldos Widget ──────────────────────────────────────────────────
export interface SaldosResumen {
  saldo_disponible: number;
  pim_total: number;
  devengado_total: number;
  porcentaje_ejecucion: number;
  semaforo: 'ok' | 'alerta' | 'critico' | null;
}

// ─── Últimos Pedidos Widget ─────────────────────────────────────────
export interface PedidoReciente {
  nro_pedido: string;
  monto: number;
  descripcion: string;
  estado: string;
  fecha: string | null;
}

// ─── Respuesta Agregada ─────────────────────────────────────────────
export interface DashboardResponse {
  alertas: AlertasResumen;
  pipeline: PipelineResumen;
  saldos: SaldosResumen;
  ultimos_pedidos: PedidoReciente[];
}
