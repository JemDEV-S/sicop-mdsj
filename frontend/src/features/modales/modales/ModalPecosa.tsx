// Modal · PECOSA (salida de almacén). Datos reales de useDetallePedido →
// MovimientoAlmacen + Conformidad. Estructura de la plantilla v2: cabecera con
// "valor despachado" a la derecha, datos de la salida, y documentos ligados.

import { formatearMoneda, formatFecha } from '@/lib/formatters';
import { useDetallePedido } from '@/features/pipeline/api';
import { useModales, type EntradaModal } from '../ModalesContext';
import { CargandoModal, ErrorModal } from '../EstadoModal';
import { FilaDato, ModalBloque, ModalHead } from '../ui';
import { ListaLigados, type Ligado } from '../componentes/FilaLigado';

type Entrada = Extract<EntradaModal, { tipo: 'pecosa' }>;

export function ModalPecosa({ entrada }: { entrada: Entrada }) {
  const { nroPedido, tipoBien, tipoPedido, nroMovimiento } = entrada;
  const { data, isLoading, isError, error, refetch } = useDetallePedido({ nroPedido, tipoBien, tipoPedido });
  const { abrir } = useModales();

  if (isLoading) return <CargandoModal texto={`Cargando salida de almacén ${nroMovimiento}…`} />;
  if (isError || !data) {
    return (
      <ErrorModal
        texto={error instanceof Error ? error.message : 'No se pudo cargar la salida de almacén. Puede ser un corte temporal del SIGA.'}
        onReintentar={() => refetch()}
      />
    );
  }

  const mov = data.movimientos_almacen.find((m) => m.nro_movimto === nroMovimiento);
  if (!mov) return <ErrorModal texto={`La salida ${nroMovimiento} ya no figura ligada al pedido ${nroPedido}.`} />;

  const conformidad = mov.nro_orden != null
    ? data.conformidades.find((c) => c.nro_orden === mov.nro_orden) ?? null
    : data.conformidades[0] ?? null;
  const orden = mov.nro_orden != null ? data.ordenes.find((o) => o.nro_orden === mov.nro_orden) ?? null : null;
  const total = orden?.total_fact_soles ?? null;

  const ligados: Ligado[] = [
    ...(orden
      ? [{ tipo: orden.tipo_bien === 'S' ? 'O/S' : 'O/C', id: orden.nro_orden, nota: orden.proveedor_nombre ?? undefined, onClick: () => abrir({ tipo: 'orden', nroPedido, tipoBien, tipoPedido, nroOrden: orden.nro_orden }) }]
      : []),
    { tipo: 'Requerim.', id: data.nro_pedido, nota: 'pedido de origen', onClick: () => abrir({ tipo: 'pedido', nroPedido, tipoBien, tipoPedido }) },
  ];

  return (
    <div className="flex flex-col gap-4">
      <ModalHead
        overline="PECOSA — salida de almacén"
        titulo={String(mov.nro_movimto)}
        mono
        descripcion="Solo bienes. Cierra la cadena: recepción en almacén y despacho al área usuaria."
        aside={
          total != null ? (
            <>
              <span className="font-mono text-xl font-semibold tabular-nums text-foreground">{formatearMoneda(total)}</span>
              <span className="text-[10.5px] text-muted-foreground">valor despachado</span>
            </>
          ) : undefined
        }
      />

      <ModalBloque titulo="Datos de la salida">
        <div className="flex flex-col">
          <FilaDato label="Fecha" mono>{formatFecha(mov.fecha_movimto)}</FilaDato>
          <FilaDato label="Tipo movimiento">{mov.tipo_movimto ?? '—'}</FilaDato>
          <FilaDato label="N° guía" mono>{mov.nro_guia ?? '—'}</FilaDato>
          <FilaDato label="Orden" mono>{mov.nro_orden ?? '—'}</FilaDato>
          {conformidad ? (
            <>
              <FilaDato label="Conformidad">{conformidad.indi_confor ?? '—'}</FilaDato>
              <FilaDato label="Responsable">{conformidad.responsable ?? '—'}</FilaDato>
              <FilaDato label="Fecha conf." mono>{formatFecha(conformidad.fecha_movimto)}</FilaDato>
            </>
          ) : null}
        </div>
      </ModalBloque>

      <ModalBloque titulo="Documentos ligados">
        <ListaLigados ligados={ligados} />
      </ModalBloque>
    </div>
  );
}
