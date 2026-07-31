import { useMemo, useState } from 'react';
import { GitBranch, Loader2 } from 'lucide-react';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import { SectionCard } from '@/components/layout/SectionCard';
import { cn } from '@/lib/utils';
import { useKanban } from '@/features/dashboard/api';
import type {
  EtapaCodigo,
  KanbanResponse,
  Macrofase,
  PedidoCard as PedidoCardType,
} from '@/features/dashboard/types';
import FiltrosPipeline, {
  FILTROS_DEFAULT,
  type FiltrosPipelineState,
} from '../FiltrosPipeline';
import KanbanColumn, { type EstiloMacrofase } from '../KanbanColumn';

// Misma gradación que el widget del dashboard, para que la lectura sea
// consistente entre la miniatura y la vista completa (§1 principio 9).
const ESTILO_MACROFASE: Record<Macrofase, EstiloMacrofase> = {
  solicitud: {
    barraClass: 'bg-primary/25',
    chipClass: 'bg-primary/15 text-primary',
  },
  programacion: {
    barraClass: 'bg-primary/45',
    chipClass: 'bg-primary/20 text-primary',
  },
  certificacion: {
    barraClass: 'bg-primary/65',
    chipClass: 'bg-primary/25 text-primary',
  },
  contratacion: {
    barraClass: 'bg-primary',
    chipClass: 'bg-primary/30 text-primary',
  },
  ejecucion: {
    barraClass: 'bg-secondary',
    chipClass: 'bg-secondary/25 text-secondary-foreground',
  },
  cierre: {
    barraClass: 'bg-muted-foreground/50',
    chipClass: 'bg-muted text-muted-foreground',
  },
};

function aplicarFiltros(
  kanban: KanbanResponse,
  filtros: FiltrosPipelineState,
): {
  pedidosPorEtapa: Partial<Record<EtapaCodigo, PedidoCardType[]>>;
  conteosPorMacrofase: Record<Macrofase, number>;
  totalEstancadosVisible: number;
} {
  const busqueda = filtros.busqueda.trim();
  const filtrar = (p: PedidoCardType): boolean => {
    if (filtros.tipoBien !== 'todos' && p.tipo_bien !== filtros.tipoBien) {
      return false;
    }
    if (filtros.soloEstancados && !p.estancado) {
      return false;
    }
    if (busqueda && !String(p.nro_pedido).includes(busqueda)) {
      return false;
    }
    return true;
  };

  const pedidosPorEtapa: Partial<Record<EtapaCodigo, PedidoCardType[]>> = {};
  const conteosPorMacrofase: Record<Macrofase, number> = {
    solicitud: 0,
    programacion: 0,
    certificacion: 0,
    contratacion: 0,
    ejecucion: 0,
    cierre: 0,
  };
  let totalEstancadosVisible = 0;

  for (const [etapa, cards] of Object.entries(kanban.pedidos_por_etapa)) {
    const filtrados = (cards ?? []).filter(filtrar);
    if (filtrados.length === 0) continue;
    pedidosPorEtapa[etapa as EtapaCodigo] = filtrados;
    // filtrados.length > 0 garantizado por el continue previo, pero TS con
    // `noUncheckedIndexedAccess` no lo deduce; derivamos la macrofase del
    // primer elemento con non-null assertion segura.
    const macrofase = filtrados[0]!.macrofase;
    conteosPorMacrofase[macrofase] += filtrados.length;
    totalEstancadosVisible += filtrados.filter((p) => p.estancado).length;
  }

  return { pedidosPorEtapa, conteosPorMacrofase, totalEstancadosVisible };
}

/** Frescura del snapshot: primer `sincronizado_hasta` de cualquier tarjeta. */
function frescuraDelKanban(data: KanbanResponse): string | null {
  for (const cards of Object.values(data.pedidos_por_etapa)) {
    for (const p of cards ?? []) {
      if (p.sincronizado_hasta) return p.sincronizado_hasta;
    }
  }
  return null;
}

