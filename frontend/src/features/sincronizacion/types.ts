/**
 * Tipos de la vista de estado de sincronizaciones (admin-only).
 *
 * Espejo de `EstadoSincronizacionResponse` en
 * `backend/app/routers/admin_jobs.py`. Consolida: scheduler embebido + jobs
 * programados + corridas persistidas (logs.sincronizacion) + edad de snapshots.
 */

export type EstadoCorrida = 'en_curso' | 'exito' | 'error';

export interface JobProgramado {
  id: string;
  nombre: string;
  trigger: string;
  proxima_ejecucion: string | null;
}

export interface CorridaPersistida {
  id: number;
  job: string;
  inicio: string;
  fin: string | null;
  estado: EstadoCorrida;
  registros_procesados: number | null;
  error_mensaje: string | null;
}

export interface SnapshotFuente {
  fuente: string;
  ultimo_sync: string | null;
  ok: boolean;
}

export interface CorridaManual {
  job_id: string;
  nombre: string;
  inicio: string;
  fin: string | null;
  estado: string;
  resultado: Record<string, unknown> | null;
  error: string | null;
}

export interface EstadoSincronizacion {
  generado_en: string;
  scheduler_activo: boolean;
  jobs_programados: JobProgramado[];
  ultimas_corridas: CorridaPersistida[];
  snapshots: SnapshotFuente[];
  corridas_manuales: CorridaManual[];
}

/** Nombre del disparador manual disponible en el endpoint admin. */
export type TriggerManual = 'sincronizar-siaf' | 'sincronizar-invierte';

/**
 * Resultado de subir un Excel del Formato A. Espejo de `CargaFormatoAResponse`
 * en `backend/app/routers/admin_jobs.py`.
 */
export interface CargaFormatoAResultado {
  archivo: string;
  ano: number;
  mes: number | null;
  registros: number;
  descartadas: number;
  ejecutora: string | null;
  periodo: string | null;
  resumen_por_fase: Record<string, number>;
}
