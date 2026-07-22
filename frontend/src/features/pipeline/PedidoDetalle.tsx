import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  ChevronLeft,
  ClipboardList,
  Loader2,
  MapPin,
  Package,
  ShoppingCart,
  Wrench,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { SectionCard } from '@/components/layout/SectionCard';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import Timeline, { type HitoTimeline } from '@/components/Timeline';
import { formatearMoneda, formatFecha } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import { useDetallePedido } from './api';
import { Anotaciones } from './Anotaciones';
import type {
  ItemPedido,
  OrdenAsociada,
  PedidoDetalle as PedidoDetalleType,
  TimelineEvento,
} from './types';

interface PedidoDetalleProps {
  nroPedido: number;
  tipoBien: string;
}

export function PedidoDetalle({ nroPedido, tipoBien }: PedidoDetalleProps) {
  const { data, isLoading, isError, error, refetch } = useDetallePedido({
    nroPedido,
    tipoBien,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <BreadcrumbVolver />
        <SectionCard padding="lg">
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <Loader2
              className="w-8 h-8 animate-spin text-primary mb-3"
              aria-hidden="true"
            />
            <p className="text-sm">Cargando pedido {nroPedido}/{tipoBien}…</p>
          </div>
        </SectionCard>
      </div>
    );
  }

  if (isError || !data) {
    const es404 =
      error instanceof Error && 'response' in error &&
      (error as { response?: { status?: number } }).response?.status === 404;

    if (es404) {
      return (
        <div className="space-y-6">
          <BreadcrumbVolver />
          <EmptyState
            icono={ClipboardList}
            titulo="Pedido no encontrado"
            descripcion={`No existe el pedido ${nroPedido}/${tipoBien} para el año activo. Verifica el número o cambia el año en el topbar.`}
            accion={{ label: 'Volver al pipeline', href: '/interno/pipeline' }}
          />
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <BreadcrumbVolver />
        <ErrorState
          titulo="No pudimos cargar el pedido"
          descripcion={
            error instanceof Error
              ? error.message
              : 'Puede ser un corte temporal del SIGA. Reintenta en unos segundos.'
          }
          onReintentar={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <BreadcrumbVolver />
      <CabeceraPedido pedido={data} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <BloquePedido pedido={data} />
        <BloqueOrdenes ordenes={data.ordenes} />
      </div>

      {data.items.length > 0 ? <BloqueItems items={data.items} /> : null}

      <BloqueTimeline eventos={data.timeline} />

      <Anotaciones nroPedido={nroPedido} tipoBien={tipoBien} />
    </div>
  );
}

function BreadcrumbVolver() {
  return (
    <Link
      to="/interno/pipeline"
      className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
    >
      <ChevronLeft className="w-4 h-4" aria-hidden="true" />
      Volver al pipeline
    </Link>
  );
}

// ─── Cabecera con estado actual ──────────────────────────────────────────

function CabeceraPedido({ pedido }: { pedido: PedidoDetalleType }) {
  const IconoTipo = pedido.tipo_bien === 'B' ? Package : Wrench;
  const tipoLabel = pedido.tipo_bien === 'B' ? 'Bien' : 'Servicio';
  const esCierre = pedido.macrofase_actual === 'cierre';
  const diasEnEtapa = diasDesde(fechaDeEtapaActual(pedido));
  const estancado = !esCierre && diasEnEtapa != null && diasEnEtapa > 15;

  return (
    <PageHeader
      titulo={`Pedido N° ${pedido.nro_pedido}-${pedido.ano_eje}`}
      descripcion={
        <span className="inline-flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1">
            <IconoTipo className="w-4 h-4" aria-hidden="true" />
            {tipoLabel}
          </span>
          {pedido.centro_costo_nombre ? (
            <>
              <span className="text-muted-foreground/50">·</span>
              <span className="inline-flex items-center gap-1">
                <MapPin className="w-4 h-4" aria-hidden="true" />
                <span>
                  {pedido.centro_costo_nombre}
                  {pedido.centro_costo ? (
                    <span className="text-muted-foreground/70 font-mono ml-1">
                      ({pedido.centro_costo})
                    </span>
                  ) : null}
                </span>
              </span>
            </>
          ) : pedido.centro_costo ? (
            <>
              <span className="text-muted-foreground/50">·</span>
              <span className="font-mono">{pedido.centro_costo}</span>
            </>
          ) : null}
        </span>
      }
      acciones={
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium border',
              esCierre
                ? 'border-muted-foreground/30 bg-muted text-muted-foreground'
                : 'border-primary/40 bg-primary/10 text-primary',
            )}
          >
            <span
              className="text-[10px] font-mono tabular-nums opacity-70"
              aria-hidden="true"
            >
              [{pedido.etapa_actual_numero}]
            </span>
            <span>{pedido.etapa_actual_label}</span>
          </span>
          {estancado ? (
            <span
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium border border-destructive/50 bg-destructive/10 text-destructive"
              title={`${diasEnEtapa} días en esta etapa`}
            >
              <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
              Estancado
            </span>
          ) : null}
        </div>
      }
    />
  );
}

// ─── Bloque pedido ───────────────────────────────────────────────────────

function BloquePedido({ pedido }: { pedido: PedidoDetalleType }) {
  return (
    <SectionCard titulo="Pedido" icono={ClipboardList} padding="md">
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
        <FilaDato label="Fecha pedido" valor={formatFecha(pedido.fecha_pedido)} />
        <FilaDato label="Aprobado" valor={formatFecha(pedido.fecha_aprob)} />
        <FilaDato label="Atendido" valor={formatFecha(pedido.fecha_atenc)} />
        <FilaDato
          label="Meta"
          valor={
            pedido.sec_func ? (
              <>
                <span className="font-mono text-muted-foreground mr-1">
                  {String(pedido.sec_func).padStart(4, '0')}
                </span>
                <span>{pedido.nombre_meta ?? '—'}</span>
              </>
            ) : (
              '—'
            )
          }
        />
        <FilaDato
          label="Fuente financ."
          valor={pedido.fuente_financ ?? '—'}
          mono
        />
        <FilaDato label="Solicitante" valor={pedido.solicitante ?? '—'} />
        {pedido.motivo ? (
          <FilaDato
            label="Motivo"
            valor={<span className="whitespace-pre-wrap">{pedido.motivo}</span>}
          />
        ) : null}
      </dl>
    </SectionCard>
  );
}

function FilaDato({
  label,
  valor,
  mono,
}: {
  label: string;
  valor: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <>
      <dt className="text-xs font-medium text-muted-foreground uppercase tracking-wide pt-0.5">
        {label}
      </dt>
      <dd
        className={cn(
          'text-sm text-foreground',
          mono && 'font-mono',
        )}
      >
        {valor}
      </dd>
    </>
  );
}

// ─── Bloque ordenes ──────────────────────────────────────────────────────

function BloqueOrdenes({ ordenes }: { ordenes: OrdenAsociada[] }) {
  if (ordenes.length === 0) {
    return (
      <SectionCard titulo="Orden emitida" icono={ShoppingCart} padding="md">
        <p className="text-sm text-muted-foreground">
          Este pedido aún no tiene orden emitida.
        </p>
      </SectionCard>
    );
  }

  return (
    <SectionCard titulo="Orden emitida" icono={ShoppingCart} padding="md">
      <ul className="space-y-4">
        {ordenes.map((o) => (
          <li
            key={`${o.nro_orden}-${o.tipo_bien}-${o.exp_siga ?? 0}`}
            className="border border-border rounded-md p-3"
          >
            <div className="flex items-baseline justify-between gap-2 flex-wrap mb-2">
              <span className="text-sm font-semibold text-foreground">
                N° {o.nro_orden} · {o.tipo_bien === 'B' ? 'Bien' : 'Servicio'}
              </span>
              {o.estado_siaf ? (
                <span className="text-xs text-muted-foreground">
                  Estado SIAF: {o.estado_siaf}
                </span>
              ) : null}
            </div>

            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-sm">
              <FilaDato label="Concepto" valor={o.concepto ?? '—'} />
              <FilaDato label="Fecha orden" valor={formatFecha(o.fecha_orden)} />
              <FilaDato
                label="Proveedor"
                valor={
                  o.proveedor_nombre ? (
                    <>
                      <span>{o.proveedor_nombre}</span>
                      {o.proveedor_ruc ? (
                        <span className="text-xs text-muted-foreground ml-1 font-mono">
                          RUC {o.proveedor_ruc}
                        </span>
                      ) : null}
                    </>
                  ) : (
                    '—'
                  )
                }
              />
              <FilaDato
                label="Monto"
                valor={
                  <span className="font-semibold tabular-nums">
                    {formatearMoneda(o.total_fact_soles)}
                  </span>
                }
              />
              {o.exp_siaf ? (
                <FilaDato
                  label="EXP SIAF"
                  valor={
                    <span className="font-mono">
                      {String(o.exp_siaf).padStart(6, '0')}
                    </span>
                  }
                />
              ) : null}
            </dl>

            {o.exp_siaf ? (
              <div className="mt-3">
                <Link
                  to={`/interno/cruce/expediente-siaf/${o.exp_siaf}`}
                  className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  Ver ejecución SIAF
                  <ArrowRight className="w-3 h-3" aria-hidden="true" />
                </Link>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </SectionCard>
  );
}

// ─── Bloque items ────────────────────────────────────────────────────────

function BloqueItems({ items }: { items: ItemPedido[] }) {
  return (
    <SectionCard
      titulo={`Ítems del pedido (${items.length})`}
      icono={ClipboardList}
      padding="md"
      bodyClassName="p-0 overflow-x-auto"
    >
      <table className="w-full text-sm">
        <thead className="bg-muted/40 border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th scope="col" className="px-4 py-2 text-left font-medium">
              Ítem
            </th>
            <th scope="col" className="px-4 py-2 text-left font-medium">
              Clasificador
            </th>
            <th scope="col" className="px-4 py-2 text-right font-medium">
              Solicitada
            </th>
            <th scope="col" className="px-4 py-2 text-right font-medium">
              Aprobada
            </th>
            <th scope="col" className="px-4 py-2 text-right font-medium">
              Atendida
            </th>
            <th scope="col" className="px-4 py-2 text-right font-medium">
              Valor S/
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {items.map((it) => (
            <tr key={it.secuencia} className="hover:bg-muted/30">
              <td className="px-4 py-2 text-foreground">
                <span className="font-mono text-muted-foreground mr-1">
                  {String(it.secuencia).padStart(2, '0')}
                </span>
                {codigoItemBien(it)}
              </td>
              <td className="px-4 py-2 font-mono text-xs text-muted-foreground">
                {it.clasificador?.trim() || '—'}
              </td>
              <td className="px-4 py-2 text-right tabular-nums">
                {formatCantidad(it.cant_solicitada)}
              </td>
              <td className="px-4 py-2 text-right tabular-nums">
                {formatCantidad(it.cant_aprobada)}
              </td>
              <td className="px-4 py-2 text-right tabular-nums">
                {formatCantidad(it.cant_atendida)}
              </td>
              <td className="px-4 py-2 text-right tabular-nums font-medium">
                {formatearMoneda(it.valor_total)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </SectionCard>
  );
}

function codigoItemBien(it: ItemPedido): string {
  const partes = [it.grupo_bien, it.clase_bien, it.familia_bien, it.item_bien]
    .map((p) => (p ?? '').trim())
    .filter(Boolean);
  return partes.length > 0 ? partes.join(' · ') : '—';
}

function formatCantidad(v: number | null): string {
  if (v == null || v === 0) return '—';
  return new Intl.NumberFormat('es-PE', {
    maximumFractionDigits: 2,
  }).format(v);
}

// ─── Bloque timeline ─────────────────────────────────────────────────────

function BloqueTimeline({ eventos }: { eventos: TimelineEvento[] }) {
  const hitos: HitoTimeline[] = eventos.map((e) => ({
    key: e.etapa,
    titulo: e.etapa_label,
    detalle: e.detalle,
    fecha: e.fecha,
    alcanzada: e.alcanzada,
    numero: e.etapa_numero,
  }));

  const alcanzadas = eventos.filter((e) => e.alcanzada).length;

  return (
    <SectionCard
      titulo={`Recorrido del pedido (${alcanzadas}/${eventos.length})`}
      padding="md"
    >
      <Timeline hitos={hitos} />
    </SectionCard>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────────

function fechaDeEtapaActual(pedido: PedidoDetalleType): string | null {
  // Buscamos la fecha del evento alcanzado con etapa_numero == etapa_actual_numero;
  // si no la encontramos, caemos a la última alcanzada con fecha.
  const eventoActual = pedido.timeline.find(
    (e) => e.etapa_numero === pedido.etapa_actual_numero && e.alcanzada,
  );
  if (eventoActual?.fecha) return eventoActual.fecha;
  const conFecha = [...pedido.timeline]
    .filter((e) => e.alcanzada && e.fecha)
    .sort((a, b) => b.etapa_numero - a.etapa_numero);
  return conFecha[0]?.fecha ?? null;
}

function diasDesde(fecha: string | null): number | null {
  if (!fecha) return null;
  const f = new Date(fecha);
  if (isNaN(f.getTime())) return null;
  const hoy = new Date();
  const ms = hoy.getTime() - f.getTime();
  return Math.max(0, Math.floor(ms / (1000 * 60 * 60 * 24)));
}

export default PedidoDetalle;
