import { useState } from 'react';
import { GitCompareArrows, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatearMoneda, formatPorcentaje } from '@/lib/formatters';
import Semaforo from '@/components/Semaforo';
import { EmptyState } from '@/components/layout/EmptyState';
import { Button } from '@/components/ui/button';
import { ModalCruce } from '@/features/cruce/ModalCruce';
import {
  mapSemaforo,
  etiquetaSemaforo,
  explicacionSemaforo,
  formatSecFunc,
} from '../lib';
import { DetalleMeta } from './DetalleMeta';
import type { SaldoItem, SemaforoSaldo } from '../types';

/** Selección activa del modal de cruce (meta, o meta+clasificador). */
interface CruceSel {
  secFunc: number;
  clasificador?: string | null;
  clasificadorNombre?: string | null;
}

/** Columnas de la tabla desktop (para el colSpan de la fila de detalle). */
const N_COLUMNAS = 8;

interface TablaSaldosProps {
  items: SaldoItem[];
  /** Semáforo activo (filtro cliente sobre la página actual). */
  filtroSemaforo: SemaforoSaldo | null;
  onLimpiarSemaforo: () => void;
  // Paginación backend.
  page: number;
  size: number;
  total: number;
  onPageChange: (page: number) => void;
  isFetching?: boolean;
}

/**
 * Tabla de saldos por meta, 100% SIAF/MEF. Toda cifra presupuestal es la oficial
 * del snapshot MEF (el PIM SIGA discrepa del SIAF en el 75% de las metas y NO se
 * usa como presupuesto). Muestra la cadena de ejecución con sus saldos:
 *
 *   PIM → Certificado → Comprometido → Devengado → Girado
 *
 * y destaca el saldo por ejecutar (PIM − devengado). El estado usa el semáforo
 * TEMPORAL: compara el avance real contra el esperado por el mes de corte, así
 * no alarma de más por el rezago propio del backup. El detalle operativo del
 * SIGA (por clasificador y fuente) se abre en el drill-down.
 */
