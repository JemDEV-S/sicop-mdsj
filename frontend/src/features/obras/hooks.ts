import { useQuery } from '@tanstack/react-query';
import { fetchObrasListado, fetchFunciones, fetchTipologias, FetchObrasParams } from './api';

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
