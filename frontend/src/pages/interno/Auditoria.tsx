/**
 * Registro de auditoría — admin-only (idea-principal §8).
 *
 * Ruta: /admin/auditoria — protegida por RequireRole="admin".
 *
 * Lectura de `logs.auditoria`: quién hizo qué, cuándo, desde dónde. Filtros por
 * acción y rango de fecha. La escritura de estos eventos ocurre en todo el
 * sistema (login, export, anotaciones, consultas sensibles…); esta pantalla
 * solo los consulta.
 */
import { useState } from 'react';
import { ScrollText, ShieldAlert } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { SectionCard } from '@/components/layout/SectionCard';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import { SkeletonTable } from '@/components/layout/LoadingSkeleton';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { formatFechaHora } from '@/lib/formatters';
import { useAccionesAuditoria, useAuditoria } from '@/features/auditoria/api';
import { etiquetaAccion, familiaAccion, type FamiliaAccion } from '@/features/auditoria/lib';
import type { AuditoriaItem, FiltrosAuditoria } from '@/features/auditoria/types';

const PAGE_SIZE = 50;

const FILTROS_VACIOS: FiltrosAuditoria = { accion: null, desde: null, hasta: null };

export default function Auditoria() {
  const [filtros, setFiltros] = useState<FiltrosAuditoria>(FILTROS_VACIOS);
  const [page, setPage] = useState(1);

  const accionesQ = useAccionesAuditoria();
  const listadoQ = useAuditoria({ ...filtros, page, size: PAGE_SIZE });

  function aplicar(parcial: Partial<FiltrosAuditoria>) {
    setFiltros((f) => ({ ...f, ...parcial }));
    setPage(1);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Registro de auditoría"
        descripcion="Rastro de acciones y consultas sensibles del sistema. Solo administración."
      />

      <SectionCard titulo="Filtros" icono={ScrollText} padding="sm">
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-foreground">Acción</span>
            <select
              className="h-9 rounded-md border border-border bg-background px-2 text-sm"
              value={filtros.accion ?? ''}
              onChange={(e) => aplicar({ accion: e.target.value || null })}
            >
              <option value="">Todas</option>
              {(accionesQ.data ?? []).map((a) => (
                <option key={a.accion} value={a.accion}>
                  {etiquetaAccion(a.accion)} ({a.total.toLocaleString('es-PE')})
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-foreground">Desde</span>
            <input
              type="date"
              className="h-9 rounded-md border border-border bg-background px-2 text-sm"
              value={filtros.desde ?? ''}
              onChange={(e) => aplicar({ desde: e.target.value || null })}
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-foreground">Hasta</span>
            <input
              type="date"
              className="h-9 rounded-md border border-border bg-background px-2 text-sm"
              value={filtros.hasta ?? ''}
              onChange={(e) => aplicar({ hasta: e.target.value || null })}
            />
          </label>

          {(filtros.accion || filtros.desde || filtros.hasta) ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setFiltros(FILTROS_VACIOS);
                setPage(1);
              }}
            >
              Limpiar
            </Button>
          ) : null}
        </div>
      </SectionCard>

      <SectionCard titulo="Eventos" icono={ShieldAlert} padding="sm" bodyClassName="p-0">
        {listadoQ.isLoading ? (
          <div className="p-4">
            <SkeletonTable rows={10} cols={5} />
          </div>
        ) : listadoQ.isError ? (
          <div className="p-4">
            <ErrorState
              titulo="No se pudo cargar el registro de auditoría"
              onReintentar={() => listadoQ.refetch()}
            />
          </div>
        ) : listadoQ.data ? (
          <TablaAuditoria
            items={listadoQ.data.items}
            total={listadoQ.data.total}
            page={page}
            size={PAGE_SIZE}
            onPageChange={setPage}
            isFetching={listadoQ.isFetching}
          />
        ) : null}
      </SectionCard>
    </div>
  );
}

const FAMILIA_ESTILO: Record<FamiliaAccion, string> = {
  fallo: 'bg-destructive/10 text-destructive',
  seguridad: 'bg-primary/10 text-primary',
  escritura: 'bg-secondary/15 text-foreground',
  consulta: 'bg-muted text-muted-foreground',
  neutro: 'bg-muted text-muted-foreground',
};

interface TablaProps {
  items: AuditoriaItem[];
  total: number;
  page: number;
  size: number;
  onPageChange: (page: number) => void;
  isFetching?: boolean;
}

function TablaAuditoria({ items, total, page, size, onPageChange, isFetching }: TablaProps) {
  const totalPaginas = Math.max(1, Math.ceil(total / size));

  if (total === 0) {
    return (
      <EmptyState
        titulo="Sin eventos"
        descripcion="No hay eventos de auditoría para los filtros seleccionados."
      />
    );
  }

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-3 text-sm text-muted-foreground">
        <span>
          <span className="font-semibold tabular-nums text-foreground">
            {total.toLocaleString('es-PE')}
          </span>{' '}
          eventos
        </span>
        {isFetching ? <span className="text-xs">Actualizando…</span> : null}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              <th className="px-4 py-2.5 text-left">Fecha y hora</th>
              <th className="px-4 py-2.5 text-left">Usuario</th>
              <th className="px-4 py-2.5 text-left">Acción</th>
              <th className="px-4 py-2.5 text-left">Detalle</th>
              <th className="px-4 py-2.5 text-left">Origen</th>
            </tr>
          </thead>
          <tbody>
            {items.map((e, i) => (
              <tr
                key={e.id}
                className={cn('border-t border-border align-top', i % 2 === 1 && 'bg-muted/20')}
              >
                <td className="whitespace-nowrap px-4 py-3 tabular-nums text-foreground">
                  {formatFechaHora(e.creado_en)}
                </td>
                <td className="px-4 py-3">
                  <span className="text-foreground">{e.usuario_nombre ?? '—'}</span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      'inline-block rounded px-1.5 py-0.5 text-[11px] font-medium',
                      FAMILIA_ESTILO[familiaAccion(e.accion)],
                    )}
                  >
                    {etiquetaAccion(e.accion)}
                  </span>
                </td>
                <td className="max-w-xs px-4 py-3">
                  {e.detalle && Object.keys(e.detalle).length > 0 ? (
                    <code className="block truncate font-mono text-[11px] text-muted-foreground" title={JSON.stringify(e.detalle)}>
                      {JSON.stringify(e.detalle)}
                    </code>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
                <td className="px-4 py-3 font-mono text-[11px] text-muted-foreground">
                  {e.ip ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between border-t border-border px-4 py-3">
        <span className="text-sm text-muted-foreground">
          Página {page} de {totalPaginas}
        </span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
            Anterior
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPaginas}
          >
            Siguiente
          </Button>
        </div>
      </div>
    </div>
  );
}
