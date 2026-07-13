import { useQuery } from '@tanstack/react-query';
import { 
  fetchEjecucionResumen, 
  fetchEjecucionPorFuncion, 
  fetchEjecucionPorFuente, 
  fetchEjecucionMensual,
  fetchEjecucionDetalle,
  exportarEjecucionPublico,
  type EjecucionParams,
  type EjecucionDetalleParams
} from './api';
import { toast } from 'sonner';

export const EJECUCION_QUERY_KEYS = {
  all: ['ejecucion'] as const,
  resumen: (params?: EjecucionParams) => [...EJECUCION_QUERY_KEYS.all, 'resumen', params] as const,
  porFuncion: (params?: EjecucionParams) => [...EJECUCION_QUERY_KEYS.all, 'por-funcion', params] as const,
  porFuente: (params?: EjecucionParams) => [...EJECUCION_QUERY_KEYS.all, 'por-fuente', params] as const,
  mensual: (params?: EjecucionParams) => [...EJECUCION_QUERY_KEYS.all, 'mensual', params] as const,
  detalle: (params: EjecucionDetalleParams) => [...EJECUCION_QUERY_KEYS.all, 'detalle', params] as const,
};

export function useEjecucionResumen(params?: EjecucionParams) {
  return useQuery({
    queryKey: EJECUCION_QUERY_KEYS.resumen(params),
    queryFn: () => fetchEjecucionResumen(params),
    staleTime: 5 * 60 * 1000, // 5 minutos, la data se actualiza por un job de sync
  });
}

export function useEjecucionPorFuncion(params?: EjecucionParams) {
  return useQuery({
    queryKey: EJECUCION_QUERY_KEYS.porFuncion(params),
    queryFn: () => fetchEjecucionPorFuncion(params),
    staleTime: 5 * 60 * 1000,
  });
}

export function useEjecucionPorFuente(params?: EjecucionParams) {
  return useQuery({
    queryKey: EJECUCION_QUERY_KEYS.porFuente(params),
    queryFn: () => fetchEjecucionPorFuente(params),
    staleTime: 5 * 60 * 1000,
  });
}

export function useEjecucionMensual(params?: EjecucionParams) {
  return useQuery({
    queryKey: EJECUCION_QUERY_KEYS.mensual(params),
    queryFn: () => fetchEjecucionMensual(params),
    staleTime: 5 * 60 * 1000,
  });
}

export function useEjecucionDetalle(params: EjecucionDetalleParams) {
  return useQuery({
    queryKey: EJECUCION_QUERY_KEYS.detalle(params),
    queryFn: () => fetchEjecucionDetalle(params),
    staleTime: 5 * 60 * 1000,
  });
}

export function useExportarEjecucionPublico() {
  return {
    exportar: async (filtros: EjecucionDetalleParams) => {
      let toastId: string | number = '';
      try {
        toastId = toast.loading('Generando reporte Excel...');
        // Filtramos paginación
        const { page, size, sort, ...soloFiltros } = filtros;
        await exportarEjecucionPublico(soloFiltros);
        toast.success('Reporte exportado exitosamente', { id: toastId });
      } catch (error: any) {
        console.error('Error exportando reporte', error);
        let mensaje = 'Ocurrió un error al exportar el reporte';
        
        // Axios con responseType='blob' devuelve el error 400 también como Blob.
        if (error.response?.data instanceof Blob) {
          try {
            const text = await error.response.data.text();
            const json = JSON.parse(text);
            if (json.detail) mensaje = json.detail;
          } catch (e) {
            // Ignorar y usar genérico
          }
        } else if (error.response?.data?.detail) {
          mensaje = error.response.data.detail;
        }
        
        toast.error(mensaje, { id: toastId });
        throw error;
      }
    }
  };
}
