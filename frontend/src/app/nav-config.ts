import type { LucideIcon } from 'lucide-react';
import {
  ArrowLeftRight,
  BarChart3,
  Building2,
  GitBranch,
  LayoutDashboard,
  MapPin,
  RefreshCw,
  ScrollText,
  Settings,
  UserCog,
  Wallet,
} from 'lucide-react';

export type Rol = 'ciudadano' | 'operativo' | 'decisor' | 'admin';

export interface NavItem {
  label: string;
  to: string;
  icono: LucideIcon;
  roles?: Rol[];
}

export interface NavSection {
  id: string;
  titulo?: string;
  items: NavItem[];
  roles?: Rol[];
}

/**
 * Navegación del portal público (ciudadano).
 * Se renderiza como enlaces horizontales en HeaderPublico.
 */
export const navPublica: NavItem[] = [
  { label: 'Obras', to: '/obras', icono: Building2 },
  { label: 'Ejecución', to: '/ejecucion', icono: BarChart3 },
  { label: 'Mapa', to: '/mapa', icono: MapPin },
];

/**
 * Navegación del panel interno (funcionario).
 * Se renderiza como secciones en el SidebarInterno.
 * Cada item filtra por rol si tiene `roles` definido.
 */
export const navInterna: NavSection[] = [
  {
    id: 'principal',
    items: [
      { label: 'Panel', to: '/interno', icono: LayoutDashboard },
      { label: 'Análisis por meta', to: '/interno/analisis', icono: GitBranch },
      { label: 'Cruce SIAF ↔ SIGA', to: '/interno/cruce', icono: ArrowLeftRight },
      { label: 'Ejecución SIAF', to: '/interno/ejecucion-siaf', icono: Wallet },
    ],
  },
  {
    id: 'administracion',
    titulo: 'Administración',
    roles: ['admin'],
    items: [
      { label: 'Usuarios', to: '/admin/usuarios', icono: UserCog, roles: ['admin'] },
      { label: 'Auditoría', to: '/admin/auditoria', icono: ScrollText, roles: ['admin'] },
      { label: 'Sincronización', to: '/admin/sincronizacion', icono: RefreshCw, roles: ['admin'] },
      { label: 'Configuración', to: '/admin/configuracion', icono: Settings, roles: ['admin', 'decisor'] },
    ],
  },
];

/**
 * Filtra un array de secciones según el rol del usuario actual.
 * Sección sin `roles` es visible para todos los logueados.
 * Item sin `roles` es visible dentro de una sección visible.
 */
export function filtrarNavPorRol(secciones: NavSection[], rol?: string): NavSection[] {
  if (!rol) return [];
  return secciones
    .filter((s) => !s.roles || s.roles.includes(rol as Rol))
    .map((s) => ({
      ...s,
      items: s.items.filter((it) => !it.roles || it.roles.includes(rol as Rol)),
    }))
    .filter((s) => s.items.length > 0);
}
