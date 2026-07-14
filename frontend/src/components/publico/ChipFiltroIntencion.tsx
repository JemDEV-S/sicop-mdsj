import type { LucideIcon } from 'lucide-react';
import { X, Filter } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChipFiltroIntencionProps {
  icono: LucideIcon;
  titulo: string;
  descripcion: string;
  /** Chips de filtros aplicados por este intento (para mostrar en el chip). */
  aplicados?: string[];
  activo?: boolean;
  acento?: 'primary' | 'secondary' | 'accent';
  onAbrir: () => void;
  onLimpiar?: () => void;
  className?: string;
}

const ACENTO_BORDE: Record<NonNullable<ChipFiltroIntencionProps['acento']>, string> = {
  primary: 'data-[activo=true]:border-primary data-[activo=true]:bg-primary/5',
  secondary: 'data-[activo=true]:border-secondary data-[activo=true]:bg-secondary/5',
  accent: 'data-[activo=true]:border-accent data-[activo=true]:bg-accent/5',
};

const ACENTO_ICONO: Record<NonNullable<ChipFiltroIntencionProps['acento']>, string> = {
  primary: 'bg-primary/10 text-primary',
  secondary: 'bg-secondary/10 text-secondary',
  accent: 'bg-accent/20 text-accent-foreground',
};

/**
 * Chip grande estilo tarjeta para filtros por intención ciudadana.
 * Al hacer click abre un panel con los controles reales del filtro.
 * Muestra los valores aplicados como badges internos, con opción de
 * limpiar todos los del bloque de un click.
 */
export function ChipFiltroIntencion({
  icono: Icono,
  titulo,
  descripcion,
  aplicados = [],
  activo = false,
  acento = 'primary',
  onAbrir,
  onLimpiar,
  className,
}: ChipFiltroIntencionProps) {
  return (
    <div
      data-activo={activo}
      className={cn(
        'group relative rounded-xl border-2 border-border bg-card p-4 md:p-5',
        'transition-all',
        ACENTO_BORDE[acento],
        className,
      )}
    >
      <button
        type="button"
        onClick={onAbrir}
        className="w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-lg"
      >
        <div className="flex items-start gap-3">
          <span
            className={cn(
              'inline-flex h-10 w-10 items-center justify-center rounded-lg shrink-0',
              ACENTO_ICONO[acento],
            )}
          >
            <Icono className="w-5 h-5" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm md:text-base font-semibold text-foreground">{titulo}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{descripcion}</p>
          </div>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground shrink-0 mt-1 inline-flex items-center gap-1">
            <Filter className="w-3 h-3" aria-hidden="true" />
            {activo ? 'Editar' : 'Filtrar'}
          </span>
        </div>
      </button>

      {aplicados.length > 0 ? (
        <div className="mt-3 pt-3 border-t border-border flex items-center gap-2 flex-wrap">
          {aplicados.map((f, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-foreground"
            >
              {f}
            </span>
          ))}
          {onLimpiar ? (
            <button
              type="button"
              onClick={onLimpiar}
              className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-destructive transition-colors"
              aria-label={`Limpiar filtros de ${titulo}`}
            >
              <X className="w-3 h-3" aria-hidden="true" />
              Limpiar
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export default ChipFiltroIntencion;
