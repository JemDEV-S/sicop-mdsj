import { useState, useMemo } from 'react';
import {
  ChevronRight,
  Trophy,
  ArrowDown,
  ArrowUpDown,
  Package,
  Coins,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { parseMonto, formatearMoneda } from '@/lib/formatters';
import { useMetaDesglose } from '@/features/ejecucion/hooks';
import type { EjecucionDetalleItem } from '@/features/ejecucion/types';
import { Button } from '@/components/ui/button';

export type SortKey = 'pim' | 'devengado' | 'pct_desc' | 'pct_asc';

interface TablaMetasProps {
  items: EjecucionDetalleItem[];
  isLoading?: boolean;
  ano: number;
  /** Paginación */
  pageIndex: number;
  pageSize: number;
  pageCount: number;
  totalItems: number;
  onPageChange: (pageIndex: number) => void;
  onPageSizeChange: (size: number) => void;
  /** Ordenamiento (controlado desde el padre para pedir al backend). */
  sortKey: SortKey;
  onSortChange: (k: SortKey) => void;
}

const PAGE_SIZES = [10, 25, 50];

const CLASE_SEMAFORO = (pct: number | null): { fondo: string; texto: string; etiqueta: string } => {
  if (pct === null) return { fondo: 'bg-muted', texto: 'text-muted-foreground', etiqueta: 'Sin datos' };
  if (pct >= 80) return { fondo: 'bg-emerald-500', texto: 'text-emerald-700 dark:text-emerald-400', etiqueta: 'Buena' };
  if (pct >= 50) return { fondo: 'bg-amber-500', texto: 'text-amber-700 dark:text-amber-400', etiqueta: 'Regular' };
  return { fondo: 'bg-rose-500', texto: 'text-rose-700 dark:text-rose-400', etiqueta: 'Baja' };
};

/**
 * Tabla especializada de metas presupuestales para el ciudadano.
 *
 * Características:
 * - Fila expandible que muestra el desglose N:N (rubro × genérica) de la meta.
 * - Barra de ejecución con semáforo dentro de la celda de progreso.
 * - Columnas Sector, Producto/Proyecto y Categoría con nombres completos.
 * - Header sortable (backend-side: PIM ↕, Devengado ↓, % ejec ↕).
 * - Zebra suave y top-3 con badge "Top gasto" según PIM.
 * - Selector de tamaño de página 10/25/50.
 */
export function TablaMetas({
  items,
  isLoading,
  ano,
  pageIndex,
  pageSize,
  pageCount,
  totalItems,
  onPageChange,
  onPageSizeChange,
  sortKey,
  onSortChange,
}: TablaMetasProps) {
  const [expandidas, setExpandidas] = useState<Set<number>>(new Set());

  // Identifica top-3 en la página por PIM.
  const top3SecFuncs = useMemo(() => {
    const ordenadas = [...items]
      .map((it) => ({ sec: it.sec_func, pim: parseMonto(it.pim) ?? 0 }))
      .sort((a, b) => b.pim - a.pim)
      .slice(0, 3)
      .map((x) => x.sec);
    return new Set(ordenadas);
  }, [items]);

  const toggleFila = (secFunc: number) => {
    setExpandidas((prev) => {
      const next = new Set(prev);
      if (next.has(secFunc)) next.delete(secFunc);
      else next.add(secFunc);
      return next;
    });
  };

  if (isLoading) {
    return <TablaEsqueleto />;
  }

  if (!items || items.length === 0) {
    return (
      <div className="p-12 text-center">
        <p className="text-sm text-muted-foreground">
          No se encontraron metas con los filtros actuales.
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Intenta quitar algunos filtros para ver más resultados.
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Header + barra de controles */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 px-5 md:px-6 py-4 border-b border-border">
        <div className="text-sm text-muted-foreground">
          Mostrando{' '}
          <span className="font-semibold text-foreground tabular-nums">
            {pageIndex * pageSize + 1}
          </span>
          –
          <span className="font-semibold text-foreground tabular-nums">
            {Math.min((pageIndex + 1) * pageSize, totalItems)}
          </span>{' '}
          de{' '}
          <span className="font-semibold text-foreground tabular-nums">
            {totalItems.toLocaleString('es-PE')}
          </span>{' '}
          metas
        </div>

        <div className="flex items-center gap-4">
          {/* Ordenamiento */}
          <label className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground">Ordenar por:</span>
            <select
              value={sortKey}
              onChange={(e) => onSortChange(e.target.value as SortKey)}
              className="h-9 rounded-md border border-input bg-background px-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="pim">Mayor presupuesto (PIM)</option>
              <option value="devengado">Mayor ejecutado</option>
              <option value="pct_desc">Mayor % ejecución</option>
              <option value="pct_asc">Menor % ejecución</option>
            </select>
          </label>

          {/* Tamaño de página */}
          <label className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground">Filas:</span>
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(parseInt(e.target.value, 10))}
              className="h-9 rounded-md border border-input bg-background px-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {PAGE_SIZES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {/* Encabezados de columnas */}
      <div className="hidden md:grid md:grid-cols-[36px_1fr_180px_140px] gap-4 px-6 py-3 bg-muted/40 border-b border-border text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        <div />
        <div>Meta presupuestal</div>
        <SortableHeader
          label="Presupuesto (PIM)"
          activo={sortKey === 'pim'}
          onClick={() => onSortChange('pim')}
        />
        <div className="text-right">Ejecución</div>
      </div>

      {/* Filas */}
      <ul>
        {items.map((meta, idx) => {
          const expandida = expandidas.has(meta.sec_func);
          const esTop = top3SecFuncs.has(meta.sec_func);
          const filaZebra = idx % 2 === 1;
          return (
            <li
              key={meta.sec_func}
              className={cn(
                'border-b border-border last:border-b-0',
                filaZebra && 'bg-muted/20',
              )}
            >
              <FilaMeta
                meta={meta}
                expandida={expandida}
                esTop={esTop}
                onToggle={() => toggleFila(meta.sec_func)}
              />
              {expandida ? <PanelDesglose secFunc={meta.sec_func} ano={ano} /> : null}
            </li>
          );
        })}
      </ul>

      {/* Paginación */}
      <div className="flex items-center justify-between px-5 md:px-6 py-4 border-t border-border">
        <div className="text-sm text-muted-foreground">
          Página {pageIndex + 1} de {Math.max(1, pageCount)}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(pageIndex - 1)}
            disabled={pageIndex <= 0}
          >
            Anterior
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(pageIndex + 1)}
            disabled={pageIndex >= pageCount - 1}
          >
            Siguiente
          </Button>
        </div>
      </div>
    </div>
  );
}

