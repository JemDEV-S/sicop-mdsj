/**
 * Dashboard Interno — Widgets de bienvenida (HU-22, T-44).
 *
 * Muestra:
 *  - Saludo personalizado con nombre y rol del funcionario
 *  - Widget de Alertas (pedidos estancados, contratos por vencer, metas rezagadas)
 *  - Widget de Pipeline (distribución por etapa)
 *  - Widget de Saldos (saldo disponible + semáforo)
 *  - Tabla de últimos pedidos de la unidad
 *  - Accesos rápidos a módulos
 *
 * Consume useDashboard() y useAuthStore (para el nombre del usuario).
 *
 * NOTA: Mientras el .bak de SIGA no esté disponible, este componente
 * solo podrá probarse con mocks (vi.mock en tests).
 */

import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Clock,
  FileText,
  GitBranch,
  Wallet,
} from 'lucide-react';
import { Link } from 'react-router-dom';

import Semaforo from '../../../components/Semaforo';
import { useAuthStore } from '../../../store/auth';
import { formatearMoneda, parseMonto, formatPorcentaje, formatFecha } from '../../../lib/formatters';
import { mapSemaforoApiToEstado } from '../../obras/api';
import { useDashboard } from '../api';
import type {
  AlertasResumen,
  PedidoReciente,
  PipelineResumen,
  SaldosResumen,
} from '../types';

// ─── Sub-componentes internos ─────────────────────────────────────────

function WidgetSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5 animate-pulse">
      <div className="h-4 bg-slate-200 rounded w-1/3 mb-4" />
      <div className="h-8 bg-slate-200 rounded w-2/3 mb-2" />
      <div className="h-3 bg-slate-200 rounded w-1/2" />
    </div>
  );
}

function WidgetError({ mensaje }: { mensaje: string }) {
  return (
    <div className="bg-white rounded-lg border border-red-200 p-5">
      <div className="flex items-center gap-2 text-red-600">
        <AlertTriangle className="w-4 h-4" />
        <span className="text-sm font-medium">Error</span>
      </div>
      <p className="mt-2 text-sm text-slate-600">{mensaje}</p>
    </div>
  );
}

// ─── Widget de Alertas ────────────────────────────────────────────────

