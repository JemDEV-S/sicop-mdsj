import { AlertTriangle, Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

export interface FiltrosPipelineState {
  tipoBien: 'todos' | 'B' | 'S';
  soloEstancados: boolean;
  busqueda: string;
}

export const FILTROS_DEFAULT: FiltrosPipelineState = {
  tipoBien: 'todos',
  soloEstancados: false,
  busqueda: '',
};

interface FiltrosPipelineProps {
  filtros: FiltrosPipelineState;
  onChange: (filtros: FiltrosPipelineState) => void;
  totalEstancados: number;
}

// AC-09.3 pide filtros por tipo (B/S), fechas, área, proveedor. Fechas y
// proveedor quedan como puertas abiertas (§7.1 v2). En MVP los tres útiles
// del día a día:
//   - Tipo bien/servicio: alterna el universo.
//   - Solo estancados: atajo a la vista de trabajo urgente.
//   - Búsqueda por N° pedido: para saltar directo cuando conoces el número.
export function FiltrosPipeline({
  filtros,
  onChange,
  totalEstancados,
}: FiltrosPipelineProps) {
  const setTipo = (tipoBien: FiltrosPipelineState['tipoBien']) =>
    onChange({ ...filtros, tipoBien });

  return (
    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Tipo
        </span>
        <div
          role="radiogroup"
          aria-label="Filtrar por tipo de pedido"
          className="inline-flex rounded-md border border-border overflow-hidden"
        >
          {(
            [
              { valor: 'todos', label: 'Todos' },
              { valor: 'B', label: 'Bienes' },
              { valor: 'S', label: 'Servicios' },
            ] as const
          ).map((opt) => {
            const activo = filtros.tipoBien === opt.valor;
            return (
              <button
                key={opt.valor}
                type="button"
                role="radio"
                aria-checked={activo}
                onClick={() => setTipo(opt.valor)}
                className={cn(
                  'px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:z-10',
                  activo
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-card text-foreground hover:bg-muted',
                )}
              >
                {opt.label}
              </button>
            );
          })}
        </div>

        <button
          type="button"
          onClick={() =>
            onChange({ ...filtros, soloEstancados: !filtros.soloEstancados })
          }
          aria-pressed={filtros.soloEstancados}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            filtros.soloEstancados
              ? 'border-destructive/60 bg-destructive/10 text-destructive'
              : 'border-border bg-card text-foreground hover:bg-muted',
          )}
        >
          <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
          Solo estancados
          <span className="ml-1 tabular-nums opacity-80">
            ({totalEstancados})
          </span>
        </button>
      </div>

      <div className="relative w-full md:w-64">
        <Search
          className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground"
          aria-hidden="true"
        />
        <Input
          type="search"
          inputMode="numeric"
          placeholder="N° de pedido"
          value={filtros.busqueda}
          onChange={(e) =>
            onChange({ ...filtros, busqueda: e.target.value })
          }
          aria-label="Buscar por número de pedido"
          className="pl-8 h-9 text-sm"
        />
      </div>
    </div>
  );
}

export default FiltrosPipeline;
