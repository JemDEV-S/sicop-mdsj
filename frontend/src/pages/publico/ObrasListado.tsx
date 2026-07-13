import { useState, useMemo } from 'react';
import type { ColumnDef, PaginationState } from '@tanstack/react-table';
import {
  Building2,
  LayoutGrid,
  Table as TableIcon,
  Search,
  X,
  ChevronLeft,
  ChevronRight,
  MapPin,
  Layers,
} from 'lucide-react';
import { DataTable } from '@/components/tabla/DataTable';
import { useObras, useFunciones, useTipologias } from '@/features/obras/hooks';
import type { ObraCardResponse } from '@/features/obras/types';
import { mapSemaforoApiToEstado } from '@/features/obras/api';
import { ObraCard } from '@/features/obras/ObraCard';
import Semaforo from '@/components/Semaforo';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ErrorState } from '@/components/layout/ErrorState';
import { EmptyState } from '@/components/layout/EmptyState';
import { SkeletonCard } from '@/components/layout/LoadingSkeleton';
import { PublicHero } from '@/components/publico/PublicHero';
import { SectionBand } from '@/components/publico/SectionBand';
import { formatearMoneda } from '@/lib/formatters';
import { cn } from '@/lib/utils';

type Vista = 'tarjetas' | 'tabla';

const OPCION_TODAS = 'todas';
const ANIO_VIGENTE = 2026;

