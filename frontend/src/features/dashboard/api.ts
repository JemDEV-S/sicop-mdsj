import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { useContextoInterno } from '../../store/contexto-interno';
import type {
  ContratoPorVencer,
  KanbanResponse,
  MetaRezagada,
  PedidoCard,
  SaldosResumen,
} from './types';

/**
 * Todos los hooks del dashboard consumen el año + CC activos del store
 * `contexto-interno`. Cambiar los chips del topbar dispara refetch automático
 * porque el `queryKey` incluye ambos valores.
 *
 * `centro_costo` se envía solo cuando hay un CC activo; si es `null` (usuario
 * sin CC asignado o admin sin foco) el backend usa el alcance completo del
 * usuario (RN-04).
 */
function useContextoDashboard() {
  const ano = useContextoInterno((s) => s.añoActivo);
  const ccActivo = useContextoInterno((s) => s.ccActivo);
  return { ano, ccCodigo: ccActivo?.codigo ?? null };
}

function paramsBase(ano: number, ccCodigo: string | null) {
  const p: Record<string, string | number> = { ano };
  if (ccCodigo) p.centro_costo = ccCodigo;
  return p;
}

export function useKanban() {
  const { ano, ccCodigo } = useContextoDashboard();
  return useQuery({
    queryKey: ['interno', 'pipeline', 'kanban', ano, ccCodigo],
    queryFn: async () => {
      const { data } = await apiClient.get<KanbanResponse>(
        '/interno/pipeline/kanban',
        { params: paramsBase(ano, ccCodigo) },
      );
      return data;
    },
  });
}

export function useResumenSaldos() {
  const { ano, ccCodigo } = useContextoDashboard();
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

export function usePedidosEstancados() {
  const { ano, ccCodigo } = useContextoDashboard();
  return useQuery({
    queryKey: ['interno', 'alertas', 'pedidos-estancados', ano, ccCodigo],
    queryFn: async () => {
      const { data } = await apiClient.get<PedidoCard[]>(
        '/interno/alertas/pedidos-estancados',
        { params: paramsBase(ano, ccCodigo) },
      );
      return data;
    },
  });
}

export function useContratosPorVencer(dias = 30) {
  return useQuery({
    // Los contratos SIGA no están amarrados a CC (ver §5 backend-issues),
    // por eso omitimos ccCodigo del queryKey.
    queryKey: ['interno', 'alertas', 'contratos-por-vencer', dias],
    queryFn: async () => {
      const { data } = await apiClient.get<ContratoPorVencer[]>(
        '/interno/alertas/contratos-por-vencer',
        { params: { dias } },
      );
      return data;
    },
  });
}

export function useMetasRezagadas(umbralPorcentaje = 50) {
  const { ano, ccCodigo } = useContextoDashboard();
  return useQuery({
    queryKey: [
      'interno',
      'saldos',
      'metas-rezagadas',
      ano,
      ccCodigo,
      umbralPorcentaje,
    ],
    queryFn: async () => {
      const { data } = await apiClient.get<MetaRezagada[]>(
        '/interno/saldos/metas-rezagadas',
        {
          params: {
            ...paramsBase(ano, ccCodigo),
            umbral_porcentaje: umbralPorcentaje,
          },
        },
      );
      return data;
    },
  });
}
