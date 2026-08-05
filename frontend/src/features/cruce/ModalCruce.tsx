import { useMemo } from 'react';
import { Package, FileCheck, FileText, Wallet } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Acordeon } from '@/components/layout/Acordeon';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import { formatearMoneda } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import { useContextoInterno } from '@/store/contexto-interno';
import {
  useConsolidadoMeta,
  useConsolidadoClasificador,
  esNoEncontrada,
} from './api';
import { formatSecFunc, totalOrdenes } from './lib';
import { KpisMeta, DetallePresupuesto } from './secciones/PresupuestoMeta';
import { TablaOrdenes, TablaCertificaciones, TablaPedidos } from './secciones/TablasCruce';

interface ModalCruceProps {
  /** Meta a consultar. `null` cierra el modal. */
  secFunc: number | null;
  /**
   * Si se pasa, el cruce se filtra a ESE clasificador (modal desde el drill-down).
   * Si es `null`/omitido, es el cruce por meta completo.
   */
  clasificador?: string | null;
  /** Nombre legible del clasificador (para la cabecera), si se conoce. */
  clasificadorNombre?: string | null;
  onClose: () => void;
}

/**
 * Modal del cruce SIAF-SIGA. Reemplaza la antigua página `/interno/cruce/meta/:id`.
 * Dos niveles según se pase `clasificador`:
 *   - Meta: presupuesto dual (SIGA + MEF oficial) + órdenes + certificaciones + pedidos.
 *   - Clasificador: mismo cruce filtrado a un clasificador; sin bloque MEF (el
 *     snapshot oficial es por meta, no baja a clasificador).
 */
