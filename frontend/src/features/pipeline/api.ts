import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useContextoInterno } from '@/store/contexto-interno';
import type { Anotacion, PedidoDetalle } from './types';

// El backend acepta entidad_id como string; usamos "NRO-TIPO" (no barra, que
// rompe el matcheo del path).
export function anotacionEntidadId(nroPedido: number, tipoBien: string): string {
  return `${nroPedido}-${tipoBien}`;
}

interface UseDetalleParams {
  nroPedido: number;
  tipoBien: string;
}

export function useDetallePedido({ nroPedido, tipoBien }: UseDetalleParams) {
  const ano = useContextoInterno((s) => s.añoActivo);
  return useQuery({
    queryKey: ['interno', 'pedido', 'detalle', ano, nroPedido, tipoBien],
    queryFn: async () => {
      const { data } = await apiClient.get<PedidoDetalle>(
        `/interno/pedidos/${nroPedido}/${tipoBien}`,
        { params: { ano } },
      );
      return data;
    },
    // El detalle es una foto momentánea del pedido; no refetch al focus.
    refetchOnWindowFocus: false,
  });
}

export function useAnotacionesPedido({ nroPedido, tipoBien }: UseDetalleParams) {
  const entidadId = anotacionEntidadId(nroPedido, tipoBien);
  return useQuery({
    queryKey: ['interno', 'anotaciones', 'pedido', entidadId],
    queryFn: async () => {
      const { data } = await apiClient.get<Anotacion[]>(
        `/interno/anotaciones/pedido/${entidadId}`,
      );
      return data;
    },
  });
}

export function useCrearAnotacionPedido({ nroPedido, tipoBien }: UseDetalleParams) {
  const entidadId = anotacionEntidadId(nroPedido, tipoBien);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (texto: string) => {
      const { data } = await apiClient.post<Anotacion>(
        `/interno/anotaciones/pedido/${entidadId}`,
        { texto },
      );
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ['interno', 'anotaciones', 'pedido', entidadId],
      });
    },
  });
}

export function useEliminarAnotacionPedido({ nroPedido, tipoBien }: UseDetalleParams) {
  const entidadId = anotacionEntidadId(nroPedido, tipoBien);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (anotacionId: number) => {
      await apiClient.delete(`/interno/anotaciones/${anotacionId}`);
      return anotacionId;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ['interno', 'anotaciones', 'pedido', entidadId],
      });
    },
  });
}
