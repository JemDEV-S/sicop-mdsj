// Pestaña PECOSAS: despachos de almacén del ámbito (salida que ejecuta una
// orden). Datos reales del snapshot (siga.movimientos_almacen ligados a la
// orden, y la orden aporta la meta). Cada fila abre el modal de PECOSA si un
// pedido visible declara la orden que la origina; si no, queda informativa.

import { formatearMoneda, formatFecha } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import { useModales } from '@/features/modales/ModalesContext';
import type { PecosaConMeta, RefPedidoOrden } from './datos';
import { EstadoVacio } from './TablaOrdenes';
import { Paginacion, usePaginado } from './Paginacion';

export function TablaPecosas({
  pecosas,
  refPorOrden,
  vacio,
}: {
  pecosas: PecosaConMeta[];
  refPorOrden: Map<number, RefPedidoOrden>;
  vacio: string;
}) {
  const { abrir } = useModales();
  const paginado = usePaginado(pecosas);

  if (pecosas.length === 0) {
    return <EstadoVacio texto={vacio} />;
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] border-collapse text-[12.5px]">
          <thead>
            <tr className="bg-superficie-alt text-left text-[11px] uppercase tracking-wide text-texto-suave">
              <Th>PECOSA</Th>
              <Th>Orden</Th>
              <Th>Meta</Th>
              <Th>Guía</Th>
              <Th>Proveedor</Th>
              <Th className="text-right">Total orden</Th>
              <Th className="text-right">Fecha despacho</Th>
            </tr>
          </thead>
          <tbody>
            {paginado.pagina.map((p) => {
            const ref = p.nro_orden != null ? refPorOrden.get(p.nro_orden) : undefined;
            const abrible = ref != null;
            return (
              <tr
                key={`${p.tipo_bien}-${p.nro_pecosa}`}
                onClick={
                  abrible
                    ? () =>
                        abrir({
                          tipo: 'pecosa',
                          nroPedido: ref!.nroPedido,
                          tipoBien: ref!.tipoBien,
                          tipoPedido: ref!.tipoPedido,
                          nroMovimiento: p.nro_pecosa,
                        })
                    : undefined
                }
                className={cn(
                  'border-b border-border/60',
                  abrible ? 'cursor-pointer hover:bg-muted/40' : '',
                )}
              >
                <Td className="font-mono font-semibold text-foreground">PECOSA {p.nro_pecosa}</Td>
                <Td className="font-mono text-muted-foreground">
                  {p.nro_orden != null ? `O/C ${p.nro_orden}` : <Dash />}
                </Td>
                <Td>
                  <span className="font-mono text-[11.5px] text-muted-foreground" title={p.nombre_meta ?? undefined}>
                    {p.sec_func}
                  </span>
                </Td>
                <Td className="font-mono text-[11.5px]">{p.nro_guia ?? <Dash />}</Td>
                <Td>
                  <span className="max-w-[200px] truncate">{p.proveedor_nombre ?? '—'}</span>
                </Td>
                <Td className="text-right font-mono tabular-nums">
                  {p.total_fact_soles > 0 ? formatearMoneda(p.total_fact_soles) : <Dash />}
                </Td>
                <Td className="text-right font-mono tabular-nums text-muted-foreground">
                  {formatFecha(p.fecha_movimto)}
                </Td>
              </tr>
            );
            })}
          </tbody>
        </table>
      </div>
      <Paginacion paginado={paginado} etiqueta="PECOSAS" />
    </>
  );
}

function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return <th className={cn('whitespace-nowrap px-3 py-2 font-semibold', className)}>{children}</th>;
}

function Td({ children, className }: { children: React.ReactNode; className?: string }) {
  return <td className={cn('px-3 py-2 align-middle', className)}>{children}</td>;
}

function Dash() {
  return <span className="italic text-muted-foreground">—</span>;
}
