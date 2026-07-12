import { useQuery } from '@tanstack/react-query';
import { fetchObrasListado, fetchFunciones, fetchTipologias, fetchObraDetalle, fetchObrasMapa, type FetchObrasParams } from './api';

export function useObras(params: FetchObrasParams) {
  return useQuery({
    queryKey: ['obras', 'listado', params],
    queryFn: () => fetchObrasListado(params),
  });
}

export function useFunciones() {
  return useQuery({
    queryKey: ['obras', 'funciones'],
    queryFn: fetchFunciones,
  });
}

export function useTipologias() {
  return useQuery({
    queryKey: ['obras', 'tipologias'],
    queryFn: fetchTipologias,
  });
}

export function useObra(codigoUnico: string) {
  return useQuery({
    queryKey: ['obras', 'detalle', codigoUnico],
    queryFn: () => fetchObraDetalle(codigoUnico),
    enabled: !!codigoUnico,
  });
}

export function useObrasMapa(params: Pick<FetchObrasParams, 'ano' | 'funcion'>) {
  return useQuery({
    queryKey: ['obras', 'mapa', params],
    queryFn: () => fetchObrasMapa(params),
    // Override a 5 min. Las coordenadas y el estado del semáforo derivado del MEF
    // provienen de un batch nocturno/diario (T-12/T-13), por lo que 1 min es
    // excesivo y genera refetches ruidosos innecesarios en la sesión del usuario.
    staleTime: 5 * 60 * 1000,
  });
}

