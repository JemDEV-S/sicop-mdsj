import { Link, useMatches } from 'react-router-dom';
import { ChevronRight, LayoutDashboard } from 'lucide-react';

interface BreadcrumbMatch {
  pathname: string;
  handle?: { breadcrumb?: string };
}

const ETIQUETAS_POR_SEGMENTO: Record<string, string> = {
  interno: 'Panel',
  pipeline: 'Pipeline',
  saldos: 'Saldos',
  cruce: 'Cruce SIAF-SIGA',
  'ejecucion-siaf': 'Ejecución SIAF',
  'expediente-siaf': 'Expediente',
  proveedores: 'Proveedores',
  alertas: 'Alertas',
  reportes: 'Reportes',
  admin: 'Administración',
  usuarios: 'Usuarios',
  configuracion: 'Configuración',
};

function etiquetarSegmento(seg: string): string {
  if (ETIQUETAS_POR_SEGMENTO[seg]) return ETIQUETAS_POR_SEGMENTO[seg];
  return seg.charAt(0).toUpperCase() + seg.slice(1);
}

export function BreadcrumbsAuto() {
  const matches = useMatches() as BreadcrumbMatch[];

  const items = matches
    .filter((m) => m.pathname.startsWith('/interno') || m.pathname.startsWith('/admin'))
    .map((m) => {
      // Normalizamos la barra final: los layouts anidados sin `path` heredan el
      // mismo pathname que su padre, a veces con "/" al final. Sin normalizar,
      // "/interno" y "/interno/" cuentan como rutas distintas y el crumb se duplica.
      const pathname = m.pathname.replace(/\/+$/, '') || '/';
      const explicito = m.handle?.breadcrumb;
      if (explicito) return { pathname, label: explicito };
      const segs = pathname.split('/').filter(Boolean);
      const ultimo = segs[segs.length - 1] ?? '';
      return { pathname, label: etiquetarSegmento(ultimo) };
    })
    // Colapsamos crumbs consecutivos con el mismo destino o la misma etiqueta:
    // las rutas de layout (RequireAuth, InternoLayout) resuelven al mismo
    // segmento que el índice y producirían "Panel > Panel".
    .filter((it, i, arr) => {
      const prev = arr[i - 1];
      if (!prev) return true;
      return prev.pathname !== it.pathname && prev.label !== it.label;
    });

  if (items.length === 0) {
    return <span className="text-sm text-muted-foreground">Panel Interno</span>;
  }

  return (
    <nav aria-label="Ubicación" className="flex items-center gap-1 text-sm min-w-0">
      <Link
        to="/interno"
        className="inline-flex items-center gap-1 text-muted-foreground hover:text-primary transition-colors"
        aria-label="Ir al panel"
      >
        <LayoutDashboard className="w-4 h-4" aria-hidden="true" />
      </Link>
      {items.map((it, i) => {
        const esUltimo = i === items.length - 1;
        return (
          <span key={it.pathname} className="flex items-center gap-1 min-w-0">
            <ChevronRight
              className="w-3.5 h-3.5 text-muted-foreground/60 shrink-0"
              aria-hidden="true"
            />
            {esUltimo ? (
              <span
                className="font-medium text-foreground truncate"
                aria-current="page"
              >
                {it.label}
              </span>
            ) : (
              <Link
                to={it.pathname}
                className="text-muted-foreground hover:text-primary transition-colors truncate"
              >
                {it.label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}

export default BreadcrumbsAuto;
