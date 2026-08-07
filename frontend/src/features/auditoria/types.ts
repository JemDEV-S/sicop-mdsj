/**
 * Tipos de la vista de auditoría (admin-only).
 *
 * Espejo de `backend/app/schemas/auditoria.py`. Lectura de `logs.auditoria`:
 * quién hizo qué, cuándo, desde dónde.
 */

export interface AuditoriaItem {
  id: number;
  usuario_id: string | null;
  usuario_nombre: string | null;
  accion: string;
  detalle: Record<string, unknown> | null;
  ip: string | null;
  user_agent: string | null;
  creado_en: string;
}

export interface AuditoriaListado {
  items: AuditoriaItem[];
  total: number;
  page: number;
  size: number;
}

export interface AccionCatalogo {
  accion: string;
  total: number;
}

export interface FiltrosAuditoria {
  accion: string | null;
  desde: string | null;
  hasta: string | null;
}
