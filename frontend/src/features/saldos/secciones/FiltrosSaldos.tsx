import { useState } from 'react';
import { Search, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { FiltroChips, type FiltroChip } from '@/components/forms/FiltroChips';
import { cn } from '@/lib/utils';
import { etiquetaFiltroSemaforo, formatSecFunc } from '../lib';
import type { FiltrosSaldos, SemaforoSaldo } from '../types';

interface FiltrosSaldosProps {
  filtros: FiltrosSaldos;
  onChange: (filtros: FiltrosSaldos) => void;
  /** Nombre del CC activo (topbar) — se muestra como contexto, no editable aquí. */
  ccNombre: string | null;
}

const SEMAFOROS: { valor: SemaforoSaldo; punto: string }[] = [
  { valor: 'rojo', punto: 'bg-[var(--semaforo-critico)]' },
  { valor: 'amarillo', punto: 'bg-[var(--semaforo-alerta)]' },
  { valor: 'verde', punto: 'bg-[var(--semaforo-ok)]' },
  { valor: 'desconocido', punto: 'bg-muted-foreground/50' },
];

/**
 * Controles de filtro del listado de saldos.
 *
 * - Semáforo: pastillas conmutables (filtra en cliente sobre el estado que ya
 *   trae cada fila desde el backend, sobre devengado MEF real).
 * - SEC_FUNC: búsqueda por meta exacta (filtro backend nativo).
 * - El centro de costo se controla desde el chip del topbar (decisión de diseño:
 *   un solo lugar de control); aquí solo se muestra como contexto.
 */
export function FiltrosSaldos({ filtros, onChange, ccNombre }: FiltrosSaldosProps) {
  const [textoMeta, setTextoMeta] = useState(
    filtros.secFunc != null ? String(filtros.secFunc) : '',
  );

  const aplicarMeta = () => {
    const limpio = textoMeta.trim();
    const num = limpio === '' ? null : Number.parseInt(limpio, 10);
    onChange({ ...filtros, secFunc: Number.isNaN(num as number) ? null : num });
  };

  const toggleSemaforo = (valor: SemaforoSaldo) => {
    onChange({
      ...filtros,
      semaforo: filtros.semaforo === valor ? null : valor,
    });
  };

  const limpiarTodos = () => {
    setTextoMeta('');
    onChange({ semaforo: null, secFunc: null });
  };

  const chips: FiltroChip[] = [];
  if (filtros.semaforo) {
    chips.push({
      id: 'semaforo',
      label: `Estado: ${etiquetaFiltroSemaforo(filtros.semaforo)}`,
      onRemove: () => onChange({ ...filtros, semaforo: null }),
    });
  }
  if (filtros.secFunc != null) {
    chips.push({
      id: 'sec_func',
      label: `Meta ${formatSecFunc(filtros.secFunc)}`,
      onRemove: () => {
        setTextoMeta('');
        onChange({ ...filtros, secFunc: null });
      },
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        {/* Semáforo */}
        <fieldset className="flex flex-col gap-2">
          <legend className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Estado de ejecución (MEF)
          </legend>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por estado">
            {SEMAFOROS.map(({ valor, punto }) => {
              const activo = filtros.semaforo === valor;
              return (
                <button
                  key={valor}
                  type="button"
                  onClick={() => toggleSemaforo(valor)}
                  aria-pressed={activo}
                  className={cn(
                    'inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    activo
                      ? 'border-primary bg-primary/10 text-foreground font-medium'
                      : 'border-border text-muted-foreground hover:bg-muted',
                  )}
                >
                  <span className={cn('h-2.5 w-2.5 rounded-full', punto)} aria-hidden="true" />
                  {etiquetaFiltroSemaforo(valor)}
                </button>
              );
            })}
          </div>
        </fieldset>

        {/* Búsqueda por meta */}
        <div className="flex flex-col gap-2">
          <label
            htmlFor="filtro-sec-func"
            className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
          >
            Buscar meta (SEC_FUNC)
          </label>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <input
                id="filtro-sec-func"
                type="text"
                inputMode="numeric"
                value={textoMeta}
                onChange={(e) => setTextoMeta(e.target.value.replace(/[^\d]/g, ''))}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') aplicarMeta();
                }}
                placeholder="Ej. 129"
                className="h-9 w-40 rounded-md border border-input bg-background pl-8 pr-8 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              {textoMeta ? (
                <button
                  type="button"
                  onClick={() => {
                    setTextoMeta('');
                    onChange({ ...filtros, secFunc: null });
                  }}
                  aria-label="Limpiar búsqueda de meta"
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              ) : null}
            </div>
            <Button type="button" variant="outline" size="sm" onClick={aplicarMeta}>
              Buscar
            </Button>
          </div>
        </div>
      </div>

      {ccNombre ? (
        <p className="text-xs text-muted-foreground">
          Mostrando las metas de{' '}
          <span className="font-medium text-foreground">{ccNombre}</span>. Cambia la
          unidad desde el selector del encabezado.
        </p>
      ) : null}

      <FiltroChips chips={chips} onLimpiarTodos={limpiarTodos} />
    </div>
  );
}

export default FiltrosSaldos;
