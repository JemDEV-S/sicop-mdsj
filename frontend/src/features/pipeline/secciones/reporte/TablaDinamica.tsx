// Tabla dinámica de pedidos: grupos colapsables con subtotal por grupo, filas
// de pedido detalladas y una fila de GRAN TOTAL al pie. Solo renderiza; recibe
// los grupos ya filtrados/agrupados/ordenados desde el orquestador.

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { formatearNumero } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import type { CategoriaMeta } from '../../reporte-types';
import { useModales } from '@/features/modales/ModalesContext';
import { MiniTimeline } from './MiniTimeline';
import type { CentroCostoLabelFn, FilaPedido, GrupoPedidos, Totales } from './tipos';

const N_COLUMNAS = 10;

export function TablaDinamica({
  grupos,
  totalGlobal,
  ccLabel,
  agrupado,
}: {
  grupos: GrupoPedidos[];
  totalGlobal: Totales;
  ccLabel: CentroCostoLabelFn;
  agrupado: boolean;
}) {
  // Todos los grupos abiertos por defecto; el usuario colapsa lo que no mira.
  const [colapsados, setColapsados] = useState<Set<string>>(new Set());
  const toggle = (k: string) =>
    setColapsados((s) => {
      const n = new Set(s);
      if (n.has(k)) n.delete(k);
      else n.add(k);
      return n;
    });

  if (grupos.length === 0) {
    return (
      <div className="rounded-md border border-border bg-card px-4 py-10 text-center text-sm text-muted-foreground">
        Ningún pedido coincide con los filtros actuales.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-md border border-border bg-card">
      <table className="w-full min-w-[1320px] table-fixed border-collapse text-sm">
        <colgroup>
          <col className="w-[22%] min-w-[240px]" />
          <col className="w-[96px]" />
          <col className="w-[118px]" />
          <col className="w-[138px]" />
          <col className="w-[140px]" />
          <col className="w-[58px]" />
          <col className="w-[120px]" />
          <col className="w-[122px]" />
          <col className="w-[122px]" />
          <col className="w-[128px]" />
        </colgroup>
        <thead className="sticky top-0 z-10">
          <tr className="bg-primary text-primary-foreground">
            <Th className="text-left">Pedido / Meta / Clasificador</Th>
            <Th className="text-left">Tipo</Th>
            <Th className="text-left">Centro de costo</Th>
            <Th className="text-left">Identificadores</Th>
            <Th className="text-left">Recorrido · Etapa</Th>
            <Th className="text-right">Días</Th>
            <Th className="text-right">Avance meta</Th>
            <Th className="text-right">Monto SIGA (S/)</Th>
            <Th className="text-right">Comprom. MEF (S/)</Th>
            <Th className="text-right">Deveng. MEF (S/)</Th>
          </tr>
        </thead>
        <tbody>
          {grupos.map((g) => {
            const cerrado = colapsados.has(g.clave);
            return (
              <FilasGrupo
                key={g.clave}
                grupo={g}
                cerrado={cerrado}
                onToggle={() => toggle(g.clave)}
                ccLabel={ccLabel}
                mostrarCabecera={agrupado}
              />
            );
          })}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-primary bg-primary/10 font-semibold">
            <Td colSpan={6} className="text-sm">
              Total {agrupado ? 'general' : ''} (filtrado)
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                {totalGlobal.n_pedidos} pedidos ·{' '}
                {totalGlobal.n_estancados > 0 ? (
                  <span className="text-destructive">
                    {totalGlobal.n_estancados} estancados por S/ {formatearNumero(totalGlobal.monto_estancado, 0)}
                  </span>
                ) : (
                  'ninguno estancado'
                )}
              </span>
            </Td>
            <Td className="text-right text-xs text-muted-foreground">SIGA → S/</Td>
            <Td className="text-right font-mono tabular-nums">
              {formatearNumero(totalGlobal.monto_siga)}
            </Td>
            <Td colSpan={2} className="text-right text-[11px] font-normal text-muted-foreground">
              MEF por pedido es contexto — no se totaliza
            </Td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function FilasGrupo({
  grupo,
  cerrado,
  onToggle,
  ccLabel,
  mostrarCabecera,
}: {
  grupo: GrupoPedidos;
  cerrado: boolean;
  onToggle: () => void;
  ccLabel: CentroCostoLabelFn;
  mostrarCabecera: boolean;
}) {
  return (
    <>
      {mostrarCabecera ? (
        <tr
          className="cursor-pointer border-y border-primary/25 bg-primary/10 hover:bg-primary/15"
          onClick={onToggle}
        >
          <Td colSpan={7} className="font-semibold">
            <div className="flex items-center gap-2">
              {cerrado ? (
                <ChevronRight className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
              ) : (
                <ChevronDown className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
              )}
              <span className="truncate" title={grupo.sublabel ?? grupo.etiqueta}>
                {grupo.etiqueta}
              </span>
              <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs font-normal text-muted-foreground">
                {grupo.totales.n_pedidos} ped.
              </span>
              {grupo.totales.n_estancados > 0 ? (
                <span className="shrink-0 rounded-full bg-destructive/15 px-2 py-0.5 text-xs font-normal text-destructive">
                  {grupo.totales.n_estancados} estancados
                </span>
              ) : null}
            </div>
          </Td>
          <Td className="text-right font-mono text-[13px] tabular-nums">
            {formatearNumero(grupo.totales.monto_siga)}
          </Td>
          <Td colSpan={2} className="text-right text-[11px] font-normal text-muted-foreground">
            subtotal SIGA
          </Td>
        </tr>
      ) : null}

      {cerrado
        ? null
        : grupo.filas.map((f) => (
            <FilaPedidoRow
              key={`${f.tipo_bien}-${f.tipo_pedido}-${f.nro_pedido}`}
              fila={f}
              ccLabel={ccLabel}
              sangria={mostrarCabecera}
            />
          ))}

      {/* Subtotal explícito al pie del grupo (además de la cabecera) — el usuario
          pidió el total "debajo" de los pedidos, como Excel. */}
      {mostrarCabecera && !cerrado ? (
        <tr className="border-b border-border bg-muted/40 text-[13px]">
          <Td colSpan={7} className="text-right text-xs font-medium text-muted-foreground">
            Subtotal · {grupo.etiqueta}
          </Td>
          <Td className="text-right font-mono font-semibold tabular-nums">
            {formatearNumero(grupo.totales.monto_siga)}
          </Td>
          <Td className="text-right font-mono tabular-nums text-muted-foreground">
            {grupo.totales.comprometido_estimado > 0
              ? formatearNumero(grupo.totales.comprometido_estimado)
              : '—'}
          </Td>
          <Td className="text-right font-mono tabular-nums text-muted-foreground">
            {grupo.totales.devengado_estimado > 0 ? (
              <span title="Suma de estimaciones por reparto — referencial, no oficial">
                {formatearNumero(grupo.totales.devengado_estimado)}
                <span className="ml-1 rounded bg-accent/20 px-1 py-0.5 font-sans text-[9px] uppercase text-accent-foreground">
                  est.
                </span>
              </span>
            ) : (
              '—'
            )}
          </Td>
        </tr>
      ) : null}
    </>
  );
}

function FilaPedidoRow({
  fila,
  ccLabel,
  sangria,
}: {
  fila: FilaPedido;
  ccLabel: CentroCostoLabelFn;
  sangria: boolean;
}) {
  const { abrir } = useModales();
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
      className="cursor-pointer border-b border-border/60 hover:bg-muted/30"
    >
      <Td>
        <div className={cn('min-w-0', sangria && 'pl-6')}>
          <div className="font-mono text-[13px] text-foreground">
            Pedido {fila.nro_pedido}
            <span className="ml-1.5 font-sans text-[10px] uppercase text-muted-foreground">
              {fila.tipo_bien === 'B' ? 'bien' : fila.tipo_bien === 'S' ? 'servicio' : fila.tipo_bien}
            </span>
          </div>
          <div
            className="truncate text-xs font-medium text-foreground"
            title={`Meta ${fila.sec_func} · ${fila.nombre_meta ?? ''}`}
          >
            <span className="font-mono">Meta {fila.sec_func}</span>
            {fila.nombre_meta ? <span className="font-normal text-muted-foreground"> · {fila.nombre_meta}</span> : null}
          </div>
          <div className="truncate text-[11px] text-muted-foreground/80">
            {fila.act_proy ? (
              <span className="font-mono" title={`${fila.categoria === 'proyecto' ? 'Proyecto' : 'Producto'} ${fila.act_proy}`}>
                {fila.categoria === 'proyecto' ? 'Proy.' : 'Prod.'} {fila.act_proy}
              </span>
            ) : null}
            {fila.clasificador !== '(sin clasificador)' ? (
              <span className="ml-1 font-mono">· clasif. {fila.clasificador}</span>
            ) : null}
            {fila.clasificador_nombre ? (
              <span className="text-muted-foreground/70"> {fila.clasificador_nombre}</span>
            ) : null}
          </div>
          {fila.motivo ? (
            <div className="truncate text-[11px] text-muted-foreground/70" title={fila.motivo}>
              {fila.motivo}
            </div>
          ) : null}
        </div>
      </Td>
      <Td>
        <BadgeCategoria categoria={fila.categoria} />
      </Td>
      <Td>{fila.centro_costo ? <ChipCC codigo={fila.centro_costo} ccLabel={ccLabel} /> : <Dash />}</Td>
      <Td>
        <Identificadores fila={fila} />
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
      <Td className="text-right">
        <AvanceMeta pct={fila.pct_devengado_meta} color={fila.semaforo_meta} />
      </Td>
      <Td className="text-right font-mono tabular-nums text-[13px]">{formatearNumero(fila.monto_siga)}</Td>
      <Td className="text-right font-mono tabular-nums text-[13px]">
        {fila.comprometido_pedido !== null ? (
          formatearNumero(fila.comprometido_pedido)
        ) : fila.tiene_orden ? (
          <Dash />
        ) : (
          <span className="text-xs italic text-muted-foreground">sin orden</span>
        )}
      </Td>
      <Td className="text-right font-mono tabular-nums text-[13px]">
        {fila.devengado_estimado !== null ? (
          <span className="inline-flex items-center justify-end gap-1">
            {formatearNumero(fila.devengado_estimado)}
            <span
              className={cn(
                'rounded px-1 py-0.5 font-sans text-[9px] uppercase',
                fila.atribucion === 'directo'
                  ? 'bg-secondary/20 text-secondary-foreground'
                  : 'bg-accent/20 text-accent-foreground',
              )}
            >
              {fila.atribucion === 'directo' ? 'directo' : 'est.'}
            </span>
          </span>
        ) : (
          <Dash />
        )}
      </Td>
    </tr>
  );
}

// ─── Piezas ──────────────────────────────────────────────────────────────

/** Badge de naturaleza del gasto: proyecto de inversión vs producto/actividad. */
function BadgeCategoria({ categoria }: { categoria: CategoriaMeta }) {
  const esProyecto = categoria === 'proyecto';
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ring-1 ring-inset',
        esProyecto
          ? 'bg-primary/10 text-primary ring-primary/30'
          : 'bg-secondary/15 text-secondary-foreground ring-secondary/30',
      )}
      title={esProyecto ? 'Proyecto de inversión (act. 2xxxxxx)' : 'Producto / actividad (gasto corriente)'}
    >
      {esProyecto ? 'Proyecto' : 'Producto'}
    </span>
  );
}

