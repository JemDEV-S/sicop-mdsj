/**
 * Página Detalle de Pedido (HU-10, T-46).
 *
 * Ruta: /interno/pedidos/:nroPedido/:tipoBien/:tipoPedido
 * Protegida por RequireAuth.
 *
 * `tipoPedido` es obligatorio en la URL: SIGA reutiliza NRO_PEDIDO entre
 * pedidos sin relación (p. ej. 3/B tiene un pedido de compra TIPO_PEDIDO='2'
 * y una atención de almacén TIPO_PEDIDO='1' que no comparten nada). Sin este
 * dato el backend no puede saber a cuál de los dos te refieres.
 */
import { useParams } from 'react-router-dom';
import { EmptyState } from '@/components/layout/EmptyState';
import { ClipboardList } from 'lucide-react';
import PedidoDetalle from '@/features/pipeline/PedidoDetalle';

export default function Pedido() {
  const params = useParams<{
    nroPedido: string;
    tipoBien: string;
    tipoPedido: string;
  }>();
  const nroPedido = Number(params.nroPedido);
  const tipoBien = (params.tipoBien ?? '').toUpperCase();
  const tipoPedido = params.tipoPedido ?? '';

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

  if (!tipoPedido) {
    return (
      <EmptyState
        icono={ClipboardList}
        titulo="Falta el tipo de pedido"
        descripcion="La URL no indica el tipo de pedido de SIGA."
        accion={{ label: 'Volver al pipeline', href: '/interno/pipeline' }}
      />
    );
  }

  return (
    <PedidoDetalle nroPedido={nroPedido} tipoBien={tipoBien} tipoPedido={tipoPedido} />
  );
}
