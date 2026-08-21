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

// ─── Confianza del match pedido <-> CCMN ─────────────────────────────────
//
// SIGA no registra qué CCMN corresponde a qué pedido: logística copia los
// datos del pedido a un CCMN nuevo y no los vincula. Cuando la bolsa agrupa
// varios pedidos hay N candidatos y ninguno es "el" del pedido.
//
// Ref: Docs/diagnostico-2026-07-20/refactorizacion-pipeline-pedido-ccmn.md §4

export type NivelConfianza =
  | 'unico'            // 1 solo candidato en la bolsa
  | 'declarado'        // el texto de la orden lo identifica
  | 'declarado_cert'   // la certificación lo identifica
  | 'resuelto_manual'  // un funcionario lo asoció
  | 'conflicto'        // una fuente declara un CCMN que no es candidato
  | 'ambiguo'          // varios candidatos, ninguna fuente resuelve
  | 'sin_ccmn';        // el pedido aún no se programó

// Estado de cada etapa. Reemplaza al booleano `alcanzada`, que no podía
// distinguir "avanzó este pedido" de "avanzó algún otro pedido de la bolsa".
export type EstadoEtapa =
  | 'directo'    // alcanzada por ESTE pedido — dato duro
  | 'via_ccmn'   // vía CCMN identificado por una fuente declarativa
  | 'grupo'      // avance del grupo: no se sabe si es de este pedido
  | 'manual'     // vía CCMN asociado manualmente
  | 'sin_dato';  // no alcanzada, o sin evidencia

/** Identificador con el que se encuentra el documento en SIGA. */
export interface DocumentoEtapa {
  etiqueta: string;
  valor: string;
}

export interface TimelineEvento {
  etapa: EtapaCodigo;
  etapa_numero: number;
  etapa_label: string;
  macrofase: Macrofase;
  fecha: string | null;
  detalle: string | null;
  estado: EstadoEtapa;
  documentos: DocumentoEtapa[];
  /** Excluye `grupo`: un avance ajeno no es avance de este pedido. */
  alcanzada: boolean;
  /** Monto neto de la fase cuando el dato es duro del Formato A (D/G/P). */
  monto: number | null;
}

// ─── Bolsa (SEC_CUA_MOD_SAL) ─────────────────────────────────────────────

export interface PedidoEnBolsa {
  nro_pedido: number;
  tipo_bien: string;
  tipo_pedido: string | null;
  centro_costo: string | null;
  sec_func: number | null;
  estado_pedido: string | null;
  fecha_pedido: string | null;
  motivo: string | null;
  solicitante: string | null;
  valor_soles: number | null;
  item: string | null;
  confianza_ccmn: NivelConfianza | null;
}

/** Un paso del recorrido propio de un CCMN. */
export interface HitoCCMN {
  codigo: string;
  label: string;
  numero: string | null;
  alcanzado: boolean;
}

export interface CandidatoCCMN {
  nro_consolid: number;
  tipo_consolid: string | null;
  fecha_cons: string | null;
  valor_plan: number | null;
  nro_est_mdo: number | null;
  nro_certifica: number | null;
  nro_certifica_siaf: number | null;
  sec_cuadro: number | null;
  nro_orden: number | null;
  fecha_orden: string | null;
  asociado_manual: boolean;
  flujo: HitoCCMN[];
}

export interface Bolsa {
  ano_eje: number;
  sec_cua_mod_sal: number;
  tipo_bien: string;
  pedidos: PedidoEnBolsa[];
  candidatos: CandidatoCCMN[];
}

export interface Resolucion {
  id: string;
  nro_consolid: number;
  sec_cua_mod_sal: number | null;
  nota: string | null;
  usuario_id: string | null;
  usuario_nombre: string | null;
  creado_en: string;
  revocado_en: string | null;
  revocado_por: string | null;
  revocado_por_nombre: string | null;
  /** Sellado por el job si la bolsa cambió tras resolver (§5.1). */
  revision_pendiente_desde: string | null;
  candidatos_en_revision: number[] | null;
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
  /** VB del jefe (seguimiento SIGA): hito real de aprobación en pedidos de compra. */
  fecha_vb_jefe: string | null;
  motivo: string | null;
  solicitante: string | null;
  fuente_financ: string | null;
  /** Nombre del catálogo de fuentes (el código va en fuente_financ). */
  fuente_financ_nombre: string | null;

  etapa_actual: EtapaCodigo;
  etapa_actual_numero: number;
  etapa_actual_label: string;
  macrofase_actual: Macrofase;
  macrofase_actual_label: string;

  confianza_ccmn: NivelConfianza | null;
  confianza_ccmn_label: string | null;
  estado_programacion: EstadoEtapa | null;
  ccmn_atribuido: number | null;
  ccmn_candidatos: number[];
  sec_cua_mod_sal: number | null;

  items: ItemPedido[];
  ordenes: OrdenAsociada[];
  cuadros: Cuadro[];
  certificaciones: Certificacion[];
  expedientes: Expediente[];
  conformidades: Conformidad[];
  movimientos_almacen: MovimientoAlmacen[];
  timeline: TimelineEvento[];
}

// ─── Detalle SIAF por expediente (Formato A, carga provisional) ──────────
//
// Rompe la ceguera SIAF del pipeline: el rastro duro llega hasta orden +
// recepción (SIGA); de ahí al pago era ciego. El Formato A trae el detalle por
// documento (fase, proveedor, monto) que la API MEF no publica. Es SOLO
// trazabilidad — nunca un total de tablero. La UI lo rotula "detalle SIAF ·
// carga provisional" con la fecha de emisión.

export interface DocumentoFaseSiaf {
  cod_doc: string | null;
  num_doc: string | null;
  fecha_doc: string | null;
  monto_soles: number;
}

export interface FaseExpedienteSiaf {
  fase: string; // 'C' | 'D' | 'G' | 'P' | 'R'
  fase_nombre: string;
  monto_neto: number;
  fecha_min: string | null;
  fecha_max: string | null;
  n_documentos: number;
  proveedor_ruc: string | null;
  proveedor_nombre: string | null;
  documentos: DocumentoFaseSiaf[];
}

export interface DetalleExpedienteSiaf {
  exp_siaf: number;
  ano_eje: number;
  /** false si nadie cargó el Formato A del año (degradación limpia). */
  tiene_datos: boolean;
  /** Meses (1-12) cargados del año. El rastro se arma acumulando meses. */
  meses_cargados: number[];
  /** Fecha de emisión del reporte (mes de corte puede diferir del MEF). */
  emitido_en: string | null;
  cargado_en: string | null;
  fases: FaseExpedienteSiaf[];
}

// ─── Ejecución SIAF agregada (Fase 2: proveedor / clasificador / rubro) ──

export interface FilaEjecucionAgregada {
  proveedor_ruc?: string | null;
  proveedor_nombre?: string | null;
  clasificador?: string | null;
  rubro?: string | null;
  rubro_nombre?: string | null;
  certificado: number;
  devengado: number;
  girado: number;
  pagado: number;
  /** devengado − pagado: brecha de tesorería (dinero comprometido sin salir). */
  en_transito: number;
  n_expedientes: number;
  n_metas: number;
}

export interface EjecucionAgregadaSiaf {
  ano: number;
  group_by: 'proveedor' | 'clasificador' | 'rubro';
  tiene_datos: boolean;
  /** Meses (1-12) cargados del año. */
  meses_cargados: number[];
  emitido_en: string | null;
  cargado_en: string | null;
  totales_por_fase: Record<string, number>;
  filas: FilaEjecucionAgregada[];
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
