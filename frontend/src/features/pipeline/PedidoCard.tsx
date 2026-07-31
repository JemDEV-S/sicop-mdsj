import { Link } from 'react-router-dom';
import { formatearMoneda, formatFecha } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import type { PedidoCard as PedidoCardType } from '../dashboard/types';
import { BadgeAlerta, CopyChip, bordeAlerta } from './pipeline-ui';

interface PedidoCardProps {
  pedido: PedidoCardType;
  /** En la bandeja "por confirmar" la card explica el avance de la bolsa. */
  contexto?: 'columna' | 'bandeja';
}

// Tarjeta v3 (rediseño UX):
//  - El MOTIVO es la línea principal: es lo único que un funcionario reconoce
//    de su pedido sin mirar números.
//  - Una sola señal de estado: borde izquierdo + badge (color nunca solo).
//  - Etapa + fecha + días en la misma línea ("Cotización · desde 12/01 · 45 días").
//  - Monto y centro de costo en el pie, alineados.
export function PedidoCard({ pedido, contexto = 'columna' }: PedidoCardProps) {
  const monto =
    pedido.monto_total > 0 ? formatearMoneda(pedido.monto_total, true) : null;
  const centroCosto = pedido.centro_costo?.trim() || null;
  const motivo = pedido.motivo?.trim() || null;

  const ids = pedido.identificadores;
  const puente = pedido.puente;
  const alerta = pedido.alerta ?? null;

  // Fecha de la etapa actual: la del código de etapa en el mapa `fechas`.
  const fechaEtapa = pedido.fechas?.[pedido.etapa] ?? null;
  const dias = pedido.dias_en_etapa ?? null;

  // Órdenes de la bolsa cuando el puente no está resuelto (tono muted, §03.1).
  const ordenesBolsa =
    !ids?.orden && puente && puente.avance_bolsa.n_ordenes > 0
      ? puente.avance_bolsa.ordenes.map((o) => o.nro_orden)
      : [];
  const avanceBolsaLabel = puente?.avance_bolsa.max_etapa_label ?? null;

  return (
    <Link
      to={`/interno/pedidos/${pedido.nro_pedido}/${pedido.tipo_bien}/${pedido.tipo_pedido ?? ''}`}
      className={cn(
        'block rounded-md border bg-card p-2.5 text-xs transition-colors',
        'hover:border-primary/50 hover:bg-muted/40',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        bordeAlerta(alerta),
      )}
      aria-label={`Pedido ${ids?.pedido ?? pedido.nro_pedido}${
        motivo ? `, ${motivo}` : ''
      }${alerta ? `, ${alerta.evidencia}` : ''}`}
    >
      {/* Identificadores + señal de estado */}
      <header className="flex items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1 min-w-0">
          <CopyChip valor={ids?.pedido ?? `${pedido.nro_pedido}-${pedido.ano_eje}`} />
          {ids?.orden ? <CopyChip valor={ids.orden} /> : null}
        </div>
        {alerta ? <BadgeAlerta alerta={alerta} className="shrink-0" /> : null}
      </header>

      {/* Motivo: lo que el solicitante reconoce como "su" pedido. */}
      {motivo ? (
        <p
          className="mt-1.5 text-foreground font-medium leading-snug line-clamp-2"
          title={motivo}
        >
          {motivo}
        </p>
      ) : null}

      {/* Etapa actual + fecha + días transcurridos */}
      <p className="mt-1.5 text-muted-foreground">
        <span className="font-medium text-foreground">{pedido.etapa_label}</span>
        {fechaEtapa ? <> · desde {formatFecha(fechaEtapa)}</> : null}
        {dias != null && dias > 0 ? (
          <span className="tabular-nums"> · {dias} días</span>
        ) : null}
      </p>

      {/* En la bandeja: qué avance tiene la bolsa y qué órdenes son candidatas. */}
      {contexto === 'bandeja' && ordenesBolsa.length > 0 ? (
        <p className="mt-1 text-muted-foreground">
          La bolsa ya llegó a{' '}
          <span className="font-medium text-foreground">
            {avanceBolsaLabel ?? 'una etapa posterior'}
          </span>{' '}
          con {pedido.tipo_bien === 'S' ? 'O/S' : 'O/C'}{' '}
          <span className="font-mono">
            {ordenesBolsa.slice(0, 3).join(', ')}
            {ordenesBolsa.length > 3 ? '…' : ''}
          </span>
        </p>
      ) : null}

      {(monto || centroCosto) && (
        <footer className="mt-1.5 flex items-baseline justify-between gap-2">
          <span
            className="min-w-0 truncate font-mono text-[11px] text-muted-foreground"
            title={centroCosto ?? undefined}
          >
            {centroCosto ?? ''}
          </span>
          {monto ? (
            <span className="shrink-0 font-semibold text-foreground tabular-nums">
              {monto}
            </span>
          ) : null}
        </footer>
      )}
    </Link>
  );
}

export default PedidoCard;
