import { useMemo } from 'react';
import {
  Trophy,
  ArrowDown,
  ArrowUpDown,
  Building2,
  User,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { parseMonto, formatearMoneda } from '@/lib/formatters';
import type { ProveedorPublicoItem } from '../types';
import { Button } from '@/components/ui/button';

export type SortKey = 'monto' | 'ordenes' | 'nombre';

interface TablaProveedoresProps {
  items: ProveedorPublicoItem[];
  isLoading?: boolean;
  pageIndex: number;
  pageSize: number;
  pageCount: number;
  totalItems: number;
  onPageChange: (pageIndex: number) => void;
  onPageSizeChange: (size: number) => void;
  sortKey: SortKey;
  onSortChange: (k: SortKey) => void;
}

const PAGE_SIZES = [10, 25, 50];

function esFlagVerdad(v: string | null): boolean {
  return v === 'S' || v === '1' || v === 'Y';
}

/**
 * Detecta si el tipo persona corresponde a una empresa (persona jurídica).
 * SIGA/SIGAF usan variantes: 'J' (letra), '2' o '02' (código SUNAT).
 * Si viene null, decidimos por el RUC (los que empiezan con 20 son jurídicas).
 */
function esPersonaJuridica(tipoPersona: string | null, ruc: string | null): boolean {
  if (tipoPersona === 'J' || tipoPersona === '2' || tipoPersona === '02') return true;
  if (tipoPersona === 'N' || tipoPersona === '1' || tipoPersona === '01') return false;
  // Fallback: RUCs peruanos que empiezan con "20" son jurídicos, "10" son naturales.
  return ruc?.startsWith('20') ?? false;
}

/**
 * Tabla especializada del directorio de proveedores.
 *
 * - Filas densas con badges (MYPE / RNP / Consorcio) y tipo persona.
 * - Barra visual del monto acumulado proporcional al mayor de la pagina.
 * - Badge "Top proveedor" para el top-3 por monto de la pagina.
 * - Zebra suave, ordenamiento configurable, selector de page size.
 */
export function TablaProveedores({
  items,
  isLoading,
  pageIndex,
  pageSize,
  pageCount,
  totalItems,
  onPageChange,
  onPageSizeChange,
  sortKey,
  onSortChange,
}: TablaProveedoresProps) {
  // Ordenamiento client-side sobre la pagina actual (el backend solo devuelve por monto DESC).
  const itemsOrdenados = useMemo(() => {
    if (!items) return [];
    const copia = [...items];
    if (sortKey === 'monto') {
      copia.sort((a, b) => (parseMonto(b.monto_acumulado) ?? 0) - (parseMonto(a.monto_acumulado) ?? 0));
    } else if (sortKey === 'ordenes') {
      copia.sort((a, b) => (b.nro_ordenes ?? 0) - (a.nro_ordenes ?? 0));
    } else if (sortKey === 'nombre') {
      copia.sort((a, b) => (a.nombre ?? '').localeCompare(b.nombre ?? '', 'es'));
    }
    return copia;
  }, [items, sortKey]);

  // Top-3 por monto en la pagina (usa el orden por monto, no el actual).
  const top3Rucs = useMemo(() => {
    const top = [...(items ?? [])]
      .map((it) => ({ ruc: it.ruc, monto: parseMonto(it.monto_acumulado) ?? 0 }))
      .filter((x) => x.monto > 0)
      .sort((a, b) => b.monto - a.monto)
      .slice(0, 3)
      .map((x) => x.ruc);
    return new Set(top);
  }, [items]);

  // Ancho maximo de la barra: relativo al mayor monto de la pagina.
  const montoMax = useMemo(
    () => (items ?? []).reduce((m, it) => Math.max(m, parseMonto(it.monto_acumulado) ?? 0), 0),
    [items],
  );

  if (isLoading) {
    return <TablaEsqueleto />;
  }

  if (!items || items.length === 0) {
    return (
      <div className="p-12 text-center">
        <p className="text-sm text-muted-foreground">
          No se encontraron proveedores con los filtros actuales.
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Intenta cambiar la búsqueda o el año.
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Barra de controles */}
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
          proveedores
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground">Ordenar por:</span>
            <select
              value={sortKey}
              onChange={(e) => onSortChange(e.target.value as SortKey)}
              className="h-9 rounded-md border border-input bg-background px-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="monto">Mayor monto acumulado</option>
              <option value="ordenes">Más órdenes</option>
              <option value="nombre">Nombre (A→Z)</option>
            </select>
          </label>

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

      {/* Header de columnas */}
      <div className="hidden md:grid md:grid-cols-[1.6fr_150px_260px] gap-4 px-6 py-3 bg-muted/40 border-b border-border text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        <SortableHeader
          label="Proveedor"
          activo={sortKey === 'nombre'}
          onClick={() => onSortChange('nombre')}
          alineacion="izquierda"
        />
        <SortableHeader
          label="Órdenes del año"
          activo={sortKey === 'ordenes'}
          onClick={() => onSortChange('ordenes')}
        />
        <SortableHeader
          label="Monto acumulado (S/)"
          activo={sortKey === 'monto'}
          onClick={() => onSortChange('monto')}
        />
      </div>

      {/* Filas */}
      <ul>
        {itemsOrdenados.map((prov, idx) => {
          const monto = parseMonto(prov.monto_acumulado) ?? 0;
          const barra = montoMax > 0 ? Math.min(100, (monto / montoMax) * 100) : 0;
          const esTop = top3Rucs.has(prov.ruc);
          const esEmpresa = esPersonaJuridica(prov.tipo_persona, prov.ruc);
          const filaZebra = idx % 2 === 1;
          const flagMype = esFlagVerdad(prov.flag_mype);
          const flagRnp = esFlagVerdad(prov.flag_rnp);
          const flagConsorcio = esFlagVerdad(prov.flag_consorcio);
          const sinCondicion = !flagMype && !flagRnp && !flagConsorcio;

          return (
            <li
              key={prov.ruc ?? `sin-ruc-${idx}`}
              className={cn(
                'border-b border-border last:border-b-0 md:grid md:grid-cols-[1.6fr_150px_260px] md:gap-4 md:items-center px-5 md:px-6 py-4 md:py-5',
                filaZebra && 'bg-muted/20',
              )}
            >
              {/* Bloque proveedor */}
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap mb-2">
                  {esTop ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide">
                      <Trophy className="w-3 h-3" aria-hidden="true" />
                      Top proveedor
                    </span>
                  ) : null}
                  <span className="inline-flex items-center gap-1 rounded-md bg-muted text-muted-foreground px-1.5 py-0.5 text-[10px] font-mono font-semibold">
                    RUC {prov.ruc ?? 'S/N'}
                  </span>
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider',
                      esEmpresa ? 'text-secondary' : 'text-accent-foreground',
                    )}
                    title={esEmpresa ? 'Persona Jurídica' : 'Persona Natural'}
                  >
                    {esEmpresa ? (
                      <Building2 className="w-3 h-3" aria-hidden="true" />
                    ) : (
                      <User className="w-3 h-3" aria-hidden="true" />
                    )}
                    {esEmpresa ? 'Empresa' : 'Persona natural'}
                  </span>
                </div>

                <p className="text-sm md:text-base font-semibold text-foreground line-clamp-2 leading-snug">
                  {prov.nombre ?? 'Desconocido'}
                </p>

                {prov.giro ? (
                  <p className="mt-1 text-xs text-muted-foreground line-clamp-1">
                    <span className="font-medium">Giro:</span> {prov.giro}
                  </p>
                ) : null}

                {/* Badges de condición */}
                <div className="mt-2 flex items-center gap-1.5 flex-wrap">
                  {flagMype ? (
                    <span
                      className="inline-block rounded-full bg-primary/10 text-primary px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                      title="Micro y Pequeña Empresa"
                    >
                      MYPE
                    </span>
                  ) : null}
                  {flagRnp ? (
                    <span
                      className="inline-block rounded-full bg-secondary/10 text-secondary px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                      title="Inscrito en el Registro Nacional de Proveedores"
                    >
                      RNP
                    </span>
                  ) : null}
                  {flagConsorcio ? (
                    <span
                      className="inline-block rounded-full bg-accent/20 text-accent-foreground px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                      title="Actúa como consorcio"
                    >
                      Consorcio
                    </span>
                  ) : null}
                  {sinCondicion ? (
                    <span className="text-[10px] text-muted-foreground italic">
                      Sin condición especial
                    </span>
                  ) : null}
                </div>
              </div>

              {/* Órdenes */}
              <div className="mt-3 md:mt-0 text-right">
                <p className="text-lg md:text-xl font-bold text-foreground tabular-nums leading-none">
                  {(prov.nro_ordenes ?? 0).toLocaleString('es-PE')}
                </p>
                <p className="text-[10px] text-muted-foreground mt-1 uppercase tracking-wider">
                  {(prov.nro_ordenes ?? 0) === 1 ? 'orden' : 'órdenes'}
                </p>
              </div>

              {/* Monto acumulado con barra */}
              <div className="mt-3 md:mt-0">
                <p className="text-lg md:text-xl font-bold text-foreground tabular-nums text-right leading-none">
                  {monto > 0 ? formatearMoneda(monto, true) : (
                    <span className="text-muted-foreground text-sm font-normal">Sin órdenes</span>
                  )}
                </p>
                <div className="mt-2 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all"
                    style={{ width: `${barra}%` }}
                    aria-hidden="true"
                  />
                </div>
                {monto > 0 ? (
                  <p className="mt-1 text-[10px] text-right text-muted-foreground tabular-nums">
                    {barra.toFixed(1)}% del máximo en la página
                  </p>
                ) : null}
              </div>
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
  alineacion?: 'izquierda' | 'derecha';
}

function SortableHeader({ label, activo, onClick, alineacion = 'derecha' }: SortableHeaderProps) {
  const izq = alineacion === 'izquierda';
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex items-center gap-1 hover:text-foreground transition-colors',
        izq ? 'justify-start' : 'justify-end text-right',
        activo && 'text-primary',
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

function TablaEsqueleto() {
  return (
    <div>
      <div className="px-6 py-4 border-b border-border">
        <div className="h-4 w-64 bg-muted animate-pulse rounded" />
      </div>
      <ul>
        {Array.from({ length: 6 }).map((_, i) => (
          <li
            key={i}
            className={cn(
              'border-b border-border md:grid md:grid-cols-[1.6fr_150px_260px] gap-4 px-6 py-5',
              i % 2 === 1 && 'bg-muted/20',
            )}
          >
            <div className="space-y-2">
              <div className="h-3 w-1/4 bg-muted animate-pulse rounded" />
              <div className="h-5 w-3/4 bg-muted animate-pulse rounded" />
              <div className="h-3 w-1/2 bg-muted animate-pulse rounded" />
            </div>
            <div className="h-6 bg-muted animate-pulse rounded" />
            <div className="h-6 bg-muted animate-pulse rounded" />
          </li>
        ))}
      </ul>
    </div>
  );
}

export default TablaProveedores;
