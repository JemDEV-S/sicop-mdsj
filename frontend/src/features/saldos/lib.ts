import type { EstadoSemaforo } from '@/lib/semaforo';
import type { SemaforoContexto, SemaforoSaldo } from './types';

/**
 * El backend de saldos emite 'verde' | 'amarillo' | 'rojo' | 'desconocido'
 * (backend/app/services/semaforo_service.py). El componente `Semaforo` del
 * sistema de diseño usa el vocabulario 'ok' | 'alerta' | 'critico'. Este mapeo
 * traduce entre ambos; 'desconocido' devuelve `null` (la meta no cruza con el
 * MEF y no hay % que colorear).
 */
export function mapSemaforo(valor: SemaforoSaldo): EstadoSemaforo | null {
  if (valor === 'verde') return 'ok';
  if (valor === 'amarillo') return 'alerta';
  if (valor === 'rojo') return 'critico';
  return null;
}

/** Etiqueta del semáforo, con el % devengado real cuando existe. */
export function etiquetaSemaforo(
  valor: SemaforoSaldo,
  porcentaje: number | null,
): string {
  if (valor === 'desconocido' || porcentaje == null) return 'Sin dato MEF';
  const pct = `${porcentaje.toFixed(1)}% devengado`;
  if (valor === 'verde') return `En avance · ${pct}`;
  if (valor === 'amarillo') return `En atención · ${pct}`;
  return `En riesgo · ${pct}`;
}

/**
 * Explicación del semáforo TEMPORAL: contrasta el avance real contra el esperado
 * al mes de corte. Da al funcionario el porqué del color, no solo el color.
 * Ej.: "44.9% dev · esperado 58.3% a jul · rezago 13.5 pp".
 */
const MESES_ABREV = [
  'ene', 'feb', 'mar', 'abr', 'may', 'jun',
  'jul', 'ago', 'set', 'oct', 'nov', 'dic',
];

export function explicacionSemaforo(ctx: SemaforoContexto | null): string | null {
  if (!ctx || ctx.real == null || ctx.rezago == null) return null;
  const mes = MESES_ABREV[Math.min(11, Math.max(0, ctx.mes_corte - 1))] ?? '';
  const base = `${ctx.real.toFixed(1)}% dev · esperado ${ctx.esperado.toFixed(1)}% a ${mes}`;
  if (ctx.rezago <= 0) {
    return `${base} · adelantado ${Math.abs(ctx.rezago).toFixed(1)} pp`;
  }
  return `${base} · rezago ${ctx.rezago.toFixed(1)} pp`;
}

/** Etiqueta corta para el resumen global (sin %). */
export function etiquetaSemaforoGlobal(valor: SemaforoSaldo): string {
  if (valor === 'verde') return 'Ejecución en avance';
  if (valor === 'amarillo') return 'Ejecución en atención';
  if (valor === 'rojo') return 'Ejecución en riesgo';
  return 'Sin dato oficial';
}

/** Etiqueta legible para el chip de filtro por semáforo. */
export function etiquetaFiltroSemaforo(valor: SemaforoSaldo): string {
  if (valor === 'verde') return 'En avance';
  if (valor === 'amarillo') return 'En atención';
  if (valor === 'rojo') return 'En riesgo';
  return 'Sin dato MEF';
}

/** SEC_FUNC como el funcionario lo reconoce: 4 dígitos con ceros a la izquierda. */
export function formatSecFunc(secFunc: number): string {
  return String(secFunc).padStart(4, '0');
}
