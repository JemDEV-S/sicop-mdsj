import { useMemo, useState } from 'react';
import { GitBranch, Loader2 } from 'lucide-react';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import { SectionCard } from '@/components/layout/SectionCard';
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
    </div>
  );
}

export default PipelineKanban;
