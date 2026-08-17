// Orquestador de la vista "Análisis por meta" v2 (fiel a la plantilla):
//   1) Barra de ámbito (buscar meta · Producto/Proyecto · metas frecuentes ·
//      Reporte completo · Quitar meta).
//   2) Fila de tarjetas KPI del ámbito (dinero MEF 1× por meta).
//   3) Sección con pestañas: Requerimientos · O/C · O/S · PECOSAS · Clasificadores.
//
// El dinero SIEMPRE es del MEF/SIAF y se cuenta una vez por meta; el SIGA aporta
// el trámite (pedidos, órdenes, PECOSAS). La pestaña Contratos de la plantilla
// se omite: en SIGA los contratos son transversales, sin llave de meta.

import { useEffect, useMemo, useState } from 'react';
import { Download, GitBranch, Loader2 } from 'lucide-react';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import { formatearMoneda } from '@/lib/formatters';
import { useModales } from '@/features/modales/ModalesContext';
import { useContextoInterno } from '@/store/contexto-interno';
import { descargarReportePipeline, useReportePipeline } from '../../api';
import type { ReporteResponse } from '../../reporte-types';
import { aplanarPedidos } from '../reporte/aplanar';
import { filtrar, totalizar } from '../reporte/procesar';
import type {
  CampoAgrupacion,
  CampoOrden,
  CentroCostoLabelFn,
  DireccionOrden,
  FiltrosReporte,
} from '../reporte/tipos';
import { FILTROS_DEFAULT } from '../reporte/tipos';
import { OPCIONES_AGRUPACION, OPCIONES_ORDEN } from '../reporte/constantes';
import { AmbitoAnalisis } from './AmbitoAnalisis';
import { CardsMeta } from './CardsMeta';
import { SeccionPestanas, SegmentoModo, type TabAnalisis, type TabDef } from './SeccionPestanas';
import { TablaRequerimientos, type ModoReq } from './TablaRequerimientos';
import { TablaOrdenes } from './TablaOrdenes';
import { TablaPecosas } from './TablaPecosas';
import { ArbolClasificadores } from './ArbolClasificadores';
import {
  agregarAmbito,
  esOC,
  esOS,
  indicePedidoPorOrden,
  metaSeleccionada,
  metasDelAmbito,
  ordenesDelAmbito,
  pecosasDelAmbito,
  type FiltroCategoria,
  type OrdenConMeta,
  type PecosaConMeta,
} from './datos';

