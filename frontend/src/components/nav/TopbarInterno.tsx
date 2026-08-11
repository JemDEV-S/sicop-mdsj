import { useEffect, useRef, useState } from 'react';
import { ChevronDown, LogOut, Menu } from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { useContextoInterno } from '@/store/contexto-interno';
import { cn } from '@/lib/utils';
import BreadcrumbsAuto from './BreadcrumbsAuto';
import { ChipAñoActivo, ChipCentroCostoActivo } from './ChipContexto';

interface TopbarInternoProps {
  breadcrumbs?: React.ReactNode;
}

export function TopbarInterno({ breadcrumbs }: TopbarInternoProps) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const abrirDrawer = useContextoInterno((s) => s.abrirDrawer);

  const [menuAbierto, setMenuAbierto] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!menuAbierto) return;
    function onClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuAbierto(false);
      }
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, [menuAbierto]);

  return (
    <header
      className="sticky top-0 z-30 bg-card border-b border-border"
      role="banner"
    >
      <div className="h-14 flex items-center gap-3 px-4 md:px-6">
        {/* Hamburguesa — solo móvil/tablet */}
        <button
          type="button"
          onClick={abrirDrawer}
          aria-label="Abrir menú de navegación"
          className="lg:hidden shrink-0 inline-flex h-10 w-10 items-center justify-center rounded-md text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Menu className="w-5 h-5" aria-hidden="true" />
        </button>

        <div className="flex-1 min-w-0 flex items-center">
          {breadcrumbs ?? <BreadcrumbsAuto />}
        </div>

        <div className="hidden md:flex items-center gap-2 shrink-0">
          <ChipAñoActivo />
          <ChipCentroCostoActivo />
        </div>

        <div className="relative shrink-0" ref={menuRef}>
          <button
            type="button"
            className={cn(
              'flex items-center gap-2 px-2 py-1.5 rounded-md text-sm',
              'hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            )}
            aria-haspopup="menu"
            aria-expanded={menuAbierto}
            onClick={() => setMenuAbierto((v) => !v)}
          >
            <span
              aria-hidden="true"
              className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-semibold"
            >
              {(user?.nombre_completo?.[0] ?? user?.usuario?.[0] ?? '?').toUpperCase()}
            </span>
            <span className="hidden xl:flex flex-col text-left leading-tight max-w-[10rem]">
              <span className="text-sm font-medium text-foreground truncate">
                {user?.nombre_completo || user?.usuario || 'Usuario'}
              </span>
              <span className="text-xs text-muted-foreground capitalize">
                {user?.rol}
              </span>
            </span>
            <ChevronDown className="w-4 h-4 text-muted-foreground" aria-hidden="true" />
          </button>

          {menuAbierto ? (
            <div
              role="menu"
              className="absolute right-0 mt-2 w-56 bg-card border border-border rounded-md py-1 z-40 shadow-md"
            >
              <div className="px-3 py-2 border-b border-border">
                <p className="text-sm font-medium text-foreground truncate">
                  {user?.nombre_completo || user?.usuario}
                </p>
                {user?.email ? (
                  <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                ) : null}
              </div>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuAbierto(false);
                  void logout();
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-muted focus-visible:outline-none focus-visible:bg-muted"
              >
                <LogOut className="w-4 h-4" aria-hidden="true" />
                Cerrar sesión
              </button>
            </div>
          ) : null}
        </div>
      </div>

      {/* Fila secundaria móvil: chips de contexto, que en el topbar se ocultan por debajo de md.
          Sin overflow-x aquí: recortaría los menús desplegables de los chips. */}
      <div className="md:hidden border-t border-border px-4 py-2 flex items-center gap-2 flex-wrap">
        <ChipAñoActivo />
        <ChipCentroCostoActivo />
      </div>
    </header>
  );
}

export default TopbarInterno;
