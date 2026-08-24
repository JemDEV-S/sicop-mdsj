// Pestaña Clasificadores: árbol Meta → Clasificador → pedidos que lo ejecutan.
// Fiel a la plantilla v2. El devengado oficial se cuenta UNA vez por meta; el
// dinero por pedido es reparto rotulado (§7) — por eso el chip del pedido lleva
// su marca "directo" / "est.".

import { formatearMoneda } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import { useModales } from '@/features/modales/ModalesContext';
import type { MetaReporte } from '../../reporte-types';
import { EstadoVacio } from './TablaOrdenes';

export function ArbolClasificadores({ metas }: { metas: MetaReporte[] }) {
  if (metas.length === 0) {
    return <EstadoVacio texto="No hay metas en el ámbito actual." />;
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[11.5px] text-texto-suave">
        Árbol Meta → Clasificador → pedidos que lo ejecutan. El devengado oficial se cuenta{' '}
        <b>una vez por meta</b>; el dinero por pedido es reparto rotulado.
      </p>
      {metas.map((m) => (
        <MetaBloque key={m.sec_func} meta={m} />
      ))}
    </div>
  );
}

function MetaBloque({ meta }: { meta: MetaReporte }) {
  const pim = meta.mef.pim;
  const dev = meta.mef.devengado;
  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 bg-superficie-alt px-3 py-2">
        <span className="font-mono text-[11px] text-muted-foreground">Meta {meta.sec_func}</span>
        <span className="text-[12.5px] font-semibold" title={meta.nombre_meta ?? undefined}>
          {meta.nombre_meta ?? 'Sin nombre'}
        </span>
        <span className="ml-auto font-mono text-[11.5px] text-muted-foreground">
          PIM {formatearMoneda(pim, true)} · Dev. {formatearMoneda(dev, true)}
        </span>
      </div>
      {meta.celdas.map((c) => (
        <ClasificadorFila key={`${meta.sec_func}-${c.clasificador}`} meta={meta} celda={c} />
      ))}
    </div>
  );
}

function ClasificadorFila({
  meta,
  celda,
}: {
  meta: MetaReporte;
  celda: MetaReporte['celdas'][number];
}) {
  const devCelda = celda.mef?.devengado ?? 0;
  const pctCelda = meta.mef.devengado > 0 ? (devCelda / meta.mef.devengado) * 100 : null;
  return (
    <div className="border-t border-border/60">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2">
        <span className="shrink-0 font-mono text-[11.5px] font-semibold text-primary">
          {celda.clasificador}
        </span>
        <span className="min-w-[160px] flex-1 text-[12px]">
          {celda.clasificador_nombre ?? (celda.clasificador === '(sin clasificador)' ? 'Sin clasificador cruzable' : '—')}
        </span>
        <span className="w-28 shrink-0 text-right font-mono text-[11.5px] tabular-nums">
          {celda.mef ? formatearMoneda(devCelda) : '—'}
        </span>
        <span className="w-12 shrink-0 text-right font-mono text-[11px] text-muted-foreground">
          {pctCelda != null ? `${pctCelda.toFixed(0)}%` : ''}
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5 px-3 pb-2.5 pl-9">
        {celda.pedidos.map((p) => (
          <ChipPedido
            key={`${p.tipo_bien}-${p.tipo_pedido}-${p.nro_pedido}`}
            nroPedido={p.nro_pedido}
            tipoBien={p.tipo_bien}
            tipoPedido={p.tipo_pedido ?? ''}
            devengado={p.devengado_estimado}
            atribucion={p.atribucion}
          />
        ))}
      </div>
    </div>
  );
}

function ChipPedido({
  nroPedido,
  tipoBien,
  tipoPedido,
  devengado,
  atribucion,
}: {
  nroPedido: number;
  tipoBien: string;
  tipoPedido: string;
  devengado: number | null;
  atribucion: 'directo' | 'estimado' | null;
}) {
  const { abrir } = useModales();
  return (
    <button
      type="button"
      onClick={() => abrir({ tipo: 'pedido', nroPedido, tipoBien, tipoPedido })}
      className="inline-flex items-center gap-1.5 rounded-full border border-border bg-superficie-alt-2 px-2.5 py-1 text-[11px] hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span className="font-mono font-semibold">{nroPedido}</span>
      {devengado != null ? (
        <>
          <span className="font-mono text-muted-foreground">{formatearMoneda(devengado, true)}</span>
          <span
            className={cn(
              'rounded px-1 py-px text-[9px] font-semibold uppercase',
              atribucion === 'directo'
                ? 'bg-secondary/20 text-secondary-foreground'
                : 'bg-accent/20 text-accent-foreground',
            )}
          >
            {atribucion === 'directo' ? 'directo' : 'est.'}
          </span>
        </>
      ) : null}
    </button>
  );
}
