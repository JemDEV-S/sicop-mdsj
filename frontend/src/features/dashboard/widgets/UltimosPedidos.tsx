import { Clock } from 'lucide-react';
import { SectionCard } from '@/components/layout/SectionCard';
import { EmptyState } from '@/components/layout/EmptyState';
import { formatearMoneda, parseMonto, formatFecha } from '@/lib/formatters';
import type { PedidoReciente } from '../types';

interface UltimosPedidosProps {
  pedidos: PedidoReciente[];
}

export function UltimosPedidos({ pedidos }: UltimosPedidosProps) {
  return (
    <SectionCard
      titulo="Últimos pedidos de mi unidad"
      icono={Clock}
      padding="sm"
      bodyClassName="p-0"
    >
      {pedidos.length === 0 ? (
        <div className="p-4">
          <EmptyState
            icono={Clock}
            titulo="Sin pedidos recientes"
            descripcion="Aún no hay pedidos registrados por tu unidad."
          />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="tabla-pedidos">
            <thead className="bg-muted">
              <tr>
                <Th align="left">N° Pedido</Th>
                <Th align="left">Descripción</Th>
                <Th align="right">Monto</Th>
                <Th align="left">Etapa</Th>
                <Th align="left">Fecha</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {pedidos.map((p) => (
                <tr key={p.nro_pedido} className="hover:bg-muted transition-colors">
                  <td className="py-2 px-3 font-medium text-foreground">{p.nro_pedido}</td>
                  <td className="py-2 px-3 text-muted-foreground">{p.descripcion}</td>
                  <td className="py-2 px-3 text-right font-medium text-foreground">
                    {formatearMoneda(parseMonto(p.monto))}
                  </td>
                  <td className="py-2 px-3">
                    <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-muted text-foreground border border-border">
                      {p.estado}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-muted-foreground">
                    {formatFecha(p.fecha)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </SectionCard>
  );
}

function Th({
  children,
  align,
}: {
  children: React.ReactNode;
  align: 'left' | 'right';
}) {
  return (
    <th
      className={`py-2 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide text-${align}`}
    >
      {children}
    </th>
  );
}

export default UltimosPedidos;
