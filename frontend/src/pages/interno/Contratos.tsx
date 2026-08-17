/**
 * Contratos + alerta de contratos por vencer (HU-19/HU-20 · T-53).
 *
 * Ruta: /interno/contratos — protegida por RequireAuth.
 *
 * Arriba la alerta de contratos por vencer (HU-20); abajo el listado completo.
 * `valor_soles` es el compromiso marco del contrato — NO lo ejecutado (eso son
 * las órdenes del proveedor). Los contratos son transversales a la entidad (no
 * filtran por CC — ver guía §5.2).
 */
import { useState } from 'react';
import { FileSignature, CalendarClock, AlertTriangle } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { SectionCard } from '@/components/layout/SectionCard';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import { SkeletonTable, SkeletonBloque } from '@/components/layout/LoadingSkeleton';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { formatearMoneda, formatFecha } from '@/lib/formatters';
import { useContextoInterno } from '@/store/contexto-interno';
import { useContratos, useContratosPorVencer } from '@/features/provint/api';
import { tipoBienLabel, urgenciaVencimiento, refContrato, type UrgenciaVencimiento } from '@/features/provint/lib';
import type { ContratoItem, ContratoPorVencer } from '@/features/provint/types';

const PAGE_SIZE = 25;
const DIAS_ALERTA = 30;

