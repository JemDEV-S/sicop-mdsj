// "Dinero del requerimiento": filas etiqueta → valor con un badge que rotula la
// naturaleza del dato (sumable / estimado / real / pendiente). El único dato
// sumable por pedido es el monto SIGA solicitado; lo demás es contexto rotulado.

import { cn } from '@/lib/utils';

export type BadgeDinero = 'sumable' | 'estimado' | 'real' | 'pendiente';

const BADGE: Record<BadgeDinero, string> = {
  sumable: 'border-border bg-muted text-muted-foreground',
  estimado: 'border-accent/40 bg-accent/10 text-accent-foreground',
  real: 'border-secondary/40 bg-secondary/10 text-secondary-foreground',
  pendiente: 'border-border bg-superficie-alt text-muted-foreground',
};

export interface FilaDinero {
  label: string;
  valor: string;
  badge: BadgeDinero;
  fuerte?: boolean;
}

export function DineroPedido({ filas, nota }: { filas: FilaDinero[]; nota?: string }) {
  return (
    <div className="flex flex-col gap-1">
      {filas.map((f) => (
        <div key={f.label} className="flex items-center gap-2.5 border-b border-border/60 py-1.5 last:border-0">
          <span className="flex-1 text-[12px] text-foreground">{f.label}</span>
          <span
            className={cn(
              'font-mono text-[12.5px] tabular-nums',
              f.fuerte ? 'font-semibold text-foreground' : 'text-muted-foreground',
            )}
          >
            {f.valor}
          </span>
          <span
            className={cn(
              'w-[74px] shrink-0 rounded border px-1.5 py-px text-center text-[9.5px] font-semibold',
              BADGE[f.badge],
            )}
          >
            {f.badge}
          </span>
        </div>
      ))}
      {nota ? <p className="pt-1 text-[10.5px] leading-relaxed text-muted-foreground">{nota}</p> : null}
    </div>
  );
}

export default DineroPedido;
