import { useQuery } from '@tanstack/react-query';
import { fetchFotosObra, fetchDocumentosObra } from './api';

export function useFotosObra(codigoUnico: string) {
  return useQuery({
    queryKey: ['obras', 'fotos', codigoUnico],
    queryFn: () => fetchFotosObra(codigoUnico),
    enabled: !!codigoUnico,
    staleTime: 5 * 60 * 1000,
  });
}

export function useDocumentosObra(codigoUnico: string) {
  return useQuery({
    queryKey: ['obras', 'documentos', codigoUnico],
    queryFn: () => fetchDocumentosObra(codigoUnico),
    enabled: !!codigoUnico,
    staleTime: 5 * 60 * 1000,
  });
}
