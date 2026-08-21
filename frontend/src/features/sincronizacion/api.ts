import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  CargaFormatoAResultado,
  EstadoSincronizacion,
  TriggerManual,
} from './types';

/**
 * Hooks de la vista de estado de sincronizaciones (admin-only).
 *
 * El estado se auto-refresca cada 15s para que la pantalla "respire" mientras
 * un job corre. Es transversal: no depende del año ni del CC activos.
 */

const REFRESCO_MS = 15_000;

export function useEstadoSincronizacion() {
  return useQuery({
    queryKey: ['admin', 'sincronizacion', 'estado'],
    queryFn: async () => {
      const { data } = await apiClient.get<EstadoSincronizacion>(
        '/admin/jobs/estado',
      );
      return data;
    },
    refetchInterval: REFRESCO_MS,
    // No parpadear entre refrescos: mantener la foto previa mientras llega.
    placeholderData: (prev) => prev,
  });
}

/**
 * Dispara un sync manual (SIAF o Invierte). El backend responde 202 con un
 * job_id; la corrida se refleja luego en el estado (auto-refresh). Al terminar
 * se invalida el estado para traer la foto fresca de inmediato.
 */
export function useTriggerSync() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (trigger: TriggerManual) => {
      const { data } = await apiClient.post<{ job_id: string; nombre: string }>(
        `/admin/jobs/${trigger}`,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'sincronizacion', 'estado'] });
    },
  });
}

/**
 * Sube un Excel del "Formato A" del SIAF (carga provisional del detalle por
 * documento). El backend deduce año y mes de la cabecera del reporte y reemplaza
 * solo ese mes (swap por año+mes): así se carga el histórico mes a mes y el mes
 * en curso se recarga a diario sin duplicar. Al terminar, invalida el estado de
 * sincronización para que la corrida aparezca en el historial.
 */
export function useCargarFormatoA() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (archivo: File): Promise<CargaFormatoAResultado> => {
      const form = new FormData();
      form.append('archivo', archivo);
      const { data } = await apiClient.post<CargaFormatoAResultado>(
        '/admin/jobs/cargar-formato-a',
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'sincronizacion', 'estado'] });
      // El detalle SIAF cambió: refrescar lo que lo consume (modales, reportes).
      qc.invalidateQueries({ queryKey: ['interno', 'expediente-siaf'] });
      qc.invalidateQueries({ queryKey: ['interno', 'ejecucion-siaf-agregada'] });
    },
  });
}
