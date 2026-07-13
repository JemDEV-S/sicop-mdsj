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
  primary: 'text-primary',
  secondary: 'text-secondary',
  accent: 'text-accent-foreground',
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
        'relative pl-5',
        'before:absolute before:left-0 before:top-1 before:bottom-1 before:w-1 before:rounded-full',
        acentoBorder[acento],
        className,
      )}
    >
      <div className="flex items-center gap-2">
        {Icono ? (
          <Icono
            className={cn('w-4 h-4 shrink-0', acentoIcono[acento])}
            aria-hidden="true"
          />
        ) : null}
        <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          {label}
        </span>
      </div>
      {cargando ? (
        <div className="mt-2 h-10 w-32 bg-muted animate-pulse rounded-md" aria-hidden="true" />
      ) : (
        <p className="mt-1 text-3xl md:text-4xl font-bold text-foreground leading-none tabular-nums">
          {valor}
        </p>
      )}
      {ayuda ? (
        <p className="mt-2 text-xs text-muted-foreground">{ayuda}</p>
      ) : null}
    </div>
  );
}

export default StatBig;
