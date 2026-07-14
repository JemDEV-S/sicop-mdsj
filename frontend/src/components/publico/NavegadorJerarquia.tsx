import { useState, useMemo } from 'react';
import { ChevronRight, ArrowLeft, Home as HomeIcon, Layers, Package, Target } from 'lucide-react';
import { cn } from '@/lib/utils';
import { parseMonto, formatearMoneda } from '@/lib/formatters';
import { useEjecucionJerarquia } from '@/features/ejecucion/hooks';
import type { NivelJerarquia, JerarquiaNodo } from '@/features/ejecucion/types';

interface NavegadorJerarquiaProps {
  ano: number;
  filtroRubro?: string;
  filtroGenerica?: string;
  /** Aviso arriba cuando hay un filtro transversal activo. */
  avisoFiltro?: React.ReactNode;
}

interface RutaItem {
  nivel: NivelJerarquia;
  codigo: string;
  nombre: string;
}

const ETIQUETAS_NIVEL: Record<NivelJerarquia, { titulo: string; icono: typeof Layers; hint: string }> = {
  funcion: {
    titulo: 'Sector (Función)',
    icono: Layers,
    hint: '¿Para qué se usa el dinero? Cada sector agrupa el gasto por su propósito.',
  },
  producto: {
    titulo: 'Producto o Proyecto',
    icono: Package,
    hint: 'Obras y servicios específicos dentro del sector.',
  },
  meta: {
    titulo: 'Metas',
    icono: Target,
    hint: 'Actividades ejecutables que reciben el presupuesto.',
  },
};

/**
 * Drill-down ciudadano de la ejecución presupuestal.
 *
 * Nivel 1 — Función (Sector): "¿Para qué?"
 *   ▼ click
 * Nivel 2 — Producto/Proyecto: "¿Qué se entrega?"
 *   ▼ click
 * Nivel 3 — Meta: "¿En qué actividad concreta?"
 *
 * Los filtros rubro/genérica son transversales y se aplican en cualquier
 * nivel para responder "¿y de esto, cuánto viene del Canon?" o similar.
 */
export function NavegadorJerarquia({
  ano,
  filtroRubro,
  filtroGenerica,
  avisoFiltro,
}: NavegadorJerarquiaProps) {
  const [ruta, setRuta] = useState<RutaItem[]>([]);

  const nivelActual: NivelJerarquia =
    ruta.length === 0 ? 'funcion' : ruta.length === 1 ? 'producto' : 'meta';

  const padreFuncion = ruta.find((r) => r.nivel === 'funcion')?.codigo;
  const padreProducto = ruta.find((r) => r.nivel === 'producto')?.codigo;

  const { data, isLoading, isError } = useEjecucionJerarquia({
    ano,
    nivel: nivelActual,
    padre_funcion: padreFuncion,
    padre_producto: padreProducto,
    filtro_rubro: filtroRubro,
    filtro_generica: filtroGenerica,
  });

  const totalNivel = useMemo(
    () => (data ?? []).reduce((acc, n) => acc + (parseMonto(n.pim) ?? 0), 0),
    [data],
  );

  const info = ETIQUETAS_NIVEL[nivelActual];
  const Icono = info.icono;

  const handleAbrir = (nodo: JerarquiaNodo) => {
    if (!nodo.tiene_hijos) return;
    setRuta((prev) => [...prev, { nivel: nivelActual, codigo: nodo.codigo, nombre: nodo.nombre }]);
  };

  const handleVolver = (indice: number) => {
    setRuta((prev) => prev.slice(0, indice));
  };

  return (
    <div className="rounded-2xl border border-border bg-card overflow-hidden">
      {/* Cabecera con breadcrumb y meta del nivel */}
      <div className="border-b border-border bg-muted/30 px-5 md:px-6 py-4">
        <Breadcrumb ruta={ruta} onVolver={handleVolver} />

        <div className="mt-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Icono className="w-4 h-4" aria-hidden="true" />
            </span>
            <div>
              <p className="text-sm font-semibold text-foreground">{info.titulo}</p>
              <p className="text-xs text-muted-foreground">{info.hint}</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Total del nivel
            </p>
            <p className="text-lg font-bold text-foreground tabular-nums">
              {formatearMoneda(totalNivel, true)}
            </p>
          </div>
        </div>

        {avisoFiltro ? <div className="mt-3">{avisoFiltro}</div> : null}
      </div>

      {/* Lista de items */}
      <div className="divide-y divide-border">
        {isLoading ? (
          <ListaEsqueleto />
        ) : isError ? (
          <div className="p-8 text-center text-sm text-destructive">
            No se pudo cargar este nivel. Intenta recargar la página.
          </div>
        ) : !data || data.length === 0 ? (
          <div className="p-10 text-center text-sm text-muted-foreground">
            No hay información para este nivel con los filtros actuales.
          </div>
        ) : (
          data.map((nodo) => (
            <NodoFila
              key={`${nivelActual}-${nodo.codigo}`}
              nodo={nodo}
              onAbrir={handleAbrir}
              nivel={nivelActual}
            />
          ))
        )}
      </div>
    </div>
  );
}

