import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  CentroCostoBreve,
  FiltrosUsuarios,
  UsuarioActualizar,
  UsuarioCrear,
  UsuarioDetalle,
  UsuariosListado,
} from './types';

/**
 * Hooks de gestión de usuarios (admin-only). No dependen del año ni del CC
 * activos: la administración es transversal.
 */

const BASE = '/interno/admin/usuarios';

interface ListadoParams extends FiltrosUsuarios {
  page: number;
  size: number;
}

export function useUsuarios({ q, rol, estado, page, size }: ListadoParams) {
  return useQuery({
    queryKey: ['admin', 'usuarios', 'listado', q, rol, estado, page, size],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, size };
      if (q) params.q = q;
      if (rol) params.rol = rol;
      if (estado) params.estado = estado;
      const { data } = await apiClient.get<UsuariosListado>(BASE, { params });
      return data;
    },
    placeholderData: (prev) => prev,
  });
}

export function useCentrosCostoDisponibles(enabled = true) {
  return useQuery({
    queryKey: ['admin', 'usuarios', 'centros-costo'],
    enabled,
    queryFn: async () => {
      const { data } = await apiClient.get<CentroCostoBreve[]>(`${BASE}/centros-costo`);
      return data;
    },
    refetchOnWindowFocus: false,
  });
}

export function useUsuarioDetalle(usuarioId: string | null) {
  return useQuery({
    queryKey: ['admin', 'usuarios', 'detalle', usuarioId],
    enabled: usuarioId != null,
    queryFn: async () => {
      const { data } = await apiClient.get<UsuarioDetalle>(`${BASE}/${usuarioId}`);
      return data;
    },
  });
}

/** Invalida todo lo relacionado con usuarios tras una mutación. */
function useInvalidarUsuarios() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ['admin', 'usuarios'] });
}

export function useCrearUsuario() {
  const invalidar = useInvalidarUsuarios();
  return useMutation({
    mutationFn: async (payload: UsuarioCrear) => {
      const { data } = await apiClient.post<UsuarioDetalle>(BASE, payload);
      return data;
    },
    onSuccess: invalidar,
  });
}

export function useActualizarUsuario() {
  const invalidar = useInvalidarUsuarios();
  return useMutation({
    mutationFn: async ({ id, cambios }: { id: string; cambios: UsuarioActualizar }) => {
      const { data } = await apiClient.patch<UsuarioDetalle>(`${BASE}/${id}`, cambios);
      return data;
    },
    onSuccess: invalidar,
  });
}

export function useResetPassword() {
  const invalidar = useInvalidarUsuarios();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.post(`${BASE}/${id}/reset-password`);
      return data;
    },
    onSuccess: invalidar,
  });
}

export function useAsignarCentro() {
  const invalidar = useInvalidarUsuarios();
  return useMutation({
    mutationFn: async ({
      id,
      centro_costo,
      es_raiz_jerarquia,
    }: {
      id: string;
      centro_costo: string;
      es_raiz_jerarquia: boolean;
    }) => {
      const { data } = await apiClient.post<UsuarioDetalle>(`${BASE}/${id}/centros`, {
        centro_costo,
        es_raiz_jerarquia,
      });
      return data;
    },
    onSuccess: invalidar,
  });
}

export function useQuitarCentro() {
  const invalidar = useInvalidarUsuarios();
  return useMutation({
    mutationFn: async ({ id, centro_costo }: { id: string; centro_costo: string }) => {
      const { data } = await apiClient.delete<UsuarioDetalle>(
        `${BASE}/${id}/centros/${encodeURIComponent(centro_costo)}`,
      );
      return data;
    },
    onSuccess: invalidar,
  });
}
