// Helpers de rótulo para el detalle SIAF (Formato A, carga provisional).
//
// El Formato A se carga por mes; el rastro se arma acumulando meses. Estos
// helpers arman el texto que explica hasta dónde llega el dato para que el
// funcionario no confunda "sin dato" con "mes aún no cargado", y detectan el
// caso "Girado/Pagado > Devengado" (parte del devengado está en un mes previo
// no cargado) — ver exp 2049.

import type { FaseExpedienteSiaf } from './types';

const MES_ABREV = [
  '', 'ene', 'feb', 'mar', 'abr', 'may', 'jun',
  'jul', 'ago', 'set', 'oct', 'nov', 'dic',
];

/** "meses cargados: ene–ago" (rango si es contiguo, lista si no). Vacío si []. */
export function etiquetaMesesCargados(meses: number[]): string {
  const ord = [...meses].filter((m) => m >= 1 && m <= 12).sort((a, b) => a - b);
  const primero = ord[0];
  const ultimo = ord[ord.length - 1];
  if (primero === undefined || ultimo === undefined) return '';
  const contiguo = ord.every((m, i) => i === 0 || m === (ord[i - 1] ?? 0) + 1);
  if (contiguo && ord.length > 1) {
    return `meses cargados: ${MES_ABREV[primero]}–${MES_ABREV[ultimo]}`;
  }
  return `meses cargados: ${ord.map((m) => MES_ABREV[m]).join(', ')}`;
}

/**
 * Rótulo completo de procedencia del detalle SIAF: carga provisional + meses.
 * Ej: "Detalle SIAF · carga provisional · meses cargados: jul–ago".
 */
export function selloDetalleSiaf(meses: number[]): string {
  const base = 'Detalle SIAF · carga provisional';
  const cob = etiquetaMesesCargados(meses);
  return cob ? `${base} · ${cob}` : base;
}

/**
 * ¿El rastro está incompleto por falta de meses previos? Es cierto cuando el
 * Girado o el Pagado netos superan al Devengado neto: parte del devengado que
 * los origina ocurrió en un mes que aún no se cargó (caso 2049). Devuelve el
 * texto de aviso, o null si el rastro es coherente.
 */
export function avisoHistoriaIncompleta(fases: FaseExpedienteSiaf[]): string | null {
  const neto = (cod: string) =>
    fases.find((f) => f.fase === cod)?.monto_neto ?? 0;
  const d = neto('D');
  const g = neto('G');
  const p = neto('P');
  // Tolerancia de 1 centavo para redondeos.
  if (d > 0 && (g - d > 0.01 || p - d > 0.01)) {
    return 'Parte del devengado que origina el girado o el pagado está en un mes anterior aún no cargado; el rastro se completará al cargar esos meses.';
  }
  return null;
}
