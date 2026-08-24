// Panel de decisión (home /interno) — Panel Interno v2.
//
// Contenedor delgado: orquesta los hooks reales del dashboard y compone las
// secciones desacopladas (KPIs, embudo de fases, pipeline por macrofase,
// bandeja de acción y focos de atención). Cada sección vive en su propio
// archivo y usa las primitivas reutilizables de `../panel/ui`.
//
// El dinero es oficial del MEF (1× por meta); el trámite es del SIGA. Las colas
// de acción salen de endpoints reales de alertas/saldos.

import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/layout/PageHeader';
import { ErrorState } from '@/components/layout/ErrorState';
import { SkeletonCard, SkeletonTable } from '@/components/layout/LoadingSkeleton';
import { useAuthStore } from '@/store/auth';
import { useContextoInterno } from '@/store/contexto-interno';
import type { PedidoCard } from '@/features/dashboard/types';
import {
  useContratosPorVencer,
  useKanban,
  useMetasRezagadas,
  usePedidosEstancados,
  useResumenSaldos,
} from '@/features/dashboard/api';
import { useModales } from '@/features/modales/ModalesContext';
import { KpisPanel } from './secciones/KpisPanel';
import { EmbudoFasesSiaf } from './secciones/EmbudoFasesSiaf';
import { PipelineMacrofase } from './secciones/PipelineMacrofase';
import { BandejaAccion } from './secciones/BandejaAccion';
import { FocosAtencion } from './secciones/FocosAtencion';

const ROL_LABEL: Record<string, string> = {
  admin: 'Administrador',
  decisor: 'Decisor',
  operativo: 'Operativo',
  ciudadano: 'Ciudadano',
};

export default function PanelDecision() {
  const navigate = useNavigate();
  const { abrir } = useModales();
  const user = useAuthStore((s) => s.user);
  const año = useContextoInterno((s) => s.añoActivo);
  const cc = useContextoInterno((s) => s.ccActivo);

  const resumenQ = useResumenSaldos();
  const kanbanQ = useKanban();
  const estancadosQ = usePedidosEstancados();
  const contratosQ = useContratosPorVencer(30);
  const rezagadasQ = useMetasRezagadas(50);

  const isLoading =
    resumenQ.isLoading ||
    kanbanQ.isLoading ||
    estancadosQ.isLoading ||
    contratosQ.isLoading ||
    rezagadasQ.isLoading;

  const isError =
    resumenQ.isError ||
    kanbanQ.isError ||
    estancadosQ.isError ||
    contratosQ.isError ||
    rezagadasQ.isError;

  const primerError =
    resumenQ.error || kanbanQ.error || estancadosQ.error || contratosQ.error || rezagadasQ.error;

  const descripcion = useMemo(
    () =>
      construirDescripcion({
        año,
        ccNombre: cc?.nombre ?? null,
        ccCodigo: cc?.codigo ?? null,
        rol: user?.rol ?? null,
        nombre: user?.nombre_completo ?? null,
      }),
    [año, cc, user],
  );

  function reintentar() {
    void resumenQ.refetch();
    void kanbanQ.refetch();
    void estancadosQ.refetch();
    void contratosQ.refetch();
    void rezagadasQ.refetch();
  }

  const abrirPedido = (p: PedidoCard) =>
    abrir({
      tipo: 'pedido',
      nroPedido: p.nro_pedido,
      tipoBien: p.tipo_bien,
      tipoPedido: p.tipo_pedido ?? '',
    });
  const analizarMeta = (secFunc: number) =>
    navigate(`/interno/analisis?meta=${secFunc}`);
  const verContrato = (ruc: string | null) =>
    navigate(ruc ? `/interno/proveedores/${ruc}` : '/interno/analisis?tab=contratos');

  return (
    <div className="space-y-6">
      <PageHeader titulo="Panel" descripcion={descripcion} />

      {isError ? (
        <ErrorState
          titulo="No se pudo cargar el panel"
          descripcion={
            primerError instanceof Error
              ? primerError.message
              : 'Ocurrió un error al consultar los datos. Puede ser un corte temporal del SIGA o SIAF.'
          }
          onReintentar={reintentar}
        />
      ) : isLoading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <SkeletonTable rows={5} cols={5} />
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-1">
            <h2 className="text-lg font-semibold tracking-tight text-foreground">
              ¿Cómo va la ejecución del pliego?
            </h2>
            <p className="text-sm text-muted-foreground">
              Ejecución oficial SIAF al mes de corte {resumenQ.data?.mes_corte ?? '—'}, y las colas
              de acción del día. El dinero es del MEF, contado una sola vez por meta; el trámite es
              del SIGA.
            </p>
          </div>

          {resumenQ.data ? (
            <KpisPanel
              resumen={resumenQ.data}
              kanban={kanbanQ.data}
              estancados={estancadosQ.data?.length ?? 0}
            />
          ) : null}

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {resumenQ.data ? <EmbudoFasesSiaf resumen={resumenQ.data} /> : null}
            {kanbanQ.data ? <PipelineMacrofase kanban={kanbanQ.data} /> : null}
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <BandejaAccion
              estancados={estancadosQ.data ?? []}
              metasRezagadas={rezagadasQ.data ?? []}
              contratos={contratosQ.data ?? []}
              onAbrirPedido={abrirPedido}
              onAnalizarMeta={analizarMeta}
              onVerContrato={verContrato}
            />
            <FocosAtencion
              metas={resumenQ.data?.top_metas_criticas ?? []}
              onAnalizarMeta={analizarMeta}
            />
          </div>
        </>
      )}
    </div>
  );
}

function construirDescripcion({
  año,
  ccNombre,
  ccCodigo,
  rol,
  nombre,
}: {
  año: number;
  ccNombre: string | null;
  ccCodigo: string | null;
  rol: string | null;
  nombre: string | null;
}) {
  const partes: string[] = [];
  if (nombre) partes.push(nombre);
  if (rol) partes.push(ROL_LABEL[rol] ?? rol);
  const cabecera = partes.join(' · ');
  const contexto = ccNombre
    ? `${ccNombre}${ccCodigo ? ` (${ccCodigo})` : ''} · Año ${año}`
    : `Año ${año}`;
  return cabecera ? `${cabecera} — ${contexto}` : contexto;
}
