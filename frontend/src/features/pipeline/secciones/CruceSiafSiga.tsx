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
import { useDetalleExpedienteSiaf, useReportePipeline } from '../api';
import type { CeldaClasificador, MetaReporte, PedidoReporte, ReporteResponse } from '../reporte-types';
import type { DetalleExpedienteSiaf } from '../types';
import {
  BarrasFasesSiaf,
  CajaTesoreria,
  DocumentosPorFase,
} from '@/features/modales/componentes/DetalleFasesSiaf';
import {
  ordenarFases,
  proveedorDeExpediente,
  selloDeDetalle,
} from '@/features/modales/componentes/detalle-fases-siaf-lib';
import { SemaforoChip } from './reporte/Semaforo';
import { KpiTile, type KpiChip } from '@/features/panel/ui/primitivas';
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
    <CruceContenido
      data={data}
      metaActiva={metaActiva}
      expBusqueda={expBusqueda}
      setExpBusqueda={setExpBusqueda}
      setMetaSelManual={setMetaSelManual}
      expMatch={expMatch}
      onAbrirMeta={onAbrirMeta}
    />
  );
}

// El cuerpo se separa para poder llamar el hook de detalle SIAF (que depende del
// expediente hallado) sin romper las reglas de hooks con los early-returns de
// carga/error de arriba.
function CruceContenido({
  data,
  metaActiva,
  expBusqueda,
  setExpBusqueda,
  setMetaSelManual,
  expMatch,
  onAbrirMeta,
}: {
  data: ReporteResponse;
  metaActiva: MetaReporte | null;
  expBusqueda: string;
  setExpBusqueda: (v: string) => void;
  setMetaSelManual: (v: number | null) => void;
  expMatch: { meta: MetaReporte; pedido: PedidoReporte } | null;
  onAbrirMeta: (secFunc: number) => void;
}) {
  // El expediente a rastrear: el del pedido hallado por la búsqueda.
  const expSiaf = expMatch?.pedido.identificadores?.exp_siaf ?? null;
  const siaf = useDetalleExpedienteSiaf(expSiaf);

  return (
    <div className="flex flex-col gap-4">
      {/* ── Rastreador: elegir meta (por sec_func) y/o expediente SIAF ── */}
      <RastreadorCruce
        data={data}
        metaActiva={metaActiva}
        expBusqueda={expBusqueda}
        onMeta={(sf) => {
          setMetaSelManual(sf);
          setExpBusqueda('');
        }}
        onExp={setExpBusqueda}
        expMatch={expMatch}
        onAbrirMeta={onAbrirMeta}
      />

      {/* Resumen del cruce de la meta activa: las cifras clave de un vistazo. */}
      {metaActiva ? (
        <ResumenCruce meta={metaActiva} mesCorte={data.mes_corte} avanceEsperado={data.avance_esperado} />
      ) : null}

      {metaActiva ? (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <PanelMef meta={metaActiva} mesCorte={data.mes_corte} avanceEsperado={data.avance_esperado} />
          <PanelSiga meta={metaActiva} pedidoResaltado={expMatch?.pedido ?? null} onAbrirMeta={onAbrirMeta} />
        </div>
      ) : null}

      {/* Rastro real del expediente (Formato A) — sólo al buscar por EXP_SIAF.
          Es lo que la API MEF no da: girado/pagado, proveedor y documentos. */}
      {expSiaf != null ? (
        <PanelExpedienteSiaf
          expSiaf={expSiaf}
          pedido={expMatch?.pedido ?? null}
          detalle={siaf.data}
          cargando={siaf.isLoading}
          error={siaf.isError}
        />
      ) : null}

      {metaActiva ? <NotaLecturaCruce /> : null}
    </div>
  );
}

// ─── Resumen del cruce (cifras clave de la meta de un vistazo) ───────────

// Traduce el color del semáforo temporal (backend) al chip de EstadoChip que
// usa KpiTile — misma convención institucional que SemaforoChip.
const CHIP_SEMAFORO: Record<string, KpiChip> = {
  verde: { texto: 'A tiempo', tono: 'ok' },
  amarillo: { texto: 'En riesgo', tono: 'alerta' },
  rojo: { texto: 'Atrasado', tono: 'critico' },
};

