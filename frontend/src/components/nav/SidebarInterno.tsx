import { NavLink } from 'react-router-dom';
import { Building2, PanelLeftClose, PanelLeftOpen, ShieldCheck, X } from 'lucide-react';
import { navInterna, filtrarNavPorRol } from '@/app/nav-config';
import { useAuthStore } from '@/store/auth';
import { useContextoInterno } from '@/store/contexto-interno';
import { cn } from '@/lib/utils';
import logoMdsj from '@/assets/logo.png';

const ETIQUETAS_ROL: Record<string, string> = {
  operativo: 'Operativo',
  decisor: 'Decisor',
  admin: 'Administrador',
};

interface SidebarInternoProps {
  /**
   * 'fijo'   → sidebar de escritorio, soporta colapsar a íconos.
   * 'drawer' → panel deslizante en móvil, siempre expandido; se cierra al navegar.
   */
  variante?: 'fijo' | 'drawer';
}

export function SidebarInterno({ variante = 'fijo' }: SidebarInternoProps) {
  const user = useAuthStore((s) => s.user);
  const cc = useContextoInterno((s) => s.ccActivo);
  const colapsadoStore = useContextoInterno((s) => s.sidebarColapsado);
  const toggleSidebar = useContextoInterno((s) => s.toggleSidebar);
  const cerrarDrawer = useContextoInterno((s) => s.cerrarDrawer);
  const secciones = filtrarNavPorRol(navInterna, user?.rol);

  const esDrawer = variante === 'drawer';
  // En drawer nunca se colapsa a íconos: en móvil no aporta y perjudica el toque.
  const colapsado = esDrawer ? false : colapsadoStore;

  const etiquetaRol = user?.rol ? ETIQUETAS_ROL[user.rol] ?? user.rol : null;

  return (
    <aside
      className={cn(
        'bg-card border-r border-border flex flex-col h-full',
        esDrawer ? 'w-72 max-w-[85vw]' : 'shrink-0 transition-[width] duration-200',
        !esDrawer && (colapsado ? 'w-16' : 'w-64'),
      )}
      aria-label="Navegación del panel interno"
    >
      <div
        className={cn(
          'h-16 flex items-center bg-primary text-primary-foreground border-b border-primary/20',
          colapsado ? 'justify-center px-0' : 'px-4 gap-3',
        )}
      >
        <img
          src={logoMdsj}
          alt="Escudo de la Municipalidad Distrital de San Jerónimo"
          className="h-10 w-10 shrink-0 object-contain"
        />
        {!colapsado ? (
          <span className="flex flex-col leading-tight min-w-0 flex-1">
            <span className="text-sm font-semibold truncate">Panel Interno</span>
            <span className="text-xs text-primary-foreground/80 truncate">
              Municipalidad San Jerónimo
            </span>
          </span>
        ) : null}
        {esDrawer ? (
          <button
            type="button"
            onClick={cerrarDrawer}
            aria-label="Cerrar menú"
            className="shrink-0 inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-primary-foreground/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground/50"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        ) : null}
      </div>

      <nav className="flex-1 overflow-y-auto py-3">
        {secciones.map((seccion) => (
          <div key={seccion.id} className="mb-4">
            {seccion.titulo && !colapsado ? (
              <div className="px-4 pb-2 pt-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {seccion.titulo}
              </div>
            ) : null}
            {seccion.titulo && colapsado ? (
              <div className="mx-3 mb-2 border-t border-border" aria-hidden="true" />
            ) : null}
            <ul className="space-y-0.5 px-2">
              {seccion.items.map((item) => {
                const Icono = item.icono;
                return (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.to === '/interno'}
                      title={colapsado ? item.label : undefined}
                      onClick={esDrawer ? cerrarDrawer : undefined}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-3 py-2 text-sm rounded-md transition-colors',
                          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                          // Toque cómodo en drawer: filas más altas.
                          esDrawer && 'min-h-[44px]',
                          colapsado ? 'justify-center px-2' : 'px-3',
                          isActive
                            ? 'bg-primary/10 text-primary font-medium border-l-4 border-primary pl-2'
                            : 'text-foreground hover:bg-muted border-l-4 border-transparent pl-2',
                        )
                      }
                    >
                      <Icono className="w-4 h-4 shrink-0" aria-hidden="true" />
                      {!colapsado ? (
                        <span className="truncate">{item.label}</span>
                      ) : (
                        <span className="sr-only">{item.label}</span>
                      )}
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {user && !colapsado ? (
        <div className="border-t border-border p-4 space-y-3">
          <div className="flex items-start gap-2 min-w-0">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                {user.nombre_completo || user.usuario}
              </p>
              {etiquetaRol ? (
                <span className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-medium">
                  <ShieldCheck className="w-3 h-3" aria-hidden="true" />
                  {etiquetaRol}
                </span>
              ) : null}
            </div>
          </div>

          {cc ? (
            <div className="flex items-start gap-2 text-xs text-muted-foreground">
              <Building2 className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden="true" />
              <div className="min-w-0">
                <p className="text-[10px] uppercase tracking-wide font-semibold text-muted-foreground/80">
                  Unidad activa
                </p>
                <p className="text-foreground text-sm truncate leading-tight">
                  {cc.nombre}
                </p>
                <p className="font-mono text-[11px] text-muted-foreground">
                  {cc.codigo}
                </p>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Colapsar a íconos solo tiene sentido en el sidebar fijo de escritorio. */}
      {!esDrawer ? (
        <div className="border-t border-border p-2">
          <button
            type="button"
            onClick={toggleSidebar}
            title={colapsado ? 'Expandir menú' : 'Colapsar menú'}
            aria-label={colapsado ? 'Expandir menú' : 'Colapsar menú'}
            aria-pressed={colapsado}
            className={cn(
              'flex items-center gap-3 w-full py-2 text-sm rounded-md text-muted-foreground',
              'hover:bg-muted hover:text-foreground transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              colapsado ? 'justify-center px-2' : 'px-3',
            )}
          >
            {colapsado ? (
              <PanelLeftOpen className="w-4 h-4 shrink-0" aria-hidden="true" />
            ) : (
              <>
                <PanelLeftClose className="w-4 h-4 shrink-0" aria-hidden="true" />
                <span>Colapsar menú</span>
              </>
            )}
          </button>
        </div>
      ) : null}
    </aside>
  );
}

export default SidebarInterno;
