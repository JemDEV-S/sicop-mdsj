/**
 * Capa de datos del Dashboard Interno (HU-22).
 *
 * Hook de React Query que consume GET /api/v1/interno/dashboard.
 * Requiere autenticación (ruta protegida por RequireAuth).
 */
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import type { DashboardResponse } from './types';

const DASHBOARD_KEY = ['interno', 'dashboard'] as const;

async function fetchDashboard(): Promise<DashboardResponse> {
  const { data } = await apiClient.get<DashboardResponse>('/interno/dashboard');
  return data;
}

/**
 * Hook para obtener los datos del dashboard del funcionario.
 * staleTime de 60s heredado del QueryClient global (T-35).
 */
export function useDashboard() {
  return useQuery({
    queryKey: DASHBOARD_KEY,
    queryFn: fetchDashboard,
  });
}
