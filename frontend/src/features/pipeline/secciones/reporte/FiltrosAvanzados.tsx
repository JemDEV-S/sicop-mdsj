// Panel de filtros avanzados + controles de la tabla dinámica (agrupar/ordenar).
// El buscador y "Agrupar por" están siempre visibles; el resto se despliega.

import { useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, Search, SlidersHorizontal, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { OPCIONES_AGRUPACION, OPCIONES_ORDEN } from './constantes';
import { ChipMultiSelect } from './ChipMultiSelect';
import type { OpcionChip } from './ChipMultiSelect';
import { MACROFASES } from './constantes';
import type {
  CampoAgrupacion,
  CampoOrden,
  CentroCostoLabelFn,
  DireccionOrden,
  FilaPedido,
  FiltrosReporte,
} from './tipos';
import { FILTROS_DEFAULT } from './tipos';

interface Props {
  filtros: FiltrosReporte;
  onChange: (f: FiltrosReporte) => void;
  filas: FilaPedido[]; // universo sin filtrar, para poblar las opciones
  ccLabel: CentroCostoLabelFn;
  agrupacion: CampoAgrupacion;
  onAgrupacion: (c: CampoAgrupacion) => void;
  orden: CampoOrden;
  direccion: DireccionOrden;
  onOrden: (c: CampoOrden) => void;
  onDireccion: (d: DireccionOrden) => void;
}

export function FiltrosAvanzados({
  filtros,
  onChange,
  filas,
  ccLabel,
  agrupacion,
  onAgrupacion,
  orden,
  direccion,
  onOrden,
  onDireccion,
}: Props) {
  const [abierto, setAbierto] = useState(false);

  const opcionesCC = useMemo<OpcionChip<string>[]>(() => {
    const set = new Set<string>();
    filas.forEach((f) => f.centro_costo && set.add(f.centro_costo));
    return [...set]
      .map((cod) => {
        const l = ccLabel(cod);
        return { valor: cod, label: l.sigla, sublabel: l.nombre };
      })
      .sort((a, b) => a.label.localeCompare(b.label, 'es'));
  }, [filas, ccLabel]);

  const opcionesMeta = useMemo<OpcionChip<number>[]>(() => {
    const map = new Map<number, string | null>();
    filas.forEach((f) => map.set(f.sec_func, f.nombre_meta));
    return [...map.entries()]
      .map(([sf, nombre]) => ({
        valor: sf,
        label: `${sf}`,
        sublabel: nombre,
      }))
      .sort((a, b) => a.valor - b.valor);
  }, [filas]);

  const opcionesMF = useMemo<OpcionChip<(typeof MACROFASES)[number]['macrofase']>[]>(
    () => MACROFASES.map((m) => ({ valor: m.macrofase, label: m.label })),
    [],
  );

  const nFiltrosActivos = contarFiltros(filtros);

  const toggleEn = <T,>(arr: T[], v: T): T[] =>
    arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v];

  return (
    <div className="flex flex-col gap-3">
      {/* Fila siempre visible: búsqueda + agrupar/ordenar + botón avanzado */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="relative w-full lg:max-w-sm">
          <Search
            className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            type="search"
            placeholder="Buscar: pedido, orden, SIAF, meta, clasificador…"
            value={filtros.busqueda}
            onChange={(e) => onChange({ ...filtros, busqueda: e.target.value })}
            aria-label="Buscar en el reporte"
            className="h-9 pl-8 text-sm"
          />
        </div>

        <div className="flex flex-wrap items-end gap-2">
          <Selector
            label="Agrupar por"
            value={agrupacion}
            onChange={(v) => onAgrupacion(v as CampoAgrupacion)}
            opciones={OPCIONES_AGRUPACION.map((o) => ({ valor: o.valor, label: o.label }))}
          />
          <Selector
            label="Ordenar por"
            value={orden}
            onChange={(v) => onOrden(v as CampoOrden)}
            opciones={OPCIONES_ORDEN.map((o) => ({ valor: o.valor, label: o.label }))}
          />
          <button
            type="button"
            onClick={() => onDireccion(direccion === 'asc' ? 'desc' : 'asc')}
            title={direccion === 'asc' ? 'Ascendente' : 'Descendente'}
            className="inline-flex h-9 items-center gap-1 rounded-md border border-border bg-card px-2.5 text-sm text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {direccion === 'asc' ? (
              <ChevronUp className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ChevronDown className="h-4 w-4" aria-hidden="true" />
            )}
          </button>

          <button
            type="button"
            onClick={() => setAbierto((v) => !v)}
            aria-expanded={abierto}
            className={cn(
              'inline-flex h-9 items-center gap-1.5 rounded-md border px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              nFiltrosActivos > 0
                ? 'border-primary/60 bg-primary/10 text-primary'
                : 'border-border bg-card text-foreground hover:bg-muted',
            )}
          >
            <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
            Filtros
            {nFiltrosActivos > 0 ? (
              <span className="ml-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-[11px] font-semibold text-primary-foreground">
                {nFiltrosActivos}
              </span>
            ) : null}
          </button>
        </div>
      </div>

      {/* Panel avanzado desplegable */}
      {abierto ? (
        <div className="flex flex-col gap-4 rounded-md border border-border bg-muted/30 p-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <ChipMultiSelect
              titulo="Fase del pipeline"
              opciones={opcionesMF}
              seleccionadas={filtros.macrofases}
              onToggle={(v) => onChange({ ...filtros, macrofases: toggleEn(filtros.macrofases, v) })}
            />
            <ChipMultiSelect
              titulo="Centro de costo"
              opciones={opcionesCC}
              seleccionadas={filtros.centrosCosto}
              onToggle={(v) => onChange({ ...filtros, centrosCosto: toggleEn(filtros.centrosCosto, v) })}
              conBuscador
              placeholderBuscador="Buscar centro…"
            />
            <ChipMultiSelect
              titulo="Meta"
              opciones={opcionesMeta}
              seleccionadas={filtros.metas}
              onToggle={(v) => onChange({ ...filtros, metas: toggleEn(filtros.metas, v) })}
              conBuscador
              placeholderBuscador="Buscar meta…"
            />
          </div>

          <div className="flex flex-wrap items-end gap-4">
            <RangoNumerico
              label="Monto SIGA (S/)"
              min={filtros.montoMin}
              max={filtros.montoMax}
              onMin={(v) => onChange({ ...filtros, montoMin: v })}
              onMax={(v) => onChange({ ...filtros, montoMax: v })}
            />
            <label className="flex flex-col gap-1">
              <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Días en etapa (mín.)
              </span>
              <input
                type="number"
                min={0}
                value={filtros.diasMin ?? ''}
                onChange={(e) =>
                  onChange({ ...filtros, diasMin: e.target.value === '' ? null : Number(e.target.value) })
                }
                placeholder="—"
                className="h-9 w-28 rounded-md border border-border bg-card px-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>

            <div className="flex flex-wrap items-center gap-2">
              <Toggle
                activo={filtros.soloEstancados}
                tono="destructive"
                onClick={() => onChange({ ...filtros, soloEstancados: !filtros.soloEstancados })}
              >
                Solo estancados
              </Toggle>
              <Toggle
                activo={filtros.soloConOrden}
                onClick={() =>
                  onChange({ ...filtros, soloConOrden: !filtros.soloConOrden, soloSinOrden: false })
                }
              >
                Con orden
              </Toggle>
              <Toggle
                activo={filtros.soloSinOrden}
                onClick={() =>
                  onChange({ ...filtros, soloSinOrden: !filtros.soloSinOrden, soloConOrden: false })
                }
              >
                Sin orden
              </Toggle>
            </div>
          </div>
        </div>
      ) : null}

      {nFiltrosActivos > 0 ? (
        <button
          type="button"
          onClick={() => onChange(FILTROS_DEFAULT)}
          className="inline-flex w-fit items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" aria-hidden="true" />
          Limpiar {nFiltrosActivos} filtro{nFiltrosActivos === 1 ? '' : 's'}
        </button>
      ) : null}
    </div>
  );
}

