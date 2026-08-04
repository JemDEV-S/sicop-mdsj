import * as React from 'react';
import { useId, useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AcordeonProps {
  titulo: string;
  icono?: LucideIcon;
  /** Contador de elementos (ej. "12"); se muestra como badge junto al título. */
  conteo?: number;
  /** Texto secundario a la derecha (ej. monto total del panel). */
  resumen?: React.ReactNode;
  defaultOpen?: boolean;
  /** Si no hay contenido, el panel se muestra deshabilitado (no expandible). */
  vacio?: boolean;
  className?: string;
  children: React.ReactNode;
}

/**
 * Panel colapsable para vistas de detalle largas (patrón progressive disclosure,
 * guía §1.1). Accesible: el encabezado es un `<button>` con `aria-expanded` y
 * `aria-controls`; el contenido tiene `role="region"`.
 *
 * Se usa uno por sección (Presupuesto, Órdenes, ...) apilados verticalmente.
 */
export function Acordeon({
  titulo,
  icono: Icono,
  conteo,
  resumen,
  defaultOpen = false,
  vacio = false,
  className,
  children,
}: AcordeonProps) {
  const [abierto, setAbierto] = useState(defaultOpen && !vacio);
  const panelId = useId();

  return (
    <section className={cn('bg-card border border-border rounded-md', className)}>
      <h3>
        <button
          type="button"
          onClick={() => !vacio && setAbierto((v) => !v)}
          disabled={vacio}
          aria-expanded={abierto}
          aria-controls={panelId}
          className={cn(
            'flex w-full items-center gap-3 px-5 py-4 text-left',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset',
            vacio ? 'cursor-default opacity-60' : 'hover:bg-muted/40',
            abierto && 'rounded-b-none',
          )}
        >
          {Icono ? (
            <Icono className="h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
          ) : null}

          <span className="flex min-w-0 items-center gap-2">
            <span className="text-sm font-semibold uppercase tracking-wide text-foreground">
              {titulo}
            </span>
            {conteo != null ? (
              <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-semibold tabular-nums text-muted-foreground">
                {conteo}
              </span>
            ) : null}
          </span>

          <span className="ml-auto flex items-center gap-3">
            {resumen ? (
              <span className="text-sm font-medium tabular-nums text-muted-foreground">
                {resumen}
              </span>
            ) : null}
            {!vacio ? (
              <ChevronDown
                className={cn(
                  'h-4 w-4 shrink-0 text-muted-foreground transition-transform',
                  abierto && 'rotate-180',
                )}
                aria-hidden="true"
              />
            ) : null}
          </span>
        </button>
      </h3>

      {abierto ? (
        <div id={panelId} role="region" className="border-t border-border">
          {children}
        </div>
      ) : null}
    </section>
  );
}

export default Acordeon;