export default function ObrasListado() {
  const [q, setQ] = useState('');
  const [funcion, setFuncion] = useState('');
  const [tipologia, setTipologia] = useState('');
  const [vista, setVista] = useState<Vista>('tarjetas');

  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 12,
  });

  const { data, isLoading, isError, refetch } = useObras({
    page: pagination.pageIndex + 1,
    size: pagination.pageSize,
    q: q || undefined,
    funcion: funcion || undefined,
    tipologia: tipologia || undefined,
  });

  const { data: funciones } = useFunciones();
  const { data: tipologias } = useTipologias();

  // KPIs derivados sobre la página actual (limitación: no tenemos endpoint de resumen global de obras)
  const items = data?.items ?? [];
  const totalItems = data?.total ?? 0;
  const kpisPagina = useMemo(() => {
    const conCoords = items.filter(
      (o) => o.latitud != null && o.longitud != null && !(o.latitud === 0 && o.longitud === 0),
    ).length;
    const funcionesDistintas = new Set(items.map((o) => o.funcion).filter(Boolean)).size;
    return { conCoords, funcionesDistintas };
  }, [items]);

  const chipsActivos = [q, funcion, tipologia].filter(Boolean).length;

  const columns = useMemo<ColumnDef<ObraCardResponse>[]>(
    () => [
      {
        accessorKey: 'codigo_unico',
        header: 'CUI',
        cell: ({ row }) => (
          <span className="font-mono text-sm text-muted-foreground">
            {row.getValue('codigo_unico')}
          </span>
        ),
      },
      {
        accessorKey: 'nombre_inversion',
        header: 'Proyecto',
        cell: ({ row }) => {
          const nombre = row.getValue('nombre_inversion') as string | null;
          return (
            <div className="max-w-md truncate text-foreground" title={nombre ?? ''}>
              {nombre || 'Sin nombre'}
            </div>
          );
        },
      },
      {
        accessorKey: 'pim_anio_actual',
        header: 'Presupuesto (PIM)',
        cell: ({ row }) => {
          const v = row.getValue('pim_anio_actual') as number | null;
          return (
            <span className="font-medium text-foreground tabular-nums">
              {v !== null && v !== undefined ? formatearMoneda(v) : '—'}
            </span>
          );
        },
      },
      {
        id: 'semaforo',
        header: 'Avance físico',
        cell: ({ row }) => {
          const estado = mapSemaforoApiToEstado(row.original.semaforo);
          if (!estado) {
            return <span className="text-muted-foreground text-sm">Sin datos</span>;
          }
          const fisico = row.original.avance_fisico;
          const texto =
            fisico !== null && fisico !== undefined ? `${fisico.toFixed(1)}%` : 'Desconocido';
          return <Semaforo estado={estado} texto={texto} />;
        },
      },
    ],
    [],
  );

  function limpiarTodo() {
    setQ('');
    setFuncion('');
    setTipologia('');
    setPagination((p) => ({ ...p, pageIndex: 0 }));
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / pagination.pageSize)) : 1;

  return (
    <div className="bg-background">
      {/* HERO */}
      <PublicHero
        eyebrow={<>Obras · Año {ANIO_VIGENTE}</>}
        titulo={
          <>
            Directorio de <span className="text-primary">obras públicas</span>
          </>
        }
        subtitulo={
          totalItems > 0
            ? `${new Intl.NumberFormat('es-PE').format(totalItems)} proyectos de inversión registrados en el distrito. Consulta el avance físico y el presupuesto de cada obra.`
            : 'Consulta el estado, avance físico y financiero de los proyectos de inversión del distrito.'
        }
        compacto
        destacado={
          <MiniStatsObras
            total={totalItems}
            conCoords={kpisPagina.conCoords}
            pageSize={pagination.pageSize}
            funcionesDistintas={kpisPagina.funcionesDistintas}
            cargando={isLoading}
          />
        }
      />

      {/* TOOLBAR DE FILTROS */}
      <div className="sticky top-16 z-20 bg-card/95 backdrop-blur border-b border-border">
        <div className="mx-auto max-w-6xl px-4 md:px-6 py-4">
          <div className="flex flex-col lg:flex-row gap-3 lg:items-center">
            {/* Búsqueda */}
            <div className="relative flex-1 lg:max-w-md">
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                id="obras-buscar"
                type="search"
                placeholder="Buscar por nombre o CUI…"
                className="pl-9 pr-9 h-10 rounded-lg"
                value={q}
                onChange={(e) => {
                  setQ(e.target.value);
                  setPagination((p) => ({ ...p, pageIndex: 0 }));
                }}
                aria-label="Buscar obras"
              />
              {q ? (
                <button
                  type="button"
                  onClick={() => {
                    setQ('');
                    setPagination((p) => ({ ...p, pageIndex: 0 }));
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 inline-flex items-center justify-center h-6 w-6 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted"
                  aria-label="Limpiar búsqueda"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              ) : null}
            </div>

            {/* Selects */}
            <div className="flex flex-col sm:flex-row gap-2 flex-1">
              <Select
                value={funcion || OPCION_TODAS}
                onValueChange={(val) => {
                  setFuncion(val === OPCION_TODAS ? '' : val);
                  setPagination((p) => ({ ...p, pageIndex: 0 }));
                }}
              >
                <SelectTrigger className="h-10 rounded-lg" aria-label="Filtrar por función">
                  <SelectValue placeholder="Todas las funciones" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={OPCION_TODAS}>Todas las funciones</SelectItem>
                  {funciones?.map((f) => (
                    <SelectItem key={f} value={f}>
                      {f}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select
                value={tipologia || OPCION_TODAS}
                onValueChange={(val) => {
                  setTipologia(val === OPCION_TODAS ? '' : val);
                  setPagination((p) => ({ ...p, pageIndex: 0 }));
                }}
              >
                <SelectTrigger className="h-10 rounded-lg" aria-label="Filtrar por tipología">
                  <SelectValue placeholder="Todas las tipologías" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={OPCION_TODAS}>Todas las tipologías</SelectItem>
                  {tipologias?.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Toggle vista */}
            <ToggleVista vista={vista} onCambiar={setVista} />
          </div>

          {/* Chips + limpiar */}
          {chipsActivos > 0 ? (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted-foreground mr-1">Filtros activos:</span>
              {q ? (
                <FiltroChip
                  label={`"${q}"`}
                  onRemove={() => {
                    setQ('');
                    setPagination((p) => ({ ...p, pageIndex: 0 }));
                  }}
                />
              ) : null}
              {funcion ? (
                <FiltroChip
                  label={funcion}
                  onRemove={() => {
                    setFuncion('');
                    setPagination((p) => ({ ...p, pageIndex: 0 }));
                  }}
                />
              ) : null}
              {tipologia ? (
                <FiltroChip
                  label={tipologia}
                  onRemove={() => {
                    setTipologia('');
                    setPagination((p) => ({ ...p, pageIndex: 0 }));
                  }}
                />
              ) : null}
              <button
                type="button"
                onClick={limpiarTodo}
                className="text-xs text-primary hover:underline ml-auto"
              >
                Limpiar todos
              </button>
            </div>
          ) : null}
        </div>
      </div>

      {/* LISTADO */}
      <SectionBand tono="background">
        {/* Header de resultados */}
        <div className="flex items-baseline justify-between mb-6">
          <p className="text-sm text-muted-foreground">
            {isLoading ? (
              <span className="inline-block w-40 h-4 bg-muted animate-pulse rounded" aria-hidden="true" />
            ) : totalItems > 0 ? (
              <>
                Mostrando{' '}
                <span className="font-semibold text-foreground tabular-nums">
                  {(pagination.pageIndex * pagination.pageSize) + 1}
                  {' – '}
                  {Math.min((pagination.pageIndex + 1) * pagination.pageSize, totalItems)}
                </span>{' '}
                de{' '}
                <span className="font-semibold text-foreground tabular-nums">
                  {new Intl.NumberFormat('es-PE').format(totalItems)}
                </span>{' '}
                obras
              </>
            ) : (
              'Sin resultados'
            )}
          </p>
        </div>

        {isError ? (
          <ErrorState
            titulo="No se pudo cargar el directorio"
            descripcion="Ocurrió un error al consultar las obras. Intenta de nuevo."
            onReintentar={() => refetch()}
          />
        ) : vista === 'tarjetas' ? (
          <ObrasEnTarjetas
            items={items}
            isLoading={isLoading}
            pageSize={pagination.pageSize}
            hayFiltros={chipsActivos > 0}
            onLimpiar={limpiarTodo}
          />
        ) : (
          <div className="rounded-xl border border-border overflow-hidden bg-card">
            <DataTable
              columns={columns}
              data={items}
              pageCount={totalPages}
              pagination={pagination}
              onPaginationChange={setPagination}
              isLoading={isLoading}
            />
          </div>
        )}

        {vista === 'tarjetas' && data && totalPages > 1 ? (
          <PaginacionSimple
            pageIndex={pagination.pageIndex}
            pageCount={totalPages}
            onCambiar={(nuevo) =>
              setPagination((p) => ({ ...p, pageIndex: nuevo }))
            }
          />
        ) : null}
      </SectionBand>
    </div>
  );
}

/* ----- Subcomponentes ----- */

interface MiniStatsObrasProps {
  total: number;
  conCoords: number;
  pageSize: number;
  funcionesDistintas: number;
  cargando: boolean;
}

function MiniStatsObras({ total, conCoords, funcionesDistintas, cargando }: MiniStatsObrasProps) {
  return (
    <div className="rounded-2xl bg-card border border-border p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary" aria-hidden="true" />
        <span className="text-[11px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
          Directorio
        </span>
      </div>

      <div className="space-y-4">
        <MiniStat
          icono={Building2}
          label="Proyectos registrados"
          valor={cargando ? null : new Intl.NumberFormat('es-PE').format(total)}
        />
        <div className="h-px bg-border" aria-hidden="true" />
        <MiniStat
          icono={MapPin}
          label="Con ubicación en esta página"
          valor={cargando ? null : new Intl.NumberFormat('es-PE').format(conCoords)}
        />
        <div className="h-px bg-border" aria-hidden="true" />
        <MiniStat
          icono={Layers}
          label="Funciones distintas"
          valor={cargando ? null : new Intl.NumberFormat('es-PE').format(funcionesDistintas)}
        />
      </div>
    </div>
  );
}

interface MiniStatProps {
  icono: typeof Building2;
  label: string;
  valor: string | null;
}

function MiniStat({ icono: Icono, label, valor }: MiniStatProps) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2.5 min-w-0">
        <Icono className="w-4 h-4 text-primary shrink-0" aria-hidden="true" />
        <span className="text-xs text-muted-foreground truncate">{label}</span>
      </div>
      {valor === null ? (
        <div className="h-6 w-12 bg-muted animate-pulse rounded" aria-hidden="true" />
      ) : (
        <span className="text-lg font-bold text-foreground tabular-nums leading-none">
          {valor}
        </span>
      )}
    </div>
  );
}

interface ToggleVistaProps {
  vista: Vista;
  onCambiar: (v: Vista) => void;
}

function ToggleVista({ vista, onCambiar }: ToggleVistaProps) {
  return (
    <div
      className="inline-flex bg-muted rounded-lg p-1 border border-border shrink-0 self-start"
      role="group"
      aria-label="Cambiar vista"
    >
      <button
        type="button"
        onClick={() => onCambiar('tarjetas')}
        aria-pressed={vista === 'tarjetas'}
        className={cn(
          'inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          vista === 'tarjetas'
            ? 'bg-card text-foreground font-medium shadow-xs'
            : 'text-muted-foreground hover:text-foreground',
        )}
      >
        <LayoutGrid className="w-3.5 h-3.5" aria-hidden="true" />
        Tarjetas
      </button>
      <button
        type="button"
        onClick={() => onCambiar('tabla')}
        aria-pressed={vista === 'tabla'}
        className={cn(
          'inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          vista === 'tabla'
            ? 'bg-card text-foreground font-medium shadow-xs'
            : 'text-muted-foreground hover:text-foreground',
        )}
      >
        <TableIcon className="w-3.5 h-3.5" aria-hidden="true" />
        Tabla
      </button>
    </div>
  );
}

interface FiltroChipProps {
  label: string;
  onRemove: () => void;
}

function FiltroChip({ label, onRemove }: FiltroChipProps) {
  return (
    <span className="inline-flex items-center gap-1.5 pl-2.5 pr-1 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
      {label}
      <button
        type="button"
        onClick={onRemove}
        className="inline-flex items-center justify-center h-4 w-4 rounded-full hover:bg-primary/20"
        aria-label={`Quitar filtro ${label}`}
      >
        <X className="w-3 h-3" />
      </button>
    </span>
  );
}

interface ObrasEnTarjetasProps {
  items: ObraCardResponse[];
  isLoading: boolean;
  pageSize: number;
  hayFiltros: boolean;
  onLimpiar: () => void;
}

function ObrasEnTarjetas({
  items,
  isLoading,
  pageSize,
  hayFiltros,
  onLimpiar,
}: ObrasEnTarjetasProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {Array.from({ length: pageSize }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-10">
        <EmptyState
          icono={Building2}
          titulo="No se encontraron obras"
          descripcion={
            hayFiltros
              ? 'Ninguna obra coincide con los filtros aplicados. Prueba con otros criterios de búsqueda.'
              : 'No hay obras registradas actualmente.'
          }
          accion={hayFiltros ? { label: 'Limpiar filtros', onClick: onLimpiar } : undefined}
        />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      {items.map((obra) => (
        <ObraCard key={obra.codigo_unico} obra={obra} />
      ))}
    </div>
  );
}

interface PaginacionSimpleProps {
  pageIndex: number;
  pageCount: number;
  onCambiar: (nuevo: number) => void;
}

function PaginacionSimple({ pageIndex, pageCount, onCambiar }: PaginacionSimpleProps) {
  return (
    <nav
      className="mt-10 flex items-center justify-between gap-4 border-t border-border pt-6"
      aria-label="Paginación de obras"
    >
      <p className="text-sm text-muted-foreground">
        Página <span className="font-semibold text-foreground tabular-nums">{pageIndex + 1}</span>{' '}
        de <span className="font-semibold text-foreground tabular-nums">{pageCount}</span>
      </p>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onCambiar(Math.max(0, pageIndex - 1))}
          disabled={pageIndex === 0}
        >
          <ChevronLeft className="w-4 h-4" aria-hidden="true" />
          Anterior
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onCambiar(Math.min(pageCount - 1, pageIndex + 1))}
          disabled={pageIndex >= pageCount - 1}
        >
          Siguiente
          <ChevronRight className="w-4 h-4" aria-hidden="true" />
        </Button>
      </div>
    </nav>
  );
}