interface SortableHeaderProps {
  label: string;
  activo: boolean;
  onClick: () => void;
}

function SortableHeader({ label, activo, onClick }: SortableHeaderProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'text-right flex items-center gap-1 justify-end hover:text-foreground transition-colors',
        activo ? 'text-primary' : '',
      )}
    >
      {label}
      {activo ? (
        <ArrowDown className="w-3 h-3" aria-hidden="true" />
      ) : (
        <ArrowUpDown className="w-3 h-3 opacity-40" aria-hidden="true" />
      )}
    </button>
  );
}

interface FilaMetaProps {
  meta: EjecucionDetalleItem;
  expandida: boolean;
  esTop: boolean;
  onToggle: () => void;
}

function FilaMeta({ meta, expandida, esTop, onToggle }: FilaMetaProps) {
  const pim = parseMonto(meta.pim) ?? 0;
  const dev = parseMonto(meta.devengado) ?? 0;
  const pct = parseMonto(meta.porcentaje_ejecucion);
  const semaforo = CLASE_SEMAFORO(pct);
  const barra = pim > 0 ? Math.min(100, (dev / pim) * 100) : 0;

  const esCapital = meta.categoria_gasto === '6';

  return (
    <button
      type="button"
      onClick={onToggle}
      className="w-full text-left px-5 md:px-6 py-4 md:py-5 md:grid md:grid-cols-[36px_1fr_180px_140px] md:gap-4 md:items-start hover:bg-primary/5 focus-visible:outline-none focus-visible:bg-primary/5 transition-colors"
      aria-expanded={expandida}
      aria-controls={`desglose-${meta.sec_func}`}
    >
      {/* Toggle chevron */}
      <div className="hidden md:flex items-center justify-center pt-0.5">
        <span
          className={cn(
            'inline-flex h-6 w-6 items-center justify-center rounded-md bg-muted text-muted-foreground transition-transform',
            expandida && 'rotate-90 bg-primary/10 text-primary',
          )}
          aria-hidden="true"
        >
          <ChevronRight className="w-3.5 h-3.5" />
        </span>
      </div>

      {/* Bloque principal */}
      <div className="min-w-0">
        {/* Badges */}
        <div className="flex items-center gap-1.5 flex-wrap mb-2">
          {esTop ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide">
              <Trophy className="w-3 h-3" aria-hidden="true" />
              Top gasto
            </span>
          ) : null}
          <span className="inline-flex items-center gap-1 rounded-md bg-muted text-muted-foreground px-1.5 py-0.5 text-[10px] font-mono font-semibold">
            #{meta.sec_func.toString().padStart(4, '0')}
          </span>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            {meta.funcion_nombre}
          </span>
          {meta.categoria_gasto_nombre ? (
            <span
              className={cn(
                'inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                esCapital
                  ? 'bg-secondary/15 text-secondary'
                  : 'bg-accent/20 text-accent-foreground',
              )}
            >
              {esCapital ? 'Capital' : 'Corriente'}
            </span>
          ) : null}
        </div>

        {/* Nombre de la meta */}
        <p className="text-sm md:text-base font-semibold text-foreground line-clamp-2 leading-snug">
          {meta.meta_nombre}
        </p>

        {/* Producto/Proyecto */}
        {meta.producto_proyecto_nombre && meta.producto_proyecto !== '3999999' ? (
          <p className="mt-1 text-xs text-muted-foreground line-clamp-1">
            <span className="font-medium">Proyecto:</span> {meta.producto_proyecto_nombre}
          </p>
        ) : null}
      </div>

      {/* PIM */}
      <div className="mt-3 md:mt-0 text-right">
        <p className="text-lg md:text-xl font-bold text-foreground tabular-nums leading-none">
          {formatearMoneda(pim, true)}
        </p>
        <p className="text-[10px] text-muted-foreground mt-1 uppercase tracking-wider">
          Presupuesto
        </p>
      </div>

      {/* Ejecución (barra + %) */}
      <div className="mt-3 md:mt-0">
        <div className="flex items-baseline justify-end gap-1 mb-1.5">
          <span className={cn('text-lg font-bold tabular-nums leading-none', semaforo.texto)}>
            {pct !== null ? `${pct.toFixed(1)}%` : '—'}
          </span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden ml-auto">
          <div
            className={cn('h-full transition-all', semaforo.fondo)}
            style={{ width: `${barra}%` }}
            aria-hidden="true"
          />
        </div>
        <p className="mt-1 text-[10px] text-right text-muted-foreground tabular-nums">
          {formatearMoneda(dev, true)} ejecutado
        </p>
      </div>
    </button>
  );
}