interface BreadcrumbProps {
  ruta: RutaItem[];
  onVolver: (indice: number) => void;
}

function Breadcrumb({ ruta, onVolver }: BreadcrumbProps) {
  return (
    <nav aria-label="Ruta de navegación jerárquica" className="flex items-center gap-1.5 flex-wrap text-sm">
      <button
        type="button"
        onClick={() => onVolver(0)}
        className={cn(
          'inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium transition-colors',
          ruta.length === 0
            ? 'bg-primary/10 text-primary'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground',
        )}
      >
        <HomeIcon className="w-3.5 h-3.5" aria-hidden="true" />
        Todos los sectores
      </button>

      {ruta.map((item, i) => {
        const esUltimo = i === ruta.length - 1;
        return (
          <span key={`${item.nivel}-${item.codigo}`} className="inline-flex items-center gap-1.5">
            <ChevronRight
              className="w-3.5 h-3.5 text-muted-foreground/60 shrink-0"
              aria-hidden="true"
            />
            <button
              type="button"
              onClick={() => onVolver(i + 1)}
              className={cn(
                'rounded-md px-2 py-1 text-xs font-medium transition-colors max-w-[240px] truncate text-left',
                esUltimo
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground',
              )}
              title={item.nombre}
            >
              {item.nombre}
            </button>
          </span>
        );
      })}

      {ruta.length > 0 ? (
        <button
          type="button"
          onClick={() => onVolver(ruta.length - 1)}
          className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
          Volver
        </button>
      ) : null}
    </nav>
  );
}

interface NodoFilaProps {
  nodo: JerarquiaNodo;
  onAbrir: (n: JerarquiaNodo) => void;
  nivel: NivelJerarquia;
}

function NodoFila({ nodo, onAbrir, nivel }: NodoFilaProps) {
  const pim = parseMonto(nodo.pim) ?? 0;
  const dev = parseMonto(nodo.devengado) ?? 0;
  const participacion = parseMonto(nodo.participacion_pim);
  const porcentaje = parseMonto(nodo.porcentaje_ejecucion);
  const barra = pim > 0 ? Math.min(100, (dev / pim) * 100) : 0;
  const clickeable = nodo.tiene_hijos;

  const Container: any = clickeable ? 'button' : 'div';
  const containerProps = clickeable
    ? {
        type: 'button',
        onClick: () => onAbrir(nodo),
      }
    : {};

  return (
    <Container
      {...containerProps}
      className={cn(
        'group w-full text-left px-5 md:px-6 py-4 md:py-5 flex items-start gap-4',
        clickeable
          ? 'hover:bg-muted/40 focus-visible:outline-none focus-visible:bg-muted/60 cursor-pointer'
          : '',
      )}
    >
      {/* Índice visual (participación) */}
      <div className="hidden md:flex flex-col items-center justify-center min-w-[54px] pt-1">
        <span className="text-sm font-bold text-foreground tabular-nums">
          {participacion !== null ? `${participacion.toFixed(1)}%` : '—'}
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mt-0.5">
          del total
        </span>
      </div>

      {/* Contenido central */}
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2 mb-1.5">
          {nivel !== 'meta' ? (
            <span className="text-[10px] font-mono font-semibold text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
              {nodo.codigo}
            </span>
          ) : null}
          <p className="font-semibold text-sm md:text-base text-foreground line-clamp-2 leading-snug">
            {nodo.nombre}
          </p>
        </div>

        {/* Barra de ejecución */}
        <div className="mt-3">
          <div
            className="h-1.5 w-full rounded-full bg-muted overflow-hidden"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(barra)}
          >
            <div
              className="h-full bg-primary transition-all"
              style={{ width: `${barra}%` }}
              aria-hidden="true"
            />
          </div>
          <div className="mt-1.5 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">
              <span className="font-semibold text-foreground tabular-nums">
                {formatearMoneda(dev, true)}
              </span>{' '}
              ejecutado de{' '}
              <span className="font-semibold text-foreground tabular-nums">
                {formatearMoneda(pim, true)}
              </span>
            </span>
            <span className="font-semibold tabular-nums text-foreground">
              {porcentaje !== null ? `${porcentaje.toFixed(1)}%` : '—'}
            </span>
          </div>
        </div>
      </div>

      {/* Chevron drill-down */}
      {clickeable ? (
        <ChevronRight
          className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all shrink-0 mt-1"
          aria-hidden="true"
        />
      ) : null}
    </Container>
  );
}

function ListaEsqueleto() {
  return (
    <div className="divide-y divide-border">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="px-6 py-5 flex gap-4">
          <div className="hidden md:block w-[54px] h-10 bg-muted animate-pulse rounded" />
          <div className="flex-1 space-y-3">
            <div className="h-4 w-3/4 bg-muted animate-pulse rounded" />
            <div className="h-1.5 w-full bg-muted animate-pulse rounded-full" />
            <div className="h-3 w-1/2 bg-muted animate-pulse rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default NavegadorJerarquia;
