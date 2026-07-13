import { apiClient } from '@/lib/api-client';
import type { DocumentoPublicoItem } from './types';

export async function fetchFotosObra(codigoUnico: string): Promise<DocumentoPublicoItem[]> {
  const { data } = await apiClient.get<DocumentoPublicoItem[]>(
    `/publico/obras/${codigoUnico}/fotos`,
  );
  return data;
}

export async function fetchDocumentosObra(
  codigoUnico: string,
): Promise<DocumentoPublicoItem[]> {
  const { data } = await apiClient.get<DocumentoPublicoItem[]>(
    `/publico/obras/${codigoUnico}/documentos`,
  );
  return data;
}

/**
 * Construye la URL absoluta de descarga/visualización de un archivo público.
 * `/media/uploads/{ruta}` va SIN prefix `/api/v1` (registro directo en el backend).
 */
export function urlDescargaMedia(rutaRelativa: string): string {
  const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
  const rutaLimpia = rutaRelativa.replace(/^\/+/, '');
  return `${base}/media/uploads/${rutaLimpia}`;
}
