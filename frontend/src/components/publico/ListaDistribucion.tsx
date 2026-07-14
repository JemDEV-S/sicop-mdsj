import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { parseMonto, formatearMoneda } from '@/lib/formatters';

export interface DistribucionItem {
  codigo: string;
  nombre: string;
  pim: string | number | null;
  devengado?: string | number | null;
  participacion_pim?: string | number | null;
}

interface ListaDistribucionProps {
  items?: DistribucionItem[];
  isLoading: boolean;
  /** Color de las barras. */
  acento?: 'primary' | 'secondary' | 'accent';
  /** Texto de contexto por item (ej: 'del presupuesto viene de'). */
  vacio?: string;
  /** Cantidad máxima de items visibles antes de scroll interno. */
  maxVisible?: number;
}

const ACENTO_BG: Record<NonNullable<ListaDistribucionProps['acento']>, string> = {
  primary: 'bg-primary',
  secondary: 'bg-secondary',
  accent: 'bg-accent',
};

/**
 * Lista horizontal de "barras de participación" para mostrar una
 * distribución de montos por categoría. Alternativa clara al pie chart:
 * el ciudadano lee de arriba a abajo, las barras dan la proporción visual.
 */
export function ListaDistribucion({
  items,
  isLoading,
  acento = 'primary',
  vacio = 'No hay datos disponibles.',
  maxVisible,
}: ListaDistribucionProps) {
  const normalizados = useMemo(() => {
    if (!items) return [];
    const filas = items.map((it) => ({
      codigo: it.codigo,
      nombre: it.nombre,
      pim: parseMonto(it.pim) ?? 0,
      devengado: parseMonto(it.devengado ?? null) ?? 0,
      participacion: parseMonto(it.participacion_pim ?? null),
    }));
    const maxPim = filas.reduce((m, f) => Math.max(m, f.pim), 0);
    return filas.map((f) => ({
      ...f,
      // Ancho relativo al mayor (no al total), para que la barra más
      // grande siempre llene todo el track y sea legible.
      widthPct: maxPim > 0 ? (f.pim / maxPim) * 100 : 0,
    }));
  }, [items]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-1.5">
            <div className="h-3 w-1/2 bg-muted animate-pulse rounded" />
            <div className="h-4 w-full bg-muted animate-pulse rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (normalizados.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
        {vacio}
      </div>
    );
  }

  return (
    <ul
      className={cn('space-y-4', maxVisible ? 'max-h-[420px] overflow-y-auto pr-1' : '')}
      style={maxVisible ? undefined : undefined}
    >
      {normalizados.map((it) => (
        <li key={it.codigo}>
          <div className="flex items-baseline justify-between gap-3 mb-1.5">
            <p className="text-sm font-medium text-foreground line-clamp-2 min-w-0 flex-1">
              {it.nombre}
            </p>
            <p className="text-sm font-bold text-foreground tabular-nums shrink-0">
              {formatearMoneda(it.pim, true)}
            </p>
          </div>

          <div className="h-2 w-full rounded-full bg-muted overflow-hidden" aria-hidden="true">
            <div
              className={cn('h-full rounded-full transition-all', ACENTO_BG[acento])}
              style={{ width: `${it.widthPct}%` }}
            />
          </div>

          <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {it.participacion !== null ? `${it.participacion.toFixed(1)}% del total` : '—'}
            </span>
            {it.devengado > 0 ? (
              <span>
                Ejecutado:{' '}
                <span className="font-semibold text-foreground tabular-nums">
                  {formatearMoneda(it.devengado, true)}
                </span>
              </span>
            ) : null}
          </div>
        </li>
      ))}
    </ul>
  );
}

export default ListaDistribucion;
