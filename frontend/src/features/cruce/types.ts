// Tipos del Cruce SIAF-SIGA · Vista consolidada por meta (HU-13 · T-51).
//
// Espejo de `backend/app/schemas/cruce.py` (ConsolidadoMetaResponse),
// verificado contra la respuesta real de /interno/cruce/meta/{sec_func}.
//
// El presupuesto es DUAL igual que en Saldos (T-48): bloque SIGA operativo
// (fases previas) + bloque MEF oficial (`*_mef`, con el devengado REAL). El %
// y el semáforo salen de `devengado_mef / pim_mef` — nunca de cert+compr.

import type { SemaforoSaldo } from '@/features/saldos/types';

export type { SemaforoSaldo };

export interface MetaCabecera {
  sec_func: number;
  ano_eje: number;
  meta: string | null;
  nombre: string | null;
  act_proy: string | null;
  funcion: string | null;
  programa: string | null;
  finalidad: string | null;
}

export interface PresupuestoMeta {
  // Bloque SIGA operativo (fases previas — NO hay "devengado" SIGA).
  pia: number;
  pim: number;
  certificado: number;
  comprometido: number;
  saldo_disponible: number;

  // Bloque MEF (oficial). `null` si la meta no cruza con el snapshot MEF.
  pim_mef: number | null;
  certificado_mef: number | null;
  comprometido_mef: number | null;
  devengado_mef: number | null;
  girado_mef: number | null;
  saldo_disponible_mef: number | null;

  // % sobre el devengado MEF real (`null` si no cruza).
  porcentaje_devengado: number | null;
}

export interface OrdenCruceItem {
  ano_eje: number;
  sec_ejec: string;
  nro_orden: number;
  tipo_bien: string;
  exp_siaf: string | null;
  exp_siga: string | null;
  /** Estado de la orden SIGA ('1' vigente, '4' anulada, ...). */
  estado: string | null;
  /** Estado en SIAF ('2' = devengado). */
  estado_siaf: string | null;
  total_fact_soles: number | null;
  concepto: string | null;
  fecha_orden: string | null;
  nro_contrato: number | null;
  ano_contrato: number | null;
  sec_contrato: number | null;
  proveedor_ruc: string | null;
  proveedor_nombre: string | null;
}

export interface PedidoOrigenItem {
  nro_pedido: number;
  tipo_bien: string;
  centro_costo: string | null;
  sec_func: number | null;
  fecha_pedido: string | null;
  estado_pedido: string | null;
  motivo: string | null;
  solicitante: string | null;
  nro_orden: number | null;
}

export interface CertificacionItem {
  nro_certifica: number | null;
  clasificador: string | null;
  valor_soles: number | null;
  fecha_reg: string | null;
}

export interface ConsolidadoMeta {
  meta: MetaCabecera;
  presupuesto: PresupuestoMeta;
  ordenes: OrdenCruceItem[];
  pedidos: PedidoOrigenItem[];
  certificaciones: CertificacionItem[];
}