// ─── Piezas del panel ────────────────────────────────────────────────────

function Selector({
  label,
  value,
  onChange,
  opciones,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  opciones: { valor: string; label: string }[];
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 min-w-[150px] rounded-md border border-border bg-card px-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {opciones.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function RangoNumerico({
  label,
  min,
  max,
  onMin,
  onMax,
}: {
  label: string;
  min: number | null;
  max: number | null;
  onMin: (v: number | null) => void;
  onMax: (v: number | null) => void;
}) {
  const parse = (v: string): number | null => (v === '' ? null : Number(v));
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <div className="flex items-center gap-1.5">
        <input
          type="number"
          min={0}
          value={min ?? ''}
          onChange={(e) => onMin(parse(e.target.value))}
          placeholder="mín."
          className="h-9 w-28 rounded-md border border-border bg-card px-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <span className="text-muted-foreground">–</span>
        <input
          type="number"
          min={0}
          value={max ?? ''}
          onChange={(e) => onMax(parse(e.target.value))}
          placeholder="máx."
          className="h-9 w-28 rounded-md border border-border bg-card px-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>
    </div>
  );
}

function Toggle({
  activo,
  tono = 'primary',
  onClick,
  children,
}: {
  activo: boolean;
  tono?: 'primary' | 'destructive';
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={activo}
      className={cn(
        'inline-flex items-center rounded-md border px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        activo
          ? tono === 'destructive'
            ? 'border-destructive/60 bg-destructive/10 text-destructive'
            : 'border-primary/60 bg-primary/10 text-primary'
          : 'border-border bg-card text-foreground hover:bg-muted',
      )}
    >
      {children}
    </button>
  );
}

function contarFiltros(f: FiltrosReporte): number {
  let n = 0;
  if (f.centrosCosto.length) n += 1;
  if (f.macrofases.length) n += 1;
  if (f.metas.length) n += 1;
  if (f.soloEstancados) n += 1;
  if (f.soloConOrden) n += 1;
  if (f.soloSinOrden) n += 1;
  if (f.montoMin != null || f.montoMax != null) n += 1;
  if (f.diasMin != null) n += 1;
  return n;
}
