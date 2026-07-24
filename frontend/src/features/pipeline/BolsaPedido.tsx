import * as React from 'react';
import { AlertTriangle, Check, Link2, Loader2, Unlink } from 'lucide-react';
import { SectionCard } from '@/components/layout/SectionCard';
import { cn } from '@/lib/utils';
import { formatFecha } from '@/lib/formatters';
import {
  useAsociarCcmn,
  useBolsaPedido,
  useResolucionesPedido,
  useRevocarCcmn,
} from './api';
import type {
  CandidatoCCMN,
  NivelConfianza,
  PedidoEnBolsa,
  Resolucion,
} from './types';

/**
 * Vista de bolsa: los pedidos y los cuadros consolidados (CCMN) que comparten
 * un mismo cuadro de necesidades.
 *
 * SIGA no registra qué CCMN corresponde a qué pedido — logística copia los
 * datos del pedido a un CCMN nuevo y no los vincula. Cuando la bolsa agrupa
 * varios pedidos, ninguno de los candidatos es "el" del pedido.
 *
 * Esta pantalla muestra el contexto completo y deja que un funcionario declare
 * la correspondencia si la conoce. NUNCA sugiere un ganador: ordenar por
 * proximidad de monto o de fecha sería una recomendación disfrazada, y ambos
 * métodos están medidos y descartados (§2 — el monto pierde el CCMN correcto
 * en 33 casos).
 *
 * Ref: Docs/diagnostico-2026-07-20/refactorizacion-pipeline-pedido-ccmn.md §5, §8.2
 */

interface BolsaPedidoProps {
  nroPedido: number;
  tipoBien: string;
  tipoPedido: string;
  /** Nivel que la cascada automática asigna al pedido que se está viendo. */
  confianza: NivelConfianza | null;
  puedeAsociar?: boolean;
}

const MONEDA = new Intl.NumberFormat('es-PE', {
  style: 'currency',
  currency: 'PEN',
  minimumFractionDigits: 2,
});

const CONFIANZA_TEXTO: Record<NivelConfianza, string> = {
  unico: 'único candidato',
  declarado: 'declarado en la orden',
  declarado_cert: 'declarado en la certificación',
  resuelto_manual: 'asociado manualmente',
  conflicto: 'conflicto entre fuentes',
  ambiguo: 'ambiguo',
  sin_ccmn: 'sin cuadro consolidado',
};

// Niveles en los que el cuadro atribuido es de este pedido.
const RESUELTO: ReadonlySet<NivelConfianza> = new Set<NivelConfianza>([
  'unico',
  'declarado',
  'declarado_cert',
  'resuelto_manual',
]);

