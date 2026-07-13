import * as React from 'react';
import { cn } from '@/lib/utils';

interface SectionHeaderProps {
  eyebrow?: string;
  titulo: React.ReactNode;
  descripcion?: React.ReactNode;
  accion?: React.ReactNode;
  alineacion?: 'izquierda' | 'centro';
  className?: string;
}

/**
 * Cabecera de sección para páginas públicas. Estructura:
 *   [eyebrow chico]
 *   Título grande       [acción opcional a la derecha]
 *   Descripción muted
 */
export function SectionHeader({
  eyebrow,
  titulo,
  descripcion,
  accion,
  alineacion = 'izquierda',
  className,
}: SectionHeaderProps) {
  const centrado = alineacion === 'centro';
  return (
    <div
      className={cn(
        'mb-10',
        centrado ? 'text-center max-w-2xl mx-auto' : '',
        !centrado && accion ? 'flex flex-col md:flex-row md:items-end md:justify-between gap-4' : '',
        className,
      )}
    >
      <div className={cn(!centrado && accion ? 'max-w-2xl' : '')}>
        {eyebrow ? (
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-primary mb-3">
            {eyebrow}
          </p>
        ) : null}
        <h2 className="text-2xl md:text-3xl font-bold text-foreground tracking-tight">
          {titulo}
        </h2>
        {descripcion ? (
          <p className="mt-3 text-base text-muted-foreground">{descripcion}</p>
        ) : null}
      </div>
      {!centrado && accion ? <div className="shrink-0">{accion}</div> : null}
    </div>
  );
}

export default SectionHeader;
