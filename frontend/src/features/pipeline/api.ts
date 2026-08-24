import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useContextoInterno } from '@/store/contexto-interno';
import type {
  Anotacion,
  Bolsa,
  DetalleExpedienteSiaf,
  EjecucionAgregadaSiaf,
  PedidoDetalle,
  Resolucion,
} from './types';
import type { ReporteResponse } from './reporte-types';

// El backend acepta entidad_id como string; usamos "NRO-TIPO" (no barra, que
// rompe el matcheo del path).
export function anotacionEntidadId(nroPedido: number, tipoBien: string): string {
  return `${nroPedido}-${tipoBien}`;
}

interface UseDetalleParams {
  nroPedido: number;
  tipoBien: string;
}

interface UseDetalleConTipoParams extends UseDetalleParams {
  tipoPedido: string;
}

export function useDetallePedido({
  nroPedido,
  tipoBien,
  tipoPedido,
}: UseDetalleConTipoParams) {
  const ano = useContextoInterno((s) => s.añoActivo);
  return useQuery({
    queryKey: ['interno', 'pedido', 'detalle', ano, nroPedido, tipoBien, tipoPedido],
    queryFn: async () => {
      const { data } = await apiClient.get<PedidoDetalle>(
        `/interno/pedidos/${nroPedido}/${tipoBien}/${tipoPedido}`,
        { params: { ano } },
      );
      return data;
    },
    enabled: Boolean(tipoPedido),
    // El detalle es una foto momentánea del pedido; no refetch al focus.
    refetchOnWindowFocus: false,
  });
}

// ─── Vista profesional: reporte Meta → Clasificador → Pedido (§9.7) ──────

/**
 * Reporte del pipeline con el cruce SIGA × SIAF por clasificador de gasto.
 * Consume año + CC del contexto interno (igual que el kanban). El backend
 * aplica el alcance por CC (RN-06) y calcula los montos MEF sin doble conteo.
 */
export function useReportePipeline() {
  const ano = useContextoInterno((s) => s.añoActivo);
  const cc = useContextoInterno((s) => s.ccActivo);
  const ccCodigo = cc?.codigo ?? null;
  return useQuery({
    queryKey: ['interno', 'pipeline', 'reporte', ano, ccCodigo],
    queryFn: async () => {
      const params: Record<string, string | number> = { ano };
      if (ccCodigo) params.centro_costo = ccCodigo;
      const { data } = await apiClient.get<ReporteResponse>(
        '/interno/pipeline/reporte',
        { params },
      );
      return data;
    },
  });
}

// Filtros del reporte pipeline. `sec_func`/`categoria` recortan el ámbito igual
// que la vista (una meta puntual, o Producto/Proyecto) para que el archivo
// coincida con lo mostrado; ambos son opcionales (sin ellos, todo el ámbito CC).
export interface FiltrosReportePipeline {
  ano: number;
  centro_costo?: string;
  sec_func?: number;
  categoria?: 'producto' | 'proyecto';
}

// Dispara la descarga de un blob en el navegador con el nombre del servidor.
function descargarBlob(data: Blob, headers: Record<string, unknown>, nombreDefecto: string) {
  const disposition = String(headers['content-disposition'] ?? '');
  const match = disposition.match(/filename="?([^"]+)"?/);
  const nombre = match?.[1] ?? nombreDefecto;
  const url = URL.createObjectURL(data);
  const a = document.createElement('a');
  a.href = url;
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/**
 * Descarga el reporte del pipeline en Excel (auditado en el backend, RN-08).
 */
export async function descargarReportePipeline(filtros: FiltrosReportePipeline): Promise<void> {
  const { data, headers } = await apiClient.post(
    '/interno/exportar/excel',
    { reporte: 'pipeline_reporte', filtros },
    { responseType: 'blob' },
  );
  descargarBlob(data as Blob, headers, `pipeline_reporte_${filtros.ano}.xlsx`);
}

/**
 * Descarga el reporte del pipeline en PDF (auditado en el backend, RN-08).
 * Mismos filtros que la vista para que el documento sea fiel a lo que se ve.
 */
