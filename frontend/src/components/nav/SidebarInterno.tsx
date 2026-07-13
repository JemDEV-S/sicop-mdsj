import { NavLink } from 'react-router-dom';
import { navInterna, filtrarNavPorRol } from '@/app/nav-config';
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';

/**
 * Sidebar del panel interno de funcionarios.
 * - Ancho fijo w-64 en desktop.
 * - Cabecera con branding en bg-primary.
 * - Items agrupados en secciones; sección "Administración" solo visible para admin.
 * - Estado activo: bg-primary/10 con borde izquierdo primary.
 *
 * Nota: la responsividad móvil (drawer) se maneja fuera de este componente,
 *       en InternoLayout (por ahora solo desktop; se agregará drawer si hace falta).
 */
export function SidebarInterno() {
  const user = useAuthStore((s) => s.user);
  const secciones = filtrarNavPorRol(navInterna, user?.rol);

  return (
    <aside
      className="w-64 shrink-0 bg-card border-r border-border flex flex-col h-full"
      aria-label="Navegación del panel interno"
    >
      {/* Branding compacto */}
      <div className="h-16 px-4 flex items-center gap-3 bg-primary text-primary-foreground border-b border-primary/20">
        <span
          aria-hidden="true"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary-foreground text-primary text-sm font-bold shrink-0"
        >
          MDSJ
        </span>
        <span className="flex flex-col leading-tight min-w-0">
          <span className="text-sm font-semibold truncate">
            Panel Interno
          </span>
          <span className="text-xs text-primary-foreground/80 truncate">
            Municipalidad San Jerónimo
          </span>
        </span>
      </div>

      {/* Secciones */}
      <nav className="flex-1 overflow-y-auto py-3">
        {secciones.map((seccion) => (
          <div key={seccion.id} className="mb-4">
            {seccion.titulo ? (
              <div className="px-4 pb-2 pt-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {seccion.titulo}
              </div>
            ) : null}
            <ul className="space-y-0.5 px-2">
              {seccion.items.map((item) => {
                const Icono = item.icono;
                return (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.to === '/interno'}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors',
                          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                          isActive
                            ? 'bg-primary/10 text-primary font-medium border-l-4 border-primary pl-2'
                            : 'text-foreground hover:bg-muted border-l-4 border-transparent pl-2',
                        )
                      }
                    >
                      <Icono className="w-4 h-4 shrink-0" aria-hidden="true" />
                      <span className="truncate">{item.label}</span>
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Info del usuario en la base */}
      {user ? (
        <div className="border-t border-border p-4">
          <p className="text-sm font-medium text-foreground truncate">
            {user.nombre_completo || user.usuario}
          </p>
          <p className="text-xs text-muted-foreground capitalize">
            {user.rol}
          </p>
        </div>
      ) : null}
    </aside>
  );
}

export default SidebarInterno;