interface PanelDesgloseProps {
  secFunc: number;
  ano: number;
}

function PanelDesglose({ secFunc, ano }: PanelDesgloseProps) {
  const { data, isLoading, isError } = useMetaDesglose(secFunc, ano);

  return (
    <div
      id={`desglose-${secFunc}`}
      className="px-5 md:px-14 py-5 md:py-6 bg-primary/5 border-t border-primary/10"
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Package className="w-4 h-4" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-semibold text-foreground">Desglose de esta meta</p>
          <p className="text-xs text-muted-foreground">
            De dónde viene el dinero (rubro) y en qué se gasta (genérica).
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-14 bg-card rounded-lg animate-pulse" />
          ))}
        </div>
      ) : isError ? (
        <p className="text-sm text-destructive">No se pudo cargar el desglose.</p>
      ) : !data || data.filas.length === 0 ? (
        <p className="text-sm text-muted-foreground">Esta meta no tiene desglose disponible.</p>
      ) : (
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          {/* Encabezado */}
          <div className="hidden md:grid md:grid-cols-[1.2fr_1.2fr_140px_140px_100px] gap-3 px-4 py-2.5 bg-muted/40 border-b border-border text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <Coins className="w-3 h-3" aria-hidden="true" />
              Origen del dinero (Rubro)
            </div>
            <div className="flex items-center gap-1.5">
              <Package className="w-3 h-3" aria-hidden="true" />
              Tipo de gasto (Genérica)
            </div>
            <div className="text-right">Presupuesto</div>
            <div className="text-right">Ejecutado</div>
            <div className="text-right">% Ejec</div>
          </div>

          {/* Filas */}
          {data.filas.map((fila, i) => {
            const pim = parseMonto(fila.pim) ?? 0;
            const dev = parseMonto(fila.devengado) ?? 0;
            const pct = parseMonto(fila.porcentaje_ejecucion);
            const semaforo = CLASE_SEMAFORO(pct);
            const barra = pim > 0 ? Math.min(100, (dev / pim) * 100) : 0;
            return (
              <div
                key={`${fila.rubro_codigo}-${fila.generica_codigo}-${i}`}
                className="grid grid-cols-1 md:grid-cols-[1.2fr_1.2fr_140px_140px_100px] gap-3 px-4 py-3 border-b border-border last:border-b-0 text-sm items-center"
              >
                <div className="min-w-0">
                  <p className="font-medium text-foreground line-clamp-2 text-xs md:text-sm">
                    {fila.rubro_nombre}
                  </p>
                </div>
                <div className="min-w-0">
                  <p className="font-medium text-foreground line-clamp-2 text-xs md:text-sm">
                    {fila.generica_nombre}
                  </p>
                </div>
                <div className="text-right tabular-nums font-semibold">
                  {formatearMoneda(pim, true)}
                </div>
                <div className="text-right tabular-nums">
                  <div>{formatearMoneda(dev, true)}</div>
                  <div className="h-1 w-full rounded-full bg-muted overflow-hidden mt-1">
                    <div
                      className={cn('h-full', semaforo.fondo)}
                      style={{ width: `${barra}%` }}
                      aria-hidden="true"
                    />
                  </div>
                </div>
                <div className={cn('text-right font-semibold tabular-nums', semaforo.texto)}>
                  {pct !== null ? `${pct.toFixed(1)}%` : '—'}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function TablaEsqueleto() {
  return (
    <div>
      <div className="px-6 py-4 border-b border-border">
        <div className="h-4 w-64 bg-muted animate-pulse rounded" />
      </div>
      <ul>
        {Array.from({ length: 5 }).map((_, i) => (
          <li
            key={i}
            className={cn(
              'border-b border-border md:grid md:grid-cols-[36px_1fr_180px_140px] gap-4 px-6 py-5',
              i % 2 === 1 && 'bg-muted/20',
            )}
          >
            <div className="h-6 w-6 bg-muted animate-pulse rounded" />
            <div className="space-y-2">
              <div className="h-3 w-1/3 bg-muted animate-pulse rounded" />
              <div className="h-5 w-2/3 bg-muted animate-pulse rounded" />
            </div>
            <div className="h-6 bg-muted animate-pulse rounded" />
            <div className="h-6 bg-muted animate-pulse rounded" />
          </li>
        ))}
      </ul>
    </div>
  );
}

export default TablaMetas;
