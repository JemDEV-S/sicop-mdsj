import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, LogOut, Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';

interface TopbarInternoProps {
  breadcrumbs?: React.ReactNode;
}

/**
 * Topbar del panel interno.
 * - Breadcrumbs a la izquierda (recibidos por prop).
 * - Buscador global de EXP_SIAF centrado/derecha.
 * - Menú de usuario con dropdown (cerrar sesión).
 */
export function TopbarInterno({ breadcrumbs }: TopbarInternoProps) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const [menuAbierto, setMenuAbierto] = useState(false);
  const [busqueda, setBusqueda] = useState('');
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

  function onBuscar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const valor = busqueda.trim();
    if (!valor) return;
    navigate(`/interno/cruce/expediente-siaf/${encodeURIComponent(valor)}`);
    setBusqueda('');
  }

  return (
    <header
      className="sticky top-0 z-30 h-14 bg-card border-b border-border flex items-center gap-4 px-6"
      role="banner"
    >
      <div className="flex-1 min-w-0 flex items-center">
        {breadcrumbs ? (
          <div className="text-sm text-muted-foreground truncate">
            {breadcrumbs}
          </div>
        ) : (
          <span className="text-sm text-muted-foreground">Panel Interno</span>
        )}
      </div>

      <form
        onSubmit={onBuscar}
        className="hidden md:block w-72"
        role="search"
        aria-label="Buscar expediente SIAF"
      >
        <div className="relative">
          <Search
            className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar EXP_SIAF..."
            className="pl-8 h-9"
            aria-label="Número de expediente SIAF"
          />
        </div>
      </form>

      {/* Menú de usuario */}
      <div className="relative" ref={menuRef}>
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
          <span className="hidden lg:flex flex-col text-left leading-tight max-w-[10rem]">
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
            className="absolute right-0 mt-2 w-56 bg-card border border-border rounded-md py-1 z-40"
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
                logout();
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-muted focus-visible:outline-none focus-visible:bg-muted"
            >
              <LogOut className="w-4 h-4" aria-hidden="true" />
              Cerrar sesión
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}

export default TopbarInterno;
