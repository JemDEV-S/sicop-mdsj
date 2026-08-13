/**
 * Estado de sincronizaciones — admin-only.
 *
 * Ruta: /admin/sincronizacion — protegida por RequireRole="admin".
 *
 * Responde "¿están corriendo las sincronizaciones?" de forma confiable:
 *   - si el scheduler embebido (APScheduler) está activo y sus próximas corridas;
 *   - la edad real del dato más reciente por fuente (semáforo de frescura);
 *   - el historial de corridas persistidas en `logs.sincronizacion` (auto +
 *     manual, sobrevive reinicios);
 *   - las corridas manuales de esta instancia.
 *
 * Auto-refresca cada 15s. Los administradores pueden forzar SIAF / Invierte.
 */
import {
  Activity,
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Database,
  History,
  RefreshCw,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { SectionCard } from '@/components/layout/SectionCard';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import { SkeletonTable } from '@/components/layout/LoadingSkeleton';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { formatFechaHora } from '@/lib/formatters';
import { useEstadoSincronizacion, useTriggerSync } from '@/features/sincronizacion/api';
import {
  duracion,
  enCuanto,
  ESTADO_ESTILO,
  ESTADO_ETIQUETA,
  etiquetaJob,
  frescura,
  FRESCURA_ESTILO,
  haceCuanto,
} from '@/features/sincronizacion/lib';
import type {
  CorridaPersistida,
  EstadoCorrida,
  JobProgramado,
  SnapshotFuente,
} from '@/features/sincronizacion/types';

const FRESCURA_ETIQUETA = {
  fresco: 'Al día',
  atencion: 'Atención',
  viejo: 'Desactualizado',
  sin_datos: 'Sin datos',
} as const;

export default function Sincronizacion() {
  const estadoQ = useEstadoSincronizacion();
  const trigger = useTriggerSync();

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Estado de sincronizaciones"
        descripcion="Salud del scheduler, frescura de los datos y últimas corridas de los procesos de sincronización SIAF, Invierte y SIGA."
        acciones={
          <div className="flex items-center gap-2">
            {estadoQ.isFetching ? (
              <span className="text-xs text-muted-foreground">Actualizando…</span>
            ) : null}
            <Button
              variant="outline"
              size="sm"
              onClick={() => estadoQ.refetch()}
              disabled={estadoQ.isFetching}
            >
              <RefreshCw className={cn('mr-1.5 h-4 w-4', estadoQ.isFetching && 'animate-spin')} />
              Refrescar
            </Button>
          </div>
        }
      />

      {estadoQ.isLoading ? (
        <SectionCard titulo="Cargando" icono={Activity} padding="sm" bodyClassName="p-4">
          <SkeletonTable rows={6} cols={4} />
        </SectionCard>
      ) : estadoQ.isError ? (
        <ErrorState
          titulo="No se pudo cargar el estado de sincronización"
          onReintentar={() => estadoQ.refetch()}
        />
      ) : estadoQ.data ? (
        <>
          {/* ── Estado del scheduler ─────────────────────────────────── */}
          <SchedulerBanner activo={estadoQ.data.scheduler_activo} />

          {/* ── Frescura de datos por fuente ─────────────────────────── */}
          <SectionCard titulo="Frescura de los datos" icono={Database} padding="sm">
            {estadoQ.data.snapshots.length === 0 ? (
              <EmptyState titulo="Sin fuentes" descripcion="No hay fuentes configuradas." />
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {estadoQ.data.snapshots.map((s) => (
                  <TarjetaSnapshot key={s.fuente} snapshot={s} />
                ))}
              </div>
            )}
          </SectionCard>

          {/* ── Próximas corridas programadas ────────────────────────── */}
          <SectionCard
            titulo="Corridas programadas"
            icono={CalendarClock}
            padding="sm"
            bodyClassName="p-0"
          >
            <TablaProgramadas jobs={estadoQ.data.jobs_programados} />
          </SectionCard>

          {/* ── Disparo manual ───────────────────────────────────────── */}
          <SectionCard titulo="Forzar sincronización" icono={RefreshCw} padding="sm">
            <p className="mb-3 text-sm text-muted-foreground">
              Dispara una corrida ahora mismo. Se ejecuta en segundo plano; el
              resultado aparecerá abajo cuando termine.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                size="sm"
                onClick={() => trigger.mutate('sincronizar-siaf')}
                disabled={trigger.isPending}
              >
                Sincronizar SIAF ahora
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => trigger.mutate('sincronizar-invierte')}
                disabled={trigger.isPending}
              >
                Sincronizar Invierte ahora
              </Button>
              {trigger.isSuccess ? (
                <span className="text-xs text-emerald-600 dark:text-emerald-400">
                  Corrida encolada.
                </span>
              ) : null}
              {trigger.isError ? (
                <span className="text-xs text-destructive">No se pudo encolar.</span>
              ) : null}
            </div>
          </SectionCard>

          {/* ── Historial de corridas ────────────────────────────────── */}
          <SectionCard
            titulo="Últimas corridas"
            icono={History}
            padding="sm"
            bodyClassName="p-0"
          >
            <TablaCorridas corridas={estadoQ.data.ultimas_corridas} />
          </SectionCard>
        </>
      ) : null}
    </div>
  );
}

