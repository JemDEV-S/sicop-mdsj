// Panel "Ejecución MEF por meta": el número honesto de gestión presupuestal.
// A diferencia de la tabla dinámica (que suma monto SIGA por pedido), aquí el
// dinero es el del SIAF, 1× por meta: PIM (ancla), comprometido y devengado
// reales, con el % de avance y el semáforo temporal (esperado vs real al mes
// de corte). El PIM es la referencia sin la cual el devengado "flota".
//
// Regla: SIGA no maneja presupuesto — las cifras SIEMPRE salen del MEF/SIAF.

import { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { formatearNumero } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import type { MetaReporte } from '../../reporte-types';
import type { CentroCostoLabelFn } from './tipos';
import { SemaforoChip } from './Semaforo';

interface FilaMeta {
  sec_func: number;
  nombre_meta: string | null;
  centros_costo: string[];
  pim: number;
  comprometido: number;
  devengado: number;
  pct: number | null;
  semaforo: string;
  semaforo_ctx: MetaReporte['mef']['semaforo_ctx'];
}

/** Deriva las filas de meta visibles y sus totales MEF (1× por meta). */
function useFilasMeta(metas: MetaReporte[], visibles: Set<number>) {
  return useMemo(() => {
    const filas: FilaMeta[] = [];
    let pim = 0;
    let comprometido = 0;
    let devengado = 0;
    for (const m of metas) {
      if (!visibles.has(m.sec_func)) continue;
      filas.push({
        sec_func: m.sec_func,
        nombre_meta: m.nombre_meta,
        centros_costo: m.centros_costo,
        pim: m.mef.pim,
        comprometido: m.mef.comprometido,
        devengado: m.mef.devengado,
        pct: m.mef.porcentaje_devengado,
        semaforo: m.mef.semaforo,
        semaforo_ctx: m.mef.semaforo_ctx,
      });
      pim += m.mef.pim;
      comprometido += m.mef.comprometido;
      devengado += m.mef.devengado;
    }
    // De mayor a menor PIM: las metas grandes primero (donde está el dinero).
    filas.sort((a, b) => b.pim - a.pim);
    const pct = pim > 0 ? Math.round((devengado / pim) * 10000) / 100 : null;
    return { filas, totales: { pim, comprometido, devengado, pct } };
  }, [metas, visibles]);
}

export function EjecucionMef({
  metas,
  visibles,
  avanceEsperado,
  mesCorte,
  ccLabel,
}: {
  metas: MetaReporte[];
  visibles: Set<number>;
  avanceEsperado: number;
  mesCorte: number;
  ccLabel: CentroCostoLabelFn;
}) {
  const [abierto, setAbierto] = useState(false);
  const { filas, totales } = useFilasMeta(metas, visibles);

  if (filas.length === 0) return null;

  return (
    <div className="overflow-hidden rounded-md border border-border bg-card">
      {/* Cabecera-resumen: siempre visible, con el % y el ancla de PIM. */}
      <button
        type="button"
        onClick={() => setAbierto((v) => !v)}
        aria-expanded={abierto}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
      >
        {abierto ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
        )}
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-foreground">Ejecución MEF por meta</p>
          <p className="text-xs text-muted-foreground">
            {filas.length} meta{filas.length === 1 ? '' : 's'} · devengado real del SIAF, contado una
            sola vez por meta. Avance esperado {avanceEsperado}% al mes {mesCorte}.
          </p>
        </div>
        <BarraAvance
          pct={totales.pct}
          esperado={avanceEsperado}
          devengado={totales.devengado}
          pim={totales.pim}
        />
      </button>

      {abierto ? (
        <div className="overflow-x-auto border-t border-border">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-[10.5px] uppercase tracking-wide text-muted-foreground">
                <th className="px-3 py-2 text-left font-semibold">Meta</th>
                <th className="px-3 py-2 text-right font-semibold">PIM (S/)</th>
                <th className="px-3 py-2 text-right font-semibold">Comprometido (S/)</th>
                <th className="px-3 py-2 text-right font-semibold">Devengado (S/)</th>
                <th className="px-3 py-2 text-right font-semibold">% Dev.</th>
                <th className="px-3 py-2 text-left font-semibold">Avance</th>
              </tr>
            </thead>
            <tbody>
              {filas.map((f) => (
                <FilaMetaRow key={f.sec_func} fila={f} ccLabel={ccLabel} />
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-primary bg-primary/10 font-semibold">
                <td className="px-3 py-2 text-left">
                  Total MEF · {filas.length} meta{filas.length === 1 ? '' : 's'}
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">
                  {formatearNumero(totales.pim)}
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">
                  {formatearNumero(totales.comprometido)}
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">
                  {formatearNumero(totales.devengado)}
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">
                  {totales.pct != null ? `${formatearNumero(totales.pct, 1)}%` : '—'}
                </td>
                <td className="px-3 py-2 text-left text-xs font-normal text-muted-foreground">
                  esperado {avanceEsperado}%
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      ) : null}
    </div>
  );
}

function FilaMetaRow({ fila, ccLabel }: { fila: FilaMeta; ccLabel: CentroCostoLabelFn }) {
  const siglas = fila.centros_costo.map((c) => ccLabel(c).sigla).join(', ');
  return (
    <tr className="border-b border-border/60 hover:bg-muted/30">
      <td className="px-3 py-2">
        <div className="font-mono text-[13px] text-foreground">Meta {fila.sec_func}</div>
        {fila.nombre_meta ? (
          <div className="max-w-[280px] truncate text-xs text-muted-foreground" title={fila.nombre_meta}>
            {fila.nombre_meta}
          </div>
        ) : null}
        {siglas ? (
          <div className="truncate text-[11px] text-muted-foreground/80" title={siglas}>
            {siglas}
          </div>
        ) : null}
      </td>
      <td className="px-3 py-2 text-right font-mono tabular-nums text-[13px]">
        {fila.pim > 0 ? formatearNumero(fila.pim) : <span className="text-muted-foreground">—</span>}
      </td>
      <td className="px-3 py-2 text-right font-mono tabular-nums text-[13px] text-muted-foreground">
        {formatearNumero(fila.comprometido)}
      </td>
      <td className="px-3 py-2 text-right font-mono tabular-nums text-[13px]">
        {formatearNumero(fila.devengado)}
      </td>
      <td className="px-3 py-2 text-right font-mono tabular-nums text-[13px]">
        {fila.pct != null ? `${formatearNumero(fila.pct, 1)}%` : '—'}
      </td>
      <td className="px-3 py-2">
        <SemaforoChip color={fila.semaforo} ctx={fila.semaforo_ctx} />
      </td>
    </tr>
  );
}

/**
 * Barra de avance compacta: llena hasta el % devengado y marca con una línea
 * dónde debería ir (esperado). El color de la barra sigue el semáforo temporal.
 */
function BarraAvance({
  pct,
  esperado,
  devengado,
  pim,
}: {
  pct: number | null;
  esperado: number;
  devengado: number;
  pim: number;
}) {
  if (pct == null) {
    return (
      <span className="shrink-0 text-xs text-muted-foreground">
        Sin PIM para calcular avance
      </span>
    );
  }
  const real = Math.min(100, Math.max(0, pct));
  const meta = Math.min(100, Math.max(0, esperado));
  // Color según rezago: al día = ok, poco atraso = alerta, mucho = crítico.
  const rezago = esperado - pct;
  const barra =
    rezago <= 0 ? 'bg-semaforo-ok' : rezago <= 10 ? 'bg-semaforo-alerta' : 'bg-semaforo-critico';

  return (
    <div className="hidden shrink-0 sm:block sm:w-56">
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <span className="font-mono text-sm font-semibold tabular-nums text-foreground">
          {formatearNumero(pct, 1)}%
        </span>
        <span className="text-[11px] text-muted-foreground">
          S/ {formatearNumero(devengado, 0)} / {formatearNumero(pim, 0)}
        </span>
      </div>
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
        <div className={cn('h-full rounded-full', barra)} style={{ width: `${real}%` }} />
        {/* Marca del avance esperado. */}
        <span
          className="absolute top-0 h-full w-0.5 bg-foreground/70"
          style={{ left: `${meta}%` }}
          aria-hidden="true"
          title={`Avance esperado ${esperado}%`}
        />
      </div>
    </div>
  );
}
