import re

# 1. Fix DataTable.tsx
with open('frontend/src/components/tabla/DataTable.tsx', 'r') as f:
    dt = f.read()

dt = dt.replace(
    "  onPaginationChange?: (updater: any) => void;\n}",
    "  onPaginationChange?: (updater: any) => void;\n  manualPagination?: boolean;\n  isLoading?: boolean;\n}"
)
dt = dt.replace(
    "manualPagination: pageCount !== undefined,",
    "manualPagination: manualPagination ?? (pageCount !== undefined),"
)

with open('frontend/src/components/tabla/DataTable.tsx', 'w') as f:
    f.write(dt)

# 2. Revert DirectorioProveedores.tsx
with open('frontend/src/pages/publico/DirectorioProveedores.tsx', 'r') as f:
    dp = f.read()

dp = dp.replace(
    "const { data, isError } = useProveedoresPublico({",
    "const { data, isLoading, isError, error } = useProveedoresPublico({"
)
dp = dp.replace(
    "pageCount={data?.total ? Math.ceil(data.total / pageSize) : -1}",
    "pageCount={data?.total ? Math.ceil(data.total / pageSize) : -1}\n            manualPagination={true}\n            isLoading={isLoading}"
)

with open('frontend/src/pages/publico/DirectorioProveedores.tsx', 'w') as f:
    f.write(dp)

# 3. Rewrite dashboard/types.ts
types_content = """export interface PedidoCard {
  ano_eje: number;
  sec_ejec: string;
  nro_pedido: number;
  tipo_bien: string;
  centro_costo?: string | null;
  sec_func?: number | null;
  fecha_pedido?: string | null;
  fecha_aprob?: string | null;
  fecha_atenc?: string | null;
  motivo?: string | null;
  solicitante?: string | null;
  fuente_financ?: string | null;
  monto_total: number;
  items: number;
  tiene_orden: number;
  tiene_conformidad: number;
  esta_devengado: number;
  etapa: string;
  dias_en_etapa?: number | null;
  estancado: boolean;
}

export interface KanbanResponse {
  solicitado: PedidoCard[];
  con_orden: PedidoCard[];
  conformidad: PedidoCard[];
  devengado: PedidoCard[];
  cerrado: PedidoCard[];
}

export interface SaldoItem {
  sec_func: number;
  nombre_meta?: string | null;
  act_proy?: string | null;
  clasificador?: string | null;
  fuente_financ?: string | null;
  centro_costo?: string | null;
  centro_costo_nombre?: string | null;
  pia: number;
  pim: number;
  certificado: number;
  comprometido_anual: number;
  comprometido_mensual: number;
  devengado: number;
  saldo_disponible: number;
  reservado_pedido: number;
  porcentaje_devengado: number;
  semaforo: string;
}

export interface SaldosListadoResponse {
  items: SaldoItem[];
  total: number;
  page: number;
  size: number;
}
"""

with open('frontend/src/features/dashboard/types.ts', 'w') as f:
    f.write(types_content)


# 4. Rewrite dashboard/api.ts
api_content = """import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import type { KanbanResponse, SaldosListadoResponse, PedidoCard } from './types';

export function useKanban() {
  return useQuery({
    queryKey: ['interno', 'pipeline', 'kanban'],
    queryFn: async () => {
      const { data } = await apiClient.get<KanbanResponse>('/interno/pipeline/kanban');
      return data;
    },
  });
}

export function useSaldos(params?: { page?: number; size?: number; ano?: number }) {
  return useQuery({
    queryKey: ['interno', 'saldos', params],
    queryFn: async () => {
      const { data } = await apiClient.get<SaldosListadoResponse>('/interno/saldos', { params });
      return data;
    },
  });
}

export function usePedidosEstancados() {
  return useQuery({
    queryKey: ['interno', 'alertas', 'pedidos-estancados'],
    queryFn: async () => {
      const { data } = await apiClient.get<PedidoCard[]>('/interno/alertas/pedidos-estancados');
      return data;
    },
  });
}
"""

with open('frontend/src/features/dashboard/api.ts', 'w') as f:
    f.write(api_content)
