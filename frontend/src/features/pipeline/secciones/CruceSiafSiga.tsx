// Cruce SIAF ↔ SIGA (Panel Interno v2 · vista 3).
//
// Lado a lado: el dinero oficial del MEF/SIAF (1× por meta) y el trámite
// operativo del SIGA (clasificadores y pedidos con sus llaves de cruce
// pedido/orden/EXP_SIAF). Se rastrea por meta o por expediente SIAF, usando el
// MISMO reporte que las otras vistas (useReportePipeline) — sin endpoint nuevo.
//
// Regla de negocio: la llave de cruce SIAF↔SIGA es la meta (SEC_FUNC) + el
// clasificador de gasto; el EXP_SIAF es llave secundaria por pedido. El dinero
// oficial es del MEF; el monto SIGA por pedido es trámite (no sumable).
// Ver memoria [[project-cruce-por-clasificador]] y [[project-cruce-mef-siga]].

import { useMemo, useState } from 'react';
import { GitBranch, Loader2, Search } from 'lucide-react';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import { formatearMoneda, formatearNumero } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import { useReportePipeline } from '../api';
import type { CeldaClasificador, MetaReporte, PedidoReporte, ReporteResponse } from '../reporte-types';
import { SemaforoChip } from './reporte/Semaforo';
import { useModales } from '@/features/modales/ModalesContext';

interface CruceProps {
  /** Meta preseleccionada (sec_func) al entrar desde otra vista. */
  metaInicial?: number | null;
  /** Salta a "Análisis por meta" con la meta seleccionada. */
  onAbrirMeta: (secFunc: number) => void;
}

export function CruceSiafSiga({ metaInicial, onAbrirMeta }: CruceProps) {
  const { data, isLoading, isError, error, refetch } = useReportePipeline();
  const [expBusqueda, setExpBusqueda] = useState('');
  const [metaSelManual, setMetaSelManual] = useState<number | null>(null);

  // La meta activa: la buscada por EXP_SIAF, la elegida a mano, la que vino de
  // otra vista, o la primera con PIM.
  const metaActiva = useMemo(() => {
    if (!data) return null;
    return resolverMeta(data, expBusqueda, metaSelManual ?? metaInicial ?? null);
  }, [data, expBusqueda, metaSelManual, metaInicial]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center rounded-md border border-border bg-card py-16 text-muted-foreground">
        <Loader2 className="mb-3 h-8 w-8 animate-spin text-primary" aria-hidden="true" />
        <p className="text-sm">Cargando cruce SIAF ↔ SIGA…</p>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <ErrorState
        titulo="No pudimos cargar el cruce"
        descripcion={
          error instanceof Error
            ? error.message
            : 'Puede ser un corte temporal del SIGA. Reintenta en unos segundos.'
        }
        onReintentar={() => refetch()}
      />
    );
  }

  if (data.metas.length === 0) {
    return (
      <EmptyState
        icono={GitBranch}
        titulo="Sin metas para cruzar"
        descripcion="No hay metas para el año y unidad seleccionados. Cambia el año o el centro de costo en la barra superior."
      />
    );
  }

  const expMatch = expBusqueda.trim()
    ? encontrarPorExp(data, expBusqueda.trim())
    : null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold tracking-tight text-foreground">Cruce SIAF ↔ SIGA</h2>
        <p className="max-w-[80ch] text-sm text-muted-foreground">
          Lado a lado, el dinero oficial del MEF y el trámite operativo del SIGA. La llave de cruce
          es la meta más el clasificador de gasto; el expediente SIAF cruza por pedido.
        </p>
      </div>

      {/* ── Rastreador ── */}
      <div className="flex flex-col gap-3 rounded-md border border-border bg-card px-4 py-4">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex flex-col gap-1 text-[11px] font-medium text-muted-foreground">
            Meta
            <select
              value={metaActiva?.sec_func ?? ''}
              onChange={(e) => {
                setMetaSelManual(Number(e.target.value));
                setExpBusqueda('');
              }}
              className="min-w-[280px] rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {data.metas.map((m) => (
                <option key={m.sec_func} value={m.sec_func}>
                  {(m.meta ?? `Meta ${m.sec_func}`) + ' — ' + (m.nombre_meta ?? 'sin nombre')}
                </option>
              ))}
            </select>
          </label>
          <div className="flex flex-1 flex-col gap-1 text-[11px] font-medium text-muted-foreground">
            Buscar por expediente SIAF
            <div className="flex min-w-[220px] items-center gap-2 rounded-md border border-border bg-card px-3 py-2">
              <Search className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <input
                value={expBusqueda}
                onChange={(e) => setExpBusqueda(e.target.value)}
                placeholder="Ej. 6113"
                inputMode="numeric"
                className="min-w-0 flex-1 bg-transparent font-mono text-sm text-foreground outline-none"
              />
            </div>
          </div>
        </div>
        {expBusqueda.trim() ? (
          <p className="text-[11.5px] text-muted-foreground">
            {expMatch
              ? `Expediente ${expBusqueda.trim()} hallado en el pedido ${expMatch.pedido.nro_pedido}, meta ${expMatch.meta.meta ?? expMatch.meta.sec_func}.`
              : `No se encontró un pedido con expediente SIAF que contenga "${expBusqueda.trim()}" en el ámbito visible.`}
          </p>
        ) : null}

        {metaActiva ? (
          <CadenaChips meta={metaActiva} pedidoExp={expMatch?.pedido ?? null} onAbrirMeta={onAbrirMeta} />
        ) : null}
      </div>

      {metaActiva ? (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <PanelMef meta={metaActiva} mesCorte={data.mes_corte} avanceEsperado={data.avance_esperado} />
          <PanelSiga meta={metaActiva} pedidoResaltado={expMatch?.pedido ?? null} onAbrirMeta={onAbrirMeta} />
        </div>
      ) : null}
    </div>
  );
}

