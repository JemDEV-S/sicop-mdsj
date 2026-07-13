import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface FiltroChip {
  id: string;
  label: string;
  onRemove: () => void;
}

interface FiltroChipsProps {
  chips: FiltroChip[];
  onLimpiarTodos?: () => void;
  className?: string;
}

export function FiltroChips({
  chips,
  onLimpiarTodos,
  className,
}: FiltroChipsProps) {
  if (chips.length === 0) return null;

  return (
    <div
      className={cn('flex flex-wrap items-center gap-2', className)}
      role="group"
      aria-label="Filtros activos"
    >
      <span className="text-sm text-muted-foreground">Filtros activos:</span>

      {chips.map((chip) => (
        <span
          key={chip.id}
          className="inline-flex items-center gap-1.5 bg-muted text-foreground text-sm px-3 py-1 rounded-md border border-border"
        >
          <span>{chip.label}</span>
          <button
            type="button"
            onClick={chip.onRemove}
            aria-label={`Quitar filtro ${chip.label}`}
            className="inline-flex items-center justify-center rounded-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
        </span>
      ))}

      {onLimpiarTodos && chips.length > 1 ? (
        <button
          type="button"
          onClick={onLimpiarTodos}
          className="text-sm text-primary hover:underline focus-visible:outline-none focus-visible:underline"
        >
          Limpiar todos
        </button>
      ) : null}
    </div>
  );
}

export default FiltroChips;
