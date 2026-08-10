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

export interface MetaReporte {
  sec_func: number;
  nombre_meta: string | null;
  centros_costo: string[];
  n_pedidos: number;
  en_contratacion: number;
  en_ejecucion: number;
  monto_siga: number;
  mef: MefMeta;
  n_celdas: number;
  n_celdas_directas: number;
  celdas: CeldaClasificador[];
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