// ─── Cadena de identificadores encontrados ───────────────────────────────

function CadenaChips({
  meta,
  pedidoExp,
  onAbrirMeta,
}: {
  meta: MetaReporte;
  pedidoExp: PedidoReporte | null;
  onAbrirMeta: (secFunc: number) => void;
}) {
  const ids = pedidoExp?.identificadores ?? null;
  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">
      <span className="text-[11px] text-muted-foreground">Cadena:</span>
      <Chip tipo="Meta" valor={meta.meta ?? String(meta.sec_func)} onClick={() => onAbrirMeta(meta.sec_func)} />
      {ids?.pedido ? <Chip tipo="Requerim." valor={ids.pedido} /> : null}
      {ids?.orden ? <Chip tipo="Orden" valor={ids.orden} /> : null}
      {ids?.exp_siaf ? <Chip tipo="Exp. SIAF" valor={String(ids.exp_siaf)} /> : null}
    </div>
  );
}

function Chip({ tipo, valor, onClick }: { tipo: string; valor: string; onClick?: () => void }) {
  const contenido = (
    <>
      <span className="text-[9.5px] uppercase tracking-wide text-muted-foreground">{tipo}</span>
      <span className="font-mono text-[12px] font-semibold text-primary">{valor}</span>
    </>
  );
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-2.5 py-1 transition-colors hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {contenido}
      </button>
    );
  }
  return (
    <span className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-2.5 py-1">
      {contenido}
    </span>
  );
}

// ─── Panel MEF (oficial) ─────────────────────────────────────────────────

