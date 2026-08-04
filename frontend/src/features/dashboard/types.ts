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

// ─── Puente pedido<->CCMN y alertas v2 (Guía Pipeline v2 §02) ────────────

export type NivelConfianza =
  | 'unico'
  | 'declarado'
  | 'declarado_cert'
  | 'resuelto_manual'
  | 'conflicto'
  | 'ambiguo'
  | 'sin_ccmn';

/** Tipos de alerta v2. Rojo solo estancado_real; el resto ámbar/gris (§02.4). */
export type TipoAlerta =
  | 'estancado_real'
  | 'puente_pendiente'
  | 'conflicto_puente'
  | 'cerrado_negativo'
  | 'sin_consolidar'
  | 'desfase_devengado';

export type SeveridadAlerta = 'rojo' | 'ambar' | 'gris';

export interface Alerta {
  tipo: TipoAlerta;
  severidad: SeveridadAlerta;
  evidencia: string;
  desde: string | null;
}

/** Los 3 identificadores principales, visibles en toda vista (§00 principio 2). */
export interface Identificadores {
  pedido: string;
  orden: string | null;
  exp_siaf: number | null;
  ccp_siaf: number | null;
}

export interface OrdenBolsa {
  nro_orden: number;
  fecha: string | null;
}

/** Avance duro de la bolsa: cierto aunque el puente no resuelva (§02.1). */
export interface AvanceBolsa {
  n_ordenes: number;
  ordenes: OrdenBolsa[];
  max_etapa: EtapaCodigo | null;
  max_etapa_label: string | null;
}

export interface Puente {
  nivel: NivelConfianza | null;
  nivel_label: string | null;
  bolsa: number | null;
  candidatos: number[];
  ccmn_atribuido: number | null;
  avance_bolsa: AvanceBolsa;
}

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

  // v2
  identificadores?: Identificadores | null;
  fechas?: Partial<Record<EtapaCodigo, string>>;
  puente?: Puente | null;
  alerta?: Alerta | null;
  sincronizado_hasta?: string | null;

  n_candidatos_ccmn?: number;
  confianza_ccmn?: NivelConfianza | null;
  confianza_ccmn_label?: string | null;
  ccmn_atribuido?: number | null;

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

// Snapshot MEF (portal ciudadano). Sin filtro por CC; sólo aparece cuando el
// usuario ve el pliego completo. Es el número oficial que ve el ciudadano.
export interface EjecucionMef {
  pia: number;
  pim: number;
  certificado: number;
  comprometido: number;
  devengado: number;
  girado: number;
  saldo_disponible: number;
  porcentaje_devengado: number;
  sincronizado_en: string | null;
}

export interface SaldosResumen {
  ano: number;
  // Bloque SIGA operativo (a nivel meta, con filtro por CC). Fases PREVIAS al
  // devengado — aquí no hay "devengado" SIGA.
  pia: number;
  pim: number;
  certificado: number;
  comprometido: number;
  saldo_disponible: number;
  reservado_pedido: number;
  // % y semáforo globales sobre el devengado MEF real.
  porcentaje_devengado: number;
  semaforo: string;
  metas_total: number;
  metas_criticas: number;
  top_metas_criticas: MetaCritica[];
  // Bloque MEF (oficial). Restringido a las metas visibles del usuario; ahora
  // aparece también para decisores/CC (ya no se oculta).
  mef: EjecucionMef | null;
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