function SchedulerBanner({ activo }: { activo: boolean }) {
  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-md border p-4',
        activo
          ? 'border-emerald-500/30 bg-emerald-500/5'
          : 'border-destructive/30 bg-destructive/5',
      )}
    >
      {activo ? (
        <CheckCircle2 className="h-6 w-6 shrink-0 text-emerald-600 dark:text-emerald-400" />
      ) : (
        <AlertTriangle className="h-6 w-6 shrink-0 text-destructive" />
      )}
      <div>
        <p className="font-semibold text-foreground">
          {activo ? 'Scheduler activo' : 'Scheduler detenido'}
        </p>
        <p className="text-sm text-muted-foreground">
          {activo
            ? 'Los procesos automáticos están programados y corriendo dentro del backend.'
            : 'Ninguna corrida automática está agendada. Revisa que el backend esté en marcha.'}
        </p>
      </div>
    </div>
  );
}

function TarjetaSnapshot({ snapshot }: { snapshot: SnapshotFuente }) {
  const f = snapshot.ok ? frescura(snapshot.ultimo_sync) : 'sin_datos';
  return (
    <div className="rounded-md border border-border bg-background p-3">
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-medium text-foreground">{snapshot.fuente}</span>
        <span
          className={cn(
            'shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium',
            FRESCURA_ESTILO[f],
          )}
        >
          {FRESCURA_ETIQUETA[f]}
        </span>
      </div>
      <p className="mt-2 text-sm tabular-nums text-foreground">
        {haceCuanto(snapshot.ultimo_sync)}
      </p>
      <p className="text-xs text-muted-foreground">
        {snapshot.ok ? formatFechaHora(snapshot.ultimo_sync) : 'No se pudo leer la tabla'}
      </p>
    </div>
  );
}

function TablaProgramadas({ jobs }: { jobs: JobProgramado[] }) {
  if (jobs.length === 0) {
    return (
      <EmptyState
        titulo="Sin corridas programadas"
        descripcion="El scheduler no tiene jobs agendados (o está detenido)."
      />
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            <th className="px-4 py-2.5 text-left">Proceso</th>
            <th className="px-4 py-2.5 text-left">Próxima corrida</th>
            <th className="px-4 py-2.5 text-left">Programación</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((j, i) => (
            <tr key={j.id} className={cn('border-t border-border', i % 2 === 1 && 'bg-muted/20')}>
              <td className="px-4 py-3 text-foreground">{j.nombre}</td>
              <td className="whitespace-nowrap px-4 py-3">
                <span className="text-foreground">{enCuanto(j.proxima_ejecucion)}</span>
                <span className="ml-2 text-xs text-muted-foreground">
                  {j.proxima_ejecucion ? formatFechaHora(j.proxima_ejecucion) : ''}
                </span>
              </td>
              <td className="px-4 py-3">
                <code className="font-mono text-[11px] text-muted-foreground">{j.trigger}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TablaCorridas({ corridas }: { corridas: CorridaPersistida[] }) {
  if (corridas.length === 0) {
    return (
      <EmptyState
        titulo="Sin corridas registradas"
        descripcion="Aún no hay corridas en el historial (logs.sincronizacion)."
      />
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            <th className="px-4 py-2.5 text-left">Proceso</th>
            <th className="px-4 py-2.5 text-left">Inicio</th>
            <th className="px-4 py-2.5 text-left">Duración</th>
            <th className="px-4 py-2.5 text-left">Estado</th>
            <th className="px-4 py-2.5 text-right">Registros</th>
            <th className="px-4 py-2.5 text-left">Detalle</th>
          </tr>
        </thead>
        <tbody>
          {corridas.map((c, i) => {
            const dur = duracion(c.inicio, c.fin);
            const est = c.estado as EstadoCorrida;
            return (
              <tr
                key={c.id}
                className={cn('border-t border-border align-top', i % 2 === 1 && 'bg-muted/20')}
              >
                <td className="px-4 py-3 text-foreground">{etiquetaJob(c.job)}</td>
                <td className="whitespace-nowrap px-4 py-3 tabular-nums text-foreground">
                  {formatFechaHora(c.inicio)}
                </td>
                <td className="whitespace-nowrap px-4 py-3 tabular-nums text-muted-foreground">
                  {dur ?? (est === 'en_curso' ? '…' : '—')}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      'inline-block rounded px-1.5 py-0.5 text-[11px] font-medium',
                      ESTADO_ESTILO[est] ?? 'bg-muted text-muted-foreground',
                    )}
                  >
                    {ESTADO_ETIQUETA[est] ?? c.estado}
                  </span>
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-right tabular-nums text-foreground">
                  {c.registros_procesados?.toLocaleString('es-PE') ?? '—'}
                </td>
                <td className="max-w-xs px-4 py-3">
                  {c.error_mensaje ? (
                    <code
                      className="block truncate font-mono text-[11px] text-destructive"
                      title={c.error_mensaje}
                    >
                      {c.error_mensaje}
                    </code>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
