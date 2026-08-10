import { useMemo, useState } from 'react';
import { Download, GitBranch, Loader2 } from 'lucide-react';
import type { Macrofase } from '@/features/dashboard/types';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import { SectionCard } from '@/components/layout/SectionCard';
import { formatearMoneda, formatearNumero } from '@/lib/formatters';
import { useContextoInterno } from '@/store/contexto-interno';
import { descargarReportePipeline, useReportePipeline } from '../api';
import type { ReporteResponse } from '../reporte-types';
import { aplanarPedidos } from './reporte/aplanar';
import { BarraResumen } from './reporte/BarraResumen';
import { EjecucionMef } from './reporte/EjecucionMef';
import { FiltrosAvanzados } from './reporte/FiltrosAvanzados';
import { Leyenda } from './reporte/Leyenda';
import { TablaDinamica } from './reporte/TablaDinamica';
import { agrupar, filtrar, resumenPorMacrofase, totalizar } from './reporte/procesar';
import type {
  CampoAgrupacion,
  CampoOrden,
  CentroCostoLabelFn,
  DireccionOrden,
  FiltrosReporte,
} from './reporte/tipos';
import { FILTROS_DEFAULT } from './reporte/tipos';

export function PipelineReporte() {
  const { data, isLoading, isError, error, refetch } = useReportePipeline();
  const año = useContextoInterno((s) => s.añoActivo);
  const ccActivo = useContextoInterno((s) => s.ccActivo);

  const [filtros, setFiltros] = useState<FiltrosReporte>(FILTROS_DEFAULT);
  const [agrupacion, setAgrupacion] = useState<CampoAgrupacion>('macrofase');
  const [orden, setOrden] = useState<CampoOrden>('monto_siga');
  const [direccion, setDireccion] = useState<DireccionOrden>('desc');

  const [exportando, setExportando] = useState(false);
  const [errorExport, setErrorExport] = useState<string | null>(null);

  // Traductor código → {nombre, sigla} a partir del catálogo del backend.
  const ccLabel = useCentroCostoLabel(data);

  // Aplanado (una fila por pedido). Base de todo el procesamiento.
  const filas = useMemo(() => (data ? aplanarPedidos(data) : []), [data]);

  // Pipeline de la tabla dinámica: filtrar → resumir → agrupar → totalizar.
  const filtradas = useMemo(() => filtrar(filas, filtros), [filas, filtros]);
  const resumen = useMemo(() => resumenPorMacrofase(filtradas), [filtradas]);
  const grupos = useMemo(
    () => agrupar(filtradas, agrupacion, orden, direccion, ccLabel),
    [filtradas, agrupacion, orden, direccion, ccLabel],
  );
  const totalGlobal = useMemo(() => totalizar(filtradas), [filtradas]);

  // Total MEF honesto (1× por meta) para el tile de resumen. No se deriva de las
  // filas (eso inflaría); sale del bloque meta de las metas visibles.
  const totalMef = useMemo(() => totalMefPorMeta(data, filtradas), [data, filtradas]);

  // Conjunto de metas visibles tras el filtro — llave del panel MEF por meta.
  const metasVisibles = useMemo(
    () => new Set(filtradas.map((f) => f.sec_func)),
    [filtradas],
  );

  const exportar = async () => {
    setExportando(true);
    setErrorExport(null);
    try {
      await descargarReportePipeline({ ano: año, centro_costo: ccActivo?.codigo });
    } catch {
      setErrorExport('No se pudo generar el archivo. Verifica tu conexión e intenta de nuevo.');
    } finally {
      setExportando(false);
    }
  };

  const toggleMacrofase = (m: Macrofase) =>
    setFiltros((f) => ({
      ...f,
      macrofases: f.macrofases.includes(m)
        ? f.macrofases.filter((x) => x !== m)
        : [...f.macrofases, m],
    }));

  if (isLoading) {
    return (
      <SectionCard padding="lg">
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <Loader2 className="mb-3 h-8 w-8 animate-spin text-primary" aria-hidden="true" />
          <p className="text-sm">Cargando reporte…</p>
        </div>
      </SectionCard>
    );
  }

  if (isError || !data) {
    return (
      <ErrorState
        titulo="No pudimos cargar el reporte"
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
        titulo="Sin pedidos registrados"
        descripcion="No hay pedidos para el año y unidad seleccionados. Cambia el año o el centro de costo en el topbar."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Frescura data={data} onExportar={exportar} exportando={exportando} />

      {errorExport ? (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {errorExport}
        </div>
      ) : null}

      <BarraResumen resumen={resumen} seleccionadas={filtros.macrofases} onToggle={toggleMacrofase} />

      <EjecucionMef
        metas={data.metas}
        visibles={metasVisibles}
        avanceEsperado={data.avance_esperado}
        mesCorte={data.mes_corte}
        ccLabel={ccLabel}
      />

      <SectionCard padding="sm">
        <FiltrosAvanzados
          filtros={filtros}
          onChange={setFiltros}
          filas={filas}
          ccLabel={ccLabel}
          agrupacion={agrupacion}
          onAgrupacion={setAgrupacion}
          orden={orden}
          direccion={direccion}
          onOrden={setOrden}
          onDireccion={setDireccion}
        />
      </SectionCard>

      <Leyenda />

      <TablaDinamica
        grupos={grupos}
        totalGlobal={totalGlobal}
        ccLabel={ccLabel}
        agrupado={agrupacion !== 'ninguno'}
      />

      <Totales
        pedidos={totalGlobal.n_pedidos}
        metas={totalMef.n_metas}
        siga={totalGlobal.monto_siga}
        pim={totalMef.pim}
        mef={totalMef.devengado}
        pct={totalMef.pct}
      />

      <NotaTotales />
    </div>
  );
}

// ─── Catálogo de CC (código → nombre + sigla) ────────────────────────────

function useCentroCostoLabel(data: ReporteResponse | undefined): CentroCostoLabelFn {
  return useMemo(() => {
    const map = new Map(data?.centros_costo.map((c) => [c.codigo, c]) ?? []);
    return (codigo: string) => {
      const c = map.get(codigo);
      return { nombre: c?.nombre ?? codigo, sigla: c?.sigla ?? codigo };
    };
  }, [data]);
}

/**
 * Totales MEF 1× por meta, restringidos a las metas visibles tras el filtro.
 * Anti-inflado §7: NUNCA se suma el devengado por pedido. El PIM es el ancla sin
 * la cual el devengado "flota"; `pct` es el avance real (devengado / PIM).
 */
function totalMefPorMeta(
  data: ReporteResponse | undefined,
  filtradas: { sec_func: number }[],
): { pim: number; comprometido: number; devengado: number; pct: number | null; n_metas: number } {
  if (!data) return { pim: 0, comprometido: 0, devengado: 0, pct: null, n_metas: 0 };
  const visibles = new Set(filtradas.map((f) => f.sec_func));
  let pim = 0;
  let comprometido = 0;
  let devengado = 0;
  let n = 0;
  for (const m of data.metas) {
    if (!visibles.has(m.sec_func)) continue;
    pim += m.mef.pim;
    comprometido += m.mef.comprometido;
    devengado += m.mef.devengado;
    n += 1;
  }
  const pct = pim > 0 ? Math.round((devengado / pim) * 10000) / 100 : null;
  return { pim, comprometido, devengado, pct, n_metas: n };
}

// ─── Franja de frescura ──────────────────────────────────────────────────

function Frescura({
  data,
  onExportar,
  exportando,
}: {
  data: ReporteResponse;
  onExportar: () => void;
  exportando: boolean;
}) {
  const siga = fechaHora(data.sincronizado_siga);
  const mef = fechaHora(data.sincronizado_mef);
  return (
    <div className="flex flex-col gap-3 rounded-md border border-border bg-card px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full bg-secondary" aria-hidden="true" />
          SIGA — continuo · <span className="font-semibold text-foreground">{siga}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full bg-primary" aria-hidden="true" />
          MEF / SIAF — corte diario · <span className="font-semibold text-foreground">{mef}</span>
        </span>
        <span>
          Corte: mes <span className="font-semibold text-foreground">{data.mes_corte}</span> · avance
          esperado {data.avance_esperado}%
        </span>
      </div>
      <div className="flex flex-col items-start gap-1 lg:items-end">
        <button
          type="button"
          onClick={onExportar}
          disabled={exportando}
          className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
        >
          {exportando ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Download className="h-4 w-4" aria-hidden="true" />
          )}
          {exportando ? 'Generando…' : 'Descargar Excel'}
        </button>
        <span className="text-[11px] text-muted-foreground">
          Incluye todos los pedidos del año y centro de costo, sin los filtros de esta pantalla.
        </span>
      </div>
    </div>
  );
}

