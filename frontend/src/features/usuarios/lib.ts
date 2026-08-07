/** Etiquetas y estilos para roles y estados de usuario (§1.1 lenguaje llano). */
import type { EstadoUsuario, Rol } from './types';

export const ROLES: { valor: Rol; label: string }[] = [
  { valor: 'operativo', label: 'Operativo' },
  { valor: 'decisor', label: 'Decisor' },
  { valor: 'admin', label: 'Administrador' },
];

export const ESTADOS: { valor: EstadoUsuario; label: string }[] = [
  { valor: 'activo', label: 'Activo' },
  { valor: 'inactivo', label: 'Inactivo' },
  { valor: 'bloqueado', label: 'Bloqueado' },
];

export function rolLabel(rol: Rol): string {
  return ROLES.find((r) => r.valor === rol)?.label ?? rol;
}

export function estadoLabel(estado: EstadoUsuario): string {
  return ESTADOS.find((e) => e.valor === estado)?.label ?? estado;
}

type BadgeVariant = 'default' | 'secondary' | 'outline' | 'destructive';

export function rolVariant(rol: Rol): BadgeVariant {
  if (rol === 'admin') return 'default';
  if (rol === 'decisor') return 'secondary';
  return 'outline';
}

export function estadoVariant(estado: EstadoUsuario): BadgeVariant {
  if (estado === 'activo') return 'secondary';
  if (estado === 'bloqueado') return 'destructive';
  return 'outline';
}

/**
 * Descripción del rol para el funcionario que administra: qué alcance implica.
 * Refleja RN-04 (el alcance real lo resuelve el backend por CC asignados).
 */
export const ROL_AYUDA: Record<Rol, string> = {
  operativo: 'Ve solo los centros de costo que le asignes.',
  decisor: 'Ve su centro de costo y toda la rama que cuelga debajo (jerarquía).',
  admin: 'Ve toda la municipalidad y administra el sistema.',
};
