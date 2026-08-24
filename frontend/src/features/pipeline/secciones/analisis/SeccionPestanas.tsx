// Sección con pestañas del Análisis por meta (fiel a la plantilla v2):
// Requerimientos · O/C · O/S · PECOSAS · Clasificadores. Cabecera de pestañas +
// barra de filtros (buscador + acciones por pestaña) + cuerpo delegado.
//
// La pestaña Contratos de la plantilla se omite a propósito: en SIGA los
// contratos son transversales (sin llave SEC_FUNC), así que no pueden ligarse a
// una meta sin inventar el vínculo. Viven en su propia página (/interno/contratos).

import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';

export type TabAnalisis = 'req' | 'oc' | 'os' | 'pec' | 'cla';

export interface TabDef {
  id: TabAnalisis;
  label: string;
  n: number;
}

export function SeccionPestanas({
  tabs,
  tabActiva,
  onTab,
  busqueda,
  onBusqueda,
  buscarPlaceholder,
  acciones,
  children,
}: {
  tabs: TabDef[];
  tabActiva: TabAnalisis;
  onTab: (t: TabAnalisis) => void;
  busqueda: string;
  onBusqueda: (v: string) => void;
  buscarPlaceholder: string;
  acciones?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-lg border border-border bg-card">
      {/* Cabecera de pestañas */}
      <div
        role="tablist"
        aria-label="Detalle del análisis"
        className="flex gap-0.5 overflow-x-auto border-b border-border bg-superficie-alt-2 px-1.5"
      >
        {tabs.map((t) => {
          const activa = tabActiva === t.id;
          return (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={activa}
              onClick={() => onTab(t.id)}
              className={cn(
                'inline-flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3.5 py-2.5 text-[12.5px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
                activa
                  ? 'border-primary font-semibold text-primary'
                  : 'border-transparent font-normal text-texto-suave hover:text-foreground',
              )}
            >
              {t.label}
              <span className="font-mono text-[10.5px] text-muted-foreground">{t.n}</span>
            </button>
          );
        })}
      </div>

      {/* Barra de filtros de la pestaña */}
      <div className="flex flex-wrap items-center gap-2.5 border-b border-border/60 px-4 py-3">
        <div className="flex min-w-[200px] flex-1 items-center gap-2 rounded-md border border-border px-3 py-1.5">
          <Search className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <input
            value={busqueda}
            onChange={(e) => onBusqueda(e.target.value)}
            placeholder={buscarPlaceholder}
            aria-label={buscarPlaceholder}
            className="min-w-0 flex-1 border-0 bg-transparent text-[12.5px] text-foreground outline-none placeholder:text-muted-foreground"
          />
        </div>
        {acciones}
      </div>

      {children}
    </section>
  );
}

/** Toggle segmentado reutilizable (modo Tabla / Kanban / Dinámica, etc.). */
export function SegmentoModo<T extends string>({
  opciones,
  valor,
  onChange,
  aria,
}: {
  opciones: { valor: T; label: string }[];
  valor: T;
  onChange: (v: T) => void;
  aria: string;
}) {
  return (
    <div
      role="radiogroup"
      aria-label={aria}
      className="inline-flex overflow-hidden rounded-md border border-border"
    >
      {opciones.map((o) => {
        const activo = valor === o.valor;
        return (
          <button
            key={o.valor}
            type="button"
            role="radio"
            aria-checked={activo}
            onClick={() => onChange(o.valor)}
            className={cn(
              'px-3 py-1.5 text-[11.5px] font-medium transition-colors focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              activo ? 'bg-primary text-primary-foreground' : 'bg-card text-foreground hover:bg-muted',
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
