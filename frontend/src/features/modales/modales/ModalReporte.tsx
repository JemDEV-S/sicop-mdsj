// Modal · Reporte por meta. Datos reales de useReportePipeline (una meta, o el
// ámbito completo si secFunc es null). Estructura de la plantilla v2: cards de
// ejecución, distribución por macrofase (dona), ejecución por clasificador
// (doble barra PIM/devengado), embudo de fases, y la lista de requerimientos.

import { useMemo } from 'react';
import { formatearMoneda, formatearNumero } from '@/lib/formatters';
import { useReportePipeline } from '@/features/pipeline/api';
import type { MetaReporte, PedidoReporte } from '@/features/pipeline/reporte-types';
import type { Macrofase } from '@/features/dashboard/types';
import { EstadoChip } from '@/features/panel/ui/primitivas';
import { tonoDeColor, ETIQUETA_SEMAFORO } from '@/features/panel/lib/semaforo';
import { LABEL_MACROFASE, MACROFASES } from '@/features/pipeline/secciones/reporte/constantes';
import { useModales, type EntradaModal } from '../ModalesContext';
import { CargandoModal, ErrorModal } from '../EstadoModal';
import { ModalBloque, ModalHead } from '../ui';
import { Dona, type SegmentoDona } from '../componentes/Dona';

type Entrada = Extract<EntradaModal, { tipo: 'reporte' }>;

const COLOR_MACRO: Record<Macrofase, string> = {
  solicitud: 'var(--chart-5)',
  programacion: 'var(--chart-2)',
  certificacion: 'var(--chart-3)',
  contratacion: 'var(--chart-1)',
  ejecucion: 'var(--secondary)',
  cierre: 'var(--chart-4)',
};

