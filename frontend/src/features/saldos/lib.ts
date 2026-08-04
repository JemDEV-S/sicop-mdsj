import type { EstadoSemaforo } from '@/lib/semaforo';
import type { SemaforoSaldo } from './types';

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
