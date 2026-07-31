import { Link } from 'react-router-dom';
import { CheckCircle2, Package, Wrench } from 'lucide-react';
import { formatearMoneda, formatFecha } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import type { PedidoCard as PedidoCardType } from '../dashboard/types';
import { BadgeAlerta, CopyChip, bordeAlerta } from './pipeline-ui';

interface PedidoCardProps {
  pedido: PedidoCardType;
}

// Tarjeta v2 (Guía Pipeline v2 §03.1):
//  - Fila de identificadores (N° pedido · O/S · SIAF) con copiar-al-clic.
//  - Fecha de la etapa actual ("en Ejecución desde 12 mar"), no solo "N días".
//  - Alerta v2 por color: rojo solo estancado_real; ámbar puente/consolidación.
//  - Avance de bolsa no atribuido: check verde suave, invita al detalle (no alarma).
export function PedidoCard({ pedido }: PedidoCardProps) {
  const tipoLabel = pedido.tipo_bien === 'B' ? 'Bien' : 'Servicio';
  const IconoTipo = pedido.tipo_bien === 'B' ? Package : Wrench;
  const monto =
    pedido.monto_total > 0 ? formatearMoneda(pedido.monto_total, true) : null;
  const centroCosto = pedido.centro_costo?.trim() || null;

  const ids = pedido.identificadores;
  const puente = pedido.puente;
  const alerta = pedido.alerta ?? null;

  // Fecha de la etapa actual: la del código de etapa en el mapa `fechas`.
  const fechaEtapa = pedido.fechas?.[pedido.etapa] ?? null;

  // Órdenes de la bolsa cuando el puente no está resuelto (tono muted, §03.1).
  const ordenesBolsa =
    !ids?.orden && puente && puente.avance_bolsa.n_ordenes > 0
      ? puente.avance_bolsa.ordenes.map((o) => o.nro_orden)
      : [];

  // Avance de bolsa sin atribuir y sin alerta: check verde suave (§03.1).
  const bolsaConAvance =
    !alerta && (puente?.avance_bolsa.n_ordenes ?? 0) > 0 && !ids?.orden;

  return (
    <Link
      to={`/interno/pedidos/${pedido.nro_pedido}/${pedido.tipo_bien}`}
      className={cn(
        'block rounded-md border bg-card p-2.5 text-xs transition-colors',
        'hover:border-primary/50 hover:bg-muted/40',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        bordeAlerta(alerta),
      )}
      aria-label={`Pedido ${ids?.pedido ?? pedido.nro_pedido}, ${tipoLabel}${
        alerta ? `, ${alerta.evidencia}` : ''
      }`}
    >
      <header className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <IconoTipo
            className="w-3.5 h-3.5 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
          <span className="font-semibold text-foreground truncate">
            {tipoLabel}
          </span>
        </div>
        {alerta ? <BadgeAlerta alerta={alerta} /> : null}
      </header>

      {/* Fila de identificadores con copiar-al-clic (§03.1) */}
      <div className="mt-1.5 flex flex-wrap gap-1">
        <CopyChip valor={ids?.pedido ?? `${pedido.nro_pedido}-${pedido.ano_eje}`} />
        {ids?.orden ? <CopyChip valor={ids.orden} /> : null}
        {ids?.exp_siaf != null ? (
          <CopyChip etiqueta="SIAF" valor={String(ids.exp_siaf)} />
        ) : null}
        {ordenesBolsa.length > 0 ? (
          <span
            className="inline-flex items-center rounded border border-border/60 bg-muted/40 px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground"
            title="Órdenes de la bolsa; confirma cuál corresponde a este pedido"
          >
            {pedido.tipo_bien === 'S' ? 'O/S' : 'O/C'} de bolsa:{' '}
            {ordenesBolsa.slice(0, 3).join(', ')}
          </span>
        ) : null}
      </div>

      {/* Etapa actual con su fecha (§03.1) */}
      <p className="mt-1.5 text-foreground">
        <span className="font-medium">{pedido.etapa_label}</span>
        {fechaEtapa ? (
          <span className="text-muted-foreground"> desde {formatFecha(fechaEtapa)}</span>
        ) : null}
      </p>

      {monto ? (
        <p className="mt-1 font-semibold text-foreground tabular-nums">{monto}</p>
      ) : null}

      {centroCosto ? (
        <p
          className="mt-1 text-muted-foreground truncate font-mono text-[11px]"
          title={centroCosto}
        >
          {centroCosto}
        </p>
      ) : null}

      {bolsaConAvance ? (
        <p className="mt-1 flex items-center gap-1 text-secondary">
          <CheckCircle2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span>Bolsa con avance</span>
        </p>
      ) : null}
    </Link>
  );
}

export default PedidoCard;