function ResumenCruce({
  meta,
  mesCorte,
  avanceEsperado,
}: {
  meta: MetaReporte;
  mesCorte: number;
  avanceEsperado: number;
}) {
  const { pim, devengado, porcentaje_devengado: pct } = meta.mef;
  const chipDevengado = CHIP_SEMAFORO[meta.mef.semaforo];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <KpiTile
        label="PIM oficial"
        fuente="MEF"
        valor={formatearMoneda(pim, true)}
        ayuda="techo vigente"
      />
      <KpiTile
        label="Devengado"
        fuente="MEF"
        valor={formatearMoneda(devengado, true)}
        valorClass="text-primary"
        ayuda={`${pct != null ? `${formatearNumero(pct, 1)}%` : '—'} · esperado ${avanceEsperado}% al mes ${mesCorte}`}
        chip={chipDevengado}
      />
      <KpiTile
        label="Requerimientos"
        fuente="SIGA"
        valor={meta.n_pedidos}
        ayuda={`${meta.en_ejecucion} en ejecución`}
      />
      <KpiTile
        label="Clasificadores"
        fuente="SIGA"
        valor={meta.n_celdas}
        ayuda={`${meta.n_celdas_directas} con cruce directo`}
      />
    </div>
  );
}

// Nota de lectura al pie: cómo interpretar los dos lados sin confundirlos.
function NotaLecturaCruce() {
  return (
    <p className="rounded-md border border-dashed border-border bg-card px-3 py-2.5 text-xs leading-relaxed text-muted-foreground">
      <span className="font-semibold text-foreground">Cómo leer:</span> el dinero oficial es del{' '}
      <span className="font-semibold">MEF/SIAF</span> y se cuenta una vez por meta (panel izquierdo).
      El monto SIGA por pedido es lo solicitado (trámite operativo, referencial), no un total
      presupuestal. Busca un expediente para ver su rastro real hasta el pago; ese detalle viene del
      Formato A (carga provisional) y explica el gasto, no lo reemplaza.
    </p>
  );
}

// ─── Rastreador: buscador de meta (por sec_func) + expediente SIAF ───────

