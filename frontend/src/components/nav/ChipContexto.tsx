import { useEffect, useRef, useState } from 'react';
import { Building2, Calendar, Check, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/store/auth';
import {
  AÑOS_DISPONIBLES,
  useContextoInterno,
  type AñoActivo,
} from '@/store/contexto-interno';
import type { CentroCostoBreve } from '@/store/auth';

interface ChipDropdownProps<T> {
  icono: React.ComponentType<{ className?: string }>;
  etiqueta: string;
  valor: string;
  opciones: T[];
  onSelect: (opcion: T) => void;
  renderOpcion: (opcion: T) => React.ReactNode;
  esActiva: (opcion: T) => boolean;
  disabled?: boolean;
  ariaLabel: string;
}

function ChipDropdown<T>({
  icono: Icono,
  etiqueta,
  valor,
  opciones,
  onSelect,
  renderOpcion,
  esActiva,
  disabled,
  ariaLabel,
}: ChipDropdownProps<T>) {
  const [abierto, setAbierto] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!abierto) return;
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setAbierto(false);
      }
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, [abierto]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => !disabled && setAbierto((v) => !v)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={abierto}
        aria-label={ariaLabel}
        className={cn(
          'inline-flex items-center gap-2 h-9 px-3 rounded-full',
          'bg-primary/10 text-primary text-sm font-medium',
          'border border-primary/20',
          'hover:bg-primary/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          'disabled:opacity-60 disabled:cursor-not-allowed',
          'transition-colors',
        )}
      >
        <Icono className="w-4 h-4 shrink-0" aria-hidden="true" />
        <span className="text-xs text-primary/70 uppercase tracking-wide hidden sm:inline">
          {etiqueta}
        </span>
        <span className="truncate max-w-[10rem]">{valor}</span>
        {!disabled ? (
          <ChevronDown className="w-3.5 h-3.5 shrink-0 opacity-70" aria-hidden="true" />
        ) : null}
      </button>

      {abierto ? (
        <div
          role="listbox"
          className="absolute right-0 mt-2 min-w-[14rem] max-w-xs bg-card border border-border rounded-md shadow-md py-1 z-40 max-h-72 overflow-y-auto"
        >
          {opciones.map((opcion, i) => {
            const activa = esActiva(opcion);
            return (
              <button
                key={i}
                type="button"
                role="option"
                aria-selected={activa}
                onClick={() => {
                  onSelect(opcion);
                  setAbierto(false);
                }}
                className={cn(
                  'w-full flex items-center gap-2 px-3 py-2 text-sm text-left',
                  'hover:bg-muted focus-visible:outline-none focus-visible:bg-muted',
                  activa && 'bg-primary/5 text-primary font-medium',
                )}
              >
                <span className="flex-1 min-w-0">{renderOpcion(opcion)}</span>
                {activa ? (
                  <Check className="w-4 h-4 shrink-0" aria-hidden="true" />
                ) : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

export function ChipAñoActivo() {
  const año = useContextoInterno((s) => s.añoActivo);
  const setAño = useContextoInterno((s) => s.setAño);

  return (
    <ChipDropdown<AñoActivo>
      icono={Calendar}
      etiqueta="Año"
      valor={String(año)}
      opciones={[...AÑOS_DISPONIBLES].reverse()}
      onSelect={(a) => setAño(a)}
      renderOpcion={(a) => <span>{a}</span>}
      esActiva={(a) => a === año}
      ariaLabel={`Año activo: ${año}. Cambiar año.`}
    />
  );
}

export function ChipCentroCostoActivo() {
  const cc = useContextoInterno((s) => s.ccActivo);
  const setCc = useContextoInterno((s) => s.setCc);
  const centros = useAuthStore((s) => s.user?.centros_costo ?? []);

  if (centros.length === 0) return null;

  const label = cc?.abreviado ?? cc?.nombre ?? cc?.codigo ?? 'Sin CC';
  const disabled = centros.length === 1;

  return (
    <ChipDropdown<CentroCostoBreve>
      icono={Building2}
      etiqueta="Unidad"
      valor={label}
      opciones={centros}
      onSelect={(c) => setCc(c)}
      renderOpcion={(c) => (
        <span className="flex flex-col leading-tight">
          <span className="truncate">{c.nombre}</span>
          <span className="text-xs text-muted-foreground font-mono">
            {c.codigo}
          </span>
        </span>
      )}
      esActiva={(c) => c.codigo === cc?.codigo}
      disabled={disabled}
      ariaLabel={
        disabled
          ? `Centro de costo: ${label} (único asignado)`
          : `Centro de costo activo: ${label}. Cambiar.`
      }
    />
  );
}
