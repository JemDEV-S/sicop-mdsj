import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  AccionCatalogo,
  AuditoriaListado,
  FiltrosAuditoria,
} from './types';

/**
 * Hooks de la vista de auditoría (admin-only). No dependen del año ni del CC
 * activos: la auditoría es transversal a todo el sistema, no de una dependencia.
 */

interface ListadoParams extends FiltrosAuditoria {
  page: number;
  size: number;
}

export function useAuditoria({ accion, desde, hasta, page, size }: ListadoParams) {
  return useQuery({
    queryKey: ['admin', 'auditoria', 'listado', accion, desde, hasta, page, size],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, size };
      if (accion) params.accion = accion;
      if (desde) params.desde = desde;
      if (hasta) params.hasta = hasta;
      const { data } = await apiClient.get<AuditoriaListado>(
        '/interno/admin/auditoria',
        { params },
      );
      return data;
    },
    // Mantener la página previa mientras llega la nueva (sin parpadeo).
    placeholderData: (prev) => prev,
  });
}

/** Catálogo dinámico de acciones presentes en el log — puebla el filtro. */
export function useAccionesAuditoria() {
  return useQuery({
    queryKey: ['admin', 'auditoria', 'acciones'],
    queryFn: async () => {
      const { data } = await apiClient.get<AccionCatalogo[]>(
        '/interno/admin/auditoria/acciones',
      );
      return data;
    },
    // El catálogo cambia poco; no refetch al focus.
    refetchOnWindowFocus: false,
  });
}
