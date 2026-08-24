// Paginación reutilizable para las tablas planas del Análisis por meta (fiel a
// la plantilla v2: nota a la izquierda + controles ‹ [n] › a la derecha).
//
// `usePaginado` es un hook puro que corta una lista en páginas y expone la
// página visible + los controles. Se resetea a la página 1 cuando cambia el
// total (p.ej. al filtrar o cambiar de meta) para no quedar en una página vacía.

import { useMemo, useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

export const TAM_PAGINA_DEFECTO = 15;

export interface Paginado<T> {
  pagina: T[];
  paginaActual: number;
  totalPaginas: number;
  total: number;
  desde: number; // índice 1-based del primer ítem visible
  hasta: number; // índice 1-based del último ítem visible
  irA: (p: number) => void;
  anterior: () => void;
  siguiente: () => void;
}

export function usePaginado<T>(items: T[], tamPagina = TAM_PAGINA_DEFECTO): Paginado<T> {
  const [paginaActual, setPagina] = useState(1);
  const total = items.length;
  const totalPaginas = Math.max(1, Math.ceil(total / tamPagina));

  // Si el total encoge por debajo de la página actual (filtro/cambio de meta),
  // volver a una página válida.
  useEffect(() => {
    if (paginaActual > totalPaginas) setPagina(totalPaginas);
  }, [paginaActual, totalPaginas]);

  const pagina = useMemo(() => {
    const inicio = (paginaActual - 1) * tamPagina;
    return items.slice(inicio, inicio + tamPagina);
  }, [items, paginaActual, tamPagina]);

  const desde = total === 0 ? 0 : (paginaActual - 1) * tamPagina + 1;
  const hasta = Math.min(paginaActual * tamPagina, total);

  return {
    pagina,
    paginaActual,
    totalPaginas,
    total,
    desde,
    hasta,
    irA: (p) => setPagina(Math.min(Math.max(1, p), totalPaginas)),
    anterior: () => setPagina((p) => Math.max(1, p - 1)),
    siguiente: () => setPagina((p) => Math.min(totalPaginas, p + 1)),
  };
}

/** Barra de paginación al pie de una tabla. No se muestra si hay una sola página. */
export function Paginacion({
  paginado,
  etiqueta = 'registros',
}: {
  paginado: Pick<
    Paginado<unknown>,
    'paginaActual' | 'totalPaginas' | 'total' | 'desde' | 'hasta' | 'anterior' | 'siguiente'
  >;
  etiqueta?: string;
}) {
  const { paginaActual, totalPaginas, total, desde, hasta, anterior, siguiente } = paginado;
  if (total === 0) return null;

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 bg-superficie-alt-2 px-4 py-2.5">
      <span className="text-[11.5px] text-muted-foreground">
        {desde}–{hasta} de {total} {etiqueta}
      </span>
      {totalPaginas > 1 ? (
        <div className="flex items-center gap-1.5">
          <BotonPagina onClick={anterior} disabled={paginaActual === 1} etiqueta="Página anterior">
            ‹
          </BotonPagina>
          <span className="rounded-md bg-primary px-2.5 py-1 font-mono text-[11.5px] font-medium text-primary-foreground">
            {paginaActual}
            <span className="font-normal opacity-80"> / {totalPaginas}</span>
          </span>
          <BotonPagina
            onClick={siguiente}
            disabled={paginaActual === totalPaginas}
            etiqueta="Página siguiente"
          >
            ›
          </BotonPagina>
        </div>
      ) : null}
    </div>
  );
}

function BotonPagina({
  onClick,
  disabled,
  etiqueta,
  children,
}: {
  onClick: () => void;
  disabled: boolean;
  etiqueta: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={etiqueta}
      className={cn(
        'flex h-7 w-7 items-center justify-center rounded-md border border-border bg-card text-[15px] leading-none text-foreground transition-colors',
        disabled ? 'cursor-not-allowed opacity-40' : 'hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
      )}
    >
      {children}
    </button>
  );
}
