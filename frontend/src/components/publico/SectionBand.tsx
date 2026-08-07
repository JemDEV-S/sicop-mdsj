import * as React from 'react';
import { cn } from '@/lib/utils';

interface SectionBandProps {
  children: React.ReactNode;
  /** Fondo alternante. `muted` para el ritmo vertical del scroll. */
  tono?: 'background' | 'muted';
  /** Espaciado vertical. */
  denso?: boolean;
  className?: string;
  id?: string;
}

/**
 * Banda de sección con ancho de contenido y padding vertical estandarizado.
 * Alternar `tono` entre secciones consecutivas genera el ritmo del scroll
 * en las páginas del portal público.
 */
export function SectionBand({
  children,
  tono = 'background',
  denso = false,
  className,
  id,
}: SectionBandProps) {
  return (
    <section
      id={id}
      className={cn(
        tono === 'muted'
          ? 'bg-gradient-to-br from-muted/80 via-muted/55 to-primary/10'
          : 'bg-gradient-to-br from-background via-background to-secondary/10',
        className,
      )}
    >
      <div
        className={cn(
          'mx-auto max-w-6xl px-4 md:px-6',
          denso ? 'py-10 md:py-12' : 'py-16 md:py-24',
        )}
      >
        {children}
      </div>
    </section>
  );
}

export default SectionBand;
