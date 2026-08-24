// Tipos de la Vista Profesional del pipeline (pivote Meta → Clasificador →
// Pedido con cruce SIGA × SIAF por clasificador de gasto §9.7).
// Espejo de app/schemas/pipeline.py (Reporte*).

import type { EtapaCodigo, Macrofase, Identificadores, Alerta, NivelConfianza } from '../dashboard/types';

export interface SemaforoCtx {
  color: string; // "verde" | "amarillo" | "rojo" | "desconocido"
  esperado: number;
  real: number | null;
  rezago: number | null;
  mes_corte: number;
}

export interface MefMeta {
  pim: number;
  comprometido: number;
  devengado: number;
  porcentaje_devengado: number | null;
  semaforo: string;
  semaforo_ctx: SemaforoCtx | null;
}

export interface MefCelda {
  pim: number;
  comprometido: number;
  devengado: number;
}

/** Cómo se atribuyó el devengado al pedido. */
export type Atribucion = 'directo' | 'estimado';

export interface PedidoReporte {
  nro_pedido: number;
  tipo_bien: string;
  tipo_pedido: string | null;
  centro_costo: string | null;
  motivo: string | null;
  identificadores: Identificadores | null;
  /** Mapa etapa → fecha (rastro para el mini-timeline por fila). */
  fechas: Partial<Record<EtapaCodigo, string>>;
  etapa: EtapaCodigo;
  etapa_label: string;
  macrofase: Macrofase;
  dias_en_etapa: number | null;
  estancado: boolean;
  alerta: Alerta | null;
  monto_siga: number;
  /** >1 ⇒ el avance de bolsa es del grupo, no exclusivo de este pedido (§2.2). */
  n_candidatos_ccmn: number;
  confianza_ccmn: NivelConfianza | null;
  tiene_orden: boolean;
  // Capa de dinero por pedido. `atribucion` null ⇒ sin orden (sin ejecución).
  comprometido_pedido: number | null;
  devengado_estimado: number | null;
  atribucion: Atribucion | null;
}

export interface CeldaClasificador {
  clasificador: string; // "3.1.10.1.1" o "(sin clasificador)"
  clasificador_nombre: string | null;
  n_pedidos: number;
  atribucion_directa: boolean;
  monto_siga: number;
  mef: MefCelda | null; // dinero MEF real de la celda; null si no cruza
  pedidos: PedidoReporte[];
}

/** Orden de compra (O/C, bien) o de servicio (O/S) de una meta. Del snapshot
 *  `siga.ordenes` keyed por sec_func; `tipo_bien` separa O/C ('B') de O/S ('S'). */
export interface OrdenReporte {
  nro_orden: number;
  tipo_bien: string; // 'B' → O/C · 'S' → O/S
  clasificador: string | null;
  estado: string | null;
  estado_siaf: string | null;
  exp_siaf: number | null;
  total_fact_soles: number;
  concepto: string | null;
  proveedor_nombre: string | null;
  proveedor_ruc: string | null;
  fecha_orden: string | null;
  /** Recepción de la orden: '1' pendiente · '2' parcial · '3' completa. */
  flag_recep: string | null;
}

/** PECOSA (despacho de almacén) de una meta, vía la orden que la origina. */
export interface PecosaReporte {
  nro_pecosa: number;
  nro_orden: number | null;
  tipo_bien: string;
  nro_guia: string | null;
  fecha_movimto: string | null;
  proveedor_nombre: string | null;
  total_fact_soles: number;
}

/** Naturaleza del gasto de la meta: proyecto de inversión vs producto/actividad. */
export type CategoriaMeta = 'producto' | 'proyecto';

export interface MetaReporte {
  sec_func: number;
  nombre_meta: string | null;
  /** Nº de meta legible (ref.metas.meta, p.ej. "0001") — no la llave sec_func. */
  meta: string | null;
  /** Clasificación SIAF cruda (proyecto_inversion, actividad_generica, …). */
  tipo_meta: string | null;
  /** Vista binaria que consume el filtro Producto/Proyecto. */
  categoria: CategoriaMeta;
  /** Código de actividad/proyecto (act_proy) — para verificar en SIAF. */
  act_proy: string | null;
  centros_costo: string[];
  n_pedidos: number;
  en_contratacion: number;
  en_ejecucion: number;
  monto_siga: number;
  mef: MefMeta;
  n_celdas: number;
  n_celdas_directas: number;
  celdas: CeldaClasificador[];
  /** Trámite operativo SIGA de la meta (pestañas O/C, O/S, PECOSAS). */
  ordenes: OrdenReporte[];
  pecosas: PecosaReporte[];
}

export interface ReporteTotales {
  n_metas: number;
  n_pedidos: number;
  total_siga_pedidos: number; // suma por pedido (informativo)
  total_mef_devengado: number; // suma 1× por meta (real, anti-inflado)
}

export interface CentroCostoInfo {
  codigo: string;
  nombre: string | null;
  sigla: string;
}

export interface ReporteResponse {
  ano: number;
  mes_corte: number;
  avance_esperado: number;
  sincronizado_siga: string | null;
  sincronizado_mef: string | null;
  centros_costo: CentroCostoInfo[];
  metas: MetaReporte[];
  totales: ReporteTotales;
}
