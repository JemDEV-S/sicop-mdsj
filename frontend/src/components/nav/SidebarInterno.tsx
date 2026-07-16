import { NavLink } from 'react-router-dom';
import { Building2, ShieldCheck } from 'lucide-react';
import { navInterna, filtrarNavPorRol } from '@/app/nav-config';
import { useAuthStore } from '@/store/auth';
import { useContextoInterno } from '@/store/contexto-interno';
import { cn } from '@/lib/utils';

const ETIQUETAS_ROL: Record<string, string> = {
  operativo: 'Operativo',
  decisor: 'Decisor',
  admin: 'Administrador',
};

export function SidebarInterno() {
  const user = useAuthStore((s) => s.user);
  const cc = useContextoInterno((s) => s.ccActivo);
  const secciones = filtrarNavPorRol(navInterna, user?.rol);

  const etiquetaRol = user?.rol ? ETIQUETAS_ROL[user.rol] ?? user.rol : null;

  return (
    <aside
      className="w-64 shrink-0 bg-card border-r border-border flex flex-col h-full"
      aria-label="Navegación del panel interno"
    >
      <div className="h-16 px-4 flex items-center gap-3 bg-primary text-primary-foreground border-b border-primary/20">
        <span
          aria-hidden="true"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary-foreground text-primary text-sm font-bold shrink-0"
        >
          MDSJ
        </span>
        <span className="flex flex-col leading-tight min-w-0">
          <span className="text-sm font-semibold truncate">Panel Interno</span>
          <span className="text-xs text-primary-foreground/80 truncate">
            Municipalidad San Jerónimo
          </span>
        </span>
      </div>

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

      {user ? (
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
    </aside>
  );
}

export default SidebarInterno;