function PanelMef({
  meta,
  mesCorte,
  avanceEsperado,
}: {
  meta: MetaReporte;
  mesCorte: number;
  avanceEsperado: number;
}) {
  const { pim, comprometido, devengado, porcentaje_devengado: pct } = meta.mef;
  const filas: { label: string; valor: string; fuerte?: boolean }[] = [
    { label: 'PIM (techo vigente)', valor: formatearMoneda(pim), fuerte: true },
    { label: 'Comprometido', valor: formatearMoneda(comprometido) },
    { label: 'Devengado', valor: formatearMoneda(devengado), fuerte: true },
    { label: 'Saldo por ejecutar', valor: formatearMoneda(pim - devengado) },
  ];
  const fases = [
    { label: 'PIM', valor: pim, barra: 'bg-primary' },
    { label: 'Comprometido', valor: comprometido, barra: 'bg-primary/70' },
    { label: 'Devengado', valor: devengado, barra: 'bg-secondary' },
  ];

  return (
    <section className="flex flex-col gap-3 rounded-md border border-border border-t-4 border-t-primary bg-card px-4 py-4">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold text-foreground">Dinero oficial — SIAF / MEF</h3>
        <span className="rounded border border-primary/30 bg-primary/10 px-1.5 py-px font-mono text-[9.5px] text-primary">
          OFICIAL
        </span>
      </div>
      <div className="flex flex-col">
        {filas.map((f) => (
          <div key={f.label} className="flex items-center justify-between gap-3 border-b border-border/60 py-1.5">
            <span className="text-[12px] text-muted-foreground">{f.label}</span>
            <span
              className={cn(
                'font-mono text-[12.5px] tabular-nums',
                f.fuerte ? 'font-semibold text-foreground' : 'text-muted-foreground',
              )}
            >
              {f.valor}
            </span>
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-2 pt-1">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Fases del snapshot
        </span>
        {fases.map((f) => {
          const w = pim > 0 ? Math.round((f.valor / pim) * 100) : 0;
          return (
            <div key={f.label} className="flex items-center gap-3">
              <span className="w-24 shrink-0 text-[11px] text-foreground">{f.label}</span>
              <div className="h-3.5 min-w-0 flex-1 overflow-hidden rounded bg-muted">
                <div className={cn('h-full rounded', f.barra)} style={{ width: `${w}%` }} />
              </div>
              <span className="w-24 shrink-0 text-right font-mono text-[11px] tabular-nums text-foreground">
                {formatearNumero(f.valor, 0)}
              </span>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-2 pt-1 text-[11px] text-muted-foreground">
        <span>
          Avance {pct != null ? `${formatearNumero(pct, 1)}%` : '—'} · esperado {avanceEsperado}% al mes {mesCorte}
        </span>
        <SemaforoChip color={meta.mef.semaforo} ctx={meta.mef.semaforo_ctx} tamano="xs" />
      </div>
    </section>
  );
}

// ─── Panel SIGA (operativo) ──────────────────────────────────────────────

function PanelSiga({
  meta,
  pedidoResaltado,
  onAbrirMeta,
}: {
  meta: MetaReporte;
  pedidoResaltado: PedidoReporte | null;
  onAbrirMeta: (secFunc: number) => void;
}) {
  return (
    <section className="flex flex-col gap-3 rounded-md border border-border border-t-4 border-t-secondary bg-card px-4 py-4">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold text-foreground">Trámite operativo — SIGA</h3>
        <span className="rounded border border-secondary/30 bg-secondary/10 px-1.5 py-px font-mono text-[9.5px] text-secondary-foreground">
          OPERATIVO
        </span>
      </div>
      <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-muted/30 px-3 py-2 text-[11.5px]">
        <span className="text-muted-foreground">
          {meta.n_pedidos} pedido{meta.n_pedidos === 1 ? '' : 's'} · {meta.n_celdas} clasificador
          {meta.n_celdas === 1 ? '' : 'es'} ({meta.n_celdas_directas} directo
          {meta.n_celdas_directas === 1 ? '' : 's'})
        </span>
        <button
          type="button"
          onClick={() => onAbrirMeta(meta.sec_func)}
          className="shrink-0 font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Abrir análisis por meta →
        </button>
      </div>
      {meta.celdas.length === 0 ? (
        <p className="rounded border border-dashed border-border px-3 py-6 text-center text-sm text-muted-foreground">
          Esta meta no tiene clasificadores con pedidos en el ámbito visible.
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {meta.celdas.map((c) => (
            <CeldaSiga key={c.clasificador} celda={c} pedidoResaltado={pedidoResaltado} />
          ))}
        </div>
      )}
      <p className="text-[11px] leading-relaxed text-muted-foreground">
        El monto SIGA es el solicitado por pedido (trámite, no presupuesto). El dinero oficial de la
        meta está en el panel de la izquierda, contado una sola vez.
      </p>
    </section>
  );
}

function CeldaSiga({
  celda,
  pedidoResaltado,
}: {
  celda: CeldaClasificador;
  pedidoResaltado: PedidoReporte | null;
}) {
  const { abrir } = useModales();
  return (
    <div className="overflow-hidden rounded-md border border-border">
      <div className="flex flex-wrap items-center gap-2 border-b border-border bg-muted/40 px-3 py-2">
        <span className="font-mono text-[11.5px] font-semibold text-primary">{celda.clasificador}</span>
        <span className="min-w-0 flex-1 truncate text-[12px] text-foreground">
          {celda.clasificador_nombre ?? 'Sin nombre de clasificador'}
        </span>
        <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
          {celda.n_pedidos} ped. · SIGA {formatearMoneda(celda.monto_siga, true)}
        </span>
      </div>
      <div className="flex flex-col divide-y divide-border/60">
        {celda.pedidos.map((p) => {
          const resaltado =
            pedidoResaltado != null &&
            p.nro_pedido === pedidoResaltado.nro_pedido &&
            p.tipo_bien === pedidoResaltado.tipo_bien;
          const ids = p.identificadores;
          const abrirPedido = () =>
            abrir({
              tipo: 'pedido',
              nroPedido: p.nro_pedido,
              tipoBien: p.tipo_bien,
              tipoPedido: p.tipo_pedido ?? '',
            });
          return (
            <button
              type="button"
              key={`${p.nro_pedido}-${p.tipo_bien}`}
              onClick={abrirPedido}
              className={cn(
                'flex w-full flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-left text-[11.5px] transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
                resaltado && 'bg-primary/5',
              )}
            >
              <span className="font-mono font-semibold text-foreground">{p.nro_pedido}</span>
              <span className="rounded border border-border px-1 py-px text-[9.5px] text-muted-foreground">
                {p.tipo_bien === 'B' ? 'Bien' : 'Servicio'}
              </span>
              <span className="min-w-0 flex-1 truncate text-muted-foreground" title={p.motivo ?? undefined}>
                {p.motivo ?? p.etapa_label}
              </span>
              {ids?.orden ? (
                <span className="font-mono text-[10.5px] text-muted-foreground">O: {ids.orden}</span>
              ) : null}
              {ids?.exp_siaf ? (
                <span
                  role="link"
                  tabIndex={0}
                  onClick={(e) => {
                    e.stopPropagation();
                    abrir({
                      tipo: 'siaf',
                      nroPedido: p.nro_pedido,
                      tipoBien: p.tipo_bien,
                      tipoPedido: p.tipo_pedido ?? '',
                      expSiaf: ids.exp_siaf!,
                    });
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      e.stopPropagation();
                      abrir({
                        tipo: 'siaf',
                        nroPedido: p.nro_pedido,
                        tipoBien: p.tipo_bien,
                        tipoPedido: p.tipo_pedido ?? '',
                        expSiaf: ids.exp_siaf!,
                      });
                    }
                  }}
                  className="cursor-pointer font-mono text-[10.5px] text-primary underline-offset-2 hover:underline"
                >
                  EXP {ids.exp_siaf}
                </span>
              ) : (
                <span className="text-[10.5px] text-muted-foreground/70">sin exp.</span>
              )}
              <span className="font-mono tabular-nums text-foreground">
                {formatearMoneda(p.monto_siga, true)}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Resolución de la meta activa ────────────────────────────────────────

function resolverMeta(
  data: ReporteResponse,
  expBusqueda: string,
  metaSel: number | null,
): MetaReporte | null {
  const exp = expBusqueda.trim();
  if (exp) {
    const hit = encontrarPorExp(data, exp);
    if (hit) return hit.meta;
  }
  if (metaSel != null) {
    const m = data.metas.find((x) => x.sec_func === metaSel);
    if (m) return m;
  }
  return data.metas.find((m) => m.mef.pim > 0) ?? data.metas[0] ?? null;
}

function encontrarPorExp(
  data: ReporteResponse,
  exp: string,
): { meta: MetaReporte; pedido: PedidoReporte } | null {
  for (const meta of data.metas) {
    for (const celda of meta.celdas) {
      for (const pedido of celda.pedidos) {
        const e = pedido.identificadores?.exp_siaf;
        if (e != null && String(e).includes(exp)) return { meta, pedido };
      }
    }
  }
  return null;
}

export default CruceSiafSiga;
