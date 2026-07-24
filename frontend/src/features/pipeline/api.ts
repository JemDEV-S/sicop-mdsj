import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useContextoInterno } from '@/store/contexto-interno';
import type { Anotacion, Bolsa, PedidoDetalle, Resolucion } from './types';

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

// ─── Bolsa y resolución manual pedido ↔ CCMN ─────────────────────────────
//
// SIGA no registra qué CCMN corresponde a qué pedido (§1 del doc de
// refactorización). Estos hooks alimentan la vista de bolsa, donde el
// funcionario ve el contexto completo y puede declarar la correspondencia.

interface UseBolsaParams {
  nroPedido: number;
  tipoBien: string;
  tipoPedido: string;
  /** No consulta si el pedido todavía no está programado. */
  habilitado?: boolean;
}

export function useBolsaPedido({
  nroPedido,
  tipoBien,
  tipoPedido,
  habilitado = true,
}: UseBolsaParams) {
  const ano = useContextoInterno((s) => s.añoActivo);
  return useQuery({
    queryKey: ['interno', 'pedido', 'bolsa', ano, nroPedido, tipoBien, tipoPedido],
    queryFn: async () => {
      const { data } = await apiClient.get<Bolsa>(
        `/interno/pedidos/${nroPedido}/${tipoBien}/${tipoPedido}/bolsa`,
        { params: { ano } },
      );
      return data;
    },
    enabled: habilitado && Boolean(tipoPedido),
    refetchOnWindowFocus: false,
  });
}

export function useResolucionesPedido({
  nroPedido,
  tipoBien,
  tipoPedido,
  habilitado = true,
}: UseBolsaParams) {
  const ano = useContextoInterno((s) => s.añoActivo);
  return useQuery({
    queryKey: ['interno', 'pedido', 'resoluciones', ano, nroPedido, tipoBien, tipoPedido],
    queryFn: async () => {
      const { data } = await apiClient.get<Resolucion[]>(
        `/interno/pedidos/${nroPedido}/${tipoBien}/${tipoPedido}/resoluciones`,
        { params: { ano, incluir_revocadas: true } },
      );
      return data;
    },
    enabled: habilitado && Boolean(tipoPedido),
    refetchOnWindowFocus: false,
  });
}

/** Invalida todo lo que cambia al asociar o revocar: detalle, bolsa y lista. */
function useInvalidarPedido(nroPedido: number, tipoBien: string) {
  const queryClient = useQueryClient();
  return () => {
    for (const key of ['detalle', 'bolsa', 'resoluciones']) {
      void queryClient.invalidateQueries({
        queryKey: ['interno', 'pedido', key],
      });
    }
    void queryClient.invalidateQueries({ queryKey: ['interno', 'pipeline'] });
  };
}

export function useAsociarCcmn({ nroPedido, tipoBien, tipoPedido }: UseBolsaParams) {
  const ano = useContextoInterno((s) => s.añoActivo);
  const invalidar = useInvalidarPedido(nroPedido, tipoBien);
  return useMutation({
    mutationFn: async (params: { nroConsolid: number; nota?: string }) => {
      const { data } = await apiClient.post<Resolucion>(
        `/interno/pedidos/${nroPedido}/${tipoBien}/resoluciones`,
        {
          tipo_pedido: tipoPedido,
          nro_consolid: params.nroConsolid,
          nota: params.nota ?? null,
          ano_eje: ano,
        },
      );
      return data;
    },
    onSuccess: invalidar,
  });
}

export function useRevocarCcmn({ nroPedido, tipoBien }: UseBolsaParams) {
  const invalidar = useInvalidarPedido(nroPedido, tipoBien);
  return useMutation({
    mutationFn: async (resolucionId: string) => {
      await apiClient.delete(`/interno/pedidos/resoluciones/${resolucionId}`);
      return resolucionId;
    },
    onSuccess: invalidar,
  });
}
