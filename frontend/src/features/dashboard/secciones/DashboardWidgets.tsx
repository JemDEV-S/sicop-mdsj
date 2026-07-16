import { useMemo } from 'react';
import { PageHeader } from '@/components/layout/PageHeader';
import { ErrorState } from '@/components/layout/ErrorState';
import {
  SkeletonCard,
  SkeletonTable,
} from '@/components/layout/LoadingSkeleton';
import { useAuthStore } from '@/store/auth';
import { useContextoInterno } from '@/store/contexto-interno';
import { WidgetAlertas } from '../widgets/WidgetAlertas';
import { WidgetPipeline } from '../widgets/WidgetPipeline';
import { WidgetSaldos } from '../widgets/WidgetSaldos';
import { UltimosPedidos } from '../widgets/UltimosPedidos';
import {
  useContratosPorVencer,
  useKanban,
  useMetasRezagadas,
  usePedidosEstancados,
  useResumenSaldos,
} from '../api';
import type { PedidoCard, SaldosResumen } from '../types';

const RESUMEN_VACIO: SaldosResumen = {
  ano: 0,
  pia: 0,
  pim: 0,
  certificado: 0,
  comprometido: 0,
  devengado: 0,
  saldo_disponible: 0,
  reservado_pedido: 0,
  porcentaje_devengado: 0,
  semaforo: 'desconocido',
  metas_total: 0,
  metas_criticas: 0,
  top_metas_criticas: [],
};


const ROL_LABEL: Record<string, string> = {
  admin: 'Administrador',
  decisor: 'Decisor',
  operativo: 'Operativo',
  ciudadano: 'Ciudadano',
};

export default function DashboardWidgets() {
  const user = useAuthStore((s) => s.user);
  const año = useContextoInterno((s) => s.añoActivo);
  const cc = useContextoInterno((s) => s.ccActivo);

  const kanbanQ = useKanban();
  const resumenQ = useResumenSaldos();
  const estancadosQ = usePedidosEstancados();
  const contratosQ = useContratosPorVencer(30);
  const metasRezagadasQ = useMetasRezagadas(50);

  const isLoading =
    kanbanQ.isLoading ||
    resumenQ.isLoading ||
    estancadosQ.isLoading ||
    contratosQ.isLoading ||
    metasRezagadasQ.isLoading;

  const isError =
    kanbanQ.isError ||
    resumenQ.isError ||
    estancadosQ.isError ||
    contratosQ.isError ||
    metasRezagadasQ.isError;

  const primerError =
    kanbanQ.error || resumenQ.error || estancadosQ.error ||
    contratosQ.error || metasRezagadasQ.error;

  const macrofasesPipeline = useMemo(
    () => kanbanQ.data?.macrofases ?? [],
    [kanbanQ.data],
  );

  const ultimosPedidos = useMemo<PedidoCard[]>(() => {
    const k = kanbanQ.data;
    if (!k) return [];
    const todos: PedidoCard[] = Object.values(k.pedidos_por_etapa ?? {})
      .flatMap((lista) => lista ?? []);
    return [...todos]
      .sort((a, b) => {
        if (!a.fecha_pedido) return 1;
        if (!b.fecha_pedido) return -1;
        return new Date(b.fecha_pedido).getTime() - new Date(a.fecha_pedido).getTime();
      })
      .slice(0, 5);
  }, [kanbanQ.data]);

  function reintentar() {
    void kanbanQ.refetch();
    void resumenQ.refetch();
    void estancadosQ.refetch();
    void contratosQ.refetch();
    void metasRezagadasQ.refetch();
  }

  const descripcionContexto = construirDescripcion({
    año,
    ccNombre: cc?.nombre ?? null,
    ccCodigo: cc?.codigo ?? null,
    rol: user?.rol ?? null,
    nombre: user?.nombre_completo ?? null,
  });

  return (
    <div className="space-y-6">
      <PageHeader titulo="Panel de trabajo" descripcion={descripcionContexto} />

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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <SkeletonTable rows={5} cols={5} />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <WidgetAlertas
              pedidosEstancados={estancadosQ.data?.length ?? 0}
              contratosPorVencer={contratosQ.data?.length ?? 0}
              metasRezagadas={metasRezagadasQ.data?.length ?? 0}
            />
            <WidgetPipeline macrofases={macrofasesPipeline} />
            <WidgetSaldos resumen={resumenQ.data ?? RESUMEN_VACIO} />
          </div>

          <UltimosPedidos pedidos={ultimosPedidos} />
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
