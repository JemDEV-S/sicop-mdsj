// Modal · Requerimiento (pedido). Datos reales de useDetallePedido.
//
// Estructura de la plantilla Panel Interno v2:
//   - Cabecera: overline + código, detalle, chips de contexto, y a la derecha
//     las 4 tarjetas de identificadores (Pedido/Orden/EXP_SIAF/PECOSA).
//   - Trazabilidad por carriles de macrofase (con barra de avance, toggle
//     Resumen/Detalle y leyenda).
//   - Dinero del requerimiento (badges) + Ítems y documentos ligados.
// Cada identificador/ligado con destino apila su propio modal.

import { Package, Wrench } from 'lucide-react';
import { formatearMoneda } from '@/lib/formatters';
import { useDetallePedido } from '@/features/pipeline/api';
import type { OrdenAsociada, PedidoDetalle } from '@/features/pipeline/types';
import { useModales, type EntradaModal } from '../ModalesContext';
import { CargandoModal, ErrorModal } from '../EstadoModal';
import { BotonLigado, ChipInfo, ModalBloque, ModalHead } from '../ui';
import { TrazabilidadCarriles } from '../componentes/TrazabilidadCarriles';
import { IdsPedido, type TarjetaId } from '../componentes/IdsPedido';
import { DineroPedido, type FilaDinero } from '../componentes/DineroPedido';
import { fasesDeEstadoSiaf } from '../lib/estados';

type Entrada = Extract<EntradaModal, { tipo: 'pedido' }>;

export function ModalPedido({ entrada }: { entrada: Entrada }) {
  const { nroPedido, tipoBien, tipoPedido } = entrada;
  const { data, isLoading, isError, error, refetch } = useDetallePedido({ nroPedido, tipoBien, tipoPedido });
  const { abrir } = useModales();

  if (isLoading) return <CargandoModal texto={`Cargando pedido ${nroPedido}…`} />;
  if (isError || !data) {
    return (
      <ErrorModal
        texto={
          error instanceof Error
            ? error.message
            : 'No se pudo cargar el pedido. Puede ser un corte temporal del SIGA.'
        }
        onReintentar={() => refetch()}
      />
    );
  }

  return <Cuerpo pedido={data} entrada={entrada} abrir={abrir} />;
}

