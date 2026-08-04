import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { apiClient } from '@/lib/api-client';
import { useContextoInterno } from '@/store/contexto-interno';
import type { ConsolidadoMeta } from './types';

/**
 * Consolidado de una meta (presupuesto dual + órdenes + certificaciones +
 * pedidos). El año viene del store `contexto-interno`; el `sec_func` es el de
 * la ruta. El backend ya filtra por el alcance de CC del usuario (404 si la
 * meta queda fuera de alcance o no existe).
 */
export function useConsolidadoMeta(secFunc: number | null) {
  const ano = useContextoInterno((s) => s.añoActivo);
  return useQuery({
    queryKey: ['interno', 'cruce', 'meta', secFunc, ano],
    enabled: secFunc != null && Number.isFinite(secFunc),
    retry: (fallidos, error) => {
      // Un 404 (meta inexistente / fuera de alcance) no se reintenta.
      if (error instanceof AxiosError && error.response?.status === 404) return false;
      return fallidos < 2;
    },
    queryFn: async () => {
      const { data } = await apiClient.get<ConsolidadoMeta>(
        `/interno/cruce/meta/${secFunc}`,
        { params: { ano } },
      );
      return data;
    },
  });
}

/** `true` si el error de la query es un 404 (meta no encontrada / fuera de alcance). */
export function esNoEncontrada(error: unknown): boolean {
  return error instanceof AxiosError && error.response?.status === 404;
}

// NOTA: la exportación del consolidado de meta (HU-13 AC-13.4) queda DIFERIDA.
// No existe un reporte backend que exporte una sola meta: `ejecucion_detalle`
// no filtra por `sec_func` (exportaría todas las metas) y `saldos` agrega por
// meta sin el detalle de órdenes/certificaciones/pedidos. Wire-arlo daría un
// archivo con alcance equivocado. Se anota en la guía §5 para crear el reporte
// `consolidado_meta` en un chat de backend.
