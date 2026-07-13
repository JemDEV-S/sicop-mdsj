import re

with open('frontend/src/features/dashboard/secciones/DashboardWidgets.tsx', 'r') as f:
    content = f.read()

# Replace imports
content = content.replace("import { useDashboard } from '../api';", "import { useKanban, useSaldos, usePedidosEstancados } from '../api';\nimport { useMemo } from 'react';")
# If it wasn't replaced (maybe it's ../api without useDashboard? no, the diff shows it was there), let's just use re.
content = re.sub(
    r"import \{ useDashboard \} from '\.\./api';",
    "import { useKanban, useSaldos, usePedidosEstancados } from '../api';\nimport { useMemo } from 'react';",
    content
)

# Remove DashboardResponse from types import if it exists
content = re.sub(
    r"import type \{ [^}]*DashboardResponse[^}]* \} from '\.\./types';\n",
    "",
    content
)

# Rewrite the component
new_component = """export default function DashboardWidgets() {
  const user = useAuthStore((s) => s.user);
  
  const { data: kanban, isLoading: isLoadingK, isError: isErrorK, error: errorK } = useKanban();
  const { data: saldosData, isLoading: isLoadingS, isError: isErrorS, error: errorS } = useSaldos({ page: 1, size: 100 });
  const { data: estancados, isLoading: isLoadingE, isError: isErrorE, error: errorE } = usePedidosEstancados();

  const isLoading = isLoadingK || isLoadingS || isLoadingE;
  const isError = isErrorK || isErrorS || isErrorE;
  const error = errorK || errorS || errorE;

  // Transformaciones
  const alertasResumen = useMemo(() => {
    return {
      pedidos_estancados: estancados?.length || 0,
      contratos_por_vencer: 0, // Pendiente de endpoint real
      metas_rezagadas: 0, // Pendiente de endpoint real
    };
  }, [estancados]);

  const pipelineResumen = useMemo(() => {
    if (!kanban) return { solicitados: 0, con_orden: 0, conformidad: 0, devengado: 0, cerrado: 0 };
    return {
      solicitados: kanban.solicitado.length,
      con_orden: kanban.con_orden.length,
      conformidad: kanban.conformidad.length,
      devengado: kanban.devengado.length,
      cerrado: kanban.cerrado.length,
    };
  }, [kanban]);

  const saldosResumen = useMemo(() => {
    if (!saldosData || !saldosData.items) return { saldo_disponible: 0, pim_total: 0, devengado_total: 0, porcentaje_ejecucion: 0, semaforo: 'desconocido' };
    let pim_total = 0;
    let devengado_total = 0;
    let saldo_disponible = 0;
    
    saldosData.items.forEach(item => {
      pim_total += item.pim || 0;
      devengado_total += item.devengado || 0;
      saldo_disponible += item.saldo_disponible || 0;
    });
    
    const porcentaje_ejecucion = pim_total > 0 ? (devengado_total / pim_total) * 100 : 0;
    
    // Semáforo global basado en el porcentaje
    let semaforo = 'ok';
    if (porcentaje_ejecucion < 40) semaforo = 'critico';
    else if (porcentaje_ejecucion < 70) semaforo = 'alerta';

    return {
      saldo_disponible,
      pim_total,
      devengado_total,
      porcentaje_ejecucion,
      semaforo
    };
  }, [saldosData]);

  const ultimosPedidos = useMemo(() => {
    if (!kanban) return [];
    // Unir todos los pedidos del kanban
    const todos = [
      ...kanban.solicitado,
      ...kanban.con_orden,
      ...kanban.conformidad,
      ...kanban.devengado,
      ...kanban.cerrado
    ];
    // Ordenar por fecha_pedido (mas reciente primero)
    todos.sort((a, b) => {
      if (!a.fecha_pedido) return 1;
      if (!b.fecha_pedido) return -1;
      return new Date(b.fecha_pedido).getTime() - new Date(a.fecha_pedido).getTime();
    });
    
    // Tomar los 5 mas recientes y mapear a lo que espera TablaPedidos
    return todos.slice(0, 5).map(p => ({
      nro_pedido: p.nro_pedido.toString(),
      monto: p.monto_total,
      descripcion: p.motivo || 'Sin descripción',
      estado: p.etapa,
      fecha: p.fecha_pedido || null,
    }));
  }, [kanban]);

  return (
    <div className="space-y-6">
      {/* Saludo */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Bienvenido{user?.nombre_completo ? `, ${user.nombre_completo}` : ''}
        </h1>
        {user?.rol && (
          <p className="text-sm text-slate-500 mt-1">
            {user.rol.nombre}
            {/* TODO: agregar user.area cuando el backend lo devuelva */}
          </p>
        )}
      </div>

      {/* Estado de carga / error */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <WidgetSkeleton />
          <WidgetSkeleton />
          <WidgetSkeleton />
        </div>
      )}

      {isError && (
        <WidgetError
          mensaje={
            error instanceof Error
              ? error.message
              : 'No se pudo cargar el dashboard. Intente nuevamente.'
          }
        />
      )}

      {/* Widgets principales */}
      {(!isLoading && !isError) && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <WidgetAlertas alertas={alertasResumen} />
            <WidgetPipeline pipeline={pipelineResumen} />
            <WidgetSaldos saldos={saldosResumen as any} />
          </div>

          {/* Últimos pedidos */}
          <div className="bg-white rounded-lg border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Clock className="w-5 h-5 text-slate-500" />
              <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
                Últimos pedidos de mi unidad
              </h2>
            </div>
            <TablaPedidos pedidos={ultimosPedidos as any} />
          </div>

          {/* Accesos rápidos (AC-22.3) */}
          <div>
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-3">
              Accesos rápidos
            </h2>
            <AccesosRapidos />
          </div>
        </>
      )}
    </div>
  );
}"""

content = re.sub(r"export default function DashboardWidgets\(\) \{.*", new_component, content, flags=re.DOTALL)

with open('frontend/src/features/dashboard/secciones/DashboardWidgets.tsx', 'w') as f:
    f.write(content)

