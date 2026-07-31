import * as React from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Check,
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
import { useBolsaPedido, useDetallePedido, useRefrescarPedido } from './api';
import { Anotaciones } from './Anotaciones';
import { BolsaPedido } from './BolsaPedido';
import { CopyChip } from './pipeline-ui';
import type {
  CandidatoCCMN,
  ItemPedido,
  OrdenAsociada,
  PedidoDetalle as PedidoDetalleType,
  TimelineEvento,
} from './types';

interface PedidoDetalleProps {
  nroPedido: number;
  tipoBien: string;
  tipoPedido: string;
}

export function PedidoDetalle({ nroPedido, tipoBien, tipoPedido }: PedidoDetalleProps) {
  const { data, isLoading, isError, error, refetch } = useDetallePedido({
    nroPedido,
    tipoBien,
    tipoPedido,
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

  // El cuadro de necesidades (CCMN) determina las etapas de programación del
  // recorrido, así que va ANTES del recorrido, no después. Cuando el pedido
  // ya está resuelto la bolsa arranca plegada — es contexto opcional; cuando
  // es ambiguo se muestra abierta, porque es justo lo que hay que resolver.
  const resuelto = esNivelResuelto(data.confianza_ccmn);

  return (
    <div className="space-y-6">
      <BreadcrumbVolver />
      <CabeceraPedido pedido={data} nroPedido={nroPedido} tipoBien={tipoBien} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <BloquePedido pedido={data} />
        <BloqueOrdenes ordenes={data.ordenes} />
      </div>

      {data.items.length > 0 ? <BloqueItems items={data.items} /> : null}

      {/* Cuadro de necesidades: el contexto que explica el recorrido. Va antes
          del recorrido porque lo determina. */}
      {data.tipo_pedido ? (
        <BolsaPedido
          nroPedido={data.nro_pedido}
          tipoBien={data.tipo_bien}
          tipoPedido={data.tipo_pedido}
          confianza={data.confianza_ccmn}
          plegableInicial={resuelto}
        />
      ) : null}

      <BloqueTimeline eventos={data.timeline} pedido={data} />

      <Anotaciones nroPedido={nroPedido} tipoBien={tipoBien} />
    </div>
  );
}

// Niveles donde el cuadro atribuido es de este pedido: la bolsa es entonces
// contexto opcional y puede arrancar plegada. `ambiguo`/`conflicto` no.
function esNivelResuelto(nivel: PedidoDetalleType['confianza_ccmn']): boolean {
  return (
    nivel === 'unico' ||
    nivel === 'declarado' ||
    nivel === 'declarado_cert' ||
    nivel === 'resuelto_manual'
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

function CabeceraPedido({
  pedido,
  nroPedido,
  tipoBien,
}: {
  pedido: PedidoDetalleType;
  nroPedido: number;
  tipoBien: string;
}) {
  const IconoTipo = pedido.tipo_bien === 'B' ? Package : Wrench;
  const tipoLabel = pedido.tipo_bien === 'B' ? 'Bien' : 'Servicio';
  const esCierre = pedido.macrofase_actual === 'cierre';

  // Identificadores (§03.2 bloque 1): los 3 IDs con copiar. La orden/SIAF solo
  // se atribuyen cuando el puente está resuelto; si no, se muestran las del
  // expediente en el bloque de órdenes, no aquí.
  const idPedido = `${pedido.nro_pedido}-${pedido.ano_eje}/${pedido.tipo_bien}`;
  const ordenAtribuida =
    pedido.ccmn_atribuido != null
      ? pedido.ordenes.find((o) => o.nro_certifica != null) ?? pedido.ordenes[0]
      : undefined;
  const prefijoOrden = pedido.tipo_bien === 'S' ? 'O/S' : 'O/C';

  return (
    <PageHeader
      titulo={`Pedido N° ${pedido.nro_pedido}-${pedido.ano_eje}`}
      descripcion={
        <div className="flex flex-col gap-2">
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
          {/* Fila de identificadores con copiar-al-clic (§00 principio 2) */}
          <div className="flex flex-wrap items-center gap-1.5">
            <CopyChip valor={idPedido} />
            {ordenAtribuida ? (
              <CopyChip valor={`${prefijoOrden} ${ordenAtribuida.nro_orden}`} />
            ) : null}
            {ordenAtribuida?.exp_siaf != null ? (
              <CopyChip
                etiqueta="SIAF"
                valor={String(ordenAtribuida.exp_siaf)}
              />
            ) : null}
            {ordenAtribuida?.nro_certifica != null ? (
              <CopyChip etiqueta="CCP" valor={String(ordenAtribuida.nro_certifica)} />
            ) : null}
          </div>
        </div>
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
          <BotonRefrescar
            nroPedido={nroPedido}
            tipoBien={tipoBien}
            tipoPedido={pedido.tipo_pedido ?? ''}
          />
        </div>
      }
    />
  );
}

// Botón "Actualizar desde SIGA" (§01.3): sincroniza solo este pedido.
function BotonRefrescar({
  nroPedido,
  tipoBien,
  tipoPedido,
}: {
  nroPedido: number;
  tipoBien: string;
  tipoPedido: string;
}) {
  const refrescar = useRefrescarPedido({ nroPedido, tipoBien, tipoPedido });
  if (!tipoPedido) return null;
  return (
    <button
      type="button"
      onClick={() => refrescar.mutate()}
      disabled={refrescar.isPending}
      className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:border-primary/50 disabled:opacity-60"
    >
      {refrescar.isPending ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
      ) : null}
      Actualizar desde SIGA
    </button>
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
        <FilaDato
          label="Cuadro necesidades"
          valor={<ValorCuadroNecesidades pedido={pedido} />}
        />
      </dl>
    </SectionCard>
  );
}

/**
 * Qué cuadro de necesidades (CCMN) se le atribuye al pedido y con qué certeza.
 *
 * Se muestra SIEMPRE lo que dice la cascada automática, también cuando hay
 * resolución manual (§5): el origen del dato debe quedar auditable.
 */
function ValorCuadroNecesidades({ pedido }: { pedido: PedidoDetalleType }) {
  const nivel = pedido.confianza_ccmn;

  if (!nivel || nivel === 'sin_ccmn') {
    return (
      <span className="text-muted-foreground">
        Todavía no programado
      </span>
    );
  }

  const noResuelto = nivel === 'ambiguo' || nivel === 'conflicto';
  const n = pedido.ccmn_candidatos?.length ?? 0;

  return (
    <span className="flex flex-wrap items-baseline gap-x-2">
      {pedido.ccmn_atribuido ? (
        <span className="font-mono">{pedido.ccmn_atribuido}</span>
      ) : (
        <span className="text-muted-foreground">Sin determinar</span>
      )}
      <span
        className={cn(
          'text-xs font-medium',
          noResuelto ? 'text-semaforo-alerta' : 'text-muted-foreground',
        )}
      >
        {pedido.confianza_ccmn_label ?? nivel}
        {noResuelto && n > 0 ? ` · ${n} candidatos` : ''}
      </span>
    </span>
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

function BloqueTimeline({
  eventos,
  pedido,
}: {
  eventos: TimelineEvento[];
  pedido: PedidoDetalleType;
}) {
  const hitos: HitoTimeline[] = eventos.map((e) => ({
    key: e.etapa,
    titulo: e.etapa_label,
    detalle: e.detalle,
    fecha: e.fecha,
    estado: e.estado,
    numero: e.etapa_numero,
    documentos: e.documentos,
  }));

  const alcanzadas = eventos.filter((e) => e.alcanzada).length;
  const enGrupo = eventos.filter((e) => e.estado === 'grupo').length;

  return (
    <SectionCard
      titulo={`Recorrido del pedido (${alcanzadas}/${eventos.length})`}
      padding="md"
    >
      {enGrupo > 0 ? <AvisoAvanceDelGrupo pedido={pedido} /> : null}
      <Timeline hitos={hitos} />

      {/* Cuando el pedido es ambiguo, el recorrido de arriba dice la verdad
          (esto es tuyo, esto es del grupo). El comparador de abajo deja mirar
          el recorrido de CADA cuadro candidato por separado, para elegir con
          criterio — sin que ninguno se muestre como "el" recorrido del pedido. */}
      {enGrupo > 0 ? <ComparadorCandidatos pedido={pedido} /> : null}
    </SectionCard>
  );
}

/**
 * Comparador de cuadros candidatos.
 *
 * Cuando la bolsa agrupa varios pedidos, cada cuadro consolidado (CCMN) tiene
 * su propio recorrido. Aquí el funcionario elige un candidato y ve HASTA DÓNDE
 * llegó ESE cuadro y con qué números — para comparar candidatos entre sí.
 *
 * Distinción crítica (§2, §7 del doc): esto NO es el recorrido del pedido y no
 * se pinta como tal. Es el recorrido del cuadro elegido, rotulado como
 * candidato. El sistema nunca dice cuál es el correcto; solo muestra los datos
 * de cada uno para que un humano decida. No se ordena ni sugiere por monto ni
 * fecha (ambos métodos están medidos y descartados).
 */
function ComparadorCandidatos({ pedido }: { pedido: PedidoDetalleType }) {
  const { data, isLoading } = useBolsaPedido({
    nroPedido: pedido.nro_pedido,
    tipoBien: pedido.tipo_bien,
    tipoPedido: pedido.tipo_pedido ?? '',
    habilitado: Boolean(pedido.tipo_pedido),
  });

  const candidatos = data?.candidatos ?? [];
  const [sel, setSel] = React.useState<number | null>(null);

  // Por defecto muestra el cuadro que la cascada atribuye, si lo hay. Es el
  // punto de partida honesto: lo que el sistema cree, no una adivinanza nueva.
  React.useEffect(() => {
    if (sel != null) return;
    const primero = candidatos[0];
    if (pedido.ccmn_atribuido != null) {
      setSel(pedido.ccmn_atribuido);
    } else if (primero) {
      setSel(primero.nro_consolid);
    }
  }, [candidatos, pedido.ccmn_atribuido, sel]);

  if (isLoading || candidatos.length < 2) return null;

  const elegido = candidatos.find((c) => c.nro_consolid === sel) ?? null;

  return (
    <div className="mt-6 border-t border-border pt-4">
      <h3 className="text-sm font-medium text-foreground">
        Comparar cuadros candidatos
      </h3>
      <p className="mt-1 text-xs text-muted-foreground">
        Cada cuadro tiene su propio recorrido. Elegí uno para ver hasta dónde
        llegó y con qué números. Esto es el recorrido del cuadro, no el de este
        pedido: SIGA no registra cuál corresponde.
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        {candidatos.map((c) => (
          <ChipCandidato
            key={c.nro_consolid}
            candidato={c}
            atribuido={c.nro_consolid === pedido.ccmn_atribuido}
            seleccionado={c.nro_consolid === sel}
            onSeleccionar={() => setSel(c.nro_consolid)}
          />
        ))}
      </div>

      {elegido ? <FlujoCandidato candidato={elegido} /> : null}
    </div>
  );
}

function ChipCandidato({
  candidato,
  atribuido,
  seleccionado,
  onSeleccionar,
}: {
  candidato: CandidatoCCMN;
  atribuido: boolean;
  seleccionado: boolean;
  onSeleccionar: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSeleccionar}
      aria-pressed={seleccionado}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
        seleccionado
          ? 'border-primary bg-primary/5 text-foreground'
          : 'border-border text-muted-foreground hover:border-primary/40 hover:bg-muted/40',
      )}
    >
      <span className="font-medium">Cuadro {candidato.nro_consolid}</span>
      <span className="tabular-nums text-xs">
        {formatearMoneda(candidato.valor_plan)}
      </span>
      {atribuido ? (
        <span className="inline-flex items-center gap-0.5 text-xs font-medium text-primary">
          <Check className="w-3 h-3" aria-hidden="true" />
          el más probable
        </span>
      ) : null}
    </button>
  );
}

/**
 * Recorrido propio de un cuadro candidato: los pasos que alcanzó y sus números.
 * Los pasos no alcanzados se muestran atenuados para que se vea dónde se detuvo.
 */
function FlujoCandidato({ candidato }: { candidato: CandidatoCCMN }) {
  return (
    <div className="mt-3 rounded-md border border-border bg-muted/20 p-3">
      <div className="flex items-baseline justify-between gap-2 flex-wrap mb-2">
        <span className="text-sm font-medium">
          Recorrido del cuadro {candidato.nro_consolid}
        </span>
        <span className="text-xs text-muted-foreground">
          consolidado {formatFecha(candidato.fecha_cons)}
        </span>
      </div>
      <ol className="flex flex-wrap items-center gap-x-1 gap-y-2">
        {candidato.flujo.map((h, i) => (
          <li key={h.codigo} className="flex items-center gap-1">
            {i > 0 ? (
              <span className="text-muted-foreground/40" aria-hidden="true">
                ›
              </span>
            ) : null}
            <span
              className={cn(
                'text-xs rounded px-1.5 py-0.5',
                h.alcanzado
                  ? 'bg-secondary/10 text-foreground'
                  : 'bg-transparent text-muted-foreground/50',
              )}
            >
              <span>{h.label}</span>
              {h.numero ? (
                <span className="ml-1 font-mono tabular-nums">{h.numero}</span>
              ) : null}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/**
 * Aviso de que parte del recorrido no es atribuible a este pedido.
 *
 * Es la pieza donde se juega la honestidad del sistema (§8): si el usuario no
 * entiende por qué hay etapas en amarillo, sólo movimos la imprecisión a un
 * símbolo más bonito. Por eso el aviso es un bloque visible y en palabras
 * llanas, no un tooltip.
 */
function AvisoAvanceDelGrupo({ pedido }: { pedido: PedidoDetalleType }) {
  const n = pedido.ccmn_candidatos?.length ?? 0;

  return (
    <div className="mb-4 rounded-md border border-semaforo-alerta/40 bg-semaforo-alerta/10 p-3">
      <div className="flex gap-2">
        <AlertTriangle
          className="w-4 h-4 shrink-0 mt-0.5 text-semaforo-alerta"
          aria-hidden="true"
        />
        <div className="min-w-0 text-sm">
          <p className="font-medium text-foreground">
            Parte de este recorrido no se puede atribuir a este pedido
          </p>
          <p className="mt-1 text-muted-foreground">
            Este pedido comparte cuadro de necesidades con otros
            {n > 0 ? (
              <>
                {' '}y hay <strong className="text-foreground">{n} cuadros
                candidatos</strong> ({pedido.ccmn_candidatos.join(', ')})
              </>
            ) : null}
            . SIGA no registra cuál corresponde a este pedido, así que las
            etapas marcadas <strong className="text-foreground">avance del
            grupo</strong> pudieron completarse por otro pedido.
          </p>
          <p className="mt-1 text-muted-foreground">
            Las demás etapas sí son datos verificados de este pedido.
          </p>
        </div>
      </div>
    </div>
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
