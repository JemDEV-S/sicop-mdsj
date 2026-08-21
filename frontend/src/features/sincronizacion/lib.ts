/**
 * Helpers de presentación de la vista de sincronizaciones: etiquetas legibles
 * de los `job` de `logs.sincronizacion` y semáforo por antigüedad.
 */
import type { EstadoCorrida } from './types';

/**
 * Traduce el código `job` (p.ej. "siaf_ejecucion:2026") a algo legible. El año
 * embebido tras `:` se preserva como sufijo. Un código desconocido se muestra
 * tal cual — nunca rompe la UI.
 */
export function etiquetaJob(job: string): string {
  const [base, ano] = job.split(':');
  const BASE: Record<string, string> = {
    siaf_ejecucion: 'SIAF · ejecución',
    invierte: 'Invierte.pe · obras',
    siga_pipeline: 'SIGA · pipeline',
    catalogos_siga: 'SIGA · catálogos',
    // Formato A: carga provisional del detalle SIAF por documento (admin).
    formato_a: 'SIAF · detalle (Formato A)',
    // Nombres de corridas manuales (scheduler._wrap_run).
    sync_siaf: 'SIAF · ejecución (manual)',
    sync_invierte: 'Invierte.pe · obras (manual)',
    sync_siga_pipeline: 'SIGA · pipeline (manual)',
    reconciliacion_siga: 'SIGA · reconciliación (manual)',
    revisar_resoluciones: 'Revisión resoluciones CCMN (manual)',
  };
  const legible = (base ? BASE[base] : undefined) ?? job;
  return ano ? `${legible} (${ano})` : legible;
}

export const ESTADO_ESTILO: Record<EstadoCorrida, string> = {
  exito: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  error: 'bg-destructive/10 text-destructive',
  en_curso: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
};

export const ESTADO_ETIQUETA: Record<EstadoCorrida, string> = {
  exito: 'Éxito',
  error: 'Error',
  en_curso: 'En curso',
};

/** Duración legible entre dos ISO timestamps. `null` si no terminó. */
export function duracion(inicio: string, fin: string | null): string | null {
  if (!fin) return null;
  const ms = new Date(fin).getTime() - new Date(inicio).getTime();
  if (!Number.isFinite(ms) || ms < 0) return null;
  const seg = Math.round(ms / 1000);
  if (seg < 60) return `${seg}s`;
  const min = Math.floor(seg / 60);
  const rem = seg % 60;
  return rem ? `${min}m ${rem}s` : `${min}m`;
}

export type Frescura = 'fresco' | 'atencion' | 'viejo' | 'sin_datos';

/**
 * Semáforo por antigüedad de un timestamp respecto a ahora.
 * - fresco   ≤ 60 min
 * - atencion ≤ 24 h
 * - viejo    > 24 h
 */
export function frescura(iso: string | null): Frescura {
  if (!iso) return 'sin_datos';
  const min = (Date.now() - new Date(iso).getTime()) / 60_000;
  if (!Number.isFinite(min)) return 'sin_datos';
  if (min <= 60) return 'fresco';
  if (min <= 24 * 60) return 'atencion';
  return 'viejo';
}

export const FRESCURA_ESTILO: Record<Frescura, string> = {
  fresco: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  atencion: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  viejo: 'bg-destructive/10 text-destructive',
  sin_datos: 'bg-muted text-muted-foreground',
};

/** Antigüedad legible "hace 3 min / hace 2 h / hace 4 d". */
export function haceCuanto(iso: string | null): string {
  if (!iso) return 'Sin datos';
  const min = (Date.now() - new Date(iso).getTime()) / 60_000;
  if (!Number.isFinite(min) || min < 0) return '—';
  if (min < 1) return 'hace segundos';
  if (min < 60) return `hace ${Math.round(min)} min`;
  const h = min / 60;
  if (h < 24) return `hace ${Math.round(h)} h`;
  return `hace ${Math.round(h / 24)} d`;
}

/** Próxima ejecución legible "en 5 min / en 3 h" o "—" si no está agendada. */
export function enCuanto(iso: string | null): string {
  if (!iso) return '—';
  const min = (new Date(iso).getTime() - Date.now()) / 60_000;
  if (!Number.isFinite(min)) return '—';
  if (min < 1) return 'inminente';
  if (min < 60) return `en ${Math.round(min)} min`;
  const h = min / 60;
  if (h < 24) return `en ${Math.round(h)} h`;
  return `en ${Math.round(h / 24)} d`;
}