export async function descargarReportePipelinePdf(filtros: FiltrosReportePipeline): Promise<void> {
  const { data, headers } = await apiClient.post(
    '/interno/exportar/pdf',
    { reporte: 'pipeline_reporte', filtros },
    { responseType: 'blob' },
  );
  descargarBlob(data as Blob, headers, `pipeline_reporte_${filtros.ano}.pdf`);
}

// ─── Detalle SIAF por expediente (Formato A, Fase 1) ─────────────────────

/**
 * Detalle SIAF por fase de un expediente (Certificación/Devengado/Girado/
 * Pagado netados con proveedor y documentos). Rompe la ceguera SIAF del
 * pipeline. Es carga PROVISIONAL: nunca un total de tablero. Si no hay Formato
 * A cargado, `tiene_datos=false` con `fases=[]` (la UI muestra estado vacío).
 */
export function useDetalleExpedienteSiaf(expSiaf: number | null | undefined) {
  const ano = useContextoInterno((s) => s.añoActivo);
  return useQuery({
    queryKey: ['interno', 'expediente-siaf', ano, expSiaf],
    queryFn: async () => {
      const { data } = await apiClient.get<DetalleExpedienteSiaf>(
        `/interno/pipeline/expediente-siaf/${expSiaf}/detalle`,
        { params: { ano } },
      );
      return data;
    },
    enabled: expSiaf != null,
    refetchOnWindowFocus: false,
  });
}

// ─── Ejecución SIAF agregada (Fase 2: proveedor / clasificador / rubro) ──

/**
 * Ejecución SIAF vigente agregada por la dimensión pedida. El detalle que la
 * API MEF no da (RUC, clasificador de 5 niveles). Consume año + CC del contexto
 * interno; el backend aplica el alcance por CC. Carga provisional (rotulada).
 */
export function useEjecucionSiafAgregada(
  groupBy: 'proveedor' | 'clasificador' | 'rubro',
) {
  const ano = useContextoInterno((s) => s.añoActivo);
  const cc = useContextoInterno((s) => s.ccActivo);
  const ccCodigo = cc?.codigo ?? null;
  return useQuery({
    queryKey: ['interno', 'ejecucion-siaf-agregada', ano, ccCodigo, groupBy],
    queryFn: async () => {
      const params: Record<string, string | number> = { ano, group_by: groupBy };
      if (ccCodigo) params.centro_costo = ccCodigo;
      const { data } = await apiClient.get<EjecucionAgregadaSiaf>(
        '/interno/pipeline/ejecucion-siaf/agregados',
        { params },
      );
      return data;
    },
  });
}

export function useAnotacionesPedido({ nroPedido, tipoBien }: UseDetalleParams) {
  const entidadId = anotacionEntidadId(nroPedido, tipoBien);
  return useQuery({
    queryKey: ['interno', 'anotaciones', 'pedido', entidadId],
    queryFn: async () => {
      const { data } = await apiClient.get<Anotacion[]>(
        `/interno/anotaciones/pedido/${entidadId}`,
      );
      return data;
    },
  });
}

export function useCrearAnotacionPedido({ nroPedido, tipoBien }: UseDetalleParams) {
  const entidadId = anotacionEntidadId(nroPedido, tipoBien);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (texto: string) => {
      const { data } = await apiClient.post<Anotacion>(
        `/interno/anotaciones/pedido/${entidadId}`,
        { texto },
      );
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ['interno', 'anotaciones', 'pedido', entidadId],
      });
    },
  });
}

export function useEliminarAnotacionPedido({ nroPedido, tipoBien }: UseDetalleParams) {
  const entidadId = anotacionEntidadId(nroPedido, tipoBien);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (anotacionId: number) => {
      await apiClient.delete(`/interno/anotaciones/${anotacionId}`);
      return anotacionId;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ['interno', 'anotaciones', 'pedido', entidadId],
      });
    },
  });
}

