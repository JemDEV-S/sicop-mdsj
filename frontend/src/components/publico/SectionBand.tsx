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
        tono === 'muted' ? 'bg-muted/40' : 'bg-background',
        className,
      )}
    >
      <div
        className={cn(
          'mx-auto max-w-6xl px-4 md:px-6',
          denso ? 'py-8 md:py-10' : 'py-14 md:py-20',
        )}
      >
        {children}
      </div>
    </section>
  );
}

export default SectionBand;