/**
 * Avance devengado/PIM de la META (no del pedido). Punto de color del semáforo
 * temporal + el %. Es contexto: mide cómo va la meta completa, nunca se suma.
 */
function AvanceMeta({ pct, color }: { pct: number | null; color: string }) {
  const punto: Record<string, string> = {
    verde: 'bg-semaforo-ok',
    amarillo: 'bg-semaforo-alerta',
    rojo: 'bg-semaforo-critico',
  };
  const dot = punto[color] ?? 'bg-muted-foreground';
  if (pct == null) return <Dash />;
  return (
    <span
      className="inline-flex items-center justify-end gap-1.5 font-mono text-[13px] tabular-nums"
      title={`Devengado ${formatearNumero(pct, 1)}% del PIM de la meta (avance de la meta completa, no del pedido)`}
    >
      <span className={cn('inline-block h-2 w-2 shrink-0 rounded-full', dot)} aria-hidden="true" />
      {formatearNumero(pct, 1)}%
    </span>
  );
}

function Identificadores({ fila }: { fila: FilaPedido }) {
  return (
    <div className="flex flex-col gap-1 text-[11px]">
      <IdChip etiqueta="PED" valor={String(fila.nro_pedido)} tono="ped" />
      {fila.orden ? <IdChip etiqueta="OC" valor={fila.orden} tono="orden" /> : null}
      {fila.exp_siaf != null ? <IdChip etiqueta="SIAF" valor={String(fila.exp_siaf)} tono="siaf" /> : null}
    </div>
  );
}