export function AnalisisPorMeta({
  metaInicial,
  tabInicial = 'req',
  modoReqInicial = 'tabla',
}: {
  metaInicial?: number | null;
  tabInicial?: TabAnalisis;
  modoReqInicial?: ModoReq;
} = {}) {
  const { data, isLoading, isError, error, refetch } = useReportePipeline();
  const año = useContextoInterno((s) => s.añoActivo);
  const ccActivo = useContextoInterno((s) => s.ccActivo);
  const { abrir } = useModales();

  const [metaSel, setMetaSel] = useState<number | null>(metaInicial ?? null);
  const [categoria, setCategoria] = useState<FiltroCategoria>('todas');
  const [tab, setTab] = useState<TabAnalisis>(tabInicial);
  const [modoReq, setModoReq] = useState<ModoReq>(modoReqInicial);
  const [busqueda, setBusqueda] = useState('');

  // Controles de la tabla dinámica (modo Dinámica de Requerimientos).
  const [agrupacion, setAgrupacion] = useState<CampoAgrupacion>('macrofase');
  const [ordenCampo, setOrdenCampo] = useState<CampoOrden>('monto_siga');
  const [direccion, setDireccion] = useState<DireccionOrden>('desc');

  const [exportando, setExportando] = useState(false);
  const [errorExport, setErrorExport] = useState<string | null>(null);

  // Si el origen (Panel/Cruce) trae una meta, se re-siembra la selección.
  useEffect(() => {
    if (metaInicial != null) setMetaSel(metaInicial);
  }, [metaInicial]);

  const ccLabel = useCentroCostoLabel(data);

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

  // ── Derivaciones del ámbito (siempre en el mismo orden de hooks) ──────────
  const metasAmbito = useMemo(
    () => (data ? metasDelAmbito(data, metaSel, categoria) : []),
    [data, metaSel, categoria],
  );
  const metaObj = useMemo(
    () => (data ? metaSeleccionada(data, metaSel) : null),
    [data, metaSel],
  );
  const agregado = useMemo(() => agregarAmbito(metasAmbito), [metasAmbito]);
  const refPorOrden = useMemo(
    () => (data ? indicePedidoPorOrden(data) : new Map()),
    [data],
  );

  // Pedidos aplanados del ámbito (para Requerimientos) + su filtro de búsqueda.
  const filasAmbito = useMemo(() => {
    if (!data) return [];
    const secFuncs = new Set(metasAmbito.map((m) => m.sec_func));
    return aplanarPedidos(data).filter((f) => secFuncs.has(f.sec_func));
  }, [data, metasAmbito]);

  const filtrosReq: FiltrosReporte = useMemo(
    () => ({ ...FILTROS_DEFAULT, busqueda: tab === 'req' ? busqueda : '' }),
    [busqueda, tab],
  );
  const filasReq = useMemo(() => filtrar(filasAmbito, filtrosReq), [filasAmbito, filtrosReq]);
  const totalReq = useMemo(() => totalizar(filasReq), [filasReq]);
  const nEstancados = useMemo(() => filasAmbito.filter((f) => f.estancado).length, [filasAmbito]);

  // Órdenes / PECOSAS del ámbito, con filtro de búsqueda por pestaña.
  const ordenes = useMemo(() => ordenesDelAmbito(metasAmbito), [metasAmbito]);
  const pecosas = useMemo(() => pecosasDelAmbito(metasAmbito), [metasAmbito]);
  const oc = useMemo(() => filtrarOrdenes(ordenes.filter(esOC), tab === 'oc' ? busqueda : ''), [ordenes, busqueda, tab]);
  const os = useMemo(() => filtrarOrdenes(ordenes.filter(esOS), tab === 'os' ? busqueda : ''), [ordenes, busqueda, tab]);
  const pecFiltradas = useMemo(
    () => filtrarPecosas(pecosas, tab === 'pec' ? busqueda : ''),
    [pecosas, busqueda, tab],
  );

  // ── Estados de carga / error / vacío (después de los hooks) ───────────────
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-border bg-card py-16 text-muted-foreground">
        <Loader2 className="mb-3 h-8 w-8 animate-spin text-primary" aria-hidden="true" />
        <p className="text-sm">Cargando análisis…</p>
      </div>
    );
  }
  if (isError || !data) {
    return (
      <ErrorState
        titulo="No pudimos cargar el análisis"
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
        descripcion="No hay pedidos para el año y unidad seleccionados. Cambia el año o el centro de costo en la barra superior."
      />
    );
  }

  const ambitoLabel = metaObj
    ? `Meta ${metaObj.sec_func} — ${metaObj.nombre_meta ?? 'Sin nombre'}`
    : `Buscar una meta · ${data.metas.length} en el ámbito`;
  const ambitoAyuda = metaObj
    ? metaObj.categoria === 'proyecto'
      ? `Proyecto de inversión ${metaObj.act_proy ?? ''}`.trim()
      : `Producto / actividad ${metaObj.act_proy ?? ''}`.trim()
    : 'elige una meta para afinar';

  const tabs: TabDef[] = [
    { id: 'req', label: 'Requerimientos', n: filasAmbito.length },
    { id: 'oc', label: 'O/C', n: ordenes.filter(esOC).length },
    { id: 'os', label: 'O/S', n: ordenes.filter(esOS).length },
    { id: 'pec', label: 'PECOSAS', n: pecosas.length },
    { id: 'cla', label: 'Clasificadores', n: metasAmbito.reduce((s, m) => s + m.n_celdas, 0) },
  ];

  const placeholderPorTab: Record<TabAnalisis, string> = {
    req: 'Buscar por código, detalle o meta…',
    oc: 'Buscar orden, proveedor o RUC…',
    os: 'Buscar orden, proveedor o RUC…',
    pec: 'Buscar PECOSA, guía o proveedor…',
    cla: 'Buscar clasificador o meta…',
  };

  return (
    <div className="flex flex-col gap-4">
      <AmbitoAnalisis
        data={data}
        metaSel={metaSel}
        categoria={categoria}
        onMeta={(sf) => {
          setMetaSel(sf);
          if (sf != null) setCategoria('todas');
        }}
        onCategoria={setCategoria}
        onReporte={() => abrir({ tipo: 'reporte', secFunc: metaSel })}
        ambitoLabel={ambitoLabel}
        ambitoAyuda={ambitoAyuda}
      />

      {errorExport ? (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {errorExport}
        </div>
      ) : null}

      <CardsMeta agregado={agregado} avanceEsperado={data.avance_esperado} nEstancados={nEstancados} />

      <SeccionPestanas
        tabs={tabs}
        tabActiva={tab}
        onTab={setTab}
        busqueda={busqueda}
        onBusqueda={setBusqueda}
        buscarPlaceholder={placeholderPorTab[tab]}
        acciones={
          <>
            {tab === 'req' ? (
              <>
                <SegmentoModo
                  aria="Modo de la tabla de requerimientos"
                  valor={modoReq}
                  onChange={setModoReq}
                  opciones={[
                    { valor: 'tabla', label: 'Tabla' },
                    { valor: 'dinamica', label: 'Dinámica' },
                    { valor: 'kanban', label: 'Kanban' },
                  ]}
                />
                {modoReq === 'dinamica' ? (
                  <ControlesDinamica
                    agrupacion={agrupacion}
                    onAgrupacion={setAgrupacion}
                    orden={ordenCampo}
                    onOrden={setOrdenCampo}
                    direccion={direccion}
                    onDireccion={setDireccion}
                  />
                ) : null}
              </>
            ) : null}
            <button
              type="button"
              onClick={exportar}
              disabled={exportando}
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-[11.5px] font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
            >
              {exportando ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <Download className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              {exportando ? 'Generando…' : 'Descargar Excel'}
            </button>
          </>
        }
      >
        {tab === 'req' ? (
          <TablaRequerimientos
            modo={modoReq}
            filas={filasReq}
            totalGlobal={totalReq}
            ccLabel={ccLabel}
            agrupacion={agrupacion}
            orden={ordenCampo}
            direccion={direccion}
          />
        ) : null}
        {tab === 'oc' ? (
          <TablaOrdenes ordenes={oc} refPorOrden={refPorOrden} vacio="Esta selección no tiene órdenes de compra." />
        ) : null}
        {tab === 'os' ? (
          <TablaOrdenes ordenes={os} refPorOrden={refPorOrden} vacio="Esta selección no tiene órdenes de servicio." />
        ) : null}
        {tab === 'pec' ? (
          <TablaPecosas pecosas={pecFiltradas} refPorOrden={refPorOrden} vacio="Esta selección no tiene PECOSAS." />
        ) : null}
        {tab === 'cla' ? <div className="px-4 py-4"><ArbolClasificadores metas={metasAmbito} /></div> : null}
      </SeccionPestanas>

      <NotaLectura totalSiga={agregado.monto_siga} devengado={agregado.devengado} />
    </div>
  );
}

