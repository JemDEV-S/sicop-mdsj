import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import type { KanbanResponse, SaldosListadoResponse, PedidoCard } from './types';

export function useKanban() {
  return useQuery({
    queryKey: ['interno', 'pipeline', 'kanban'],
    queryFn: async () => {
      const { data } = await apiClient.get<KanbanResponse>('/interno/pipeline/kanban');
      return data;
    },
  });
}

export function useSaldos(params?: { page?: number; size?: number; ano?: number }) {
  return useQuery({
    queryKey: ['interno', 'saldos', params],
    queryFn: async () => {
      const { data } = await apiClient.get<SaldosListadoResponse>('/interno/saldos', { params });
      return data;
    },
  });
}

export function usePedidosEstancados() {
  return useQuery({
    queryKey: ['interno', 'alertas', 'pedidos-estancados'],
    queryFn: async () => {
      const { data } = await apiClient.get<PedidoCard[]>('/interno/alertas/pedidos-estancados');
      return data;
    },
  });
}