export default function Contratos() {
  const año = useContextoInterno((s) => s.añoActivo);
  const [page, setPage] = useState(1);

  const vencerQ = useContratosPorVencer(DIAS_ALERTA);
  const listadoQ = useContratos({ page, size: PAGE_SIZE, estado: null });

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Contratos"
        descripcion={
          <>
            Contratos de la entidad y alerta de vencimientos.{' '}
            <span className="text-muted-foreground">Año {año}</span>
          </>
        }
      />

      {/* Alerta de contratos por vencer (HU-20) */}
      <SectionCard
        titulo={`Por vencer (≤ ${DIAS_ALERTA} días)`}
        icono={CalendarClock}
        padding="sm"
        bodyClassName="p-0"
      >
        {vencerQ.isLoading ? (
          <div className="p-4">
            <SkeletonBloque className="h-24 w-full" />
          </div>
        ) : vencerQ.isError ? (
          <div className="p-4">
            <ErrorState
              titulo="No se pudo cargar la alerta de vencimientos"
              onReintentar={() => vencerQ.refetch()}
            />
          </div>
        ) : (vencerQ.data?.length ?? 0) === 0 ? (
          <EmptyState
            titulo="Sin contratos por vencer"
            descripcion={`Ningún contrato vence en los próximos ${DIAS_ALERTA} días para la fecha de referencia del año ${año}.`}
          />
        ) : (
          <ListaPorVencer contratos={vencerQ.data ?? []} />
        )}
      </SectionCard>

      {/* Listado completo (HU-19) */}
      <SectionCard titulo="Todos los contratos" icono={FileSignature} padding="sm" bodyClassName="p-0">
        {listadoQ.isLoading ? (
          <div className="p-4">
            <SkeletonTable rows={8} cols={5} />
          </div>
        ) : listadoQ.isError ? (
          <div className="p-4">
            <ErrorState
              titulo="No se pudieron cargar los contratos"
              onReintentar={() => listadoQ.refetch()}
            />
          </div>
        ) : listadoQ.data ? (
          <TablaContratos
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

const URGENCIA_ESTILO: Record<UrgenciaVencimiento, { borde: string; texto: string }> = {
  critico: { borde: 'border-l-destructive', texto: 'text-destructive' },
  alerta: { borde: 'border-l-[var(--semaforo-alerta)]', texto: 'text-foreground' },
  neutro: { borde: 'border-l-border', texto: 'text-muted-foreground' },
};

function ListaPorVencer({ contratos }: { contratos: ContratoPorVencer[] }) {
  return (
    <ul className="divide-y divide-border">
      {contratos.map((c) => {
        const urgencia = urgenciaVencimiento(c.dias_restantes);
        const estilo = URGENCIA_ESTILO[urgencia];
        return (
          <li
            key={`${c.nro_contrato}-${c.ano_eje}-${c.sec_contrato}`}
            className={cn('flex flex-col gap-2 border-l-4 px-4 py-3 sm:flex-row sm:items-center sm:justify-between', estilo.borde)}
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-semibold text-foreground">
                  {refContrato(c.nro_contrato, c.ano_eje)}
                </span>
                <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {tipoBienLabel(c.tipo_bien)}
                </span>
              </div>
              <p className="mt-0.5 truncate text-sm text-foreground" title={c.proveedor_nombre ?? ''}>
                {c.proveedor_nombre ?? 'Sin proveedor'}
              </p>
            </div>

            <div className="flex items-center gap-4 sm:gap-6">
              <div className="text-right">
                <p className="text-xs text-muted-foreground">Vence</p>
                <p className="text-sm font-medium tabular-nums text-foreground">
                  {formatFecha(c.fecha_final)}
                </p>
              </div>
              <div className={cn('flex items-center gap-1.5 text-right font-semibold', estilo.texto)}>
                {urgencia === 'critico' ? (
                  <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                ) : null}
                <span className="tabular-nums">{c.dias_restantes ?? '—'} días</span>
              </div>
              {c.proveedor_ruc ? (
                <span className="font-mono text-[11px] text-muted-foreground">
                  RUC {c.proveedor_ruc}
                </span>
              ) : null}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

interface TablaContratosProps {
  items: ContratoItem[];
  total: number;
  page: number;
  size: number;
  onPageChange: (page: number) => void;
  isFetching?: boolean;
}

function TablaContratos({ items, total, page, size, onPageChange, isFetching }: TablaContratosProps) {
  const totalPaginas = Math.max(1, Math.ceil(total / size));
  const desde = total === 0 ? 0 : (page - 1) * size + 1;
  const hasta = Math.min(page * size, total);

  if (total === 0) {
    return (
      <EmptyState
        titulo="Sin contratos"
        descripcion="No hay contratos registrados para el año seleccionado."
      />
    );
  }

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-3 text-sm text-muted-foreground">
        <span>
          Mostrando <span className="font-semibold tabular-nums text-foreground">{desde}</span>–
          <span className="font-semibold tabular-nums text-foreground">{hasta}</span> de{' '}
          <span className="font-semibold tabular-nums text-foreground">
            {total.toLocaleString('es-PE')}
          </span>{' '}
          contratos
        </span>
        {isFetching ? <span className="text-xs">Actualizando…</span> : null}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              <th className="px-4 py-2.5 text-left">Contrato</th>
              <th className="px-4 py-2.5 text-left">Proveedor</th>
              <th className="px-4 py-2.5 text-right">Valor (marco)</th>
              <th className="px-4 py-2.5 text-left">Vigencia</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c, i) => (
              <tr
                key={`${c.nro_contrato}-${c.ano_eje}-${c.sec_contrato}`}
                className={cn('border-t border-border align-top', i % 2 === 1 && 'bg-muted/20')}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-xs font-semibold text-foreground">
                      {refContrato(c.nro_contrato, c.ano_eje)}
                    </span>
                    <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                      {tipoBienLabel(c.tipo_bien)}
                    </span>
                  </div>
                  {c.nro_documento ? (
                    <p className="text-[11px] text-muted-foreground">{c.nro_documento}</p>
                  ) : null}
                </td>
                <td className="px-4 py-3">
                  <span className="text-foreground">{c.proveedor_nombre ?? '—'}</span>
                  {c.proveedor_ruc ? (
                    <p className="font-mono text-[11px] text-muted-foreground">RUC {c.proveedor_ruc}</p>
                  ) : null}
                </td>
                <td className="px-4 py-3 text-right font-medium tabular-nums text-foreground">
                  {c.valor_soles != null ? formatearMoneda(c.valor_soles, true) : '—'}
                </td>
                <td className="px-4 py-3 text-xs text-muted-foreground">
                  {formatFecha(c.fecha_inicial)} → {formatFecha(c.fecha_final)}
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
