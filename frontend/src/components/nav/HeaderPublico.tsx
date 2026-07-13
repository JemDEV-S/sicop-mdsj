import { useState } from 'react';
import { NavLink, Link, useLocation } from 'react-router-dom';
import { Menu, X, LogIn } from 'lucide-react';
import { navPublica } from '@/app/nav-config';
import { cn } from '@/lib/utils';

/**
 * Header institucional del portal público.
 * - Fondo bg-primary con texto blanco.
 * - Escudo institucional (placeholder MDSJ hasta que la muni provea el asset).
 * - Enlaces principales con subrayado amarillo (accent) en la ruta activa.
 * - Botón "Ingresar" outline a la derecha.
 * - En móvil: menú hamburguesa con drawer vertical.
 */
export function HeaderPublico() {
  const [menuAbierto, setMenuAbierto] = useState(false);
  const location = useLocation();

  const cerrarMenu = () => setMenuAbierto(false);

  return (
    <header className="sticky top-0 z-40 bg-primary text-primary-foreground border-b border-primary/20">
      <div className="mx-auto max-w-7xl px-4 md:px-6">
        <div className="flex h-16 items-center justify-between gap-4">
          {/* Branding */}
          <Link
            to="/"
            className="flex items-center gap-3 min-w-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground rounded-md"
            onClick={cerrarMenu}
          >
            <span
              aria-hidden="true"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary-foreground text-primary text-sm font-bold shrink-0"
            >
              MDSJ
            </span>
            <span className="flex flex-col leading-tight min-w-0">
              <span className="text-sm font-semibold truncate">
                Municipalidad de San Jerónimo
              </span>
              <span className="text-xs text-primary-foreground/80 truncate">
                Portal de Transparencia
              </span>
            </span>
          </Link>

          {/* Nav desktop */}
          <nav
            className="hidden md:flex items-center gap-1"
            aria-label="Navegación principal"
          >
            {navPublica.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    'px-3 py-2 text-sm font-medium rounded-md transition-colors',
                    'hover:bg-primary-foreground/10',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground',
                    isActive
                      ? 'border-b-2 border-accent rounded-b-none'
                      : 'border-b-2 border-transparent rounded-b-none',
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          {/* Acciones desktop */}
          <div className="hidden md:flex items-center gap-2">
            <Link
              to="/login"
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md border border-primary-foreground/40 hover:bg-primary-foreground/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground"
            >
              <LogIn className="w-4 h-4" aria-hidden="true" />
              Ingresar
            </Link>
          </div>

          {/* Botón hamburguesa móvil */}
          <button
            type="button"
            className="md:hidden inline-flex items-center justify-center w-10 h-10 rounded-md hover:bg-primary-foreground/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground"
            aria-label={menuAbierto ? 'Cerrar menú' : 'Abrir menú'}
            aria-expanded={menuAbierto}
            onClick={() => setMenuAbierto((v) => !v)}
          >
            {menuAbierto ? (
              <X className="w-5 h-5" aria-hidden="true" />
            ) : (
              <Menu className="w-5 h-5" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      {/* Drawer móvil */}
      {menuAbierto ? (
        <div className="md:hidden border-t border-primary-foreground/20 bg-primary">
          <nav
            className="px-4 py-3 flex flex-col gap-1"
            aria-label="Navegación principal móvil"
          >
            {navPublica.map((item) => {
              const activo = location.pathname === item.to || location.pathname.startsWith(item.to + '/');
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  onClick={cerrarMenu}
                  className={cn(
                    'px-3 py-2 rounded-md text-sm font-medium',
                    activo
                      ? 'bg-primary-foreground/15 border-l-4 border-accent'
                      : 'hover:bg-primary-foreground/10',
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
            <Link
              to="/login"
              onClick={cerrarMenu}
              className="mt-2 inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md border border-primary-foreground/40 hover:bg-primary-foreground/10"
            >
              <LogIn className="w-4 h-4" aria-hidden="true" />
              Ingresar
            </Link>
          </nav>
        </div>
      ) : null}
    </header>
  );
}

export default HeaderPublico;
