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
  primary: 'bg-gradient-to-br from-primary/20 via-primary/10 to-secondary/15 text-primary group-hover:from-primary group-hover:via-primary group-hover:to-secondary group-hover:text-primary-foreground',
  secondary: 'bg-gradient-to-br from-secondary/20 via-secondary/10 to-primary/15 text-secondary group-hover:from-secondary group-hover:via-secondary group-hover:to-primary group-hover:text-secondary-foreground',
  accent: 'bg-gradient-to-br from-accent/35 via-accent/20 to-primary/15 text-accent-foreground group-hover:from-accent group-hover:via-accent group-hover:to-primary/20',
};

const acentoFondo: Record<NonNullable<FeatureCardProps['acento']>, string> = {
  primary: 'bg-gradient-to-br from-card via-card to-primary/10',
  secondary: 'bg-gradient-to-br from-card via-card to-secondary/10',
  accent: 'bg-gradient-to-br from-card via-card to-accent/25',
};

const acentoKpi: Record<NonNullable<FeatureCardProps['acento']>, string> = {
  primary: 'bg-gradient-to-r from-primary/10 to-secondary/10 border-primary/20',
  secondary: 'bg-gradient-to-r from-secondary/10 to-primary/10 border-secondary/20',
  accent: 'bg-gradient-to-r from-accent/25 to-primary/10 border-accent/40',
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
  const mostrarKpi = kpi !== undefined && (cargando || Boolean(kpi));

  return (
    <Link
      to={to}
      className={cn(
        'group relative flex flex-col overflow-hidden rounded-lg border border-border border-t-4 border-t-transparent',
        'transition-all duration-300 ease-out',
        'hover:-translate-y-1 hover:shadow-lg hover:border-border/60',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        acentoBorde[acento],
        acentoFondo[acento],
        destacado ? 'md:col-span-2 md:flex-row md:items-stretch' : '',
        className,
      )}
    >
      <div
        className={cn(
          'flex flex-col p-7 md:p-8 flex-1 min-w-0',
          destacado ? 'md:p-10' : '',
        )}
      >
        <div
          className={cn(
            'inline-flex h-14 w-14 items-center justify-center rounded-lg transition-all duration-200',
            acentoIcono[acento],
            'group-hover:scale-110',
          )}
        >
          <Icono className="w-7 h-7" aria-hidden="true" />
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

        {mostrarKpi ? (
          <div
            className={cn(
              'mt-6 inline-flex w-fit max-w-full items-center gap-3 rounded-lg border px-3.5 py-2.5',
              acentoKpi[acento],
            )}
          >
            {cargando ? (
              <div className="space-y-1.5" aria-hidden="true">
                <div className="h-5 w-20 bg-muted animate-pulse rounded-md" />
                <div className="h-3 w-28 bg-muted animate-pulse rounded-md" />
              </div>
            ) : (
              <>
                <span className="text-2xl font-bold leading-none text-foreground tabular-nums">
                  {kpi}
                </span>
                {kpiLabel ? (
                  <span className="max-w-[150px] text-[11px] font-semibold uppercase leading-tight tracking-wide text-muted-foreground">
                    {kpiLabel}
                  </span>
                ) : null}
              </>
            )}
          </div>
        ) : null}

        <span className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-primary group-hover:gap-2.5 transition-all">
          {cta}
          <ArrowRight className="w-4 h-4" aria-hidden="true" />
        </span>
      </div>
    </Link>
  );
}

export default FeatureCard;
