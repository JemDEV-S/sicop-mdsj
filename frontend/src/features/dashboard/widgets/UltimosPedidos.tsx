import { Link } from 'react-router-dom';
import { Clock } from 'lucide-react';
import { SectionCard } from '@/components/layout/SectionCard';
import { EmptyState } from '@/components/layout/EmptyState';
import { formatearMoneda, formatFecha } from '@/lib/formatters';
import type { Macrofase, PedidoCard } from '../types';

interface UltimosPedidosProps {
  pedidos: PedidoCard[];
}

/**
 * Últimos pedidos de la unidad ordenados por fecha_pedido DESC (mockup HU-22).
 * Cada fila lleva al detalle del pedido (HU-10 · T-46). El estado "estancado"
 * (RN-02, > 15 días sin avance) se resalta con acento visual y aria-label.
 */
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
            descripcion="No hay pedidos registrados en el año y unidad seleccionados."
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
                <FilaPedido
                  key={`${p.ano_eje}-${p.nro_pedido}-${p.tipo_bien}`}
                  pedido={p}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </SectionCard>
  );
}

function FilaPedido({ pedido }: { pedido: PedidoCard }) {
  const href = `/interno/pedidos/${pedido.nro_pedido}/${pedido.tipo_bien}?ano=${pedido.ano_eje}`;

  return (
    <tr className="hover:bg-muted transition-colors">
      <td className="py-2 px-3 font-medium">
        <Link
          to={href}
          className="text-foreground hover:text-primary hover:underline"
        >
          {pedido.nro_pedido}
          <span className="ml-1 text-xs text-muted-foreground font-normal">
            /{pedido.tipo_bien}
          </span>
        </Link>
      </td>
      <td className="py-2 px-3 text-muted-foreground max-w-md truncate" title={pedido.motivo ?? ''}>
        {pedido.motivo || 'Sin descripción'}
      </td>
      <td className="py-2 px-3 text-right font-medium text-foreground tabular-nums">
        {formatearMoneda(pedido.monto_total)}
      </td>
      <td className="py-2 px-3">
        <ChipEtapa
          macrofase={pedido.macrofase}
          etapaLabel={pedido.etapa_label}
          etapaNumero={pedido.etapa_numero}
          estancado={pedido.estancado}
          dias={pedido.dias_en_etapa ?? null}
        />
      </td>
      <td className="py-2 px-3 text-muted-foreground">
        {formatFecha(pedido.fecha_pedido)}
      </td>
    </tr>
  );
}

const CHIP_ESTILOS: Record<Macrofase, string> = {
  solicitud:     'bg-primary/10 text-primary border-primary/20',
  programacion:  'bg-primary/15 text-primary border-primary/25',
  certificacion: 'bg-primary/20 text-primary border-primary/30',
  contratacion:  'bg-primary/25 text-primary border-primary/40',
  ejecucion:     'bg-secondary/15 text-secondary border-secondary/30',
  cierre:        'bg-muted text-muted-foreground border-border',
};

function ChipEtapa({
  macrofase,
  etapaLabel,
  etapaNumero,
  estancado,
  dias,
}: {
  macrofase: Macrofase;
  etapaLabel: string;
  etapaNumero: number;
  estancado: boolean;
  dias: number | null;
}) {
  if (estancado) {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-accent/30 text-accent-foreground border border-accent"
        aria-label={`Etapa ${etapaNumero} ${etapaLabel}, estancado hace ${dias ?? 0} días`}
      >
        <span className="tabular-nums">[{etapaNumero}]</span>
        {etapaLabel}
        <span className="text-[10px] font-semibold">· {dias ?? 0}d</span>
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${CHIP_ESTILOS[macrofase]}`}
      title={`Macrofase: ${macrofase}`}
    >
      <span className="tabular-nums">[{etapaNumero}]</span>
      {etapaLabel}
    </span>
  );
}

function Th({ children, align }: { children: React.ReactNode; align: 'left' | 'right' }) {
  return (
    <th
      className={`py-2 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide text-${align}`}
    >
      {children}
    </th>
  );
}

export default UltimosPedidos;
