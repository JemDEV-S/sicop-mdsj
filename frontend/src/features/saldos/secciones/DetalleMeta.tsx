import { GitCompareArrows } from 'lucide-react';
import { useDetalleMeta } from '../api';
import { formatearMoneda } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import type { ClasificadorDetalle, FuenteDetalle } from '../types';

interface DetalleMetaProps {
  secFunc: number;
  /** Nº de columnas de la tabla contenedora, para el colSpan de la fila. */
  colSpan: number;
  /** Abre el modal de cruce SIAF-SIGA filtrado a un clasificador. */
  onVerCruceClasif: (codigo: string, nombre: string | null) => void;
}

/**
 * Panel de detalle de una meta, embebido como fila expandible. Muestra el
 * detalle OPERATIVO del SIGA (qué se compra en cada clasificador), jerarquizado
 * por fuente de financiamiento:
 *
 *   Fuente de financiamiento
 *     └─ Clasificador de gasto (nombre) — PIM, comprometido, saldo por comprometer
 *
 * NO es presupuesto (eso es la cabecera SIAF de la fila): es el desglose del
 * gasto que el SIGA sí maneja bien. Se muestran TODOS los clasificadores,
 * incluidos los de PIM 0 (marcados "sin techo"), para no ocultar líneas del plan.
 */
export function DetalleMeta({ secFunc, colSpan, onVerCruceClasif }: DetalleMetaProps) {
  const { data, isLoading, isError } = useDetalleMeta(secFunc);

  return (
    <tr>
      <td colSpan={colSpan} className="border-b border-border bg-muted/10 px-4 py-4">
        <p className="mb-3 text-xs text-muted-foreground">
          <span className="font-semibold text-foreground">Detalle del gasto (SIGA)</span>{' '}
          — composición operativa por fuente y clasificador. El presupuesto oficial
          es el de la fila (SIAF).
        </p>
        {isLoading ? (
          <div className="space-y-2">
            <div className="h-4 w-48 animate-pulse rounded bg-muted" />
            <div className="h-24 w-full animate-pulse rounded bg-muted" />
          </div>
        ) : isError || !data ? (
          <p className="text-sm text-muted-foreground">
            No se pudo cargar el detalle de esta meta.
          </p>
        ) : data.fuentes.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Esta meta no tiene líneas de clasificador en el SIGA.
          </p>
        ) : (
          <div className="space-y-4">
            {data.fuentes.map((f) => (
              <ArbolFuente
                key={f.fuente_codigo ?? Math.random()}
                fuente={f}
                onVerCruceClasif={onVerCruceClasif}
              />
            ))}
          </div>
        )}
      </td>
    </tr>
  );
}

function ArbolFuente({
  fuente,
  onVerCruceClasif,
}: {
  fuente: FuenteDetalle;
  onVerCruceClasif: (codigo: string, nombre: string | null) => void;
}) {
  return (
    <div className="overflow-hidden rounded-md border border-border">
      {/* Cabecera de la fuente */}
      <div className="flex items-center justify-between gap-3 bg-muted/40 px-3 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="rounded bg-background px-1.5 py-0.5 font-mono text-[11px] font-semibold text-muted-foreground">
            {fuente.fuente_codigo ?? '—'}
          </span>
          <span className="truncate text-sm font-semibold text-foreground">
            {fuente.fuente_nombre ?? 'Sin fuente'}
          </span>
          <span className="shrink-0 text-[11px] text-muted-foreground">
            · {fuente.n_clasificadores} clasificador
            {fuente.n_clasificadores === 1 ? '' : 'es'}
          </span>
        </div>
        <span className="shrink-0 text-sm font-semibold tabular-nums text-foreground">
          {formatearMoneda(fuente.pim, true)}
        </span>
      </div>

      {/* Clasificadores */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              <th className="px-3 py-2 text-left">Clasificador de gasto</th>
              <th className="px-3 py-2 text-right">PIM</th>
              <th className="px-3 py-2 text-right" title="Certificado SIGA">
                Certificado
              </th>
              <th className="px-3 py-2 text-right" title="Comprometido SIGA">
                Comprometido
              </th>
              <th className="px-3 py-2 text-right" title="PIM − comprometido">
                Por comprometer
              </th>
              <th className="px-3 py-2 text-right" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {fuente.clasificadores.map((c) => (
              <FilaClasificador
                key={c.codigo ?? c.nombre ?? Math.random()}
                c={c}
                onVerCruceClasif={onVerCruceClasif}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FilaClasificador({
  c,
  onVerCruceClasif,
}: {
  c: ClasificadorDetalle;
  onVerCruceClasif: (codigo: string, nombre: string | null) => void;
}) {
  const codigo = c.codigo?.replace(/\s+/g, ' ').trim() ?? '—';
  return (
    <tr className={cn('group', c.sin_pim && 'opacity-60')}>
      <td className="max-w-[26rem] px-3 py-2">
        <div className="flex items-baseline gap-2">
          <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
            {codigo}
          </span>
          <span className="truncate text-foreground" title={c.nombre ?? ''}>
            {c.nombre ?? 'Sin descripción'}
          </span>
          {c.sin_pim ? (
            <span
              className="shrink-0 rounded-full bg-muted px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide text-muted-foreground"
              title="Línea del plan sin techo asignado (PIM 0)."
            >
              sin techo
            </span>
          ) : null}
        </div>
      </td>
      <td className="px-3 py-2 text-right tabular-nums">
        {formatearMoneda(c.pim, true)}
      </td>
      <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
        {formatearMoneda(c.certificado, true)}
      </td>
      <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
        {formatearMoneda(c.comprometido, true)}
      </td>
      <td className="px-3 py-2 text-right tabular-nums">
        {formatearMoneda(c.saldo_por_comprometer, true)}
      </td>
      <td className="px-3 py-2 text-right">
        {c.codigo ? (
          <button
            type="button"
            onClick={() => onVerCruceClasif(c.codigo!, c.nombre)}
            className="inline-flex items-center gap-1 whitespace-nowrap text-[11px] text-primary hover:underline"
            title="Ver órdenes, certificaciones y pedidos de este clasificador"
          >
            <GitCompareArrows className="h-3 w-3" aria-hidden="true" /> Cruce
          </button>
        ) : null}
      </td>
    </tr>
  );
}

export default DetalleMeta;
