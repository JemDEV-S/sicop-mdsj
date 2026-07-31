import { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, GitBranch, Loader2 } from 'lucide-react';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import { SectionCard } from '@/components/layout/SectionCard';
import { formatearMoneda } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import { useKanban } from '@/features/dashboard/api';
import type {
  KanbanResponse,
  Macrofase,
  PedidoCard as PedidoCardType,
} from '@/features/dashboard/types';
import FiltrosPipeline, {
  FILTROS_DEFAULT,
  type FiltrosPipelineState,
} from '../FiltrosPipeline';
import KanbanColumn, { type EstiloMacrofase } from '../KanbanColumn';
import PedidoCard from '../PedidoCard';

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

const NIVELES_RESUELTOS = new Set(['unico', 'declarado', 'declarado_cert', 'resuelto_manual']);

/**
 * ¿El avance observado es de la bolsa pero no atribuible a ESTE pedido?
 *
 * Mismo criterio que la alerta `puente_pendiente` del backend: puente sin
 * resolver y bolsa con órdenes. Estos pedidos NO se cuentan en las columnas
 * de fase — su columna sería una mentira (ni "programación" ni "ejecución"
 * son afirmables) — sino en la bandeja "avance por confirmar".
 */
function esPorConfirmar(p: PedidoCardType): boolean {
  const nivel = p.confianza_ccmn ?? p.puente?.nivel ?? null;
  if (nivel && NIVELES_RESUELTOS.has(nivel)) return false;
  return (p.puente?.avance_bolsa.n_ordenes ?? 0) > 0;
}

function todasLasCards(kanban: KanbanResponse): PedidoCardType[] {
  return Object.values(kanban.pedidos_por_etapa).flatMap((cards) => cards ?? []);
}

