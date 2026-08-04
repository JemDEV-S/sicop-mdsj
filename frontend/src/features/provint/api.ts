import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { apiClient } from '@/lib/api-client';
import { useContextoInterno } from '@/store/contexto-interno';
import type {
  ContratoItem,
  ContratoPorVencer,
  ContratosListado,
  OrdenProveedor,
  ProveedorInterno,
  ProveedoresListado,
} from './types';

const AÑO_VIGENTE = 2026;

/** `true` si el error de la query es un 404. */
export function esNoEncontrado(error: unknown): boolean {
  return error instanceof AxiosError && error.response?.status === 404;
}

// ─── Directorio de proveedores ────────────────────────────────────────────

interface DirectorioParams {
  q: string;
  page: number;
  size: number;
}

export function useProveedores({ q, page, size }: DirectorioParams) {
  const ano = useContextoInterno((s) => s.añoActivo);
  return useQuery({
    queryKey: ['interno', 'proveedores', 'listado', ano, q, page, size],
    placeholderData: keepPreviousData,
    queryFn: async () => {
      const params: Record<string, string | number> = { ano, page, size };
      if (q.trim()) params.q = q.trim();
      const { data } = await apiClient.get<ProveedoresListado>(
        '/interno/proveedores',
        { params },
      );
      return data;
    },
  });
}

export function useProveedor(ruc: string | null) {
  return useQuery({
    queryKey: ['interno', 'proveedores', 'detalle', ruc],
    enabled: !!ruc,
    retry: (n, err) => (esNoEncontrado(err) ? false : n < 2),
    queryFn: async () => {
      const { data } = await apiClient.get<ProveedorInterno>(
        `/interno/proveedores/${ruc}`,
      );
      return data;
    },
  });
}

export function useOrdenesProveedor(ruc: string | null) {
  const ano = useContextoInterno((s) => s.añoActivo);
  return useQuery({
    queryKey: ['interno', 'proveedores', 'ordenes', ruc, ano],
    enabled: !!ruc,
    queryFn: async () => {
      const { data } = await apiClient.get<OrdenProveedor[]>(
        `/interno/proveedores/${ruc}/ordenes`,
        { params: { ano } },
      );
      return data;
    },
  });
}

/** Contratos de un proveedor concreto (para el perfil). */
export function useContratosProveedor(ruc: string | null) {
  return useQuery({
    queryKey: ['interno', 'proveedores', 'contratos', ruc],
    enabled: !!ruc,
    queryFn: async () => {
      const { data } = await apiClient.get<ContratosListado>('/interno/contratos', {
        params: { proveedor_ruc: ruc, size: 100 },
      });
      return data.items;
    },
  });
}

// ─── Contratos ─────────────────────────────────────────────────────────────

interface ContratosParams {
  page: number;
  size: number;
  estado: string | null;
}

export function useContratos({ page, size, estado }: ContratosParams) {
  const ano = useContextoInterno((s) => s.añoActivo);
  return useQuery({
    queryKey: ['interno', 'contratos', 'listado', ano, page, size, estado],
    placeholderData: keepPreviousData,
    queryFn: async () => {
      const params: Record<string, string | number> = { ano, page, size };
      if (estado) params.estado = estado;
      const { data } = await apiClient.get<ContratosListado>('/interno/contratos', {
        params,
      });
      return data;
    },
  });
}

/**
 * Contratos por vencer (HU-20). Los contratos SIGA NO están amarrados a CC
 * (ver guía §5.2): esta alerta es transversal a toda la entidad.
 *
 * Datos sobre BACKUP: `contratos_por_vencer` mide contra `fecha_referencia`
 * (default = hoy del servidor). Para que la ventana tenga sentido en años
 * pasados del backup, cuando el año activo NO es el vigente enviamos una fecha
 * de referencia dentro de ese año (mediados). Para el año vigente usamos el
 * default del servidor (hoy real). El rezago del backup NO es bug.
 */
export function useContratosPorVencer(dias = 30) {
  const ano = useContextoInterno((s) => s.añoActivo);
  return useQuery({
    queryKey: ['interno', 'alertas', 'contratos-por-vencer', ano, dias],
    queryFn: async () => {
      const params: Record<string, string | number> = { dias };
      if (ano !== AÑO_VIGENTE) params.fecha_referencia = `${ano}-06-30`;
      const { data } = await apiClient.get<ContratoPorVencer[]>(
        '/interno/alertas/contratos-por-vencer',
        { params },
      );
      return data;
    },
  });
}

export type { ContratoItem };
