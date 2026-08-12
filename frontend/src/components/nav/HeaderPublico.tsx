import { useState } from 'react';
import { NavLink, Link, useLocation } from 'react-router-dom';
import { Menu, X, LogIn } from 'lucide-react';
import { navPublica } from '@/app/nav-config';
import { cn } from '@/lib/utils';
import { BotonInstalarApp } from '@/components/pwa/BotonInstalarApp';
import logoMdsj from '@/assets/logo.png';

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
    <header className="sticky top-0 z-40 border-b border-primary-foreground/15 bg-primary text-primary-foreground shadow-[0_10px_30px_rgba(15,23,42,0.12)]">
      <div
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          background:
            'linear-gradient(90deg, rgba(255,255,255,0.10) 0%, transparent 38%, rgba(255,255,255,0.06) 100%)',
        }}
        aria-hidden="true"
      />
      <div className="relative mx-auto max-w-7xl px-4 md:px-6">
        <div className="flex h-[72px] items-center justify-between gap-6 md:h-20">
          {/* Branding */}
          <Link
            to="/"
            className="group flex min-w-0 items-center gap-3.5 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground"
            onClick={cerrarMenu}
          >
            <img
              src={logoMdsj}
              alt="Escudo de la Municipalidad Distrital de San Jerónimo"
              className="h-11 w-11 shrink-0 object-contain transition-transform duration-200 group-hover:-translate-y-0.5"
            />
            <span className="flex flex-col leading-tight min-w-0">
              <span className="truncate text-base font-bold tracking-tight">
                Municipalidad de San Jerónimo
              </span>
              <span className="truncate text-sm text-primary-foreground/80">
                Portal de Transparencia
              </span>
            </span>
          </Link>

          {/* Nav desktop */}
          <nav
            className="hidden items-center gap-1 rounded-xl border border-primary-foreground/20 bg-primary-foreground/10 px-1.5 py-1 shadow-inner md:flex"
            aria-label="Navegación principal"
          >
            {navPublica.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    'relative rounded-lg px-4 py-2 text-sm font-semibold transition-all duration-200',
                    'hover:bg-primary-foreground/15 hover:text-primary-foreground',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground',
                    isActive
                      ? 'bg-primary-foreground/15 text-primary-foreground shadow-sm after:absolute after:left-4 after:right-4 after:-bottom-1 after:h-0.5 after:rounded-full after:bg-accent'
                      : 'text-primary-foreground/90',
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          {/* Acciones desktop */}
          <div className="hidden md:flex items-center gap-2">
            <BotonInstalarApp />
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-lg border border-primary-foreground/50 bg-primary-foreground/10 px-4 py-2.5 text-sm font-bold shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-primary-foreground/20 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground"
            >
              <LogIn className="w-4 h-4" aria-hidden="true" />
              Ingresar
            </Link>
          </div>

          {/* Botón hamburguesa móvil */}
          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-primary-foreground/20 bg-primary-foreground/10 hover:bg-primary-foreground/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground md:hidden"
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
            <BotonInstalarApp className="mt-2 w-full justify-center" onInstalado={cerrarMenu} />
            <Link
              to="/login"
              onClick={cerrarMenu}
              className="mt-3 inline-flex items-center gap-2 px-3 py-2 text-sm font-semibold rounded-md border border-primary-foreground/50 bg-primary-foreground/10 hover:bg-primary-foreground/20 transition-colors"
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