export function PipelineKanban() {
  const { data, isLoading, isError, error, refetch } = useKanban();
  const [filtros, setFiltros] = useState<FiltrosPipelineState>(FILTROS_DEFAULT);

  const totalEstancadosGlobal = useMemo(() => {
    if (!data) return 0;
    return Object.values(data.pedidos_por_etapa).reduce(
      (acc, cards) => acc + (cards ?? []).filter((p) => p.estancado).length,
      0,
    );
  }, [data]);

  const sincronizadoHasta = useMemo(
    () => (data ? frescuraDelKanban(data) : null),
    [data],
  );

  const filtrado = useMemo(() => {
    if (!data) return null;
    return aplicarFiltros(data, filtros);
  }, [data, filtros]);

  if (isLoading) {
    return (
      <SectionCard padding="lg">
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <Loader2
            className="w-8 h-8 animate-spin text-primary mb-3"
            aria-hidden="true"
          />
          <p className="text-sm">Cargando pipeline…</p>
        </div>
      </SectionCard>
    );
  }

  if (isError || !data) {
    return (
      <ErrorState
        titulo="No pudimos cargar el pipeline"
        descripcion={
          error instanceof Error
            ? error.message
            : 'Puede ser un corte temporal del SIGA. Reintenta en unos segundos.'
        }
        onReintentar={() => refetch()}
      />
    );
  }

  const totalGlobal = data.macrofases.reduce((acc, m) => acc + m.conteo, 0);
  if (totalGlobal === 0) {
    return (
      <EmptyState
        icono={GitBranch}
        titulo="Sin pedidos registrados"
        descripcion="No hay pedidos para el año y unidad seleccionados. Cambia el año o el centro de costo en el topbar."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <SectionCard padding="sm">
        <FiltrosPipeline
          filtros={filtros}
          onChange={setFiltros}
          totalEstancados={totalEstancadosGlobal}
        />
      </SectionCard>

      {/* Grid responsivo: 1 col mobile, 2 tablet, 3 lg, 6 xl (una por macrofase). */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
        {data.macrofases.map((m) => (
          <KanbanColumn
            key={m.macrofase}
            macrofase={m.macrofase}
            macrofaseLabel={m.macrofase_label}
            conteo={filtrado?.conteosPorMacrofase[m.macrofase] ?? m.conteo}
            etapas={m.etapas}
            pedidosPorEtapa={filtrado?.pedidosPorEtapa ?? {}}
            estilo={ESTILO_MACROFASE[m.macrofase]}
          />
        ))}
      </div>

      <FrescuraFooter sincronizadoHasta={sincronizadoHasta} onActualizar={() => refetch()} />
    </div>
  );
}

// ─── Pie de frescura (§03.1.2): "Datos SIGA al …" + botón Actualizar ─────

function FrescuraFooter({
  sincronizadoHasta,
  onActualizar,
}: {
  sincronizadoHasta: string | null;
  onActualizar: () => void;
}) {
  // Punto verde si el snapshot es de hoy; ámbar si es más viejo (umbral simple:
  // 12 h). El estado se comunica con color + texto (§04), nunca color solo.
  let al = 'sin dato de sincronización';
  let fresco = false;
  if (sincronizadoHasta) {
    const d = new Date(sincronizadoHasta);
    al = d.toLocaleString('es-PE', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
    fresco = Date.now() - d.getTime() < 12 * 60 * 60 * 1000;
  }
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-card px-3 py-2 text-xs text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <span
          className={cn(
            'inline-block h-2 w-2 rounded-full',
            fresco ? 'bg-secondary' : 'bg-accent',
          )}
          aria-hidden="true"
        />
        Datos de SIGA al {al}
        <span className="sr-only">
          {fresco ? ' (actualizado)' : ' (desactualizado, más de 12 horas)'}
        </span>
      </span>
      <button
        type="button"
        onClick={onActualizar}
        className="rounded border border-border bg-card px-2 py-1 font-medium text-foreground transition-colors hover:border-primary/50"
      >
        Actualizar
      </button>
    </div>
  );
}

export default PipelineKanban;
