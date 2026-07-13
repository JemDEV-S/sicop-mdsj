import { Calendar, Check, Circle } from 'lucide-react';
import { formatFecha } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import type { ObraDetalleResponse } from '../types';

export function Cronograma({ obra }: { obra: ObraDetalleResponse }) {
  const hitos: Hito[] = [
    { label: 'Viabilidad', fecha: obra.fecha_viabilidad, descripcion: 'Aprobación del proyecto' },
    { label: 'Inicio de ejecución', fecha: obra.fec_ini_ejecucion, descripcion: 'Se autoriza empezar' },
    { label: 'Primer devengado', fecha: obra.primer_devengado, descripcion: 'Primer pago reconocido' },
    { label: 'Último devengado', fecha: obra.ultimo_devengado, descripcion: 'Movimiento más reciente' },
    { label: 'Fin de ejecución', fecha: obra.fec_fin_ejecucion, descripcion: 'Cierre previsto de la obra' },
  ];

  return (
    <div className="rounded-2xl bg-card border border-border overflow-hidden h-full flex flex-col">
      <header className="flex items-center gap-2 px-6 py-4 border-b border-border bg-muted/40">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Calendar className="w-4 h-4" aria-hidden="true" />
        </span>
        <div>
          <h3 className="text-sm font-semibold text-foreground">Cronograma</h3>
          <p className="text-xs text-muted-foreground">Hitos del ciclo de la obra</p>
        </div>
      </header>

      <ol className="p-6 flex-1 relative">
        {/* Línea vertical */}
        <span
          className="absolute left-[26px] top-9 bottom-9 w-px bg-border"
          aria-hidden="true"
        />
        {hitos.map((hito, idx) => (
          <HitoItem key={hito.label} hito={hito} esUltimo={idx === hitos.length - 1} />
        ))}
      </ol>
    </div>
  );
}

interface Hito {
  label: string;
  fecha: string | null;
  descripcion: string;
}

function HitoItem({ hito, esUltimo }: { hito: Hito; esUltimo: boolean }) {
  const cumplido = hito.fecha !== null && hito.fecha !== '';
  return (
    <li className={cn('relative flex gap-4', esUltimo ? '' : 'pb-5')}>
      <span
        className={cn(
          'relative z-10 inline-flex h-6 w-6 items-center justify-center rounded-full border-2 shrink-0 mt-0.5',
          cumplido
            ? 'bg-primary border-primary text-primary-foreground'
            : 'bg-card border-border text-muted-foreground',
        )}
        aria-hidden="true"
      >
        {cumplido ? (
          <Check className="w-3 h-3" strokeWidth={3} />
        ) : (
          <Circle className="w-2 h-2" />
        )}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-sm font-semibold text-foreground">{hito.label}</p>
          <span
            className={cn(
              'text-xs tabular-nums shrink-0',
              cumplido ? 'text-foreground font-medium' : 'text-muted-foreground',
            )}
          >
            {cumplido ? formatFecha(hito.fecha) : 'Pendiente'}
          </span>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">{hito.descripcion}</p>
      </div>
    </li>
  );
}
