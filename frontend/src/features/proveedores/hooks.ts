import { useQuery } from '@tanstack/react-query';
import { obtenerProveedoresPublico } from './api';
import type { ProveedoresParams } from './types';

export const PROVEEDORES_QUERY_KEYS = {
  all: ['proveedores'] as const,
  publico: (params: ProveedoresParams) => [...PROVEEDORES_QUERY_KEYS.all, 'publico', params] as const,
};

export function useProveedoresPublico(params: ProveedoresParams) {
  return useQuery({
    queryKey: PROVEEDORES_QUERY_KEYS.publico(params),
    queryFn: () => obtenerProveedoresPublico(params),
    staleTime: 5 * 60 * 1000,
  });
}
