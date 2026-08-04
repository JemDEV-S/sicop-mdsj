import { CheckCircle2, Ban, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatearMoneda, formatFecha } from '@/lib/formatters';
import {
  tipoBienLabel,
  ordenAnulada,
  ordenDevengadaSiaf,
} from '../lib';
import type {
  CertificacionItem,
  OrdenCruceItem,
  PedidoOrigenItem,
} from '../types';

const NUM_ORDEN = (o: OrdenCruceItem) => `${o.nro_orden}-${o.ano_eje}`;

/** Panel de órdenes de adquisición: proveedor, monto, estado SIAF, contrato. */
export function TablaOrdenes({ ordenes }: { ordenes: OrdenCruceItem[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            <th className="px-4 py-2.5 text-left">Orden</th>
            <th className="px-4 py-2.5 text-left">Proveedor</th>
            <th className="px-4 py-2.5 text-right">Importe</th>
            <th className="px-4 py-2.5 text-left">SIAF</th>
            <th className="px-4 py-2.5 text-left">Estado</th>
          </tr>
        </thead>
        <tbody>
          {ordenes.map((o, i) => {
            const anulada = ordenAnulada(o.estado);
            const devengada = ordenDevengadaSiaf(o.estado_siaf);
            return (
              <tr
                key={`${o.nro_orden}-${o.ano_eje}`}
                className={cn('border-t border-border align-top', i % 2 === 1 && 'bg-muted/20')}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-xs font-semibold text-foreground">
                      {NUM_ORDEN(o)}
                    </span>
                    <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                      {tipoBienLabel(o.tipo_bien)}
                    </span>
                  </div>
                  {o.concepto ? (
                    <p className="mt-1 line-clamp-2 max-w-md text-xs text-muted-foreground" title={o.concepto}>
                      {o.concepto}
                    </p>
                  ) : null}
                  {o.nro_contrato != null ? (
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      Contrato {o.nro_contrato}
                      {o.ano_contrato ? `-${o.ano_contrato}` : ''}
                    </p>
                  ) : null}
                </td>
                <td className="px-4 py-3">
                  <p className="text-foreground">{o.proveedor_nombre ?? '—'}</p>
                  {o.proveedor_ruc ? (
                    <p className="font-mono text-[11px] text-muted-foreground">RUC {o.proveedor_ruc}</p>
                  ) : null}
                </td>
                <td className="px-4 py-3 text-right font-medium tabular-nums text-foreground">
                  {o.total_fact_soles != null ? formatearMoneda(o.total_fact_soles, true) : '—'}
                  {o.fecha_orden ? (
                    <p className="text-[11px] font-normal text-muted-foreground">
                      {formatFecha(o.fecha_orden)}
                    </p>
                  ) : null}
                </td>
                <td className="px-4 py-3">
                  {devengada ? (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-secondary">
                      <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                      Devengado
                    </span>
                  ) : (
                    <span
                      className="text-xs text-muted-foreground"
                      title={`Estado SIAF: ${o.estado_siaf ?? 'sin dato'}`}
                    >
                      Pendiente
                    </span>
                  )}
                  {o.exp_siaf ? (
                    <p className="font-mono text-[11px] text-muted-foreground">
                      EXP {o.exp_siaf}
                    </p>
                  ) : null}
                </td>
                <td className="px-4 py-3">
                  {anulada ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-destructive/10 px-2 py-0.5 text-xs font-medium text-destructive">
                      <Ban className="h-3 w-3" aria-hidden="true" />
                      Anulada
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">Vigente</span>
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

/** Panel de certificaciones presupuestales (crédito reservado por clasificador). */
export function TablaCertificaciones({ items }: { items: CertificacionItem[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            <th className="px-4 py-2.5 text-left">N° Certificación</th>
            <th className="px-4 py-2.5 text-left">Clasificador</th>
            <th className="px-4 py-2.5 text-right">Importe</th>
            <th className="px-4 py-2.5 text-left">Fecha</th>
          </tr>
        </thead>
        <tbody>
          {items.map((c, i) => (
            <tr
              key={`${c.nro_certifica}-${i}`}
              className={cn('border-t border-border', i % 2 === 1 && 'bg-muted/20')}
            >
              <td className="px-4 py-2.5 font-mono text-xs text-foreground">
                {c.nro_certifica ?? '—'}
              </td>
              <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground">
                {c.clasificador ?? '—'}
              </td>
              <td className="px-4 py-2.5 text-right tabular-nums text-foreground">
                {c.valor_soles != null ? formatearMoneda(c.valor_soles, true) : '—'}
              </td>
              <td className="px-4 py-2.5 text-muted-foreground">{formatFecha(c.fecha_reg)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Panel de pedidos que originaron el gasto de esta meta. */
export function TablaPedidos({ pedidos }: { pedidos: PedidoOrigenItem[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            <th className="px-4 py-2.5 text-left">Pedido</th>
            <th className="px-4 py-2.5 text-left">Motivo</th>
            <th className="px-4 py-2.5 text-left">Unidad</th>
            <th className="px-4 py-2.5 text-left">Fecha</th>
            <th className="px-4 py-2.5 text-left">Orden</th>
          </tr>
        </thead>
        <tbody>
          {pedidos.map((p, i) => (
            <tr
              key={`${p.nro_pedido}-${p.tipo_bien}-${i}`}
              className={cn('border-t border-border align-top', i % 2 === 1 && 'bg-muted/20')}
            >
              <td className="px-4 py-3">
                <div className="flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                  <span className="font-mono text-xs font-semibold text-foreground">
                    {p.nro_pedido}
                  </span>
                  <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                    {tipoBienLabel(p.tipo_bien)}
                  </span>
                </div>
              </td>
              <td className="px-4 py-3">
                <p className="line-clamp-2 max-w-md text-xs text-muted-foreground" title={p.motivo ?? ''}>
                  {p.motivo ?? '—'}
                </p>
              </td>
              <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                {p.centro_costo ?? '—'}
              </td>
              <td className="px-4 py-3 text-muted-foreground">{formatFecha(p.fecha_pedido)}</td>
              <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                {p.nro_orden != null ? p.nro_orden : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