function RastreadorCruce({
  data,
  metaActiva,
  expBusqueda,
  onMeta,
  onExp,
  expMatch,
  onAbrirMeta,
}: {
  data: ReporteResponse;
  metaActiva: MetaReporte | null;
  expBusqueda: string;
  onMeta: (secFunc: number | null) => void;
  onExp: (v: string) => void;
  expMatch: { meta: MetaReporte; pedido: PedidoReporte } | null;
  onAbrirMeta: (secFunc: number) => void;
}) {
  const [busqueda, setBusqueda] = useState('');

  // Desplegable del buscador de meta: por número de secuencia funcional o
  // nombre. Igual criterio que "Análisis por meta" (la meta se identifica por
  // su sec_func, no por el correlativo).
  const coincidencias = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    if (!q) return [];
    return data.metas
      .filter(
        (m) =>
          String(m.sec_func).includes(q) ||
          (m.nombre_meta ?? '').toLowerCase().includes(q),
      )
      .slice(0, 8);
  }, [data.metas, busqueda]);

  // Metas frecuentes = las de mayor PIM del ámbito visible.
  const chips = useMemo(
    () => [...data.metas].sort((a, b) => b.mef.pim - a.mef.pim).slice(0, 5),
    [data.metas],
  );

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-card px-4 py-4">
      {/* Fila 1 — buscador de meta + buscador de expediente */}
      <div className="flex flex-wrap items-start gap-3">
        <span className="mt-2 shrink-0 text-etiqueta text-muted-foreground">
          Rastrear
        </span>

        {/* Buscador de meta (desplegable) */}
        <div className="relative min-w-[280px] flex-1">
          <div className="flex items-center gap-2 rounded-md border border-border bg-superficie-alt-2 px-3 py-2">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <input
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder={
                metaActiva
                  ? `Meta ${metaActiva.sec_func} — ${metaActiva.nombre_meta ?? 'Sin nombre'}`
                  : 'Buscar una meta por número de secuencia funcional o nombre'
              }
              aria-label="Buscar una meta por número de secuencia funcional o nombre"
              className="min-w-0 flex-1 border-0 bg-transparent text-sm font-medium text-foreground outline-none placeholder:font-normal placeholder:text-muted-foreground"
            />
          </div>
          {coincidencias.length > 0 ? (
            <ul className="absolute z-30 mt-1 max-h-72 w-full overflow-y-auto rounded-md border border-border bg-popover py-1 shadow-lg">
              {coincidencias.map((m) => (
                <li key={m.sec_func}>
                  <button
                    type="button"
                    onClick={() => {
                      onMeta(m.sec_func);
                      setBusqueda('');
                    }}
                    className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-muted"
                  >
                    <span className="shrink-0 font-mono text-xs text-muted-foreground">{m.sec_func}</span>
                    <span className="min-w-0 flex-1 truncate">{m.nombre_meta ?? 'Sin nombre'}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        {/* Buscador de expediente SIAF */}
        <div className="flex min-w-[200px] items-center gap-2 rounded-md border border-border bg-superficie-alt-2 px-3 py-2">
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <input
            value={expBusqueda}
            onChange={(e) => onExp(e.target.value)}
            placeholder="Expediente SIAF (ej. 6113)"
            inputMode="numeric"
            aria-label="Buscar por expediente SIAF"
            className="min-w-0 flex-1 bg-transparent font-mono text-sm text-foreground outline-none"
          />
        </div>
      </div>

      {expBusqueda.trim() ? (
        <p className="text-[11.5px] text-muted-foreground">
          {expMatch
            ? `Expediente ${expBusqueda.trim()} hallado en el pedido ${expMatch.pedido.nro_pedido}, meta ${expMatch.meta.sec_func}.`
            : `No se encontró un pedido con expediente SIAF que contenga "${expBusqueda.trim()}" en el ámbito visible.`}
        </p>
      ) : null}

      {/* Fila 2 — metas frecuentes */}
      {chips.length > 0 ? (
        <div className="flex flex-wrap items-center gap-1.5 border-t border-border/60 pt-3">
          <span className="text-[11px] text-muted-foreground">Metas frecuentes:</span>
          {chips.map((m) => {
            const activo = metaActiva?.sec_func === m.sec_func;
            return (
              <button
                key={m.sec_func}
                type="button"
                onClick={() => onMeta(activo ? null : m.sec_func)}
                aria-pressed={activo}
                title={m.nombre_meta ?? undefined}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11.5px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  activo
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border bg-card text-foreground hover:bg-muted',
                )}
              >
                <span className="font-mono">{m.sec_func}</span>
                <span className="max-w-[180px] truncate">{m.nombre_meta ?? 'Sin nombre'}</span>
              </button>
            );
          })}
        </div>
      ) : null}

      {/* Fila 3 — cadena de identificadores del rastro activo */}
      {metaActiva ? (
        <CadenaChips meta={metaActiva} pedidoExp={expMatch?.pedido ?? null} onAbrirMeta={onAbrirMeta} />
      ) : null}
    </div>
  );
}

// ─── Panel del expediente SIAF (rastro real del Formato A) ────────────────

function PanelExpedienteSiaf({
  expSiaf,
  pedido,
  detalle,
  cargando,
  error,
}: {
  expSiaf: number;
  pedido: PedidoReporte | null;
  detalle: DetalleExpedienteSiaf | null | undefined;
  cargando: boolean;
  error: boolean;
}) {
  const { abrir } = useModales();
  const { fases } = ordenarFases(detalle);
  const tieneFases = Boolean(detalle?.tiene_datos) && fases.length > 0;
  const { nombre: proveedor, ruc: proveedorRuc } = proveedorDeExpediente(detalle);

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-border border-t-[3px] border-t-secondary bg-card px-4 py-4">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold text-foreground">
          Rastro del expediente <span className="font-mono text-primary">{expSiaf}</span>
        </h3>
        <span className="rounded border border-secondary/30 bg-secondary/10 px-1.5 py-px font-mono text-[9.5px] font-semibold uppercase tracking-wide text-secondary-foreground">
          SIAF real
        </span>
        {pedido ? (
          <button
            type="button"
            onClick={() =>
              abrir({
                tipo: 'siaf',
                nroPedido: pedido.nro_pedido,
                tipoBien: pedido.tipo_bien,
                tipoPedido: pedido.tipo_pedido ?? '',
                expSiaf,
              })
            }
            className="ml-auto shrink-0 text-[11.5px] font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Ver expediente completo →
          </button>
        ) : null}
      </div>

      {cargando ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando detalle SIAF del expediente…</p>
      ) : error ? (
        <p className="py-6 text-center text-sm text-muted-foreground">
          No se pudo cargar el detalle SIAF del expediente. Intenta de nuevo más tarde.
        </p>
      ) : !detalle?.tiene_datos ? (
        <p className="rounded border border-dashed border-border px-3 py-6 text-center text-sm leading-relaxed text-muted-foreground">
          Aún no se ha cargado el Formato A del SIAF para este año. Un administrador puede subirlo
          para ver el girado, el pagado y los documentos reales de este expediente.
        </p>
      ) : !tieneFases ? (
        <p className="rounded border border-dashed border-border px-3 py-6 text-center text-sm text-muted-foreground">
          El expediente aún no registra fases de gasto en el detalle SIAF.
        </p>
      ) : (
        <>
          {proveedor ? (
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-[12px]">
              <span className="text-muted-foreground">Proveedor:</span>
              <span className="font-medium text-foreground">{proveedor}</span>
              {proveedorRuc ? (
                <span className="font-mono text-[11px] text-muted-foreground">· RUC {proveedorRuc}</span>
              ) : null}
            </div>
          ) : null}
          <CajaTesoreria detalle={detalle} />
          <div>
            <span className="mb-1.5 block text-etiqueta text-muted-foreground">
              Monto real por fase
            </span>
            <BarrasFasesSiaf detalle={detalle} />
          </div>
          <details className="group rounded-md border border-border/70">
            <summary className="cursor-pointer select-none px-3 py-2 text-[12px] font-medium text-foreground marker:content-none">
              <span className="text-primary group-open:hidden">Ver documentos sustento por fase</span>
              <span className="hidden text-primary group-open:inline">Ocultar documentos sustento</span>
            </summary>
            <div className="border-t border-border/70 px-3 py-3">
              <DocumentosPorFase detalle={detalle} />
            </div>
          </details>
          <p className="text-[11px] leading-relaxed text-muted-foreground">
            {selloDeDetalle(detalle)}. Explica el gasto oficial (quién, qué documento, cuándo por
            fase); no reemplaza los totales del MEF de la izquierda.
          </p>
        </>
      )}
    </section>
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
      <Chip tipo="Meta" valor={String(meta.sec_func)} onClick={() => onAbrirMeta(meta.sec_func)} />
      {ids?.pedido ? <Chip tipo="Requerim." valor={ids.pedido} /> : null}
      {ids?.orden ? <Chip tipo="Orden" valor={ids.orden} /> : null}
      {ids?.exp_siaf ? <Chip tipo="Exp. SIAF" valor={String(ids.exp_siaf)} /> : null}
    </div>
  );
}

