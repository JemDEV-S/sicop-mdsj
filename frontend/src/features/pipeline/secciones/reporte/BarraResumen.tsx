// Barra superior: un chip por macrofase con su total de monto SIGA y cuántos
// pedidos están estancados. Clicar un chip filtra la tabla a esa macrofase.

import type { Macrofase } from '@/features/dashboard/types';
import { formatearNumero } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import { ACENTO_MACROFASE, LABEL_MACROFASE } from './constantes';
import type { ResumenMacrofase } from './tipos';

export function BarraResumen({
  resumen,
  seleccionadas,
  onToggle,
}: {
  resumen: ResumenMacrofase[];
  seleccionadas: Macrofase[];
  onToggle: (m: Macrofase) => void;
}) {
  if (resumen.length === 0) return null;
  const setSel = new Set(seleccionadas);

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
      {resumen.map((r) => {
        const activa = setSel.has(r.macrofase);
        return (
          <button
            key={r.macrofase}
            type="button"
            onClick={() => onToggle(r.macrofase)}
            aria-pressed={activa}
            className={cn(
              'flex flex-col items-start gap-0.5 rounded-md border border-l-4 bg-card px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              ACENTO_MACROFASE[r.macrofase],
              activa ? 'border-primary bg-primary/5 ring-1 ring-primary/40' : 'hover:bg-muted',
            )}
          >
            <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              {LABEL_MACROFASE[r.macrofase]}
            </span>
            <span className="font-mono text-base font-semibold tabular-nums text-foreground">
              <span className="text-xs font-normal text-muted-foreground">S/ </span>
              {formatearNumero(r.monto_siga, 0)}
            </span>
            <span className="text-[11px] text-muted-foreground">
              {r.n_pedidos} ped.
              {r.n_estancados > 0 ? (
                <span className="ml-1 font-medium text-destructive">
                  · {r.n_estancados} estanc.
                </span>
              ) : null}
            </span>
          </button>
        );
      })}
    </div>
  );
}
