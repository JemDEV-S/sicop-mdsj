import * as React from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

type Padding = 'sm' | 'md' | 'lg';

interface SectionCardProps {
  titulo?: string;
  icono?: LucideIcon;
  accion?: React.ReactNode;
  padding?: Padding;
  className?: string;
  bodyClassName?: string;
  children: React.ReactNode;
}

const paddingMap: Record<Padding, string> = {
  sm: 'p-4',
  md: 'p-5',
  lg: 'p-6',
};

export function SectionCard({
  titulo,
  icono: Icono,
  accion,
  padding = 'md',
  className,
  bodyClassName,
  children,
}: SectionCardProps) {
  const tieneCabecera = Boolean(titulo || accion);

  return (
    <section
      className={cn(
        'bg-card border border-border rounded-md',
        className,
      )}
    >
      {tieneCabecera ? (
        <header
          className={cn(
            'flex items-center justify-between gap-4 border-b border-border',
            padding === 'sm' ? 'px-4 py-3' : padding === 'lg' ? 'px-6 py-4' : 'px-5 py-3',
          )}
        >
          <div className="flex items-center gap-2 min-w-0">
            {Icono ? (
              <Icono className="w-5 h-5 text-primary shrink-0" aria-hidden="true" />
            ) : null}
            {titulo ? (
              <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground truncate">
                {titulo}
              </h2>
            ) : null}
          </div>
          {accion ? <div className="shrink-0">{accion}</div> : null}
        </header>
      ) : null}

      <div className={cn(paddingMap[padding], bodyClassName)}>{children}</div>
    </section>
  );
}

export default SectionCard;