function Cuerpo({
  pedido,
  entrada,
  abrir,
}: {
  pedido: PedidoDetalle;
  entrada: Entrada;
  abrir: (e: EntradaModal) => void;
}) {
  const IconoTipo = pedido.tipo_bien === 'B' ? Package : Wrench;
  const tipoLabel = pedido.tipo_bien === 'B' ? 'Bien' : 'Servicio';
  const tipoPedido = entrada.tipoPedido;

  // Orden atribuida (la que trae certificación o la primera) y su expediente.
  const ordenAtribuida =
    pedido.ordenes.find((o) => o.nro_certifica != null) ?? pedido.ordenes[0] ?? null;
  const expedientes = pedido.expedientes.filter((x) => x.exp_siaf != null);
  const expAtribuido = ordenAtribuida?.exp_siaf ?? expedientes[0]?.exp_siaf ?? null;
  const pecosa = pedido.movimientos_almacen[0] ?? null;
  const montoSiga = pedido.items.reduce((a, it) => a + (it.valor_total ?? 0), 0);

  // ── Tarjetas de identificadores ──
  const tarjetas: TarjetaId[] = [
    { label: 'Pedido', valor: String(pedido.nro_pedido), onClick: null },
    {
      label: 'Orden',
      valor: ordenAtribuida ? String(ordenAtribuida.nro_orden) : 'sin orden',
      onClick: ordenAtribuida
        ? () => abrir({ tipo: 'orden', nroPedido: pedido.nro_pedido, tipoBien: pedido.tipo_bien, tipoPedido, nroOrden: ordenAtribuida.nro_orden })
        : null,
    },
    {
      label: 'EXP_SIAF',
      valor: expAtribuido != null ? String(expAtribuido) : 'pendiente',
      onClick: expAtribuido != null
        ? () => abrir({ tipo: 'siaf', nroPedido: pedido.nro_pedido, tipoBien: pedido.tipo_bien, tipoPedido, expSiaf: expAtribuido })
        : null,
    },
    {
      label: 'PECOSA',
      valor: pecosa ? String(pecosa.nro_movimto) : '—',
      onClick: pecosa
        ? () => abrir({ tipo: 'pecosa', nroPedido: pedido.nro_pedido, tipoBien: pedido.tipo_bien, tipoPedido, nroMovimiento: pecosa.nro_movimto })
        : null,
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <ModalHead
        overline="Requerimiento"
        titulo={`${pedido.nro_pedido}-${pedido.ano_eje}`}
        mono
        descripcion={pedido.motivo ?? undefined}
        chips={
          <>
            <ChipInfo>
              <span className="inline-flex items-center gap-1">
                <IconoTipo className="h-3 w-3" aria-hidden="true" />
                {tipoLabel}
              </span>
            </ChipInfo>
            {pedido.sec_func != null ? (
              <ChipInfo>
                Meta {pedido.sec_func}
                {pedido.nombre_meta ? ` · ${pedido.nombre_meta}` : ''}
              </ChipInfo>
            ) : null}
            {pedido.fuente_financ_nombre ? <ChipInfo>{pedido.fuente_financ_nombre}</ChipInfo> : null}
            {pedido.solicitante ? <ChipInfo>Solicita: {pedido.solicitante}</ChipInfo> : null}
          </>
        }
        aside={<IdsPedido tarjetas={tarjetas} />}
      />

      <TrazabilidadCarriles
        timeline={pedido.timeline}
        etapaActualNumero={pedido.etapa_actual_numero}
        etapaActualLabel={pedido.etapa_actual_label}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ModalBloque titulo="Dinero del requerimiento">
          <DineroPedido
            filas={dineroDe(montoSiga, ordenAtribuida)}
            nota="El monto SIGA solicitado es el único sumable por pedido. Certificado/devengado/girado por orden serán reales cuando llegue la ejecución SIAF por expediente; hoy van rotulados según el estado de la orden."
          />
        </ModalBloque>

        <ModalBloque titulo="Ítems y documentos ligados">
          {pedido.items.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-[11.5px]">
                <thead>
                  <tr className="bg-superficie-alt text-left text-muted-foreground">
                    <th className="px-2 py-1.5 font-semibold">Ítem</th>
                    <th className="px-2 py-1.5 font-semibold">Clasificador</th>
                    <th className="px-2 py-1.5 text-right font-semibold">Cant.</th>
                    <th className="px-2 py-1.5 text-right font-semibold">Valor S/</th>
                  </tr>
                </thead>
                <tbody>
                  {pedido.items.map((it) => (
                    <tr key={it.secuencia} className="border-b border-border/50">
                      <td className="px-2 py-1.5">{it.item_bien ?? `Ítem ${it.secuencia}`}</td>
                      <td className="px-2 py-1.5 font-mono text-primary">{it.clasificador ?? '—'}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums">
                        {it.cant_solicitada ?? '—'}
                      </td>
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums">
                        {it.valor_total != null ? formatearMoneda(it.valor_total) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-[12px] text-muted-foreground">Sin ítems registrados para este pedido.</p>
          )}

          <div className="flex flex-wrap gap-2 pt-1">
            {pedido.ordenes.map((o) => (
              <BotonLigado
                key={`ord-${o.nro_orden}`}
                tipo={o.tipo_bien === 'S' ? 'O/S' : 'O/C'}
                id={o.nro_orden}
                onClick={() =>
                  abrir({ tipo: 'orden', nroPedido: pedido.nro_pedido, tipoBien: pedido.tipo_bien, tipoPedido, nroOrden: o.nro_orden })
                }
              />
            ))}
            {expedientes.map((x) => (
              <BotonLigado
                key={`exp-${x.exp_siga}`}
                tipo="Exp. SIAF"
                id={x.exp_siaf!}
                onClick={() =>
                  abrir({ tipo: 'siaf', nroPedido: pedido.nro_pedido, tipoBien: pedido.tipo_bien, tipoPedido, expSiaf: x.exp_siaf! })
                }
              />
            ))}
            {pedido.movimientos_almacen.map((m) => (
              <BotonLigado
                key={`mov-${m.nro_movimto}`}
                tipo="PECOSA"
                id={m.nro_movimto}
                onClick={() =>
                  abrir({ tipo: 'pecosa', nroPedido: pedido.nro_pedido, tipoBien: pedido.tipo_bien, tipoPedido, nroMovimiento: m.nro_movimto })
                }
              />
            ))}
            {pedido.ordenes.length === 0 && expedientes.length === 0 && pedido.movimientos_almacen.length === 0 ? (
              <span className="text-[11.5px] text-muted-foreground">
                Aún no hay órdenes, expedientes ni salidas de almacén ligados.
              </span>
            ) : null}
          </div>
        </ModalBloque>
      </div>
    </div>
  );
}

// Deriva las filas de dinero. Solo el monto SIGA es sumable; el resto se rotula
// según el estado SIAF real de la orden atribuida (sin inventar montos por fase).
function dineroDe(montoSiga: number, orden: OrdenAsociada | null): FilaDinero[] {
  const filas: FilaDinero[] = [
    { label: 'Monto SIGA solicitado', valor: formatearMoneda(montoSiga), badge: 'sumable', fuerte: true },
  ];
  if (orden) {
    const fases = fasesDeEstadoSiaf(orden.estado_siaf);
    const alcanzada = (nombre: string) => fases.find((f) => f.label === nombre)?.hecho ?? false;
    const total = orden.total_fact_soles;
    filas.push(
      {
        label: 'Total facturado (orden)',
        valor: total != null ? formatearMoneda(total) : '—',
        badge: 'real',
        fuerte: true,
      },
      {
        label: 'Devengado (orden)',
        valor: total != null && alcanzada('Devengado') ? formatearMoneda(total) : '—',
        badge: alcanzada('Devengado') ? 'real' : 'pendiente',
      },
      {
        label: 'Girado (orden)',
        valor: total != null && alcanzada('Girado') ? formatearMoneda(total) : '—',
        badge: alcanzada('Girado') ? 'real' : 'pendiente',
      },
    );
  } else {
    filas.push({ label: 'Ejecución por orden', valor: 'sin orden ligada', badge: 'pendiente' });
  }
  return filas;
}
