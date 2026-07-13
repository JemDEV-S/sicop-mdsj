import { useMemo } from 'react';
import { BarChart3, FileText, GitBranch, Wallet } from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { ErrorState } from '@/components/layout/ErrorState';
import { SkeletonKPI } from '@/components/layout/LoadingSkeleton';
import { AccesosRapidos, type AccesoRapido } from '@/components/nav/AccesosRapidos';
import { WidgetAlertas } from '../widgets/WidgetAlertas';
import { WidgetPipeline } from '../widgets/WidgetPipeline';
import { WidgetSaldos } from '../widgets/WidgetSaldos';
import { UltimosPedidos } from '../widgets/UltimosPedidos';
import { useKanban, useSaldos, usePedidosEstancados } from '../api';
import type { SaldosResumen } from '../types';

const ACCESOS: AccesoRapido[] = [
  { label: 'Pipeline', icono: GitBranch, href: '/interno/pipeline' },
  { label: 'Saldos', icono: Wallet, href: '/interno/saldos' },
  { label: 'Reportes', icono: FileText, href: '/interno/reportes' },
  { label: 'Ejecución', icono: BarChart3, href: '/ejecucion' },
];

export default function DashboardWidgets() {
  const user = useAuthStore((s) => s.user);

  const {
    data: kanban,
    isLoading: isLoadingK,
    isError: isErrorK,
    error: errorK,
    refetch: refetchK,
  } = useKanban();
  const {
    data: saldosData,
    isLoading: isLoadingS,
    isError: isErrorS,
    error: errorS,
    refetch: refetchS,
  } = useSaldos({ page: 1, size: 100 });
  const {
    data: estancados,
    isLoading: isLoadingE,
    isError: isErrorE,
    error: errorE,
    refetch: refetchE,
  } = usePedidosEstancados();

  const isLoading = isLoadingK || isLoadingS || isLoadingE;
  const isError = isErrorK || isErrorS || isErrorE;
  const error = errorK || errorS || errorE;

  const alertasResumen = useMemo(
    () => ({
      pedidos_estancados: estancados?.length ?? 0,
      contratos_por_vencer: 0,
      metas_rezagadas: 0,
    }),
    [estancados],
  );

  const pipelineResumen = useMemo(() => {
    if (!kanban) {
      return { solicitados: 0, con_orden: 0, conformidad: 0, devengado: 0, cerrado: 0 };
    }
    return {
      solicitados: kanban.solicitado.length,
      con_orden: kanban.con_orden.length,
      conformidad: kanban.conformidad.length,
      devengado: kanban.devengado.length,
      cerrado: kanban.cerrado.length,
    };
  }, [kanban]);

  const saldosResumen = useMemo<SaldosResumen>(() => {
    if (!saldosData || !saldosData.items) {
      return {
        saldo_disponible: 0,
        pim_total: 0,
        devengado_total: 0,
        porcentaje_ejecucion: 0,
        semaforo: null,
      };
    }

    let pim_total = 0;
    let devengado_total = 0;
    let saldo_disponible = 0;

    saldosData.items.forEach((item) => {
      pim_total += item.pim || 0;
      devengado_total += item.devengado || 0;
      saldo_disponible += item.saldo_disponible || 0;
    });

    const porcentaje_ejecucion = pim_total > 0 ? (devengado_total / pim_total) * 100 : 0;

    let semaforo: SaldosResumen['semaforo'] = 'ok';
    if (porcentaje_ejecucion < 40) semaforo = 'critico';
    else if (porcentaje_ejecucion < 70) semaforo = 'alerta';

    return {
      saldo_disponible,
      pim_total,
      devengado_total,
      porcentaje_ejecucion,
      semaforo,
    };
  }, [saldosData]);

  const ultimosPedidos = useMemo(() => {
    if (!kanban) return [];
    const todos = [
      ...kanban.solicitado,
      ...kanban.con_orden,
      ...kanban.conformidad,
      ...kanban.devengado,
      ...kanban.cerrado,
    ];
    todos.sort((a, b) => {
      if (!a.fecha_pedido) return 1;
      if (!b.fecha_pedido) return -1;
      return new Date(b.fecha_pedido).getTime() - new Date(a.fecha_pedido).getTime();
    });

    return todos.slice(0, 5).map((p) => ({
      nro_pedido: p.nro_pedido.toString(),
      monto: p.monto_total,
      descripcion: p.motivo || 'Sin descripción',
      estado: p.etapa,
      fecha: p.fecha_pedido || null,
    }));
  }, [kanban]);

  function reintentar() {
    void refetchK();
    void refetchS();
    void refetchE();
  }

  return (
    <div className="space-y-6">
      {/* Saludo */}
      <header>
        <h1 className="text-2xl font-bold text-foreground">
          Bienvenido{user?.nombre_completo ? `, ${user.nombre_completo}` : ''}
        </h1>
        {user?.rol ? (
          <p className="text-sm text-muted-foreground mt-1 capitalize">{user.rol}</p>
        ) : null}
      </header>

      {isError ? (
        <ErrorState
          titulo="No se pudo cargar el dashboard"
          descripcion={
            error instanceof Error ? error.message : 'Ocurrió un error al consultar los datos.'
          }
          onReintentar={reintentar}
        />
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SkeletonKPI />
          <SkeletonKPI />
          <SkeletonKPI />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <WidgetAlertas alertas={alertasResumen} />
            <WidgetPipeline pipeline={pipelineResumen} />
            <WidgetSaldos saldos={saldosResumen} />
          </div>

          <UltimosPedidos pedidos={ultimosPedidos} />

          <div>
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
              Accesos rápidos
            </h2>
            <AccesosRapidos items={ACCESOS} />
          </div>
        </>
      )}
    </div>
  );
}
