import * as React from 'react';
import { CheckCircle2, Circle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatFecha } from '@/lib/formatters';

export interface HitoTimeline {
  key: string;
  titulo: string;
  detalle?: string | null;
  fecha?: string | null;
  alcanzada: boolean;
  numero?: number | null;
}

interface TimelineProps {
  hitos: HitoTimeline[];
  className?: string;
}

// Componente vertical con puntos rellenos (alcanzados) o vacíos (pendientes)
// y línea conectora. Se declara aquí (nivel components/) porque va a servir
// también al detalle de obra (T-51) y potencialmente al cierre de meta.
export function Timeline({ hitos, className }: TimelineProps) {
  return (
    <ol className={cn('relative flex flex-col gap-4', className)}>
      {hitos.map((h, i) => {
        const esUltimo = i === hitos.length - 1;
        return (
          <li key={h.key} className="relative flex gap-3">
            {/* Línea conectora al siguiente hito */}
            {!esUltimo ? (
              <span
                aria-hidden="true"
                className={cn(
                  'absolute left-[9px] top-6 w-px h-full -bottom-2',
                  h.alcanzada ? 'bg-primary/40' : 'bg-border',
                )}
              />
            ) : null}

            {/* Punto: relleno si alcanzada, contorno si pendiente */}
            <span
              className="relative z-10 shrink-0 flex items-center justify-center w-5 h-5 mt-0.5"
              aria-hidden="true"
            >
              {h.alcanzada ? (
                <CheckCircle2 className="w-5 h-5 text-primary" fill="currentColor" fillOpacity={0.15} />
              ) : (
                <Circle className="w-5 h-5 text-muted-foreground" />
              )}
            </span>

            <div className="min-w-0 flex-1 pb-1">
              <div className="flex items-baseline gap-2 flex-wrap">
                {h.numero != null ? (
                  <span className="text-[11px] font-mono text-muted-foreground tabular-nums">
                    [{h.numero}]
                  </span>
                ) : null}
                <p
                  className={cn(
                    'text-sm font-medium',
                    h.alcanzada ? 'text-foreground' : 'text-muted-foreground',
                  )}
                >
                  {h.titulo}
                </p>
                {h.fecha ? (
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {formatFecha(h.fecha)}
                  </span>
                ) : (
                  h.alcanzada ? null : (
                    <span className="text-xs text-muted-foreground italic">
                      pendiente
                    </span>
                  )
                )}
              </div>
              {h.detalle ? (
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {h.detalle}
                </p>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export default Timeline;
