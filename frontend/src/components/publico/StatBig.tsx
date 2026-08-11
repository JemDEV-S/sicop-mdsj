import * as React from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatBigProps {
  label: string;
  valor: React.ReactNode;
  ayuda?: React.ReactNode;
  icono?: LucideIcon;
  cargando?: boolean;
  /** Acento a la izquierda: `primary`, `secondary`, `accent`. */
  acento?: 'primary' | 'secondary' | 'accent';
  className?: string;
}

const acentoBorder: Record<NonNullable<StatBigProps['acento']>, string> = {
  primary: 'before:bg-primary',
  secondary: 'before:bg-secondary',
  accent: 'before:bg-accent',
};

const acentoIcono: Record<NonNullable<StatBigProps['acento']>, string> = {
  primary: 'bg-gradient-to-br from-primary/15 via-primary/10 to-secondary/10 text-primary',
  secondary: 'bg-gradient-to-br from-secondary/15 via-secondary/10 to-primary/10 text-secondary',
  accent: 'bg-gradient-to-br from-accent/30 via-accent/20 to-primary/10 text-accent-foreground',
};

/**
 * Estadística grande con barra de acento vertical a la izquierda.
 * Reemplaza las cajas dentro de cajas — es una tira horizontal limpia.
 */
export function StatBig({
  label,
  valor,
  ayuda,
  icono: Icono,
  cargando = false,
  acento = 'primary',
  className,
}: StatBigProps) {
  return (
    <div
      className={cn(
        'relative rounded-lg border border-border/50 bg-gradient-to-br from-card/90 via-card/70 to-primary/5 p-5 pl-7 shadow-sm',
        'before:absolute before:left-0 before:top-2 before:bottom-2 before:w-1.5 before:rounded-full',
        acentoBorder[acento],
        className,
      )}
    >
      <div className="flex items-center gap-3">
        {Icono ? (
          <span className={cn('inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg shadow-sm', acentoIcono[acento])}>
            <Icono className="w-5 h-5" aria-hidden="true" />
          </span>
        ) : null}
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
      </div>
      {cargando ? (
        <div className="mt-3 h-10 w-40 bg-muted animate-pulse rounded-md" aria-hidden="true" />
      ) : (
        <p className="mt-2 text-4xl md:text-5xl font-bold text-foreground leading-tight tabular-nums">
          {valor}
        </p>
      )}
      {ayuda ? (
        <p className="mt-2.5 text-xs font-medium text-muted-foreground">{ayuda}</p>
      ) : null}
    </div>
  );
}

export default StatBig;