// ─── Bolsa y resolución manual pedido ↔ CCMN ─────────────────────────────
//
// SIGA no registra qué CCMN corresponde a qué pedido (§1 del doc de
// refactorización). Estos hooks alimentan la vista de bolsa, donde el
// funcionario ve el contexto completo y puede declarar la correspondencia.

interface UseBolsaParams {
  nroPedido: number;
  tipoBien: string;
  tipoPedido: string;
  /** No consulta si el pedido todavía no está programado. */
  habilitado?: boolean;
}

export function useBolsaPedido({
  nroPedido,
  tipoBien,
  tipoPedido,
  habilitado = true,
}: UseBolsaParams) {
  const ano = useContextoInterno((s) => s.añoActivo);
  return useQuery({
    queryKey: ['interno', 'pedido', 'bolsa', ano, nroPedido, tipoBien, tipoPedido],
    queryFn: async () => {
      const { data } = await apiClient.get<Bolsa>(
        `/interno/pedidos/${nroPedido}/${tipoBien}/${tipoPedido}/bolsa`,
        { params: { ano } },
      );
      return data;
    },
    enabled: habilitado && Boolean(tipoPedido),
    refetchOnWindowFocus: false,
  });
}

export function useResolucionesPedido({
  nroPedido,
  tipoBien,
  tipoPedido,
  habilitado = true,
}: UseBolsaParams) {
  const ano = useContextoInterno((s) => s.añoActivo);
  return useQuery({
    queryKey: ['interno', 'pedido', 'resoluciones', ano, nroPedido, tipoBien, tipoPedido],
    queryFn: async () => {
      const { data } = await apiClient.get<Resolucion[]>(
        `/interno/pedidos/${nroPedido}/${tipoBien}/${tipoPedido}/resoluciones`,
        { params: { ano, incluir_revocadas: true } },
      );
      return data;
    },
    enabled: habilitado && Boolean(tipoPedido),
    refetchOnWindowFocus: false,
  });
}

/** Invalida todo lo que cambia al asociar o revocar: detalle, bolsa y lista. */
function useInvalidarPedido() {
  const queryClient = useQueryClient();
  return () => {
    for (const key of ['detalle', 'bolsa', 'resoluciones']) {
      void queryClient.invalidateQueries({
        queryKey: ['interno', 'pedido', key],
      });
    }
    void queryClient.invalidateQueries({ queryKey: ['interno', 'pipeline'] });
  };
}

export function useAsociarCcmn({ nroPedido, tipoBien, tipoPedido }: UseBolsaParams) {
  const ano = useContextoInterno((s) => s.añoActivo);
  const invalidar = useInvalidarPedido();
  return useMutation({
    mutationFn: async (params: { nroConsolid: number; nota?: string }) => {
      const { data } = await apiClient.post<Resolucion>(
        `/interno/pedidos/${nroPedido}/${tipoBien}/resoluciones`,
        {
          tipo_pedido: tipoPedido,
          nro_consolid: params.nroConsolid,
          nota: params.nota ?? null,
          ano_eje: ano,
        },
      );
      return data;
    },
    onSuccess: invalidar,
  });
}

/** Refresca UN pedido desde SIGA (§01.3) e invalida su detalle/bolsa. */
export function useRefrescarPedido({
  nroPedido,
  tipoBien,
  tipoPedido,
}: UseBolsaParams) {
  const ano = useContextoInterno((s) => s.añoActivo);
  const invalidar = useInvalidarPedido();
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post<{
        refrescado: boolean;
        total: number;
      }>(
        `/interno/pedidos/${nroPedido}/${tipoBien}/${tipoPedido}/refrescar`,
        null,
        { params: { ano } },
      );
      return data;
    },
    onSuccess: invalidar,
  });
}

export function useRevocarCcmn(_params: UseBolsaParams) {
  const invalidar = useInvalidarPedido();
  return useMutation({
    mutationFn: async (resolucionId: string) => {
      await apiClient.delete(`/interno/pedidos/resoluciones/${resolucionId}`);
      return resolucionId;
    },
    onSuccess: invalidar,
  });
}
