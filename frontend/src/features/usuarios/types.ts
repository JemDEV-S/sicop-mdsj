/**
 * Tipos de gestión de usuarios (admin-only · HU-17 · T-54).
 * Espejo de `backend/app/schemas/usuarios.py`.
 */

export type Rol = 'operativo' | 'decisor' | 'admin';
export type EstadoUsuario = 'activo' | 'inactivo' | 'bloqueado';

export interface CentroAsignado {
  codigo: string;
  nombre: string;
  abreviado: string | null;
  es_raiz_jerarquia: boolean;
}

export interface CentroCostoBreve {
  codigo: string;
  nombre: string;
  abreviado: string | null;
}

export interface UsuarioItem {
  id: string;
  usuario: string;
  nombre_completo: string;
  dni: string | null;
  email: string | null;
  rol: Rol;
  estado: EstadoUsuario;
  debe_cambiar_password: boolean;
  nro_centros: number;
  creado_en: string;
}

export interface UsuarioDetalle extends UsuarioItem {
  centros: CentroAsignado[];
}

export interface UsuariosListado {
  items: UsuarioItem[];
  total: number;
  page: number;
  size: number;
}

export interface UsuarioCrear {
  usuario: string;
  nombre_completo: string;
  dni: string;
  rol: Rol;
  email?: string | null;
}

export interface UsuarioActualizar {
  nombre_completo?: string;
  email?: string | null;
  rol?: Rol;
  estado?: EstadoUsuario;
}

export interface FiltrosUsuarios {
  q: string | null;
  rol: Rol | null;
  estado: EstadoUsuario | null;
}