export function PipelineKanban() {
  const { data, isLoading, isError, error, refetch } = useKanban();
  const [filtros, setFiltros] = useState<FiltrosPipelineState>(FILTROS_DEFAULT);

  const derivado = useMemo(() => {
    if (!data) return null;
    const todas = todasLasCards(data);

    const busqueda = filtros.busqueda.trim().toLowerCase();
    const pasaFiltros = (p: PedidoCardType): boolean => {
      if (filtros.tipoBien !== 'todos' && p.tipo_bien !== filtros.tipoBien) return false;
      if (filtros.soloEstancados && !p.estancado) return false;
      if (
        busqueda &&
        !String(p.nro_pedido).includes(busqueda) &&
        !(p.motivo ?? '').toLowerCase().includes(busqueda)
      ) {
        return false;
      }
      return true;
    };

    const visibles = todas.filter(pasaFiltros);
    const porConfirmar = visibles.filter(esPorConfirmar);
    const enFlujo = visibles.filter((p) => !esPorConfirmar(p));

    const porMacrofase = new Map<Macrofase, PedidoCardType[]>();
    for (const p of enFlujo) {
      const lista = porMacrofase.get(p.macrofase) ?? [];
      lista.push(p);
      porMacrofase.set(p.macrofase, lista);
    }

    return {
      todas,
      visibles,
      porConfirmar,
      porMacrofase,
      totalEstancados: todas.filter((p) => p.estancado).length,
      estancadosVisibles: visibles.filter((p) => p.estancado).length,
      montoVisible: visibles.reduce((a, p) => a + (p.monto_total || 0), 0),
      montoPorConfirmar: porConfirmar.reduce((a, p) => a + (p.monto_total || 0), 0),
      sincronizadoHasta: todas.find((p) => p.sincronizado_hasta)?.sincronizado_hasta ?? null,
    };
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

  if (isError || !data || !derivado) {
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

  if (derivado.todas.length === 0) {
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
      <ResumenPipeline derivado={derivado} />

      <SectionCard padding="sm">
        <FiltrosPipeline
          filtros={filtros}
          onChange={setFiltros}
          totalEstancados={derivado.totalEstancados}
        />
      </SectionCard>

      {/* Grid responsivo: 1 col mobile, 2 tablet, 3 lg, 6 xl (una por macrofase). */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
        {data.macrofases.map((m) => (
          <KanbanColumn
            key={m.macrofase}
            macrofase={m.macrofase}
            macrofaseLabel={m.macrofase_label}
            pedidos={derivado.porMacrofase.get(m.macrofase) ?? []}
            etapas={m.etapas}
            estilo={ESTILO_MACROFASE[m.macrofase]}
          />
        ))}
      </div>

      <BandejaPorConfirmar
        pedidos={derivado.porConfirmar}
        monto={derivado.montoPorConfirmar}
      />

      <FrescuraFooter
        sincronizadoHasta={derivado.sincronizadoHasta}
        onActualizar={() => refetch()}
      />
    </div>
  );
}

// ─── Franja de resumen: la lectura ejecutiva antes del tablero ───────────

interface Derivado {
  visibles: PedidoCardType[];
  porConfirmar: PedidoCardType[];
  estancadosVisibles: number;
  montoVisible: number;
  montoPorConfirmar: number;
}

function ResumenPipeline({ derivado }: { derivado: Derivado }) {
  const enEjecucion = derivado.visibles.filter(
    (p) => p.macrofase === 'ejecucion' && !esPorConfirmar(p),
  ).length;

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <TileResumen
        titulo="Pedidos en curso"
        valor={String(derivado.visibles.length)}
        detalle={formatearMoneda(derivado.montoVisible, true)}
      />
      <TileResumen
        titulo="En ejecución"
        valor={String(enEjecucion)}
        detalle="con orden atendida o devengada"
        acentoClass="border-l-secondary"
      />
      <TileResumen
        titulo="Estancados"
        valor={String(derivado.estancadosVisibles)}
        detalle="sin avance sobre el plazo esperado"
        acentoClass="border-l-destructive"
        valorClass={derivado.estancadosVisibles > 0 ? 'text-destructive' : undefined}
      />
      <TileResumen
        titulo="Avance por confirmar"
        valor={String(derivado.porConfirmar.length)}
        detalle={`${formatearMoneda(derivado.montoPorConfirmar, true)} · la bolsa avanzó; falta confirmar el cuadro`}
        acentoClass="border-l-accent"
      />
    </div>
  );
}

function TileResumen({
  titulo,
  valor,
  detalle,
  acentoClass,
  valorClass,
}: {
  titulo: string;
  valor: string;
  detalle?: string;
  acentoClass?: string;
  valorClass?: string;
}) {
  return (
    <div
      className={cn(
        'rounded-md border border-border bg-card px-3 py-2.5',
        acentoClass && cn('border-l-4', acentoClass),
      )}
    >
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {titulo}
      </p>
      <p className={cn('mt-0.5 text-xl font-semibold tabular-nums text-foreground', valorClass)}>
        {valor}
      </p>
      {detalle ? (
        <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">{detalle}</p>
      ) : null}
    </div>
  );
}

// ─── Bandeja "avance por confirmar" (§02.1: honestidad del puente) ───────
//
// Estos pedidos comparten bolsa con otros y la bolsa ya tiene órdenes: el
// avance existe pero SIGA no registra de quién es. Ponerlos en "programación"
// infla la fase y los pinta como atrasados; ponerlos en "ejecución" sería
// atribuirles un avance no probado. Van en su propia bandeja, como cola de
// trabajo: cada uno se resuelve confirmando el cuadro en su detalle.

function BandejaPorConfirmar({
  pedidos,
  monto,
}: {
  pedidos: PedidoCardType[];
  monto: number;
}) {
  const [abierta, setAbierta] = useState(false);
  const [visibles, setVisibles] = useState(12);

  if (pedidos.length === 0) return null;

  const ordenados = [...pedidos].sort(
    (a, b) => (b.monto_total || 0) - (a.monto_total || 0),
  );
  const mostrados = ordenados.slice(0, visibles);
  const restantes = ordenados.length - mostrados.length;

  return (
    <section
      className="rounded-md border border-accent/50 bg-card"
      aria-labelledby="bandeja-por-confirmar"
    >
      <button
        type="button"
        onClick={() => setAbierta((s) => !s)}
        aria-expanded={abierta}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md"
      >
        <div className="flex items-center gap-2 min-w-0">
          {abierta ? (
            <ChevronDown className="w-4 h-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          ) : (
            <ChevronRight className="w-4 h-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          )}
          <div className="min-w-0">
            <h2
              id="bandeja-por-confirmar"
              className="text-sm font-semibold text-foreground"
            >
              Avance por confirmar
              <span className="ml-2 rounded bg-accent/20 px-1.5 py-0.5 text-xs font-semibold tabular-nums text-accent-foreground">
                {pedidos.length}
              </span>
            </h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {formatearMoneda(monto, true)} en pedidos cuya bolsa ya tiene órdenes,
              pero SIGA no registra a cuál pedido corresponden. Abre cada pedido y
              confirma su cuadro para que aparezca en la fase real.
            </p>
          </div>
        </div>
      </button>

      {abierta ? (
        <div className="border-t border-border px-4 py-3">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {mostrados.map((p) => (
              <PedidoCard
                key={`${p.ano_eje}-${p.nro_pedido}-${p.tipo_bien}`}
                pedido={p}
                contexto="bandeja"
              />
            ))}
          </div>
          {restantes > 0 ? (
            <button
              type="button"
              onClick={() => setVisibles((v) => v + 12)}
              className="mt-3 w-full rounded-md border border-dashed border-border py-1.5 text-xs text-muted-foreground hover:text-foreground hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Mostrar 12 más ({restantes} restantes)
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
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
