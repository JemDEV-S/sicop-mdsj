import { Link } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import { ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FeatureCardProps {
  to: string;
  icono: LucideIcon;
  titulo: string;
  descripcion: string;
  kpi?: string | null;
  kpiLabel?: string;
  cargando?: boolean;
  cta: string;
  /** Destacado = card ancha, con acento visual más fuerte. */
  destacado?: boolean;
  /** Acento cromático del ícono/borde superior. */
  acento?: 'primary' | 'secondary' | 'accent';
  className?: string;
}

const acentoBorde: Record<NonNullable<FeatureCardProps['acento']>, string> = {
  primary: 'group-hover:border-t-primary',
  secondary: 'group-hover:border-t-secondary',
  accent: 'group-hover:border-t-accent',
};

const acentoIcono: Record<NonNullable<FeatureCardProps['acento']>, string> = {
  primary: 'bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground',
  secondary: 'bg-secondary/10 text-secondary group-hover:bg-secondary group-hover:text-secondary-foreground',
  accent: 'bg-accent/20 text-accent-foreground group-hover:bg-accent',
};

/**
 * Tarjeta de módulo del portal público. Estados hover coordinados
 * (borde superior de color + ícono lleno). Modo destacado ocupa
 * 2 columnas en el grid.
 */
export function FeatureCard({
  to,
  icono: Icono,
  titulo,
  descripcion,
  kpi,
  kpiLabel,
  cargando = false,
  cta,
  destacado = false,
  acento = 'primary',
  className,
}: FeatureCardProps) {
  return (
    <Link
      to={to}
      className={cn(
        'group relative flex flex-col overflow-hidden rounded-xl bg-card border border-border border-t-4 border-t-transparent',
        'transition-all duration-200',
        'hover:-translate-y-0.5 hover:shadow-sm hover:border-border/80',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        acentoBorde[acento],
        destacado ? 'md:col-span-2 md:flex-row md:items-stretch' : '',
        className,
      )}
    >
      <div
        className={cn(
          'flex flex-col p-6 md:p-7 flex-1 min-w-0',
          destacado ? 'md:p-8' : '',
        )}
      >
        <div
          className={cn(
            'inline-flex h-12 w-12 items-center justify-center rounded-lg transition-colors',
            acentoIcono[acento],
          )}
        >
          <Icono className="w-6 h-6" aria-hidden="true" />
        </div>

        <h3
          className={cn(
            'mt-5 font-bold text-foreground tracking-tight',
            destacado ? 'text-xl md:text-2xl' : 'text-lg',
          )}
        >
          {titulo}
        </h3>

        <p
          className={cn(
            'mt-2 text-muted-foreground flex-1',
            destacado ? 'text-base' : 'text-sm',
          )}
        >
          {descripcion}
        </p>

        <span className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-primary group-hover:gap-2.5 transition-all">
          {cta}
          <ArrowRight className="w-4 h-4" aria-hidden="true" />
        </span>
      </div>

      {/* Panel de KPI */}
      {kpi !== undefined ? (
        <div
          className={cn(
            'border-t border-border bg-muted/30 p-6 md:p-7',
            destacado ? 'md:border-t-0 md:border-l md:w-64 md:flex md:flex-col md:justify-center' : '',
          )}
        >
          {cargando ? (
            <div className="space-y-2" aria-hidden="true">
              <div className="h-8 w-28 bg-muted animate-pulse rounded-md" />
              <div className="h-3 w-32 bg-muted animate-pulse rounded-md" />
            </div>
          ) : kpi ? (
            <>
              <p className="text-3xl font-bold text-foreground leading-none tabular-nums">
                {kpi}
              </p>
              {kpiLabel ? (
                <p className="mt-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  {kpiLabel}
                </p>
              ) : null}
            </>
          ) : (
            <p className="text-xs text-muted-foreground">Consulta el detalle completo</p>
          )}
        </div>
      ) : null}
    </Link>
  );
}

export default FeatureCard;
