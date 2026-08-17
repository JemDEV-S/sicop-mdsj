// Barra de ámbito del Análisis por meta (fiel a la plantilla v2): buscador de
// meta, filtro de naturaleza del gasto (Producto / Proyecto), chips de metas
// frecuentes, y las acciones "Reporte completo" y "Quitar meta".
//
// El filtro Producto/Proyecto es el que la plantilla no consideró y el usuario
// pidió sumar: filtra el ámbito cuando NO hay una meta puntual elegida.

import { useMemo, useState } from 'react';
import { BarChart3, Search, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { MetaReporte, ReporteResponse } from '../../reporte-types';
import { idMeta, type FiltroCategoria } from './datos';

const CATEGORIAS: { valor: FiltroCategoria; label: string }[] = [
  { valor: 'todas', label: 'Todas' },
  { valor: 'producto', label: 'Producto' },
  { valor: 'proyecto', label: 'Proyecto' },
];

export function AmbitoAnalisis({
  data,
  metaSel,
  categoria,
  onMeta,
  onCategoria,
  onReporte,
  ambitoLabel,
  ambitoAyuda,
}: {
  data: ReporteResponse;
  metaSel: number | null;
  categoria: FiltroCategoria;
  onMeta: (secFunc: number | null) => void;
  onCategoria: (c: FiltroCategoria) => void;
  onReporte: () => void;
  ambitoLabel: string;
  ambitoAyuda: string;
}) {
  const [busqueda, setBusqueda] = useState('');

  // Metas para el desplegable del buscador: filtradas por texto (nº o nombre).
  const coincidencias = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    if (!q) return [];
    return data.metas
      .filter(
        (m) =>
          idMeta(m).toLowerCase().includes(q) ||
          (m.nombre_meta ?? '').toLowerCase().includes(q),
      )
      .slice(0, 8);
  }, [data.metas, busqueda]);

  // Metas frecuentes = las de mayor PIM del ámbito (donde está el dinero).
  const chips = useMemo(
    () => [...data.metas].sort((a, b) => b.mef.pim - a.mef.pim).slice(0, 5),
    [data.metas],
  );

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-card px-4 py-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="shrink-0 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Ámbito de análisis
        </span>

        {/* Buscador de meta con desplegable de coincidencias */}
        <div className="relative min-w-[280px] flex-1">
          <div className="flex items-center gap-2 rounded-md border border-border bg-superficie-alt-2 px-3 py-2">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <input
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder={ambitoLabel}
              aria-label="Buscar una meta por número o nombre"
              className="min-w-0 flex-1 border-0 bg-transparent text-sm font-medium text-foreground outline-none placeholder:font-normal placeholder:text-muted-foreground"
            />
            <span className="hidden shrink-0 text-[10.5px] text-muted-foreground sm:inline">
              {ambitoAyuda}
            </span>
          </div>
          {coincidencias.length > 0 ? (
            <ul className="absolute z-30 mt-1 max-h-72 w-full overflow-y-auto rounded-md border border-border bg-popover py-1 shadow-lg">
              {coincidencias.map((m) => (
                <li key={m.sec_func}>
                  <button
                    type="button"
                    onClick={() => {
                      onMeta(m.sec_func);
                      setBusqueda('');
                    }}
                    className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-muted"
                  >
                    <span className="shrink-0 font-mono text-xs text-muted-foreground">
                      {idMeta(m)}
                    </span>
                    <span className="min-w-0 flex-1 truncate">{m.nombre_meta ?? 'Sin nombre'}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        {metaSel != null ? (
          <button
            type="button"
            onClick={() => onMeta(null)}
            className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border bg-card px-2.5 py-1.5 text-[11.5px] font-medium text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
            Quitar meta
          </button>
        ) : null}

        <button
          type="button"
          onClick={onReporte}
          className="inline-flex shrink-0 items-center gap-2 rounded-md border border-primary bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <BarChart3 className="h-4 w-4" aria-hidden="true" />
          Reporte completo
        </button>
      </div>

      {/* Naturaleza del gasto (solo cuando el ámbito es "todas las metas"). */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-muted-foreground">Naturaleza del gasto:</span>
          <div className="inline-flex overflow-hidden rounded-md border border-border">
            {CATEGORIAS.map((c) => {
              const activo = categoria === c.valor;
              const deshabilitado = metaSel != null;
              return (
                <button
                  key={c.valor}
                  type="button"
                  disabled={deshabilitado}
                  aria-pressed={activo}
                  onClick={() => onCategoria(c.valor)}
                  className={cn(
                    'px-3 py-1.5 text-[11.5px] font-medium transition-colors focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    activo ? 'bg-primary text-primary-foreground' : 'bg-card text-foreground hover:bg-muted',
                    deshabilitado && 'cursor-not-allowed opacity-50',
                  )}
                  title={deshabilitado ? 'Quita la meta elegida para filtrar por naturaleza' : undefined}
                >
                  {c.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Metas frecuentes (chips) */}
        {chips.length > 0 ? (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] text-muted-foreground">Metas frecuentes:</span>
            {chips.map((m) => (
              <ChipMeta key={m.sec_func} meta={m} activo={metaSel === m.sec_func} onSel={onMeta} />
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ChipMeta({
  meta,
  activo,
  onSel,
}: {
  meta: MetaReporte;
  activo: boolean;
  onSel: (secFunc: number | null) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSel(activo ? null : meta.sec_func)}
      aria-pressed={activo}
      title={meta.nombre_meta ?? undefined}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11.5px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        activo
          ? 'border-primary bg-primary text-primary-foreground'
          : 'border-border bg-card text-foreground hover:bg-muted',
      )}
    >
      <span className="font-mono">{idMeta(meta)}</span>
      <span className="max-w-[180px] truncate">{meta.nombre_meta ?? 'Sin nombre'}</span>
    </button>
  );
}
