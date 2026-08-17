// Modal · Orden (O/C u O/S). Datos reales de useDetallePedido → OrdenAsociada.
// Estructura de la plantilla v2: cabecera con total facturado + estado a la
// derecha, "Avance SIAF de esta orden" (fases en columnas) con enlace al
// expediente, y "Datos de la orden" + "Documentos ligados".

import { formatearMoneda, formatFecha } from '@/lib/formatters';
import { useDetallePedido } from '@/features/pipeline/api';
import { EstadoChip } from '@/features/panel/ui/primitivas';
import type { MovimientoAlmacen, OrdenAsociada } from '@/features/pipeline/types';
import { useModales, type EntradaModal } from '../ModalesContext';
import { CargandoModal, ErrorModal } from '../EstadoModal';
import { ChipInfo, FilaDato, ModalBloque, ModalHead } from '../ui';
import { FasesColumnas, type FaseCol } from '../componentes/Fases';
import { ListaLigados, type Ligado } from '../componentes/FilaLigado';
import { fasesDeEstadoSiaf, tonoEstadoSiaf } from '../lib/estados';

type Entrada = Extract<EntradaModal, { tipo: 'orden' }>;

export function ModalOrden({ entrada }: { entrada: Entrada }) {
  const { nroPedido, tipoBien, tipoPedido, nroOrden } = entrada;
  const { data, isLoading, isError, error, refetch } = useDetallePedido({ nroPedido, tipoBien, tipoPedido });
  const { abrir } = useModales();

  if (isLoading) return <CargandoModal texto={`Cargando orden ${nroOrden}…`} />;
  if (isError || !data) {
    return (
      <ErrorModal
        texto={error instanceof Error ? error.message : 'No se pudo cargar la orden. Puede ser un corte temporal del SIGA.'}
        onReintentar={() => refetch()}
      />
    );
  }

  const orden = data.ordenes.find((o) => o.nro_orden === nroOrden);
  if (!orden) return <ErrorModal texto={`La orden ${nroOrden} ya no figura ligada al pedido ${nroPedido}.`} />;

  const tipoLabel = orden.tipo_bien === 'S' ? 'Orden de servicio' : 'Orden de compra';
  const total = orden.total_fact_soles;

  // Fases derivadas del estado SIAF real; el monto solo se muestra en las
  // alcanzadas (no inventamos desglose por fase que el SIGA no da).
  const fasesEstado = fasesDeEstadoSiaf(orden.estado_siaf);
  const fases: FaseCol[] = fasesEstado.map((f) => ({
    label: f.label,
    hecho: f.hecho,
    monto: f.hecho && total != null ? formatearMoneda(total, true) : undefined,
    badge: f.hecho ? 'alcanzada' : 'pendiente',
    badgeTono: f.hecho ? 'ok' : 'neutral',
  }));

  const ligados: Ligado[] = [
    { tipo: 'Requerim.', id: data.nro_pedido, nota: 'pedido de origen', onClick: () => abrir({ tipo: 'pedido', nroPedido, tipoBien, tipoPedido }) },
    ...(orden.exp_siaf != null
      ? [{ tipo: 'Exp. SIAF', id: orden.exp_siaf, nota: 'afectación presupuestal oficial', onClick: () => abrir({ tipo: 'siaf', nroPedido, tipoBien, tipoPedido, expSiaf: orden.exp_siaf! }) }]
      : []),
    ...movimientosDeOrden(data.movimientos_almacen, orden).map((m) => ({
      tipo: 'PECOSA',
      id: m.nro_movimto,
      nota: m.nro_guia ? `Guía ${m.nro_guia}` : 'salida de almacén',
      onClick: () => abrir({ tipo: 'pecosa', nroPedido, tipoBien, tipoPedido, nroMovimiento: m.nro_movimto }),
    })),
  ];

  return (
    <div className="flex flex-col gap-4">
      <ModalHead
        overline={tipoLabel}
        titulo={`${orden.tipo_bien === 'S' ? 'O/S' : 'O/C'} ${orden.nro_orden}`}
        mono
        descripcion={orden.concepto ?? undefined}
        chips={
          <>
            {orden.proveedor_nombre ? <ChipInfo>{orden.proveedor_nombre}</ChipInfo> : null}
            {orden.proveedor_ruc ? <ChipInfo>RUC {orden.proveedor_ruc}</ChipInfo> : null}
          </>
        }
        aside={
          <>
            <span className="font-mono text-xl font-semibold tabular-nums text-foreground">
              {total != null ? formatearMoneda(total) : '—'}
            </span>
            <span className="text-[10.5px] text-muted-foreground">total facturado · SIGA</span>
            {orden.estado_siaf ? (
              <EstadoChip tono={tonoEstadoSiaf(orden.estado_siaf)} tamano="sm">
                {orden.estado_siaf}
              </EstadoChip>
            ) : null}
          </>
        }
      />

      <ModalBloque
        titulo="Avance SIAF de esta orden"
        accion={
          orden.exp_siaf != null ? (
            <button
              type="button"
              onClick={() => abrir({ tipo: 'siaf', nroPedido, tipoBien, tipoPedido, expSiaf: orden.exp_siaf! })}
              className="rounded-md border border-primary bg-card px-2.5 py-1 text-[11.5px] font-medium text-primary transition-colors hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Ver expediente {orden.exp_siaf} →
            </button>
          ) : null
        }
        nota="Las fases marcadas reflejan el estado SIAF actual de la orden. El SIGA no desglosa el monto por fase; el total facturado es el dato operativo."
      >
        <FasesColumnas fases={fases} />
      </ModalBloque>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ModalBloque titulo="Datos de la orden">
          <div className="flex flex-col">
            <FilaDato label="Fecha" mono>{formatFecha(orden.fecha_orden)}</FilaDato>
            <FilaDato label="Proveedor">{orden.proveedor_nombre ?? '—'}</FilaDato>
            <FilaDato label="RUC" mono>{orden.proveedor_ruc ?? '—'}</FilaDato>
            <FilaDato label="Estado">{orden.estado ?? '—'}</FilaDato>
            <FilaDato label="Estado SIAF">{orden.estado_siaf ?? '—'}</FilaDato>
            <FilaDato label="N° certificación" mono>{orden.nro_certifica ?? '—'}</FilaDato>
          </div>
        </ModalBloque>

        <ModalBloque titulo="Documentos ligados">
          <ListaLigados ligados={ligados} />
        </ModalBloque>
      </div>
    </div>
  );
}

function movimientosDeOrden(movimientos: MovimientoAlmacen[], orden: OrdenAsociada): MovimientoAlmacen[] {
  return movimientos.filter((m) => m.nro_orden == null || m.nro_orden === orden.nro_orden);
}
