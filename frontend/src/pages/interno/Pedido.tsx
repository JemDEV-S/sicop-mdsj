/**
 * Página Detalle de Pedido (HU-10, T-46).
 *
 * Ruta: /interno/pedidos/:nroPedido/:tipoBien
 * Protegida por RequireAuth.
 */
import { useParams } from 'react-router-dom';
import { EmptyState } from '@/components/layout/EmptyState';
import { ClipboardList } from 'lucide-react';
import PedidoDetalle from '@/features/pipeline/PedidoDetalle';

export default function Pedido() {
  const params = useParams<{ nroPedido: string; tipoBien: string }>();
  const nroPedido = Number(params.nroPedido);
  const tipoBien = (params.tipoBien ?? '').toUpperCase();

  if (!Number.isFinite(nroPedido) || nroPedido <= 0) {
    return (
      <EmptyState
        icono={ClipboardList}
        titulo="Número de pedido inválido"
        descripcion="La URL no contiene un número de pedido válido."
        accion={{ label: 'Volver al pipeline', href: '/interno/pipeline' }}
      />
    );
  }

  if (tipoBien !== 'B' && tipoBien !== 'S') {
    return (
      <EmptyState
        icono={ClipboardList}
        titulo="Tipo de pedido inválido"
        descripcion="El tipo debe ser B (Bien) o S (Servicio)."
        accion={{ label: 'Volver al pipeline', href: '/interno/pipeline' }}
      />
    );
  }

  return <PedidoDetalle nroPedido={nroPedido} tipoBien={tipoBien} />;
}
