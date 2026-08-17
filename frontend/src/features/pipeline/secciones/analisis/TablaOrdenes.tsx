// Pestañas O/C y O/S: la lista de órdenes del ámbito (bienes o servicios). Datos
// reales del snapshot (siga.ordenes por meta). Cada fila abre el modal de la
// orden SOLO si un pedido visible la declara (el modal necesita un pedido de
// origen); si no, la fila queda informativa — no se inventa el pedido.

import { formatearMoneda, formatFecha } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import { EstadoChip, type Tono } from '@/features/panel/ui/primitivas';
import { useModales } from '@/features/modales/ModalesContext';
import { tonoEstadoSiaf } from '@/features/modales/lib/estados';
import type { OrdenConMeta, RefPedidoOrden } from './datos';
import { labelRecepcion } from './datos';
import { Paginacion, usePaginado } from './Paginacion';

export function TablaOrdenes({
  ordenes,
  refPorOrden,
  vacio,
}: {
  ordenes: OrdenConMeta[];
  refPorOrden: Map<number, RefPedidoOrden>;
  vacio: string;
}) {
  const { abrir } = useModales();
  const paginado = usePaginado(ordenes);

  if (ordenes.length === 0) {
    return <EstadoVacio texto={vacio} />;
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[880px] border-collapse text-[12.5px]">
          <thead>
            <tr className="bg-superficie-alt text-left text-[11px] uppercase tracking-wide text-texto-suave">
              <Th>Orden</Th>
              <Th>Proveedor</Th>
              <Th>Meta</Th>
              <Th>Estado</Th>
              <Th>Recepción</Th>
              <Th className="text-right">Total facturado</Th>
              <Th className="text-right">Fecha</Th>
            </tr>
          </thead>
          <tbody>
            {paginado.pagina.map((o) => {
            const ref = refPorOrden.get(o.nro_orden);
            const abrible = ref != null;
            const codigo = `${o.tipo_bien === 'S' ? 'O/S' : 'O/C'} ${o.nro_orden}`;
            const recep = labelRecepcion(o.flag_recep);
            return (
              <tr
                key={`${o.tipo_bien}-${o.nro_orden}`}
                onClick={
                  abrible
                    ? () =>
                        abrir({
                          tipo: 'orden',
                          nroPedido: ref!.nroPedido,
                          tipoBien: ref!.tipoBien,
                          tipoPedido: ref!.tipoPedido,
                          nroOrden: o.nro_orden,
                        })
                    : undefined
                }
                className={cn(
                  'border-b border-border/60',
                  abrible ? 'cursor-pointer hover:bg-muted/40' : '',
                )}
              >
                <Td>
                  <div className="flex flex-col gap-0.5">
                    <span className="font-mono font-semibold text-foreground">{codigo}</span>
                    {o.concepto ? (
                      <span className="max-w-[260px] truncate text-[11px] text-muted-foreground" title={o.concepto}>
                        {o.concepto}
                      </span>
                    ) : null}
                  </div>
                </Td>
                <Td>
                  <div className="flex flex-col gap-0.5">
                    <span className="max-w-[200px] truncate">{o.proveedor_nombre ?? '—'}</span>
                    {o.proveedor_ruc ? (
                      <span className="font-mono text-[11px] text-muted-foreground">RUC {o.proveedor_ruc}</span>
                    ) : null}
                  </div>
                </Td>
                <Td>
                  <span className="font-mono text-[11.5px] text-muted-foreground" title={o.nombre_meta ?? undefined}>
                    {o.sec_func}
                  </span>
                </Td>
                <Td>
                  {o.estado_siaf ? (
                    <EstadoChip tono={tonoEstadoSiaf(o.estado_siaf)} tamano="xs">
                      {o.estado_siaf}
                    </EstadoChip>
                  ) : o.estado ? (
                    <EstadoChip tono={'neutral' as Tono} tamano="xs" punto={false}>
                      {o.estado}
                    </EstadoChip>
                  ) : (
                    <Dash />
                  )}
                </Td>
                <Td>
                  {recep ? (
                    <span className="text-[11.5px] text-muted-foreground">{recep}</span>
                  ) : (
                    <Dash />
                  )}
                </Td>
                <Td className="text-right font-mono tabular-nums">
                  {o.total_fact_soles > 0 ? formatearMoneda(o.total_fact_soles) : <Dash />}
                </Td>
                <Td className="text-right font-mono tabular-nums text-muted-foreground">
                  {formatFecha(o.fecha_orden)}
                </Td>
              </tr>
            );
            })}
          </tbody>
        </table>
      </div>
      <Paginacion paginado={paginado} etiqueta="órdenes" />
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

export function EstadoVacio({ texto }: { texto: string }) {
  return (
    <div className="px-4 py-10 text-center text-sm text-muted-foreground">{texto}</div>
  );
}