function Chip({ tipo, valor, onClick }: { tipo: string; valor: string; onClick?: () => void }) {
  const contenido = (
    <>
      <span className="text-microdato uppercase tracking-wide text-muted-foreground">{tipo}</span>
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
  const saldo = pim - devengado;
  // La progresión del gasto oficial como barras (única representación; las
  // cifras "de un vistazo" viven en el resumen KPI, no se repiten aquí). El %
  // sobre el PIM a la derecha es dato nuevo, no una copia del monto.
  const fases = [
    { label: 'PIM', valor: pim, barra: 'bg-primary' },
    { label: 'Comprometido', valor: comprometido, barra: 'bg-primary/70' },
    { label: 'Devengado', valor: devengado, barra: 'bg-secondary' },
  ];

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-border border-t-[3px] border-t-primary bg-card px-4 py-4">
      <EncabezadoPanel titulo="Dinero oficial — SIAF / MEF" etiqueta="OFICIAL" tono="primary" />
      <div className="flex flex-col gap-2">
        <span className="text-etiqueta text-muted-foreground">Progresión del gasto</span>
        {fases.map((f) => {
          const w = pim > 0 ? Math.round((f.valor / pim) * 100) : 0;
          return (
            <div key={f.label} className="flex items-center gap-3">
              <span className="text-dato w-24 shrink-0 text-foreground">{f.label}</span>
              <div className="h-3.5 min-w-0 flex-1 overflow-hidden rounded bg-muted">
                <div className={cn('h-full rounded', f.barra)} style={{ width: `${w}%` }} />
              </div>
              <span className="text-cifra w-28 shrink-0 text-right text-foreground">
                {formatearMoneda(f.valor, true)}
              </span>
              <span className="w-12 shrink-0 text-right font-mono text-[11px] tabular-nums text-muted-foreground">
                {pim > 0 ? `${w}%` : '—'}
              </span>
            </div>
          );
        })}
      </div>
      {/* Saldo por ejecutar + semáforo temporal: el cierre de contexto del panel
          (no está en el resumen, así que no es redundante). */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 pt-3">
        <span className="text-dato text-muted-foreground">
          Saldo por ejecutar{' '}
          <span className="text-cifra ml-1 text-foreground">{formatearMoneda(saldo, true)}</span>
        </span>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-muted-foreground">
            {pct != null ? `${formatearNumero(pct, 1)}%` : '—'} · esperado {avanceEsperado}% al mes {mesCorte}
          </span>
          <SemaforoChip color={meta.mef.semaforo} ctx={meta.mef.semaforo_ctx} tamano="xs" />
        </div>
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
    <section className="flex flex-col gap-3 rounded-lg border border-border border-t-[3px] border-t-secondary bg-card px-4 py-4">
      <EncabezadoPanel titulo="Trámite operativo — SIGA" etiqueta="OPERATIVO" tono="secondary" />
      <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-superficie-alt px-3 py-2 text-[11.5px]">
        <span className="text-muted-foreground">
          <span className="font-semibold text-foreground">{meta.n_pedidos}</span> pedido
          {meta.n_pedidos === 1 ? '' : 's'} ·{' '}
          <span className="font-semibold text-foreground">{meta.n_celdas}</span> clasificador
          {meta.n_celdas === 1 ? '' : 'es'} ({meta.n_celdas_directas} con cruce directo)
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
        <p className="rounded-md border border-dashed border-border px-3 py-8 text-center text-sm text-muted-foreground">
          Esta meta no tiene clasificadores con pedidos en el ámbito visible.
        </p>
      ) : (
        <div className="flex flex-col gap-2.5">
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

// Encabezado consistente de los paneles del cruce: título + etiqueta de rol
// (OFICIAL / OPERATIVO / SIAF REAL) con el tono institucional correspondiente.
function EncabezadoPanel({
  titulo,
  etiqueta,
  tono,
}: {
  titulo: string;
  etiqueta: string;
  tono: 'primary' | 'secondary';
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <h3 className="text-sm font-semibold text-foreground">{titulo}</h3>
      <span
        className={cn(
          'shrink-0 rounded border px-1.5 py-px font-mono text-[9.5px] font-semibold uppercase tracking-wide',
          tono === 'primary'
            ? 'border-primary/30 bg-primary/10 text-primary'
            : 'border-secondary/30 bg-secondary/10 text-secondary-foreground',
        )}
      >
        {etiqueta}
      </span>
    </div>
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
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-border bg-superficie-alt px-3 py-2">
        <span className="font-mono text-[11.5px] font-semibold text-primary">{celda.clasificador}</span>
        {celda.atribucion_directa ? (
          <span
            className="rounded border border-secondary/30 bg-secondary/10 px-1.5 py-px text-[9.5px] font-medium text-secondary-foreground"
            title="Un solo pedido en esta específica de gasto: el cruce SIAF↔SIGA es directo, sin reparto."
          >
            cruce directo
          </span>
        ) : null}
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
                'flex w-full flex-wrap items-center gap-x-3 gap-y-1 border-l-2 border-transparent px-3 py-2 text-left text-[11.5px] transition-colors hover:bg-superficie-alt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
                resaltado && 'border-l-primary bg-primary/5',
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
                  title="Ver el rastro SIAF real de este expediente"
                  className="cursor-pointer rounded border border-primary/30 bg-primary/5 px-1.5 py-px font-mono text-[10px] font-medium text-primary transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
