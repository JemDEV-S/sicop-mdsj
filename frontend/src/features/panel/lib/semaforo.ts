// Semáforo temporal reutilizable: rezago (esperado − real) → tono + etiqueta.
// Un solo lugar para la regla, compartido por Panel, Análisis y Cruce.

import { formatearNumero } from '@/lib/formatters';
import type { KpiChip, Tono } from '../ui/primitivas';

/** Traduce el color crudo del backend ('verde'|'amarillo'|'rojo') a tono UI. */
export function tonoDeColor(color: string): Tono {
  if (color === 'verde') return 'ok';
  if (color === 'amarillo') return 'alerta';
  if (color === 'rojo') return 'critico';
  return 'neutral';
}

export const ETIQUETA_SEMAFORO: Record<Tono, string> = {
  ok: 'A tiempo',
  alerta: 'En riesgo',
  accent: 'Requiere acción',
  critico: 'Atrasado',
  neutral: 'Sin dato',
  primary: '—',
};

/**
 * Chip de semáforo temporal a partir del % real y el esperado. Devuelve null
 * cuando no hay % (sin PIM / sin ejecución) para no mostrar un estado falso.
 */
export function chipSemaforoTemporal(pct: number | null, esperado: number): KpiChip | undefined {
  if (pct == null) return undefined;
  const rezago = esperado - pct;
  if (rezago <= 0) return { texto: ETIQUETA_SEMAFORO.ok, tono: 'ok' };
  if (rezago <= 10) return { texto: `${ETIQUETA_SEMAFORO.alerta} ${formatearNumero(rezago, 1)} pts`, tono: 'alerta' };
  return { texto: `${ETIQUETA_SEMAFORO.critico} ${formatearNumero(rezago, 1)} pts`, tono: 'critico' };
}