export function BolsaPedido({
  nroPedido,
  tipoBien,
  tipoPedido,
  confianza,
  puedeAsociar = true,
}: BolsaPedidoProps) {
  const params = { nroPedido, tipoBien, tipoPedido };
  const { data, isLoading } = useBolsaPedido(params);
  const { data: resoluciones } = useResolucionesPedido(params);
  const asociar = useAsociarCcmn(params);
  const revocar = useRevocarCcmn(params);

  // Los dos extremos de la asociación. El pedido que se está viendo arranca
  // seleccionado: es el caso más frecuente y ahorra un clic.
  const [pedidoSel, setPedidoSel] = React.useState<number | null>(nroPedido);
  const [ccmnSel, setCcmnSel] = React.useState<number | null>(null);
  const [nota, setNota] = React.useState('');

  if (isLoading) {
    return (
      <SectionCard titulo="Cuadro de necesidades compartido" padding="md">
        <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
          Cargando el cuadro de necesidades…
        </div>
      </SectionCard>
    );
  }

  if (!data || data.candidatos.length === 0) {
    return null; // pedido sin programar: no hay bolsa que mostrar
  }

  const activas = (resoluciones ?? []).filter((r) => !r.revocado_en);
  const historial = (resoluciones ?? []).filter((r) => r.revocado_en);
  const asociadosDelPedido = new Set(activas.map((r) => r.nro_consolid));

  const varios = data.pedidos.length > 1;
  const puedeConfirmar =
    pedidoSel != null && ccmnSel != null && pedidoSel === nroPedido;

  return (
    <SectionCard
      titulo={`Cuadro de necesidades ${data.sec_cua_mod_sal}`}
      descripcion={
        varios
          ? `Este cuadro agrupa ${data.pedidos.length} pedidos y ${data.candidatos.length} cuadros consolidados. SIGA no registra cuál corresponde a cada pedido.`
          : `Este cuadro corresponde solo a este pedido.`
      }
      padding="md"
    >
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_1fr] gap-4 lg:gap-3">
        {/* ── Extremo izquierdo: pedidos ── */}
        <div>
          <EncabezadoColumna
            titulo="Pedidos en este cuadro"
            ayuda="Más reciente primero"
          />
          <ul className="space-y-2">
            {data.pedidos.map((p) => (
              <TarjetaPedido
                key={`${p.nro_pedido}-${p.tipo_pedido}`}
                pedido={p}
                esActual={p.nro_pedido === nroPedido}
                seleccionado={pedidoSel === p.nro_pedido}
                onSeleccionar={() =>
                  setPedidoSel(pedidoSel === p.nro_pedido ? null : p.nro_pedido)
                }
              />
            ))}
          </ul>
        </div>

        {/* ── Conector ── */}
        <div className="hidden lg:flex flex-col items-center justify-center px-1">
          <div
            className={cn(
              'w-px flex-1',
              puedeConfirmar ? 'bg-primary' : 'bg-border',
            )}
            aria-hidden="true"
          />
          <Link2
            className={cn(
              'w-4 h-4 my-2 shrink-0',
              puedeConfirmar ? 'text-primary' : 'text-muted-foreground/40',
            )}
            aria-hidden="true"
          />
          <div
            className={cn(
              'w-px flex-1',
              puedeConfirmar ? 'bg-primary' : 'bg-border',
            )}
            aria-hidden="true"
          />
        </div>

        {/* ── Extremo derecho: CCMN ── */}
        <div>
          <EncabezadoColumna
            titulo="Cuadros consolidados"
            ayuda="Más reciente primero"
          />
          <ul className="space-y-2">
            {data.candidatos.map((c) => (
              <TarjetaCcmn
                key={c.nro_consolid}
                candidato={c}
                seleccionado={ccmnSel === c.nro_consolid}
                asociado={asociadosDelPedido.has(c.nro_consolid)}
                onSeleccionar={() =>
                  setCcmnSel(ccmnSel === c.nro_consolid ? null : c.nro_consolid)
                }
              />
            ))}
          </ul>
        </div>
      </div>

      {/* ── Barra de acción ── */}
      {puedeAsociar && varios ? (
        <BarraAsociar
          pedidoSel={pedidoSel}
          ccmnSel={ccmnSel}
          esPedidoActual={pedidoSel === nroPedido}
          nroPedido={nroPedido}
          yaAsociado={ccmnSel != null && asociadosDelPedido.has(ccmnSel)}
          nota={nota}
          onNota={setNota}
          enviando={asociar.isPending}
          error={asociar.error}
          onAsociar={() => {
            if (ccmnSel == null) return;
            asociar.mutate(
              { nroConsolid: ccmnSel, nota: nota.trim() || undefined },
              { onSuccess: () => { setCcmnSel(null); setNota(''); } },
            );
          }}
        />
      ) : null}

      {/* ── Asociaciones vigentes ── */}
      {activas.length > 0 ? (
        <ListaResoluciones
          titulo="Asociaciones declaradas para este pedido"
          resoluciones={activas}
          confianza={confianza}
          onRevocar={
            puedeAsociar ? (id) => revocar.mutate(id) : undefined
          }
          revocando={revocar.isPending}
        />
      ) : null}

      {historial.length > 0 ? (
        <details className="mt-3">
          <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">
            Ver asociaciones revocadas ({historial.length})
          </summary>
          <ListaResoluciones
            resoluciones={historial}
            confianza={confianza}
            revocadas
          />
        </details>
      ) : null}
    </SectionCard>
  );
}

// ─── Piezas ──────────────────────────────────────────────────────────────

function EncabezadoColumna({
  titulo,
  ayuda,
}: {
  titulo: string;
  ayuda: string;
}) {
  return (
    <div className="flex items-baseline justify-between gap-2 mb-2">
      <h4 className="text-sm font-medium text-foreground">{titulo}</h4>
      <span className="text-xs text-muted-foreground">{ayuda}</span>
    </div>
  );
}