function IdChip({
  etiqueta,
  valor,
  tono,
}: {
  etiqueta: string;
  valor: string;
  tono: 'ped' | 'orden' | 'siaf';
}) {
  const tonos = {
    ped: 'bg-muted text-muted-foreground',
    orden: 'bg-primary/15 text-primary',
    siaf: 'bg-accent/20 text-accent-foreground',
  } as const;
  return (
    <span className="inline-flex items-center gap-1 truncate" title={`${etiqueta} ${valor}`}>
      <span className={cn('rounded px-1 py-0.5 font-sans text-[9px] font-semibold uppercase', tonos[tono])}>
        {etiqueta}
      </span>
      <span className="truncate font-mono text-foreground">{valor}</span>
    </span>
  );
}

function ChipCC({ codigo, ccLabel }: { codigo: string; ccLabel: CentroCostoLabelFn }) {
  const l = ccLabel(codigo);
  return (
    <span
      className="inline-flex max-w-full items-center rounded bg-muted px-1.5 py-0.5 text-[11px] font-medium text-foreground"
      title={l.nombre}
    >
      <span className="truncate">{l.sigla}</span>
    </span>
  );
}

function Th({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <th
      className={cn(
        'border-r border-primary-foreground/10 px-2.5 py-2 text-[10.5px] font-semibold uppercase tracking-wide last:border-r-0',
        className,
      )}
    >
      {children}
    </th>
  );
}

function Td({
  className,
  children,
  colSpan,
}: {
  className?: string;
  children: React.ReactNode;
  colSpan?: number;
}) {
  return (
    <td
      colSpan={colSpan}
      className={cn('border-r border-border px-2.5 py-1.5 align-middle last:border-r-0', className)}
    >
      {children}
    </td>
  );
}

function Dash() {
  return <span className="italic text-muted-foreground">—</span>;
}

export { N_COLUMNAS };
