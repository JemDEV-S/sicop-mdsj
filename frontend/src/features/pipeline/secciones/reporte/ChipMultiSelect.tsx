// Multi-selección ligera por chips toggleables, con buscador interno cuando la
// lista es larga. Sin dependencias extra (no hay popover/checkbox en la UI).

import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface OpcionChip<T extends string | number> {
  valor: T;
  label: string;
  sublabel?: string | null;
}

export function ChipMultiSelect<T extends string | number>({
  titulo,
  opciones,
  seleccionadas,
  onToggle,
  conBuscador = false,
  placeholderBuscador = 'Buscar…',
}: {
  titulo: string;
  opciones: OpcionChip<T>[];
  seleccionadas: T[];
  onToggle: (valor: T) => void;
  conBuscador?: boolean;
  placeholderBuscador?: string;
}) {
  const [q, setQ] = useState('');
  const setSel = useMemo(() => new Set(seleccionadas), [seleccionadas]);

  const visibles = useMemo(() => {
    if (!conBuscador || !q.trim()) return opciones;
    const t = q.trim().toLowerCase();
    return opciones.filter(
      (o) =>
        o.label.toLowerCase().includes(t) ||
        (o.sublabel ?? '').toLowerCase().includes(t) ||
        String(o.valor).toLowerCase().includes(t),
    );
  }, [opciones, q, conBuscador]);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          {titulo}
        </span>
        {seleccionadas.length > 0 ? (
          <span className="text-[11px] text-muted-foreground">
            {seleccionadas.length} seleccionado{seleccionadas.length === 1 ? '' : 's'}
          </span>
        ) : null}
      </div>

      {conBuscador ? (
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={placeholderBuscador}
            className="h-8 w-full rounded-md border border-border bg-card pl-7 pr-2 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
      ) : null}

      <div className="flex max-h-32 flex-wrap gap-1.5 overflow-y-auto">
        {visibles.length === 0 ? (
          <span className="text-xs text-muted-foreground">Sin coincidencias.</span>
        ) : (
          visibles.map((o) => {
            const activa = setSel.has(o.valor);
            return (
              <button
                key={String(o.valor)}
                type="button"
                onClick={() => onToggle(o.valor)}
                aria-pressed={activa}
                title={o.sublabel ?? o.label}
                className={cn(
                  'inline-flex max-w-full items-center rounded-full border px-2.5 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  activa
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border bg-card text-foreground hover:bg-muted',
                )}
              >
                <span className="truncate">{o.label}</span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
