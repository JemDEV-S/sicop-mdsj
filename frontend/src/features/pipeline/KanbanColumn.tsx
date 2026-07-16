import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import PedidoCard from './PedidoCard';
import type {
  EtapaCodigo,
  EtapaConteo,
  Macrofase,
  PedidoCard as PedidoCardType,
} from '../dashboard/types';

interface KanbanColumnProps {
  macrofase: Macrofase;
  macrofaseLabel: string;
  conteo: number;
  etapas: EtapaConteo[];
  pedidosPorEtapa: Partial<Record<EtapaCodigo, PedidoCardType[]>>;
  estilo: EstiloMacrofase;
}

export interface EstiloMacrofase {
  // Barra superior de la columna: identidad visual de la macrofase.
  barraClass: string;
  chipClass: string;
}

// Cuántos pedidos rendereamos por columna antes de mostrar "Cargar más".
// Con 1023 pedidos en cierre no podemos volcar todo al DOM (bloquea el
// hilo principal y la scroll perf se rompe). Igual que en el widget del
// dashboard, mostramos lo relevante y damos control explícito al usuario.
const PAGE_SIZE = 20;

export function KanbanColumn({
  macrofase,
  macrofaseLabel,
  conteo,
  etapas,
  pedidosPorEtapa,
  estilo,
}: KanbanColumnProps) {
  // Aplanamos los pedidos de todas las etapas de la macrofase en una lista única,
  // priorizando los estancados (para que aparezcan siempre visibles arriba).
  const pedidos: PedidoCardType[] = etapas
    .flatMap((e) => pedidosPorEtapa[e.etapa as EtapaCodigo] ?? [])
    .sort((a, b) => {
      // Estancados primero, luego por días descendente.
      if (a.estancado !== b.estancado) return a.estancado ? -1 : 1;
      return (b.dias_en_etapa ?? 0) - (a.dias_en_etapa ?? 0);
    });

  const estancados = pedidos.filter((p) => p.estancado).length;
  const [visibles, setVisibles] = useState(PAGE_SIZE);
  const [mostrarEtapas, setMostrarEtapas] = useState(false);

  const mostrados = pedidos.slice(0, visibles);
  const restantes = pedidos.length - mostrados.length;

  return (
    <section
      className="flex flex-col rounded-md border border-border bg-muted/30 min-h-[24rem]"
      aria-labelledby={`col-${macrofase}`}
    >
      {/* Barra superior identidad de la macrofase */}
      <div className={cn('h-1 rounded-t-md', estilo.barraClass)} aria-hidden="true" />

      <header className="px-3 py-2.5 border-b border-border/60 bg-card rounded-t-none">
        <div className="flex items-center justify-between gap-2">
          <h2
            id={`col-${macrofase}`}
            className="text-xs font-semibold uppercase tracking-wide text-foreground truncate"
          >
            {macrofaseLabel}
          </h2>
          <span
            className={cn(
              'shrink-0 rounded px-1.5 py-0.5 text-xs font-semibold tabular-nums',
              estilo.chipClass,
            )}
          >
            {conteo}
          </span>
        </div>

        {estancados > 0 ? (
          <p className="mt-1 text-[11px] text-destructive font-medium">
            {estancados} estancado{estancados === 1 ? '' : 's'}
          </p>
        ) : null}

        {/* Drill-down opcional a las etapas SIGA (13/16) que componen la macrofase. */}
        {etapas.length > 1 && conteo > 0 ? (
          <button
            type="button"
            onClick={() => setMostrarEtapas((s) => !s)}
            className="mt-1.5 inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:underline"
            aria-expanded={mostrarEtapas}
          >
            {mostrarEtapas ? (
              <ChevronDown className="w-3 h-3" aria-hidden="true" />
            ) : (
              <ChevronRight className="w-3 h-3" aria-hidden="true" />
            )}
            <span>Ver etapas</span>
          </button>
        ) : null}

        {mostrarEtapas ? (
          <ul className="mt-1.5 space-y-0.5 border-l border-border/50 pl-2">
            {etapas.map((e) => (
              <li
                key={e.etapa}
                className="flex items-center justify-between text-[11px] text-muted-foreground"
              >
                <span className="truncate">
                  <span className="tabular-nums mr-1 text-muted-foreground/70">
                    [{e.etapa_numero}]
                  </span>
                  {e.etapa_label}
                </span>
                <span className="tabular-nums font-medium ml-2">{e.conteo}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </header>

      <div className="flex-1 p-2 flex flex-col gap-1.5 overflow-y-auto">
        {mostrados.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-6">
            Sin pedidos en esta fase.
          </p>
        ) : (
          mostrados.map((pedido) => (
            <PedidoCard
              key={`${pedido.ano_eje}-${pedido.nro_pedido}-${pedido.tipo_bien}`}
              pedido={pedido}
            />
          ))
        )}

        {restantes > 0 ? (
          <button
            type="button"
            onClick={() => setVisibles((v) => v + PAGE_SIZE)}
            className="mt-1 rounded-md border border-dashed border-border py-1.5 text-xs text-muted-foreground hover:text-foreground hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Cargar {Math.min(PAGE_SIZE, restantes)} más
            <span className="text-muted-foreground/70"> ({restantes} restantes)</span>
          </button>
        ) : null}
      </div>
    </section>
  );
}

export default KanbanColumn;
