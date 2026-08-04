import type { OrdenProveedor } from './types';

// ─── Identidad del proveedor ────────────────────────────────────────────────

/**
 * Persona jurídica (empresa) vs. natural. Códigos SIGA verificados:
 * '02'/'2'/'J' = jurídica, '01'/'1'/'N' = natural. Si viene null, se decide por
 * el RUC (los peruanos que empiezan con "20" son jurídicos, "10" naturales).
 * (Misma regla que el directorio público — features/proveedores.)
 */
export function esPersonaJuridica(tipoPersona: string | null, ruc: string | null): boolean {
  if (tipoPersona === 'J' || tipoPersona === '2' || tipoPersona === '02') return true;
  if (tipoPersona === 'N' || tipoPersona === '1' || tipoPersona === '01') return false;
  return ruc?.startsWith('20') ?? false;
}

export function tipoPersonaLabel(tipoPersona: string | null, ruc: string | null): string {
  return esPersonaJuridica(tipoPersona, ruc) ? 'Persona jurídica' : 'Persona natural';
}

/** Flag SIGA en verdad ('S'/'1'/'Y'/'SI'). */
export function esFlagVerdad(flag: string | null): boolean {
  if (!flag) return false;
  const f = flag.trim().toUpperCase();
  return f === 'S' || f === '1' || f === 'Y' || f === 'SI';
}

export function tipoBienLabel(tipo: string | null): string {
  if (tipo === 'B') return 'Bien';
  if (tipo === 'S') return 'Servicio';
  return tipo ?? '—';
}

// ─── Órdenes (estados autoritativos verificados) ────────────────────────────

/** `estado='4'` = orden anulada (verificado, migración d5e6f7a8b9c2). */
export function ordenAnulada(estado: string | null): boolean {
  return estado === '4';
}

/** `estado_siaf='2'` = orden devengada en SIAF (bien/servicio recibido). */
export function ordenDevengadaSiaf(estadoSiaf: string | null): boolean {
  return estadoSiaf === '2';
}

/** KPIs del historial de órdenes (fuente real, ya que el detalle trae null). */
export function resumenOrdenes(ordenes: OrdenProveedor[]) {
  const vigentes = ordenes.filter((o) => !ordenAnulada(o.estado));
  const total = vigentes.reduce((acc, o) => acc + (o.total_fact_soles ?? 0), 0);
  const fechas = ordenes
    .map((o) => o.fecha_orden)
    .filter((f): f is string => !!f)
    .sort();
  return {
    montoTotal: total,
    nroOrdenes: vigentes.length,
    ultimaFecha: fechas.length ? fechas[fechas.length - 1] : null,
  };
}

// ─── Contratos por vencer: urgencia por días restantes ──────────────────────
//
// Esto es un semáforo de URGENCIA de la UI (no un umbral de negocio configurado):
// cuánto apremia renovar/cerrar. Rojo ≤7 días, ámbar ≤15, neutro el resto.

export type UrgenciaVencimiento = 'critico' | 'alerta' | 'neutro';

export function urgenciaVencimiento(dias: number | null): UrgenciaVencimiento {
  if (dias == null) return 'neutro';
  if (dias <= 7) return 'critico';
  if (dias <= 15) return 'alerta';
  return 'neutro';
}

/** Referencia de contrato como la reconoce el funcionario: NNN-AAAA. */
export function refContrato(nro: number, ano: number): string {
  return `${nro}-${ano}`;
}
