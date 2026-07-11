import { QueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';

/**
 * Función de lógica pura para evaluar si una query debe reintentarse.
 * Rechaza el reintento automático si el error HTTP es 401 (Unauthorized) 
 * o 403 (Forbidden), ya que el interceptor de Axios se encarga del refresco.
 */
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (error && typeof error === 'object' && 'isAxiosError' in error) {
    const axiosError = error as AxiosError;
    const status = axiosError.response?.status;
    if (status === 401 || status === 403) {
      return false;
    }
  }
  // Para otros errores, reintenta máximo 1 vez (failureCount es 0-indexed)
  return failureCount < 1;
}

// Cliente global de TanStack Query
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // DEFAULT: 1 minuto (según cita literal de Docs/actividad-3-arquitectura-tecnica.md §8.3 para datos internos tipo pipeline)
      // Nota: Dominios específicos como datos públicos o saldos requerirán un override a 5 mins en sus respectivos hooks.
      staleTime: 60 * 1000, 
      
      // Desactivamos el refresco al cambiar de pestaña para evitar tráfico innecesario en la API
      refetchOnWindowFocus: false,
      
      // Control centralizado de reintentos
      retry: shouldRetryQuery,
    },
  },
});
