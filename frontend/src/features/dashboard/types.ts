// ─── Taxonomia jerarquica (6 macrofases → 13/16 etapas) ─────────────────
// Ver Docs/exploracion-siga-pipeline-extendido.md §17.6.

export type Macrofase =
  | 'solicitud'
  | 'programacion'
  | 'certificacion'
  | 'contratacion'
  | 'ejecucion'
  | 'cierre';

export type EtapaCodigo =
  | 'pedido_registrado'    // [1]
  | 'pedido_aprobado'      // [2]
  | 'cuadro_necesidad'     // [3]
  | 'puente_paac'          // [4]
  | 'ccmn_em_cvr'          // [5]
  | 'cotizacion'           // [6]
  | 'cuadro_adquisicion'   // [7]
  | 'certificacion_ccp'    // [8]
  | 'orden_emitida'        // [9]
  | 'compromiso_siaf'      // [10]
  | 'ejecucion'            // [11]
  | 'recepcion_kardex'     // [12] solo B
  | 'pedido_interno'       // [13] solo B
  | 'despacho_pecosa'      // [14] solo B
  | 'devengado'            // [15]
  | 'cierre';              // [16]

export interface PedidoCard {
  ano_eje: number;
  sec_ejec: string;
  nro_pedido: number;
  tipo_bien: string;
  tipo_pedido?: string | null;
  centro_costo?: string | null;
  sec_func?: number | null;
  estado_pedido?: string | null;
  fecha_pedido?: string | null;
  fecha_aprob?: string | null;
  fecha_atenc?: string | null;
  motivo?: string | null;
  solicitante?: string | null;
  fuente_financ?: string | null;
  monto_total: number;
  items: number;

  etapa: EtapaCodigo;
  etapa_numero: number;
  etapa_label: string;
  macrofase: Macrofase;
  macrofase_label: string;

  tiene_cuadro_neces?: number;
  tiene_puente_paac?: number;
  tiene_ccmn?: number;
  tiene_cotizacion?: number;
  tiene_cuadro_adq?: number;
  tiene_certificacion?: number;
  tiene_orden?: number;
  tiene_compromiso?: number;
  tiene_ejecucion?: number;
  tiene_kardex?: number;
  tiene_pedido_interno?: number;
  tiene_pecosa?: number;
  tiene_devengado?: number;
  tiene_cierre?: number;

  nro_consolid_muestra?: number | null;
  nro_est_mdo_muestra?: number | null;
  nro_orden_muestra?: number | null;
  exp_siaf_muestra?: number | null;
  exp_siga_muestra?: number | null;
  sec_cuadro_muestra?: number | null;
  nro_certifica_muestra?: number | null;
  nro_certifica_siaf_muestra?: number | null;
  match_metodo?: string | null;

  dias_en_etapa?: number | null;
  estancado: boolean;
}

export interface EtapaConteo {
  etapa: EtapaCodigo;
  etapa_numero: number;
  etapa_label: string;
  conteo: number;
  monto: number;
}

export interface MacrofaseConteo {
  macrofase: Macrofase;
  macrofase_label: string;
  conteo: number;
  monto: number;
  etapas: EtapaConteo[];
}

export interface KanbanResponse {
  ano: number;
  macrofases: MacrofaseConteo[];
  pedidos_por_etapa: Partial<Record<EtapaCodigo, PedidoCard[]>>;
}

// ─── Resumen agregado de saldos (endpoint /interno/saldos/resumen) ────────
export interface MetaCritica {
  sec_func: number;
  nombre_meta: string | null;
  pim: number;
  devengado: number;
  porcentaje_devengado: number;
  semaforo: string;
}

export interface SaldosResumen {
  ano: number;
  pia: number;
  pim: number;
  certificado: number;
  comprometido: number;
  devengado: number;
  saldo_disponible: number;
  reservado_pedido: number;
  porcentaje_devengado: number;
  semaforo: string;
  metas_total: number;
  metas_criticas: number;
  top_metas_criticas: MetaCritica[];
}

// ─── Contratos por vencer (endpoint /interno/alertas/contratos-por-vencer)
export interface ContratoPorVencer {
  ano_eje: number;
  nro_contrato: number;
  sec_contrato: number;
  tipo_contrato: string;
  tipo_bien: string | null;
  proveedor_ruc: string | null;
  proveedor_nombre: string | null;
  fecha_inicial: string | null;
  fecha_final: string | null;
  valor_soles: number | null;
  objeto: string | null;
  estado: string | null;
  dias_restantes: number;
}

// ─── Metas rezagadas (endpoint /interno/saldos/metas-rezagadas) ───────────
export interface MetaRezagada {
  sec_func: number;
  nombre_meta: string | null;
  act_proy: string | null;
  pim: number;
  devengado: number;
  porcentaje_devengado: number;
  semaforo: string;
}
