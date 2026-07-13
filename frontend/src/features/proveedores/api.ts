import { apiClient } from '../../lib/api-client';
import type { ProveedoresParams, ProveedoresListado } from './types';

export async function obtenerProveedoresPublico(params: ProveedoresParams): Promise<ProveedoresListado> {
  const { data } = await apiClient.get<ProveedoresListado>('/publico/proveedores', { params });
  return data;
}