export function TablaSaldos({
  items,
  filtroSemaforo,
  onLimpiarSemaforo,
  page,
  size,
  total,
  onPageChange,
  isFetching,
}: TablaSaldosProps) {
  const [expandida, setExpandida] = useState<number | null>(null);
  const toggle = (secFunc: number) =>
    setExpandida((prev) => (prev === secFunc ? null : secFunc));

  // Modal de cruce SIAF-SIGA (por meta o por clasificador).
  const [cruce, setCruce] = useState<CruceSel | null>(null);

  const visibles = filtroSemaforo
    ? items.filter((i) => i.semaforo === filtroSemaforo)
    : items;

  const totalPaginas = Math.max(1, Math.ceil(total / size));
  const desde = total === 0 ? 0 : (page - 1) * size + 1;
  const hasta = Math.min(page * size, total);

  if (total === 0) {
    return (
      <EmptyState
        titulo="Sin metas con presupuesto"
        descripcion="Esta unidad no registra metas con PIM en el año seleccionado. Prueba con otro año o cambia la unidad desde el encabezado."
      />
    );
  }

  return (
    <div className="flex flex-col">
      {/* Barra de conteo */}
      <div className="flex flex-col gap-2 border-b border-border px-4 py-3 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <span>
          Mostrando{' '}
          <span className="font-semibold tabular-nums text-foreground">{desde}</span>–
          <span className="font-semibold tabular-nums text-foreground">{hasta}</span> de{' '}
          <span className="font-semibold tabular-nums text-foreground">
            {total.toLocaleString('es-PE')}
          </span>{' '}
          metas
          {filtroSemaforo ? (
            <>
              {' · '}
              <span className="text-foreground">{visibles.length}</span> en esta página con
              el estado filtrado
            </>
          ) : null}
        </span>
        {isFetching ? <span className="text-xs">Actualizando…</span> : null}
      </div>

      {/* Tabla desktop */}
      <div className="hidden overflow-x-auto lg:block">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              <th className="border-b border-border px-4 py-2 text-left" colSpan={1}>
                Meta
              </th>
              <th
                className="border-b border-border px-4 py-2 text-center"
                colSpan={4}
                title="Cadena de ejecución del gasto según el SIAF/MEF (fuente oficial)."
              >
                Ejecución oficial (SIAF)
              </th>
              <th
                className="border-b border-primary/30 bg-primary/5 px-4 py-2 text-center"
                colSpan={2}
                title="Saldo aún por ejecutar y estado de avance frente a lo esperado."
              >
                Saldo y avance
              </th>
            </tr>
            <tr className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              <th className="border-b border-border px-4 py-2.5 text-left" />
              <th className="border-b border-border px-4 py-2.5 text-right" title="Presupuesto Institucional Modificado (oficial).">
                PIM
              </th>
              <th className="border-b border-border px-4 py-2.5 text-right" title="Crédito certificado disponible para comprometer.">
                Certificado
              </th>
              <th className="border-b border-border px-4 py-2.5 text-right" title="Compromiso anual del gasto.">
                Comprometido
              </th>
              <th className="border-b border-border px-4 py-2.5 text-right" title="Devengado: el bien/servicio se recibió (obligación de pago). Girado bajo la barra.">
                Devengado
              </th>
              <th className="border-b border-primary/30 bg-primary/5 px-4 py-2.5 text-right" title="PIM − Devengado: cuánto queda por ejecutar.">
                Por ejecutar
              </th>
              <th className="border-b border-primary/30 bg-primary/5 px-4 py-2.5 text-right">
                Avance · Estado
              </th>
            </tr>
          </thead>
          <tbody>
            {visibles.length === 0 ? (
              <tr>
                <td colSpan={N_COLUMNAS} className="px-4 py-10 text-center">
                  <p className="text-sm text-muted-foreground">
                    Ninguna meta de esta página tiene el estado filtrado.
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    onClick={onLimpiarSemaforo}
                  >
                    Quitar filtro de estado
                  </Button>
                </td>
              </tr>
            ) : (
              visibles.map((it, idx) => (
                <FilaSaldo
                  key={it.sec_func}
                  item={it}
                  zebra={idx % 2 === 1}
                  expandida={expandida === it.sec_func}
                  onToggle={() => toggle(it.sec_func)}
                  onVerCruce={() => setCruce({ secFunc: it.sec_func })}
                  onVerCruceClasif={(codigo, nombre) =>
                    setCruce({
                      secFunc: it.sec_func,
                      clasificador: codigo,
                      clasificadorNombre: nombre,
                    })
                  }
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Tarjetas móvil / tablet */}
      <ul className="divide-y divide-border lg:hidden">
        {visibles.length === 0 ? (
          <li className="px-4 py-10 text-center">
            <p className="text-sm text-muted-foreground">
              Ninguna meta de esta página tiene el estado filtrado.
            </p>
            <Button variant="outline" size="sm" className="mt-3" onClick={onLimpiarSemaforo}>
              Quitar filtro de estado
            </Button>
          </li>
        ) : (
          visibles.map((it) => (
            <li key={it.sec_func} className="px-4 py-4">
              <TarjetaSaldo item={it} onVerCruce={() => setCruce({ secFunc: it.sec_func })} />
            </li>
          ))
        )}
      </ul>

      {/* Paginación */}
      <div className="flex items-center justify-between border-t border-border px-4 py-3">
        <span className="text-sm text-muted-foreground">
          Página {page} de {totalPaginas}
        </span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
          >
            Anterior
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPaginas}
          >
            Siguiente
          </Button>
        </div>
      </div>

      {/* Modal de cruce SIAF-SIGA (meta o clasificador) */}
      <ModalCruce
        secFunc={cruce?.secFunc ?? null}
        clasificador={cruce?.clasificador ?? null}
        clasificadorNombre={cruce?.clasificadorNombre ?? null}
        onClose={() => setCruce(null)}
      />
    </div>
  );
}

/**
 * Barra de avance por fases apiladas sobre el PIM: certificado (más claro),
 * comprometido, devengado (sólido) y girado (marca oscura). Muestra de un vistazo
 * la cascada Certificado ≥ Comprometido ≥ Devengado ≥ Girado y dónde se detiene.
 */
function BarraFases({ item }: { item: SaldoItem }) {
  const dev = item.porcentaje_devengado;
  if (dev == null) return null;
  const clamp = (v: number | null) => (v == null ? 0 : Math.min(100, Math.max(0, v)));
  const cert = clamp(item.porcentaje_certificado);
  const compr = clamp(item.porcentaje_comprometido);
  const devP = clamp(dev);
  const gir = clamp(item.porcentaje_girado);
  return (
    <div
      className="relative h-2 w-full overflow-hidden rounded-full bg-muted"
      title={`Certificado ${cert.toFixed(0)}% · Comprometido ${compr.toFixed(0)}% · Devengado ${devP.toFixed(0)}% · Girado ${gir.toFixed(0)}%`}
    >
      {/* Capas apiladas de menor a mayor avance (las más avanzadas encima). */}
      <div className="absolute inset-y-0 left-0 bg-primary/15" style={{ width: `${cert}%` }} />
      <div className="absolute inset-y-0 left-0 bg-primary/30" style={{ width: `${compr}%` }} />
      <div className="absolute inset-y-0 left-0 bg-primary/60" style={{ width: `${devP}%` }} />
      <div className="absolute inset-y-0 left-0 bg-primary" style={{ width: `${gir}%` }} />
    </div>
  );
}

/** Semáforo temporal con explicación (esperado vs. real). */
function SemaforoMeta({ item }: { item: SaldoItem }) {
  const estado = mapSemaforo(item.semaforo);
  const explicacion = explicacionSemaforo(item.semaforo_ctx);
  if (!estado) {
    return (
      <span
        className="inline-flex items-center gap-2 rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground"
        title="La meta no cruza con el snapshot MEF, no hay devengado oficial que evaluar."
      >
        <span className="h-2 w-2 rounded-full bg-muted-foreground/50" aria-hidden="true" />
        Sin dato MEF
      </span>
    );
  }
  return (
    <span title={explicacion ?? undefined}>
      <Semaforo
        estado={estado}
        texto={etiquetaSemaforo(item.semaforo, item.porcentaje_devengado)}
      />
    </span>
  );
}

function BotonCruce({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
    >
      <GitCompareArrows className="h-3 w-3" aria-hidden="true" /> Ver cruce
    </button>
  );
}

/** Celda de monto oficial: valor o guion si la meta no cruza con MEF. */
function Monto({ valor, fuerte }: { valor: number | null; fuerte?: boolean }) {
  return (
    <td className={cn('px-4 py-3 text-right tabular-nums', fuerte && 'font-semibold text-foreground')}>
      {valor != null ? formatearMoneda(valor, true) : '—'}
    </td>
  );
}

function FilaSaldo({
  item,
  zebra,
  expandida,
  onToggle,
  onVerCruce,
  onVerCruceClasif,
}: {
  item: SaldoItem;
  zebra: boolean;
  expandida: boolean;
  onToggle: () => void;
  onVerCruce: () => void;
  onVerCruceClasif: (codigo: string, nombre: string | null) => void;
}) {
  const explicacion = explicacionSemaforo(item.semaforo_ctx);
  return (
    <>
      <tr className={cn('align-top', (zebra || expandida) && 'bg-muted/20')}>
        {/* Meta */}
        <td className="max-w-[22rem] px-4 py-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onToggle}
              aria-expanded={expandida}
              aria-label={expandida ? 'Ocultar composición' : 'Ver composición'}
              className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              {expandida ? (
                <ChevronDown className="h-4 w-4" aria-hidden="true" />
              ) : (
                <ChevronRight className="h-4 w-4" aria-hidden="true" />
              )}
            </button>
            <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] font-semibold text-muted-foreground">
              {formatSecFunc(item.sec_func)}
            </span>
            <BotonCruce onClick={onVerCruce} />
          </div>
          <p
            className="mt-1 line-clamp-2 pl-7 text-sm font-medium text-foreground"
            title={item.nombre_meta ?? ''}
          >
            {item.nombre_meta ?? 'Sin nombre'}
          </p>
          <button
            type="button"
            onClick={onToggle}
            className="mt-0.5 pl-7 text-[11px] text-primary hover:underline"
          >
            Ver detalle del gasto ({item.filas_clasificador} líneas)
          </button>
        </td>

        {/* Cadena SIAF */}
        <Monto valor={item.pim_mef} />
        <Monto valor={item.certificado_mef} />
        <Monto valor={item.comprometido_mef} />
        <td className="px-4 py-3 text-right">
          <span className="font-semibold tabular-nums text-foreground">
            {item.devengado_mef != null ? formatearMoneda(item.devengado_mef, true) : '—'}
          </span>
          {item.girado_mef != null ? (
            <p
              className="mt-0.5 text-[11px] text-muted-foreground"
              title="Girado (pagado)"
            >
              Girado {formatearMoneda(item.girado_mef, true)}
            </p>
          ) : null}
        </td>

        {/* Saldo por ejecutar */}
        <td className="bg-primary/[0.03] px-4 py-3 text-right">
          <span className="font-semibold tabular-nums text-foreground">
            {item.saldo_por_ejecutar != null
              ? formatearMoneda(item.saldo_por_ejecutar, true)
              : '—'}
          </span>
          {item.saldo_por_pagar != null && item.saldo_por_pagar > 0 ? (
            <p className="mt-0.5 text-[11px] text-muted-foreground" title="Devengado aún no pagado">
              Por pagar {formatearMoneda(item.saldo_por_pagar, true)}
            </p>
          ) : null}
        </td>

        {/* Avance + estado */}
        <td className="bg-primary/[0.03] px-4 py-3 text-right">
          <div className="flex flex-col items-end gap-1.5">
            <span className="font-semibold tabular-nums" title={explicacion ?? undefined}>
              {item.porcentaje_devengado != null
                ? formatPorcentaje(item.porcentaje_devengado)
                : '—'}
            </span>
            <BarraFases item={item} />
            <SemaforoMeta item={item} />
          </div>
        </td>
      </tr>
      {expandida ? (
        <DetalleMeta
          secFunc={item.sec_func}
          colSpan={N_COLUMNAS}
          onVerCruceClasif={onVerCruceClasif}
        />
      ) : null}
    </>
  );
}

function TarjetaSaldo({ item, onVerCruce }: { item: SaldoItem; onVerCruce: () => void }) {
  const explicacion = explicacionSemaforo(item.semaforo_ctx);
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] font-semibold text-muted-foreground">
            {formatSecFunc(item.sec_func)}
          </span>
          <p
            className="mt-1 line-clamp-2 text-sm font-medium text-foreground"
            title={item.nombre_meta ?? ''}
          >
            {item.nombre_meta ?? 'Sin nombre'}
          </p>
        </div>
      </div>

      <SemaforoMeta item={item} />
      {explicacion ? (
        <p className="text-[11px] text-muted-foreground">{explicacion}</p>
      ) : null}
      <BarraFases item={item} />

      <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        <dt className="col-span-2 mt-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
          Ejecución oficial (SIAF)
        </dt>
        <dt className="text-muted-foreground">PIM</dt>
        <dd className="text-right tabular-nums">
          {item.pim_mef != null ? formatearMoneda(item.pim_mef, true) : '—'}
        </dd>
        <dt className="text-muted-foreground">Certificado</dt>
        <dd className="text-right tabular-nums">
          {item.certificado_mef != null ? formatearMoneda(item.certificado_mef, true) : '—'}
        </dd>
        <dt className="text-muted-foreground">Comprometido</dt>
        <dd className="text-right tabular-nums">
          {item.comprometido_mef != null ? formatearMoneda(item.comprometido_mef, true) : '—'}
        </dd>
        <dt className="text-muted-foreground">Devengado</dt>
        <dd className="text-right font-semibold tabular-nums text-foreground">
          {item.devengado_mef != null ? formatearMoneda(item.devengado_mef, true) : '—'}
        </dd>
        <dt className="text-muted-foreground">Girado (pagado)</dt>
        <dd className="text-right tabular-nums">
          {item.girado_mef != null ? formatearMoneda(item.girado_mef, true) : '—'}
        </dd>

        <dt className="col-span-2 mt-2 text-[10px] font-bold uppercase tracking-wider text-primary/70">
          Saldos
        </dt>
        <dt className="text-muted-foreground">Por ejecutar</dt>
        <dd className="text-right font-semibold tabular-nums text-foreground">
          {item.saldo_por_ejecutar != null
            ? formatearMoneda(item.saldo_por_ejecutar, true)
            : '—'}
        </dd>
        <dt className="text-muted-foreground">Por pagar</dt>
        <dd className="text-right tabular-nums">
          {item.saldo_por_pagar != null ? formatearMoneda(item.saldo_por_pagar, true) : '—'}
        </dd>
      </dl>

      <BotonCruce onClick={onVerCruce} />
    </div>
  );
}

export default TablaSaldos;