// ─── Controles de la tabla dinámica (agrupar / ordenar / dirección) ──────

function ControlesDinamica({
  agrupacion,
  onAgrupacion,
  orden,
  onOrden,
  direccion,
  onDireccion,
}: {
  agrupacion: CampoAgrupacion;
  onAgrupacion: (c: CampoAgrupacion) => void;
  orden: CampoOrden;
  onOrden: (c: CampoOrden) => void;
  direccion: DireccionOrden;
  onDireccion: (d: DireccionOrden) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <Select
        label="Agrupar"
        value={agrupacion}
        onChange={(v) => onAgrupacion(v as CampoAgrupacion)}
        opciones={OPCIONES_AGRUPACION.map((o) => ({ valor: o.valor, label: o.label }))}
      />
      <Select
        label="Ordenar"
        value={orden}
        onChange={(v) => onOrden(v as CampoOrden)}
        opciones={OPCIONES_ORDEN.map((o) => ({ valor: o.valor, label: o.label }))}
      />
      <button
        type="button"
        onClick={() => onDireccion(direccion === 'asc' ? 'desc' : 'asc')}
        title={direccion === 'asc' ? 'Ascendente' : 'Descendente'}
        className="h-8 rounded-md border border-border bg-card px-2.5 text-[11.5px] text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {direccion === 'asc' ? '↑' : '↓'}
      </button>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  opciones,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  opciones: { valor: string; label: string }[];
}) {
  return (
    <label className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground">
      <span>{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 rounded-md border border-border bg-card px-2 text-[11.5px] text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {opciones.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function NotaLectura({ totalSiga, devengado }: { totalSiga: number; devengado: number }) {
  return (
    <p className="rounded-md border border-dashed border-border bg-card px-3 py-2.5 text-xs leading-relaxed text-muted-foreground">
      <span className="font-semibold text-foreground">Cómo leer:</span> el dinero oficial es del{' '}
      <span className="font-semibold">MEF/SIAF</span> y se cuenta una vez por meta — devengado del
      ámbito {formatearMoneda(devengado)}. El monto SIGA por pedido ({formatearMoneda(totalSiga)}) es
      lo solicitado, referencial; las órdenes y PECOSAS son el trámite operativo, no un total
      presupuestal.
    </p>
  );
}

// ─── Filtros de búsqueda de las pestañas de trámite ──────────────────────

function filtrarOrdenes(ordenes: OrdenConMeta[], q: string): OrdenConMeta[] {
  const s = q.trim().toLowerCase();
  if (!s) return ordenes;
  return ordenes.filter((o) =>
    [o.nro_orden, o.proveedor_nombre ?? '', o.proveedor_ruc ?? '', o.concepto ?? '', o.sec_func, o.nombre_meta ?? '']
      .join(' ')
      .toLowerCase()
      .includes(s),
  );
}

function filtrarPecosas(pecosas: PecosaConMeta[], q: string): PecosaConMeta[] {
  const s = q.trim().toLowerCase();
  if (!s) return pecosas;
  return pecosas.filter((p) =>
    [p.nro_pecosa, p.nro_orden ?? '', p.nro_guia ?? '', p.proveedor_nombre ?? '', p.sec_func, p.nombre_meta ?? '']
      .join(' ')
      .toLowerCase()
      .includes(s),
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

export default AnalisisPorMeta;
