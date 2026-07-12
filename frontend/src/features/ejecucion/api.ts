import { apiClient } from '../../lib/api-client';
import type { 
  EjecucionResumen, 
  EjecucionPorFuncion, 
  EjecucionPorFuente, 
  EjecucionMensual,
  EjecucionDetalleFiltros,
  EjecucionDetalleResponse
} from './types';

export interface EjecucionParams {
  ano?: number;
}

export async function fetchEjecucionResumen(params?: EjecucionParams): Promise<EjecucionResumen> {
  const { data } = await apiClient.get<EjecucionResumen>('/publico/ejecucion/resumen', { params });
  return data;
}

export async function fetchEjecucionPorFuncion(params?: EjecucionParams): Promise<EjecucionPorFuncion[]> {
  const { data } = await apiClient.get<EjecucionPorFuncion[]>('/publico/ejecucion/por-funcion', { params });
  return data;
}

export async function fetchEjecucionPorFuente(params?: EjecucionParams): Promise<EjecucionPorFuente[]> {
  const { data } = await apiClient.get<EjecucionPorFuente[]>('/publico/ejecucion/por-fuente', { params });
  return data;
}

export async function fetchEjecucionMensual(params?: EjecucionParams): Promise<EjecucionMensual[]> {
  const { data } = await apiClient.get<EjecucionMensual[]>('/publico/ejecucion/mensual', { params });
  return data;
}

export interface EjecucionDetalleParams extends EjecucionDetalleFiltros {
  page?: number;
  size?: number;
  sort?: string;
}

export async function fetchEjecucionDetalle(params: EjecucionDetalleParams): Promise<EjecucionDetalleResponse> {
  const { data } = await apiClient.get<EjecucionDetalleResponse>('/publico/ejecucion/detalle', { params });
  return data;
}

export async function exportarEjecucionPublico(filtros: EjecucionDetalleFiltros): Promise<void> {
  const response = await apiClient.post(
    '/publico/exportar/excel',
    { reporte: 'ejecucion_detalle', filtros },
    { responseType: 'blob' }
  );
  
  // Extraer el nombre del archivo del header Content-Disposition si es posible
  let filename = 'ejecucion_detalle.xlsx';
  const disposition = response.headers['content-disposition'];
  if (disposition && disposition.indexOf('filename=') !== -1) {
    const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
    const matches = filenameRegex.exec(disposition);
    if (matches != null && matches[1]) { 
      filename = matches[1].replace(/['"]/g, '');
    }
  }

  // Trigger descarga en el navegador
  const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
