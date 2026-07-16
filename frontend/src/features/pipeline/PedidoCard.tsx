import { Link } from 'react-router-dom';
import { AlertTriangle, Package, Wrench } from 'lucide-react';
import { formatearMoneda } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import type { PedidoCard as PedidoCardType } from '../dashboard/types';

interface PedidoCardProps {
  pedido: PedidoCardType;
}

// AC-09.2: tarjeta muestra N°, tipo, monto, solicitante, días en etapa.
// AC-09.4: click abre el detalle (ruta stub de T-46 ya montada).
// AC-09.6: pedidos estancados se resaltan con borde-l destructive + icono.
export function PedidoCard({ pedido }: PedidoCardProps) {
  const nroTexto = `N° ${pedido.nro_pedido}-${pedido.ano_eje}`;
  const tipoLabel = pedido.tipo_bien === 'B' ? 'Bien' : 'Servicio';
  const IconoTipo = pedido.tipo_bien === 'B' ? Package : Wrench;
  const dias = pedido.dias_en_etapa;
  const monto = pedido.monto_total > 0 ? formatearMoneda(pedido.monto_total, true) : null;
  const centroCosto = pedido.centro_costo?.trim() || null;

  return (
    <Link
      to={`/interno/pedidos/${pedido.nro_pedido}/${pedido.tipo_bien}`}
      className={cn(
        'block rounded-md border bg-card p-2.5 text-xs transition-colors',
        'hover:border-primary/50 hover:bg-muted/40',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        pedido.estancado
          ? 'border-l-4 border-l-destructive border-y border-r-border'
          : 'border-border',
      )}
      aria-label={`Pedido ${nroTexto}, ${tipoLabel}, ${
        pedido.estancado ? 'estancado' : ''
      }`}
    >
      <header className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <IconoTipo
            className="w-3.5 h-3.5 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
          <span className="font-semibold text-foreground truncate">
            {nroTexto}
          </span>
          <span className="text-muted-foreground/70">·</span>
          <span className="text-muted-foreground">{tipoLabel}</span>
        </div>
        {pedido.estancado ? (
          <AlertTriangle
            className="w-3.5 h-3.5 shrink-0 text-destructive"
            aria-label="Pedido estancado"
          />
        ) : null}
      </header>

      {monto ? (
        <p className="mt-1 font-semibold text-foreground tabular-nums">
          {monto}
        </p>
      ) : null}

      {centroCosto ? (
        <p
          className="mt-1 text-muted-foreground truncate font-mono text-[11px]"
          title={centroCosto}
        >
          {centroCosto}
        </p>
      ) : null}

      {dias != null ? (
        <p
          className={cn(
            'mt-1 tabular-nums',
            pedido.estancado
              ? 'text-destructive font-medium'
              : 'text-muted-foreground',
          )}
        >
          {dias === 0 ? 'Hoy' : `Hace ${dias} día${dias === 1 ? '' : 's'}`}
        </p>
      ) : null}
    </Link>
  );
}

export default PedidoCard;
