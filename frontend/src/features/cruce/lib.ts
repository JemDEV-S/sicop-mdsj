import type { EstadoSemaforo } from '@/lib/semaforo';
import type { OrdenCruceItem, SemaforoSaldo } from './types';

/**
 * El endpoint /cruce/meta NO devuelve un `semaforo` pre-calculado (a diferencia
 * de /saldos). Para mostrar el MISMO color que el resto del sistema, replicamos
 * los umbrales del backend (`sistema.umbrales_semaforos`, módulo saldos:
 * verde ≥90%, amarillo ≥60%, rojo <60% sobre el devengado MEF real).
 *
 * Verificado coherente: meta 129 = 44.87% → 'rojo', igual que /saldos.
 */
export function semaforoDesdePorcentaje(pct: number | null): SemaforoSaldo {
  if (pct == null) return 'desconocido';
  if (pct >= 90) return 'verde';
  if (pct >= 60) return 'amarillo';
  return 'rojo';
}

export function mapSemaforo(valor: SemaforoSaldo): EstadoSemaforo | null {
  if (valor === 'verde') return 'ok';
  if (valor === 'amarillo') return 'alerta';
  if (valor === 'rojo') return 'critico';
  return null;
}

export function etiquetaSemaforo(valor: SemaforoSaldo, pct: number | null): string {
  if (valor === 'desconocido' || pct == null) return 'Sin dato MEF';
  const s = `${pct.toFixed(1)}% devengado`;
  if (valor === 'verde') return `En avance · ${s}`;
  if (valor === 'amarillo') return `En atención · ${s}`;
  return `En riesgo · ${s}`;
}

/** Meta como el funcionario la reconoce: SEC_FUNC de 4 dígitos. */
export function formatSecFunc(secFunc: number): string {
  return String(secFunc).padStart(4, '0');
}

/** Tipo de bien/servicio a partir del código SIGA. */
export function tipoBienLabel(tipo: string | null): string {
  if (tipo === 'B') return 'Bien';
  if (tipo === 'S') return 'Servicio';
  return tipo ?? '—';
}

// ─── Estados (solo se etiqueta lo autoritativo; el resto muestra el código) ──

/**
 * Estado de la orden SIGA. Código autoritativo verificado: '4' = anulada
 * (migración d5e6f7a8b9c2). El resto son estados de trámite; se muestra el
 * código para no inventar significados.
 */
export function ordenAnulada(estado: string | null): boolean {
  return estado === '4';
}

/**
 * `estado_siaf = '2'` ⇒ la orden ya está devengada en SIAF (bien/servicio
 * recibido, obligación de pago). Es el hito que interesa al funcionario.
 */
export function ordenDevengadaSiaf(estadoSiaf: string | null): boolean {
  return estadoSiaf === '2';
}

/** Suma del importe facturado de las órdenes NO anuladas. */
export function totalOrdenes(ordenes: OrdenCruceItem[]): number {
  return ordenes
    .filter((o) => !ordenAnulada(o.estado))
    .reduce((acc, o) => acc + (o.total_fact_soles ?? 0), 0);
}