function WidgetAlertas({ alertas }: { alertas: AlertasResumen }) {
  const total = alertas.pedidos_estancados + alertas.contratos_por_vencer + alertas.metas_rezagadas;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5" data-testid="widget-alertas">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-5 h-5 text-amber-500" />
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
          Alertas
        </h3>
      </div>

      {total === 0 ? (
        <p className="text-sm text-slate-500">Sin alertas pendientes</p>
      ) : (
        <div className="space-y-2">
          {alertas.pedidos_estancados > 0 && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Pedidos estancados</span>
              <span className="font-bold text-amber-600">{alertas.pedidos_estancados}</span>
            </div>
          )}
          {alertas.contratos_por_vencer > 0 && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Contratos por vencer</span>
              <span className="font-bold text-orange-600">{alertas.contratos_por_vencer}</span>
            </div>
          )}
          {alertas.metas_rezagadas > 0 && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Metas rezagadas</span>
              <span className="font-bold text-red-600">{alertas.metas_rezagadas}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Widget de Pipeline ───────────────────────────────────────────────

function WidgetPipeline({ pipeline }: { pipeline: PipelineResumen }) {
  const etapas = [
    { label: 'Solicitados', valor: pipeline.solicitados, color: 'bg-blue-500' },
    { label: 'Con orden', valor: pipeline.con_orden, color: 'bg-indigo-500' },
    { label: 'Conformidad', valor: pipeline.conformidad, color: 'bg-violet-500' },
    { label: 'Devengado', valor: pipeline.devengado, color: 'bg-emerald-500' },
    { label: 'Cerrado', valor: pipeline.cerrado, color: 'bg-slate-400' },
  ];
  const total = etapas.reduce((sum, e) => sum + e.valor, 0);

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5" data-testid="widget-pipeline">
      <div className="flex items-center gap-2 mb-3">
        <GitBranch className="w-5 h-5 text-indigo-500" />
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
          Pipeline
        </h3>
      </div>
      <p className="text-2xl font-bold text-slate-900 mb-3">{total} pedidos</p>

      {/* Barra de progreso segmentada */}
      {total > 0 && (
        <div className="flex h-2 rounded-full overflow-hidden mb-3">
          {etapas.map((e) => (
            e.valor > 0 && (
              <div
                key={e.label}
                className={`${e.color}`}
                style={{ width: `${(e.valor / total) * 100}%` }}
                title={`${e.label}: ${e.valor}`}
              />
            )
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-1.5">
        {etapas.map((e) => (
          <div key={e.label} className="flex items-center gap-1.5 text-xs text-slate-600">
            <div className={`w-2 h-2 rounded-full ${e.color}`} />
            <span>{e.label}</span>
            <span className="font-semibold ml-auto">{e.valor}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Widget de Saldos ─────────────────────────────────────────────────

function WidgetSaldos({ saldos }: { saldos: SaldosResumen }) {
  const semaforoEstado = mapSemaforoApiToEstado(saldos.semaforo ?? 'desconocido');
  const saldoFormateado = formatearMoneda(parseMonto(saldos.saldo_disponible));
  const porcentaje = formatPorcentaje(saldos.porcentaje_ejecucion);

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5" data-testid="widget-saldos">
      <div className="flex items-center gap-2 mb-3">
        <Wallet className="w-5 h-5 text-emerald-500" />
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
          Saldo de la Unidad
        </h3>
      </div>

      <p className="text-2xl font-bold text-slate-900 mb-1">{saldoFormateado}</p>
      <p className="text-sm text-slate-500 mb-3">
        Ejecución: {porcentaje}
      </p>

      {semaforoEstado && (
        <Semaforo
          estado={semaforoEstado}
          texto={semaforoEstado === 'ok' ? 'Normal' : semaforoEstado === 'alerta' ? 'Atención' : 'Crítico'}
        />
      )}
    </div>
  );
}

// ─── Tabla de Últimos Pedidos ─────────────────────────────────────────

function TablaPedidos({ pedidos }: { pedidos: PedidoReciente[] }) {
  if (pedidos.length === 0) {
    return (
      <p className="text-sm text-slate-500 py-4 text-center">
        No hay pedidos recientes.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" data-testid="tabla-pedidos">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">N° Pedido</th>
            <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Descripción</th>
            <th className="text-right py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Monto</th>
            <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Estado</th>
            <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase">Fecha</th>
          </tr>
        </thead>
        <tbody>
          {pedidos.map((p) => (
            <tr key={p.nro_pedido} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="py-2 px-3 font-medium text-slate-800">{p.nro_pedido}</td>
              <td className="py-2 px-3 text-slate-600">{p.descripcion}</td>
              <td className="py-2 px-3 text-right font-medium text-slate-800">
                {formatearMoneda(parseMonto(p.monto))}
              </td>
              <td className="py-2 px-3">
                <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                  {p.estado}
                </span>
              </td>
              <td className="py-2 px-3 text-slate-500">{formatFecha(p.fecha)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Accesos Rápidos ──────────────────────────────────────────────────

function AccesosRapidos() {
  const accesos = [
    { label: 'Pipeline', icon: GitBranch, href: '/interno/pipeline' },
    { label: 'Saldos', icon: Wallet, href: '/interno/saldos' },
    { label: 'Reportes', icon: FileText, href: '/interno/reportes' },
    { label: 'Ejecución', icon: BarChart3, href: '/ejecucion' },
  ];

  return (
    <div className="flex flex-wrap gap-3" data-testid="accesos-rapidos">
      {accesos.map((a) => (
        <Link
          key={a.label}
          to={a.href}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors"
        >
          <a.icon className="w-4 h-4" />
          {a.label}
          <ArrowRight className="w-3 h-3 ml-1 text-slate-400" />
        </Link>
      ))}
    </div>
  );
}

// ─── Componente Principal ─────────────────────────────────────────────

export default function DashboardWidgets() {
  const user = useAuthStore((s) => s.user);
  const { data, isLoading, isError, error } = useDashboard();

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
      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <WidgetAlertas alertas={data.alertas} />
            <WidgetPipeline pipeline={data.pipeline} />
            <WidgetSaldos saldos={data.saldos} />
          </div>

          {/* Últimos pedidos */}
          <div className="bg-white rounded-lg border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Clock className="w-5 h-5 text-slate-500" />
              <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
                Últimos pedidos de mi unidad
              </h2>
            </div>
            <TablaPedidos pedidos={data.ultimos_pedidos} />
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
}