export function ModalReporte({ entrada }: { entrada: Entrada }) {
  const { secFunc } = entrada;
  const { data, isLoading, isError, error, refetch } = useReportePipeline();
  const { abrir } = useModales();

  const metas = useMemo(() => {
    if (!data) return [];
    return secFunc != null ? data.metas.filter((m) => m.sec_func === secFunc) : data.metas;
  }, [data, secFunc]);

  if (isLoading) return <CargandoModal texto="Cargando reporte de ejecución…" />;
  if (isError || !data) {
    return (
      <ErrorModal
        texto={error instanceof Error ? error.message : 'No se pudo cargar el reporte. Puede ser un corte temporal del SIGA.'}
        onReintentar={() => refetch()}
      />
    );
  }

  const totales = agregar(metas);
  const meta = secFunc != null ? metas[0] : null;
  const titulo = meta ? `${meta.meta ?? meta.sec_func} — ${meta.nombre_meta ?? 'sin nombre'}` : 'Todo el ámbito visible';
  const sub = `Corte al mes ${data.mes_corte} · dinero SIAF (1× por meta), trámite SIGA por pedido.`;
  const pedidos = metas.flatMap((m) => m.celdas.flatMap((c) => c.pedidos));

  // Distribución por macrofase (dona) — agrupación real y honesta.
  const donaSegmentos: SegmentoDona[] = MACROFASES.map((mf) => ({
    label: mf.label,
    n: pedidos.filter((p) => p.macrofase === mf.macrofase).length,
    color: COLOR_MACRO[mf.macrofase],
  })).filter((s) => s.n > 0);

  // Ejecución por clasificador (doble barra PIM/devengado).
  const celdas = metas
    .flatMap((m) => m.celdas)
    .filter((c) => c.mef != null)
    .sort((a, b) => (b.mef?.devengado ?? 0) - (a.mef?.devengado ?? 0))
    .slice(0, 6);

  // Embudo de fases (PIM → comprometido → devengado; lo que expone el reporte).
  const embudo = [
    { label: 'PIM', valor: totales.pim, barra: 'bg-primary' },
    { label: 'Comprometido', valor: totales.comprometido, barra: 'bg-primary/70' },
    { label: 'Devengado', valor: totales.devengado, barra: 'bg-secondary' },
  ];

  return (
    <div className="flex flex-col gap-4">
      <ModalHead overline="Reporte de ejecución" titulo={titulo} descripcion={sub} />

      {/* Cards */}
      <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
        <Card label="Devengado" valor={formatearMoneda(totales.devengado, true)} valorClass="text-primary" ayuda={`${totales.pct != null ? formatearNumero(totales.pct, 1) : '—'}% del PIM`} destacada />
        <Card label="PIM" valor={formatearMoneda(totales.pim, true)} ayuda="Techo vigente" />
        <Card label="Saldo por ejecutar" valor={formatearMoneda(totales.pim - totales.devengado, true)} valorClass="text-destructive" ayuda="PIM − devengado" />
        <Card label="Requerimientos" valor={String(pedidos.length)} ayuda={`${formatearMoneda(sumaSiga(pedidos), true)} solicitado`} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Dona por macrofase */}
        <ModalBloque titulo="Requerimientos por macrofase">
          {donaSegmentos.length > 0 ? (
            <Dona segmentos={donaSegmentos} total={pedidos.length} />
          ) : (
            <p className="text-[12px] text-muted-foreground">Sin requerimientos en el ámbito.</p>
          )}
        </ModalBloque>

        {/* Embudo de fases */}
        <ModalBloque titulo="Embudo de fases SIAF" nota="Tres fases del snapshot MEF por meta.">
          <div className="flex flex-col gap-2">
            {embudo.map((f) => {
              const w = totales.pim > 0 ? Math.round((f.valor / totales.pim) * 100) : 0;
              return (
                <div key={f.label} className="flex items-center gap-2.5">
                  <span className="w-24 shrink-0 text-[11.5px] font-semibold text-foreground">{f.label}</span>
                  <div className="h-5 min-w-0 flex-1 overflow-hidden rounded bg-muted">
                    <div className={`h-full rounded ${f.barra}`} style={{ width: `${w}%` }} />
                  </div>
                  <span className="w-24 shrink-0 text-right font-mono text-[11px] tabular-nums text-foreground">
                    {formatearNumero(f.valor, 0)}
                  </span>
                  <span className="w-10 shrink-0 text-right font-mono text-[10.5px] text-muted-foreground">{w}%</span>
                </div>
              );
            })}
          </div>
        </ModalBloque>
      </div>

      {/* Ejecución por clasificador */}
      <ModalBloque titulo="Ejecución por clasificador (SIAF)" nota="Barra clara: PIM de la celda. Barra sólida: devengado real de la celda.">
        {celdas.length === 0 ? (
          <p className="text-[12px] text-muted-foreground">Sin celdas de clasificador con cruce MEF en el ámbito.</p>
        ) : (
          <div className="flex flex-col gap-2.5">
            {celdas.map((c) => {
              const pim = c.mef?.pim ?? 0;
              const dev = c.mef?.devengado ?? 0;
              const pct = pim > 0 ? (dev / pim) * 100 : 0;
              return (
                <div key={c.clasificador} className="flex flex-col gap-1">
                  <div className="flex justify-between gap-2 text-[11.5px]">
                    <span className="truncate">
                      <span className="font-mono text-primary">{c.clasificador}</span> {c.clasificador_nombre ?? ''}
                    </span>
                    <span className="shrink-0 font-mono text-muted-foreground">{formatearNumero(pct, 1)}%</span>
                  </div>
                  <div className="relative h-3.5 overflow-hidden rounded bg-muted">
                    <div className="absolute inset-y-0 left-0 w-full bg-primary/25" />
                    <div className="absolute inset-y-0 left-0 bg-primary" style={{ width: `${Math.min(100, pct)}%` }} />
                  </div>
                  <span className="font-mono text-[10.5px] text-muted-foreground/80">
                    dev. {formatearMoneda(dev, true)} · pim {formatearMoneda(pim, true)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </ModalBloque>

      {/* Lista de requerimientos */}
      <section className="overflow-hidden rounded-lg border border-border">
        <div className="flex flex-wrap items-center gap-2 border-b border-border bg-superficie-alt-2 px-4 py-2.5">
          <h3 className="text-[13px] font-semibold text-foreground">Requerimientos del ámbito</h3>
          <span className="text-[11px] text-muted-foreground">Clic en una fila abre la ficha completa del pedido.</span>
        </div>
        {pedidos.length === 0 ? (
          <p className="px-4 py-6 text-center text-[12px] text-muted-foreground">Sin requerimientos en el ámbito.</p>
        ) : (
          <div className="max-h-72 overflow-y-auto">
            <table className="w-full min-w-[640px] border-collapse text-[12px]">
              <thead className="sticky top-0 bg-superficie-alt">
                <tr className="text-left text-muted-foreground">
                  <th className="px-3 py-2 font-semibold">Código</th>
                  <th className="px-3 py-2 font-semibold">Detalle</th>
                  <th className="px-3 py-2 font-semibold">Recorrido</th>
                  <th className="px-3 py-2 text-right font-semibold">Monto SIGA</th>
                </tr>
              </thead>
              <tbody>
                {pedidos.map((p) => (
                  <tr
                    key={`${p.nro_pedido}-${p.tipo_bien}`}
                    onClick={() => abrir({ tipo: 'pedido', nroPedido: p.nro_pedido, tipoBien: p.tipo_bien, tipoPedido: p.tipo_pedido ?? '' })}
                    className="cursor-pointer border-b border-border/50 hover:bg-muted/40"
                  >
                    <td className="px-3 py-2 font-mono font-semibold text-primary">{p.nro_pedido}</td>
                    <td className="max-w-[280px] px-3 py-2"><span className="block truncate">{p.motivo ?? p.etapa_label}</span></td>
                    <td className="px-3 py-2 text-muted-foreground">{p.etapa_label} · {LABEL_MACROFASE[p.macrofase]}</td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums">{formatearMoneda(p.monto_siga, true)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {meta ? (
        <div className="flex items-center gap-2">
          <EstadoChip tono={tonoDeColor(meta.mef.semaforo)} tamano="sm">
            {ETIQUETA_SEMAFORO[tonoDeColor(meta.mef.semaforo)]}
          </EstadoChip>
          <span className="text-[11px] text-muted-foreground">
            Avance esperado {data.avance_esperado}% al mes {data.mes_corte}.
          </span>
        </div>
      ) : null}
    </div>
  );
}

function Card({
  label,
  valor,
  ayuda,
  valorClass,
  destacada,
}: {
  label: string;
  valor: string;
  ayuda: string;
  valorClass?: string;
  destacada?: boolean;
}) {
  return (
    <div className={`flex flex-col gap-1 rounded-lg border border-border px-3 py-2.5 ${destacada ? 'bg-superficie-alt-2' : 'bg-card'}`}>
      <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className={`font-mono text-lg font-semibold tabular-nums text-foreground ${valorClass ?? ''}`}>{valor}</span>
      <span className="text-[10.5px] text-muted-foreground">{ayuda}</span>
    </div>
  );
}

function agregar(metas: MetaReporte[]) {
  let pim = 0;
  let comprometido = 0;
  let devengado = 0;
  for (const m of metas) {
    pim += m.mef.pim;
    comprometido += m.mef.comprometido;
    devengado += m.mef.devengado;
  }
  const pct = pim > 0 ? Math.round((devengado / pim) * 10000) / 100 : null;
  return { pim, comprometido, devengado, pct };
}

function sumaSiga(pedidos: PedidoReporte[]): number {
  return pedidos.reduce((a, p) => a + (p.monto_siga || 0), 0);
}
