import { apiClient } from '../../lib/api-client';
import type { ObraListadoResponse, ObraDetalleResponse, ObrasMapaResponse } from './types';

/**
 * Función defensiva para garantizar tipado estricto en el componente visual Semaforo.
 * Retorna null si el backend envía 'desconocido' o cualquier valor que no coincida
 * exactamente con los permitidos por la UI.
 */
export function mapSemaforoApiToEstado(valor: string): 'ok' | 'alerta' | 'critico' | null {
  if (valor === 'ok' || valor === 'alerta' || valor === 'critico') {
    return valor;
  }
  return null;
}

export interface FetchObrasParams {
  ano?: number;
  funcion?: string;
  tipologia?: string;
  modalidad?: string;
  q?: string;
  page?: number;
  size?: number;
  sort?: string;
}

export async function fetchObrasListado(params: FetchObrasParams): Promise<ObraListadoResponse> {
  const { data } = await apiClient.get<ObraListadoResponse>('/publico/obras', {
    params
  });
  return data;
}

export async function fetchObrasMapa(params: Pick<FetchObrasParams, 'ano' | 'funcion'>): Promise<ObrasMapaResponse> {
  const { data } = await apiClient.get<ObrasMapaResponse>('/publico/obras/mapa', {
    params
  });
  return data;
}

export async function fetchFunciones(): Promise<string[]> {
  const { data } = await apiClient.get<string[]>('/publico/obras/funciones');
  return data;
}

export async function fetchTipologias(): Promise<string[]> {
  const { data } = await apiClient.get<string[]>('/publico/obras/tipologias');
  return data;
}

export async function fetchObraDetalle(codigoUnico: string): Promise<ObraDetalleResponse> {
  const { data } = await apiClient.get<ObraDetalleResponse>(`/publico/obras/${codigoUnico}`);
  return data;
}