export function ModalCruce({
  secFunc,
  clasificador = null,
  clasificadorNombre = null,
  onClose,
}: ModalCruceProps) {
  const abierto = secFunc != null;
  return (
    <Dialog open={abierto} onOpenChange={(o) => (!o ? onClose() : undefined)}>
      <DialogContent className="max-h-[90vh] gap-0 overflow-hidden p-0 sm:max-w-4xl">
        {abierto ? (
          clasificador ? (
            <ContenidoClasificador
              secFunc={secFunc}
              clasificador={clasificador}
              clasificadorNombre={clasificadorNombre}
            />
          ) : (
            <ContenidoMeta secFunc={secFunc} />
          )
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

/**
 * Cabecera institucional del modal: una etiqueta de tipo (Meta / Clasificador),
 * el código destacado y el nombre. Sobre fondo blanco, sobria.
 */
function Cabecera({
  etiqueta,
  codigo,
  nombre,
  meta,
  ano,
}: {
  etiqueta: string;
  codigo: string;
  nombre: string;
  meta?: string;
  ano: number;
}) {
  return (
    <DialogHeader className="space-y-0 border-b border-border bg-card px-6 py-4 text-left">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="rounded bg-primary/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-primary">
          {etiqueta}
        </span>
        <span className="font-mono text-sm font-semibold text-foreground">{codigo}</span>
        {meta ? (
          <span className="text-xs text-muted-foreground">{meta}</span>
        ) : null}
        <span className="ml-auto text-xs text-muted-foreground">Año {ano}</span>
      </div>
      <DialogTitle className="mt-1.5 text-base font-semibold leading-snug">
        {nombre}
      </DialogTitle>
      <DialogDescription className="sr-only">
        Cruce de información entre el SIAF y el SIGA: presupuesto, órdenes,
        certificaciones y pedidos.
      </DialogDescription>
    </DialogHeader>
  );
}

/**
 * Franja de resumen: totales de un vistazo (órdenes, importe, pedidos,
 * certificaciones) antes de expandir los acordeones. Densidad de información.
 */
function FranjaResumen({
  items,
}: {
  items: { label: string; valor: React.ReactNode; tono?: 'primario' }[];
}) {
  return (
    <dl className="grid grid-cols-2 divide-x divide-border border-b border-border sm:grid-cols-4">
      {items.map((it) => (
        <div key={it.label} className="px-4 py-3">
          <dt className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            {it.label}
          </dt>
          <dd
            className={cn(
              'mt-0.5 text-lg font-bold tabular-nums leading-tight',
              it.tono === 'primario' ? 'text-primary' : 'text-foreground',
            )}
          >
            {it.valor}
          </dd>
        </div>
      ))}
    </dl>
  );
}

/** Cuerpo scrolleable con los acordeones. */
function CuerpoAcordeones({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-h-[calc(90vh-13rem)] space-y-3 overflow-y-auto bg-muted/10 p-4">
      {children}
    </div>
  );
}

function Cargando() {
  return (
    <div className="space-y-4 p-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-md bg-muted" />
        ))}
      </div>
      <div className="h-14 animate-pulse rounded-md bg-muted" />
      <div className="h-14 animate-pulse rounded-md bg-muted" />
    </div>
  );
}

function ContenidoMeta({ secFunc }: { secFunc: number }) {
  const ano = useContextoInterno((s) => s.añoActivo);
  const { data, isLoading, isError, error, refetch } = useConsolidadoMeta(secFunc);
  const totalOrd = useMemo(() => (data ? totalOrdenes(data.ordenes) : 0), [data]);

  if (isError && esNoEncontrada(error)) {
    return (
      <div className="p-6">
        <EmptyState
          titulo="Meta no encontrada"
          descripcion="Esta meta no existe en el año seleccionado o está fuera de tu alcance."
        />
      </div>
    );
  }
  if (isError) {
    return (
      <div className="p-6">
        <ErrorState
          titulo="No se pudo cargar el cruce de la meta"
          descripcion="Puede ser un corte temporal del SIGA. Vuelve a intentarlo."
          onReintentar={() => refetch()}
        />
      </div>
    );
  }
  if (isLoading || !data) return <Cargando />;

  return (
    <div className="flex flex-col">
      <Cabecera
        etiqueta="Meta"
        codigo={formatSecFunc(secFunc)}
        nombre={data.meta.nombre ?? 'Sin nombre'}
        ano={ano}
      />
      <FranjaResumen
        items={[
          { label: 'Devengado (MEF)', valor: data.presupuesto.devengado_mef != null ? formatearMoneda(data.presupuesto.devengado_mef, true) : 'ND', tono: 'primario' },
          { label: 'Órdenes', valor: data.ordenes.length },
          { label: 'Certificaciones', valor: data.certificaciones.length },
          { label: 'Pedidos', valor: data.pedidos.length },
        ]}
      />
      <CuerpoAcordeones>
        <div className="rounded-md border border-border bg-card p-4">
          <KpisMeta presupuesto={data.presupuesto} />
        </div>
        <Acordeon titulo="Presupuesto (SIGA y MEF)" icono={Wallet} defaultOpen>
          <DetallePresupuesto presupuesto={data.presupuesto} />
        </Acordeon>
        <Acordeon
          titulo="Órdenes de adquisición"
          icono={Package}
          conteo={data.ordenes.length}
          resumen={data.ordenes.length > 0 ? formatearMoneda(totalOrd, true) : undefined}
          vacio={data.ordenes.length === 0}
        >
          <TablaOrdenes ordenes={data.ordenes} />
        </Acordeon>
        <Acordeon
          titulo="Certificaciones"
          icono={FileCheck}
          conteo={data.certificaciones.length}
          vacio={data.certificaciones.length === 0}
        >
          <TablaCertificaciones items={data.certificaciones} />
        </Acordeon>
        <Acordeon
          titulo="Pedidos de origen"
          icono={FileText}
          conteo={data.pedidos.length}
          vacio={data.pedidos.length === 0}
        >
          <TablaPedidos pedidos={data.pedidos} />
        </Acordeon>
      </CuerpoAcordeones>
    </div>
  );
}

function ContenidoClasificador({
  secFunc,
  clasificador,
  clasificadorNombre,
}: {
  secFunc: number;
  clasificador: string;
  clasificadorNombre: string | null;
}) {
  const ano = useContextoInterno((s) => s.añoActivo);
  const ccActivo = useContextoInterno((s) => s.ccActivo);
  const { data, isLoading, isError, error, refetch } = useConsolidadoClasificador(
    secFunc,
    clasificador,
    ccActivo?.codigo ?? null,
  );
  const totalOrd = useMemo(() => (data ? totalOrdenes(data.ordenes) : 0), [data]);

  if (isError && esNoEncontrada(error)) {
    return (
      <div className="p-6">
        <EmptyState
          titulo="Sin datos"
          descripcion="Este clasificador no tiene movimiento en el año seleccionado o está fuera de tu alcance."
        />
      </div>
    );
  }
  if (isError) {
    return (
      <div className="p-6">
        <ErrorState
          titulo="No se pudo cargar el cruce del clasificador"
          descripcion="Puede ser un corte temporal del SIGA. Vuelve a intentarlo."
          onReintentar={() => refetch()}
        />
      </div>
    );
  }
  if (isLoading || !data) return <Cargando />;

  const p = data.presupuesto;
  const nombreClasif = data.clasificador_nombre ?? clasificadorNombre ?? 'Clasificador';
  const codigo = data.clasificador.replace(/\s+/g, ' ').trim();

  return (
    <div className="flex flex-col">
      <Cabecera
        etiqueta="Clasificador"
        codigo={codigo}
        nombre={nombreClasif}
        meta={`Meta ${formatSecFunc(secFunc)}`}
        ano={ano}
      />
      <FranjaResumen
        items={[
          { label: 'PIM (SIGA)', valor: formatearMoneda(p.pim, true), tono: 'primario' },
          { label: 'Órdenes', valor: data.ordenes.length },
          { label: 'Certificaciones', valor: data.certificaciones.length },
          { label: 'Pedidos', valor: data.pedidos.length },
        ]}
      />
      <CuerpoAcordeones>
        {/* Cadena de fases SIGA de la línea (Certificado → Comprometido). */}
        <div className="rounded-md border border-border bg-card p-4">
          <CadenaClasificador presupuesto={p} />
          <p className="mt-3 border-t border-border pt-3 text-xs text-muted-foreground">
            Estos montos son el techo operativo del SIGA para esta línea de gasto.
            El devengado oficial y el porcentaje de avance se calculan por meta,
            no por clasificador. El detalle de abajo (órdenes, certificaciones,
            pedidos) sí corresponde solo a este clasificador.
          </p>
        </div>
        <Acordeon
          titulo="Órdenes de adquisición"
          icono={Package}
          conteo={data.ordenes.length}
          resumen={data.ordenes.length > 0 ? formatearMoneda(totalOrd, true) : undefined}
          vacio={data.ordenes.length === 0}
          defaultOpen
        >
          <TablaOrdenes ordenes={data.ordenes} />
        </Acordeon>
        <Acordeon
          titulo="Certificaciones"
          icono={FileCheck}
          conteo={data.certificaciones.length}
          vacio={data.certificaciones.length === 0}
        >
          <TablaCertificaciones items={data.certificaciones} />
        </Acordeon>
        <Acordeon
          titulo="Pedidos de origen"
          icono={FileText}
          conteo={data.pedidos.length}
          vacio={data.pedidos.length === 0}
        >
          <TablaPedidos pedidos={data.pedidos} />
        </Acordeon>
      </CuerpoAcordeones>
    </div>
  );
}

/** Fases del techo SIGA del clasificador, en una fila horizontal legible. */
function CadenaClasificador({
  presupuesto: p,
}: {
  presupuesto: { pim: number; certificado: number; comprometido: number; saldo_disponible: number };
}) {
  const fases = [
    { label: 'PIM', valor: p.pim },
    { label: 'Certificado', valor: p.certificado },
    { label: 'Comprometido', valor: p.comprometido },
    { label: 'Saldo disponible', valor: p.saldo_disponible },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {fases.map((f) => (
        <div key={f.label}>
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            {f.label}
          </p>
          <p className="mt-0.5 text-base font-semibold tabular-nums text-foreground">
            {formatearMoneda(f.valor, true)}
          </p>
        </div>
      ))}
    </div>
  );
}

export default ModalCruce;
