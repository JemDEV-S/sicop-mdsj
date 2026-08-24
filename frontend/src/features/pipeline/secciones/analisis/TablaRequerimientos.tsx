// Pestaña Requerimientos: los pedidos del ámbito, en tres modos —
//   · Tabla    → lista plana con las columnas de la plantilla v2.
//   · Dinámica → la tabla dinámica agrupable Meta→Clasificador→Pedido (se
//                conserva íntegra: es la herramienta del economista, ya probada).
//   · Kanban   → el tablero por macrofase existente.
// Cada fila abre el modal del pedido.

import { useMemo } from 'react';
import { formatearMoneda } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import { useModales } from '@/features/modales/ModalesContext';
import { EstadoChip, type Tono } from '@/features/panel/ui/primitivas';
import PipelineKanban from '../PipelineKanban';
import { TablaDinamica } from '../reporte/TablaDinamica';
import { MiniTimeline } from '../reporte/MiniTimeline';
import { agrupar } from '../reporte/procesar';
import type {
  CampoAgrupacion,
  CampoOrden,
  CentroCostoLabelFn,
  DireccionOrden,
  FilaPedido,
  Totales,
} from '../reporte/tipos';
import { EstadoVacio } from './TablaOrdenes';
import { Paginacion, usePaginado } from './Paginacion';

export type ModoReq = 'tabla' | 'dinamica' | 'kanban';

export function TablaRequerimientos({
  modo,
  filas,
  totalGlobal,
  ccLabel,
  agrupacion,
  orden,
  direccion,
}: {
  modo: ModoReq;
  filas: FilaPedido[];
  totalGlobal: Totales;
  ccLabel: CentroCostoLabelFn;
  agrupacion: CampoAgrupacion;
  orden: CampoOrden;
  direccion: DireccionOrden;
}) {
  const grupos = useMemo(
    () => agrupar(filas, agrupacion, orden, direccion, ccLabel),
    [filas, agrupacion, orden, direccion, ccLabel],
  );
  // La paginación aplica solo al modo Tabla (plano). El hook se llama siempre
  // (regla de hooks); su resultado se usa nada más en ese modo.
  const paginado = usePaginado(filas);

  if (modo === 'kanban') {
    // El tablero se auto-alcanza por año + CC del contexto (RN-06).
    return (
      <div className="px-4 py-4">
        <PipelineKanban />
      </div>
    );
  }

  if (modo === 'dinamica') {
    return (
      <div className="px-4 py-4">
        <TablaDinamica
          grupos={grupos}
          totalGlobal={totalGlobal}
          ccLabel={ccLabel}
          agrupado={agrupacion !== 'ninguno'}
        />
      </div>
    );
  }

  // Modo Tabla (plano): columnas de la plantilla v2.
  if (filas.length === 0) {
    return <EstadoVacio texto="Ningún requerimiento coincide con los filtros actuales." />;
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[940px] border-collapse text-[12.5px]">
          <thead>
            <tr className="bg-superficie-alt text-left text-[11px] uppercase tracking-wide text-texto-suave">
              <Th>Código</Th>
              <Th>Detalle · Meta</Th>
              <Th>Centro de costo</Th>
              <Th>Estado</Th>
              <Th>Recorrido · Etapa</Th>
              <Th className="text-right">Días</Th>
              <Th className="text-right">Monto SIGA</Th>
            </tr>
          </thead>
          <tbody>
            {paginado.pagina.map((f) => (
              <FilaReq key={`${f.tipo_bien}-${f.tipo_pedido}-${f.nro_pedido}`} fila={f} ccLabel={ccLabel} />
            ))}
          </tbody>
        </table>
      </div>
      <Paginacion paginado={paginado} etiqueta="requerimientos" />
    </>
  );
}

function FilaReq({ fila, ccLabel }: { fila: FilaPedido; ccLabel: CentroCostoLabelFn }) {
  const { abrir } = useModales();
  const cc = fila.centro_costo ? ccLabel(fila.centro_costo) : null;
  return (
    <tr
      onClick={() =>
        abrir({
          tipo: 'pedido',
          nroPedido: fila.nro_pedido,
          tipoBien: fila.tipo_bien,
          tipoPedido: fila.tipo_pedido ?? '',
        })
      }
      className="cursor-pointer border-b border-border/60 hover:bg-muted/40"
    >
      <Td>
        <div className="flex flex-col gap-0.5">
          <span className="font-mono font-semibold text-foreground">Ped. {fila.nro_pedido}</span>
          <span className="text-[10px] uppercase text-muted-foreground">
            {fila.tipo_bien === 'B' ? 'bien' : fila.tipo_bien === 'S' ? 'servicio' : fila.tipo_bien}
          </span>
        </div>
      </Td>
      <Td>
        <div className="flex min-w-0 flex-col gap-0.5">
          {fila.motivo ? (
            <span className="max-w-[280px] truncate" title={fila.motivo}>
              {fila.motivo}
            </span>
          ) : (
            <span className="italic text-muted-foreground">Sin detalle</span>
          )}
          <span className="truncate text-[11px] text-muted-foreground" title={fila.nombre_meta ?? undefined}>
            <span className="font-mono">Meta {fila.sec_func}</span>
            {fila.nombre_meta ? ` · ${fila.nombre_meta}` : ''}
          </span>
        </div>
      </Td>
      <Td>
        {cc ? (
          <span className="inline-flex max-w-full items-center rounded bg-muted px-1.5 py-0.5 text-[11px] font-medium" title={cc.nombre}>
            <span className="truncate">{cc.sigla}</span>
          </span>
        ) : (
          <Dash />
        )}
      </Td>
      <Td>
        {fila.estancado ? (
          <EstadoChip tono={'critico' as Tono} tamano="xs">
            Estancado
          </EstadoChip>
        ) : (
          <EstadoChip tono={'neutral' as Tono} tamano="xs" punto={false}>
            En curso
          </EstadoChip>
        )}
      </Td>
      <Td>
        <div className="flex flex-col gap-1">
          <MiniTimeline fila={fila} />
          <span className="text-[11px] text-muted-foreground">{fila.etapa_label}</span>
        </div>
      </Td>
      <Td className={cn('text-right font-mono tabular-nums', fila.estancado && 'font-semibold text-destructive')}>
        {fila.dias_en_etapa ?? '—'}
      </Td>
      <Td className="text-right font-mono tabular-nums">{formatearMoneda(fila.monto_siga)}</Td>
    </tr>
  );
}

function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return <th className={cn('whitespace-nowrap px-3 py-2 font-semibold', className)}>{children}</th>;
}

function Td({ children, className }: { children: React.ReactNode; className?: string }) {
  return <td className={cn('px-3 py-2 align-middle', className)}>{children}</td>;
}

function Dash() {
  return <span className="italic text-muted-foreground">—</span>;
}