function TarjetaPedido({
  pedido,
  esActual,
  seleccionado,
  onSeleccionar,
}: {
  pedido: PedidoEnBolsa;
  esActual: boolean;
  seleccionado: boolean;
  onSeleccionar: () => void;
}) {
  const noResuelto =
    pedido.confianza_ccmn === 'ambiguo' ||
    pedido.confianza_ccmn === 'conflicto';

  return (
    <li>
      <button
        type="button"
        onClick={onSeleccionar}
        aria-pressed={seleccionado}
        className={cn(
          'w-full text-left rounded-md border p-3 transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
          seleccionado
            ? 'border-primary bg-primary/5'
            : 'border-border hover:border-primary/40 hover:bg-muted/40',
        )}
      >
        <div className="flex items-baseline justify-between gap-2 flex-wrap">
          <span className="font-medium text-sm">
            Pedido {pedido.nro_pedido}
            {esActual ? (
              <span className="ml-2 text-xs font-normal text-primary">
                estás viendo este
              </span>
            ) : null}
          </span>
          <span className="text-sm tabular-nums">
            {MONEDA.format(pedido.valor_soles ?? 0)}
          </span>
        </div>
        <div className="mt-1 flex items-baseline gap-2 flex-wrap text-xs text-muted-foreground">
          <span>{formatFecha(pedido.fecha_pedido)}</span>
          {pedido.confianza_ccmn ? (
            <span
              className={cn(
                'font-medium',
                noResuelto ? 'text-semaforo-alerta' : 'text-muted-foreground',
              )}
            >
              {CONFIANZA_TEXTO[pedido.confianza_ccmn]}
            </span>
          ) : null}
        </div>
        {pedido.motivo ? (
          <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
            {pedido.motivo}
          </p>
        ) : null}
      </button>
    </li>
  );
}

function TarjetaCcmn({
  candidato,
  seleccionado,
  asociado,
  onSeleccionar,
}: {
  candidato: CandidatoCCMN;
  seleccionado: boolean;
  asociado: boolean;
  onSeleccionar: () => void;
}) {
  const alcanzados = candidato.flujo.filter((h) => h.alcanzado);

  return (
    <li>
      <button
        type="button"
        onClick={onSeleccionar}
        aria-pressed={seleccionado}
        className={cn(
          'w-full text-left rounded-md border p-3 transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
          seleccionado
            ? 'border-primary bg-primary/5'
            : asociado
              ? 'border-secondary/50 bg-secondary/5'
              : 'border-border hover:border-primary/40 hover:bg-muted/40',
        )}
      >
        <div className="flex items-baseline justify-between gap-2 flex-wrap">
          <span className="font-medium text-sm">
            Cuadro consolidado {candidato.nro_consolid}
          </span>
          <span className="text-sm tabular-nums">
            {MONEDA.format(candidato.valor_plan ?? 0)}
          </span>
        </div>
        <div className="mt-1 text-xs text-muted-foreground">
          {formatFecha(candidato.fecha_cons)}
          {asociado ? (
            <span className="ml-2 inline-flex items-center gap-1 font-medium text-secondary">
              <Check className="w-3 h-3" aria-hidden="true" />
              asociado a este pedido
            </span>
          ) : null}
        </div>

        {/* Recorrido propio del cuadro: hasta dónde llegó y con qué números.
            Es lo que permite comparar candidatos entre sí. */}
        {alcanzados.length > 0 ? (
          <ol className="mt-2 flex flex-wrap items-center gap-x-1 gap-y-1">
            {alcanzados.map((h, i) => (
              <li key={h.codigo} className="flex items-center gap-1">
                {i > 0 ? (
                  <span className="text-muted-foreground/40" aria-hidden="true">
                    ›
                  </span>
                ) : null}
                <span className="text-[11px] rounded bg-muted px-1.5 py-0.5">
                  <span className="text-muted-foreground">{h.label}</span>
                  {h.numero ? (
                    <span className="ml-1 font-mono tabular-nums">
                      {h.numero}
                    </span>
                  ) : null}
                </span>
              </li>
            ))}
          </ol>
        ) : null}
      </button>
    </li>
  );
}