// ─── Totales duales + nota ───────────────────────────────────────────────

function Totales({
  pedidos,
  metas,
  siga,
  pim,
  mef,
  pct,
}: {
  pedidos: number;
  metas: number;
  siga: number;
  pim: number;
  mef: number;
  pct: number | null;
}) {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      <div className="rounded-md border border-border border-l-4 border-l-muted-foreground bg-card px-4 py-3">
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Total SIGA — pedidos visibles
        </p>
        <p className="mt-0.5 font-mono text-2xl font-semibold tabular-nums text-foreground">
          {formatearMoneda(siga)}
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {pedidos} pedidos · dinero solicitado por pedido (informativo)
        </p>
      </div>
      <div className="rounded-md border border-border border-l-4 border-l-primary bg-card px-4 py-3">
        <div className="flex items-baseline justify-between gap-2">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            MEF — devengado sobre PIM, por meta
          </p>
          {pct != null ? (
            <span className="shrink-0 rounded-full bg-primary/10 px-2 py-0.5 font-mono text-xs font-semibold tabular-nums text-primary">
              {formatearNumero(pct, 1)}%
            </span>
          ) : null}
        </div>
        <p className="mt-0.5 font-mono text-2xl font-semibold tabular-nums text-foreground">
          {formatearMoneda(mef)}
          <span className="ml-1.5 font-sans text-sm font-normal text-muted-foreground">
            de {formatearMoneda(pim)} PIM
          </span>
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {metas} metas visibles · devengado real del SIAF, único por meta
        </p>
      </div>
    </div>
  );
}

function NotaTotales() {
  return (
    <p className="rounded-md border border-dashed border-border bg-card px-3 py-2.5 text-xs leading-relaxed text-muted-foreground">
      <span className="font-semibold text-foreground">Cómo leer los totales:</span> el total y los
      subtotales suman el <span className="font-semibold">monto SIGA</span> de cada pedido (dinero
      solicitado). El comprometido/devengado MEF por pedido es contexto —{' '}
      <span className="font-semibold">no se suma por pedido</span> porque es un reparto dentro del
      clasificador. El total MEF real es el devengado contado una sola vez por meta.
    </p>
  );
}

function fechaHora(iso: string | null): string {
  if (!iso) return 'sin dato';
  return new Date(iso).toLocaleString('es-PE', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default PipelineReporte;
