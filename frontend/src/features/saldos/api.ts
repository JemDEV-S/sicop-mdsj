import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useContextoInterno } from '@/store/contexto-interno';
import type { SaldosResumen } from '@/features/dashboard/types';
import type { SaldoDetalle, SaldoItem, SaldosListadoResponse } from './types';

/**
 * Hooks del módulo de Saldos. Todos consumen el año + CC activos del store
 * `contexto-interno`; cambiar los chips del topbar dispara refetch porque el
 * `queryKey` incluye ambos valores (patrón confirmado en el dashboard T-44).
 *
 * `centro_costo` se envía solo cuando hay un CC activo. Si es `null` el backend
 * usa el alcance completo del usuario según su rol (RN-04).
 */
function useContextoSaldos() {
  const ano = useContextoInterno((s) => s.añoActivo);
  const ccActivo = useContextoInterno((s) => s.ccActivo);
  return { ano, ccCodigo: ccActivo?.codigo ?? null };
}

function paramsBase(ano: number, ccCodigo: string | null) {
  const p: Record<string, string | number> = { ano };
  if (ccCodigo) p.centro_costo = ccCodigo;
  return p;
}

/** KPIs agregados + bloque MEF oficial (reutiliza el endpoint del dashboard). */
export function useResumenSaldos() {
  const { ano, ccCodigo } = useContextoSaldos();
  return useQuery({
    queryKey: ['interno', 'saldos', 'resumen', ano, ccCodigo],
    queryFn: async () => {
      const { data } = await apiClient.get<SaldosResumen>(
        '/interno/saldos/resumen',
        { params: paramsBase(ano, ccCodigo) },
      );
      return data;
    },
  });
}

interface ListadoParams {
  page: number;
  size: number;
  /** SEC_FUNC exacto (filtro backend nativo). */
  secFunc: number | null;
}

/**
 * Listado paginado de saldos por meta (dual SIGA + MEF).
 *
 * El filtro por semáforo NO existe en el backend: se resuelve en el cliente
 * sobre las filas de la página (ver `secciones/TablaSaldos`). El backend sí
 * filtra por `sec_func`, año y CC.
 */
export function useSaldos({ page, size, secFunc }: ListadoParams) {
  const { ano, ccCodigo } = useContextoSaldos();
  return useQuery({
    queryKey: ['interno', 'saldos', 'listado', ano, ccCodigo, page, size, secFunc],
    queryFn: async () => {
      const params: Record<string, string | number> = {
        ...paramsBase(ano, ccCodigo),
        page,
        size,
      };
      if (secFunc != null) params.sec_func = secFunc;
      const { data } = await apiClient.get<SaldosListadoResponse>(
        '/interno/saldos',
        { params },
      );
      return data;
    },
    // Mantener la página previa visible mientras llega la nueva (sin parpadeo).
    placeholderData: (prev) => prev,
  });
}

/**
 * Detalle drill-down de una meta: cabecera dual + composición SIGA por
 * clasificador y por fuente. Solo se ejecuta cuando `secFunc != null` (el panel
 * se abre bajo demanda al expandir una fila).
 */
export function useDetalleMeta(secFunc: number | null) {
  const { ano, ccCodigo } = useContextoSaldos();
  return useQuery({
    queryKey: ['interno', 'saldos', 'detalle', ano, ccCodigo, secFunc],
    enabled: secFunc != null,
    queryFn: async () => {
      const { data } = await apiClient.get<SaldoDetalle>(
        `/interno/saldos/meta/${secFunc}/detalle`,
        { params: paramsBase(ano, ccCodigo) },
      );
      return data;
    },
  });
}

export type { SaldoItem };

/**
 * Descarga un reporte de saldos (Excel o PDF) con los filtros de contexto
 * aplicados. Devuelve el blob y dispara la descarga en el navegador.
 *
 * El backend ya respeta `centro_costo` (subrama del usuario) y exporta el
 * esquema DUAL completo: columnas SIGA (fases previas) + MEF (devengado/girado
 * oficiales). El reporte `saldos_detalle` exporta la composición por
 * clasificador de una meta (requiere `sec_func`).
 */
export async function descargarSaldos(
  formato: 'excel' | 'pdf',
  filtros: { ano: number; centro_costo?: string; sec_func?: number },
  reporte: 'saldos' | 'saldos_detalle' = 'saldos',
): Promise<void> {
  const ruta = formato === 'excel' ? 'excel' : 'pdf';
  const { data, headers } = await apiClient.post(
    `/interno/exportar/${ruta}`,
    { reporte, filtros },
    { responseType: 'blob' },
  );

  const disposition = String(headers['content-disposition'] ?? '');
  const match = disposition.match(/filename="?([^"]+)"?/);
  const ext = formato === 'excel' ? 'xlsx' : 'pdf';
  const nombre = match?.[1] ?? `${reporte}_${filtros.ano}.${ext}`;

  const url = URL.createObjectURL(data as Blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