function BarraAsociar({
  pedidoSel,
  ccmnSel,
  esPedidoActual,
  nroPedido,
  yaAsociado,
  nota,
  onNota,
  enviando,
  error,
  onAsociar,
}: {
  pedidoSel: number | null;
  ccmnSel: number | null;
  esPedidoActual: boolean;
  nroPedido: number;
  yaAsociado: boolean;
  nota: string;
  onNota: (v: string) => void;
  enviando: boolean;
  error: unknown;
  onAsociar: () => void;
}) {
  const faltaAlgo = pedidoSel == null || ccmnSel == null;

  return (
    <div className="mt-4 rounded-md border border-border bg-muted/30 p-3">
      {faltaAlgo ? (
        <p className="text-sm text-muted-foreground">
          Si sabés qué cuadro consolidado corresponde a este pedido, seleccioná
          uno de cada lado para declararlo. Es opcional: el sistema funciona sin
          esta declaración.
        </p>
      ) : !esPedidoActual ? (
        <p className="text-sm text-muted-foreground">
          Solo podés declarar la correspondencia del pedido que estás viendo
          (Pedido {nroPedido}). Abrí el pedido {pedidoSel} para asociarlo.
        </p>
      ) : yaAsociado ? (
        <p className="text-sm text-muted-foreground">
          El cuadro {ccmnSel} ya está asociado a este pedido.
        </p>
      ) : (
        <div className="space-y-2">
          <p className="text-sm">
            Declarar que el{' '}
            <strong>cuadro consolidado {ccmnSel}</strong> corresponde al{' '}
            <strong>pedido {pedidoSel}</strong>.
          </p>
          <input
            type="text"
            value={nota}
            onChange={(e) => onNota(e.target.value)}
            placeholder="Nota (opcional): en qué te basás para afirmarlo"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          />
          <button
            type="button"
            onClick={onAsociar}
            disabled={enviando}
            className={cn(
              'inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium',
              'bg-primary text-primary-foreground hover:bg-primary/90',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
              'disabled:opacity-60',
            )}
          >
            {enviando ? (
              <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
            ) : (
              <Link2 className="w-4 h-4" aria-hidden="true" />
            )}
            Asociar cuadro {ccmnSel} al pedido {pedidoSel}
          </button>
        </div>
      )}

      {error ? (
        <p className="mt-2 flex items-start gap-1.5 text-sm text-destructive">
          <AlertTriangle
            className="w-4 h-4 shrink-0 mt-0.5"
            aria-hidden="true"
          />
          No se pudo guardar la asociación. Verificá tu conexión e intentá de
          nuevo.
        </p>
      ) : null}
    </div>
  );
}

function ListaResoluciones({
  titulo,
  resoluciones,
  confianza,
  onRevocar,
  revocando,
  revocadas = false,
}: {
  titulo?: string;
  resoluciones: Resolucion[];
  confianza: NivelConfianza | null;
  onRevocar?: (id: string) => void;
  revocando?: boolean;
  revocadas?: boolean;
}) {
  return (
    <div className="mt-4">
      {titulo ? (
        <h4 className="text-sm font-medium mb-2">{titulo}</h4>
      ) : null}
      <ul className="space-y-2">
        {resoluciones.map((r) => (
          <li
            key={r.id}
            className={cn(
              'flex items-start justify-between gap-3 rounded-md border p-2.5 text-sm',
              revocadas
                ? 'border-border bg-muted/30 text-muted-foreground'
                : 'border-secondary/40 bg-secondary/5',
            )}
          >
            <div className="min-w-0">
              <p>
                Cuadro consolidado{' '}
                <span className="font-mono">{r.nro_consolid}</span>
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {revocadas ? 'Revocada' : 'Declarada'} por{' '}
                {r.usuario_nombre ?? 'un funcionario'} el{' '}
                {formatFecha(revocadas ? r.revocado_en : r.creado_en)}
                {revocadas && r.revocado_por_nombre
                  ? ` · revocó ${r.revocado_por_nombre}`
                  : ''}
              </p>
              {r.nota ? (
                <p className="text-xs text-muted-foreground mt-0.5 italic">
                  {r.nota}
                </p>
              ) : null}
              {/* La UI siempre muestra qué dice la cascada automática junto a
                  la resolución manual (§5): el origen debe ser auditable. */}
              {!revocadas && confianza && confianza !== 'resuelto_manual' ? (
                <p className="text-xs text-muted-foreground mt-1">
                  La detección automática dice:{' '}
                  {CONFIANZA_TEXTO[confianza]}
                  {RESUELTO.has(confianza) ? '' : ' — sin resolver'}
                </p>
              ) : null}
            </div>
            {onRevocar && !revocadas ? (
              <button
                type="button"
                onClick={() => onRevocar(r.id)}
                disabled={revocando}
                className="shrink-0 inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-60"
              >
                <Unlink className="w-3 h-3" aria-hidden="true" />
                Quitar
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default BolsaPedido;
