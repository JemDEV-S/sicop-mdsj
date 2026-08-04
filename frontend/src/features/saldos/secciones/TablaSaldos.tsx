import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatearMoneda, formatPorcentaje } from '@/lib/formatters';
import Semaforo from '@/components/Semaforo';
import { EmptyState } from '@/components/layout/EmptyState';
import { Button } from '@/components/ui/button';
import { mapSemaforo, etiquetaSemaforo, formatSecFunc } from '../lib';
import type { SaldoItem, SemaforoSaldo } from '../types';

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
 * Tabla DUAL de saldos por meta. La regla de oro de la consolidación:
 *
 *   - Columnas SIGA (PIM, Certificado, Comprometido): fases PREVIAS. Fondo neutro.
 *   - Columnas MEF (PIM oficial, Devengado, % y semáforo): el número oficial que
 *     ve el ciudadano. Resaltadas con un tinte primary para separarlas del SIGA.
 *
 * Nunca se mezclan ni se presenta cert/compr como "devengado".
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
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full border-collapse text-sm">
          {/* Cabecera de grupo: separa visualmente SIGA de MEF */}
          <thead>
            <tr className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              <th className="border-b border-border px-4 py-2 text-left" colSpan={1} />
              <th
                className="border-b border-border bg-muted/40 px-4 py-2 text-center"
                colSpan={3}
                title="Fases previas del gasto según el SIGA de la muni. No son devengado."
              >
                SIGA · Operativo (fases previas)
              </th>
              <th
                className="border-b border-primary/30 bg-primary/5 px-4 py-2 text-center"
                colSpan={3}
                title="Snapshot oficial del portal MEF. El devengado real que ve el ciudadano."
              >
                MEF · Oficial
              </th>
            </tr>
            <tr className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              <th className="border-b border-border px-4 py-2.5 text-left">Meta</th>
              <th className="border-b border-border bg-muted/40 px-4 py-2.5 text-right">
                PIM
              </th>
              <th className="border-b border-border bg-muted/40 px-4 py-2.5 text-right">
                Certificado
              </th>
              <th className="border-b border-border bg-muted/40 px-4 py-2.5 text-right">
                Comprometido
              </th>
              <th className="border-b border-primary/30 bg-primary/5 px-4 py-2.5 text-right">
                PIM MEF
              </th>
              <th className="border-b border-primary/30 bg-primary/5 px-4 py-2.5 text-right">
                Devengado
              </th>
              <th className="border-b border-primary/30 bg-primary/5 px-4 py-2.5 text-right">
                % · Estado
              </th>
            </tr>
          </thead>
          <tbody>
            {visibles.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center">
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
                <FilaSaldo key={it.sec_func} item={it} zebra={idx % 2 === 1} />
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Tarjetas móvil */}
      <ul className="divide-y divide-border md:hidden">
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
              <TarjetaSaldo item={it} />
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
    </div>
  );
}

/** Semáforo compacto reutilizado en fila y tarjeta. */
function SemaforoMeta({ item }: { item: SaldoItem }) {
  const estado = mapSemaforo(item.semaforo);
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
    <Semaforo
      estado={estado}
      texto={etiquetaSemaforo(item.semaforo, item.porcentaje_devengado)}
    />
  );
}

function EnlaceCruce({ secFunc }: { secFunc: number }) {
  return (
    <Link
      to={`/interno/cruce/meta/${secFunc}`}
      className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
    >
      Ver cruce <ArrowRight className="h-3 w-3" aria-hidden="true" />
    </Link>
  );
}

function FilaSaldo({ item, zebra }: { item: SaldoItem; zebra: boolean }) {
  const comprometido = item.comprometido_anual;
  return (
    <tr className={cn('align-top', zebra && 'bg-muted/20')}>
      {/* Meta */}
      <td className="max-w-[22rem] px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] font-semibold text-muted-foreground">
            {formatSecFunc(item.sec_func)}
          </span>
          <EnlaceCruce secFunc={item.sec_func} />
        </div>
        <p
          className="mt-1 line-clamp-2 text-sm font-medium text-foreground"
          title={item.nombre_meta ?? ''}
        >
          {item.nombre_meta ?? 'Sin nombre'}
        </p>
      </td>

      {/* SIGA */}
      <td className="bg-muted/20 px-4 py-3 text-right tabular-nums">
        {formatearMoneda(item.pim, true)}
      </td>
      <td className="bg-muted/20 px-4 py-3 text-right tabular-nums text-muted-foreground">
        {formatearMoneda(item.certificado, true)}
      </td>
      <td className="bg-muted/20 px-4 py-3 text-right tabular-nums text-muted-foreground">
        {formatearMoneda(comprometido, true)}
      </td>

      {/* MEF */}
      <td className="bg-primary/[0.03] px-4 py-3 text-right tabular-nums">
        {item.pim_mef != null ? formatearMoneda(item.pim_mef, true) : '—'}
      </td>
      <td className="bg-primary/[0.03] px-4 py-3 text-right font-semibold tabular-nums text-foreground">
        {item.devengado_mef != null ? formatearMoneda(item.devengado_mef, true) : '—'}
      </td>
      <td className="bg-primary/[0.03] px-4 py-3 text-right">
        <div className="flex flex-col items-end gap-1">
          <span className="font-semibold tabular-nums">
            {item.porcentaje_devengado != null
              ? formatPorcentaje(item.porcentaje_devengado)
              : '—'}
          </span>
          <SemaforoMeta item={item} />
        </div>
      </td>
    </tr>
  );
}

function TarjetaSaldo({ item }: { item: SaldoItem }) {
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

      <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        <dt className="text-muted-foreground">Devengado (MEF)</dt>
        <dd className="text-right font-semibold tabular-nums text-foreground">
          {item.devengado_mef != null ? formatearMoneda(item.devengado_mef, true) : '—'}
        </dd>
        <dt className="text-muted-foreground">PIM (MEF)</dt>
        <dd className="text-right tabular-nums">
          {item.pim_mef != null ? formatearMoneda(item.pim_mef, true) : '—'}
        </dd>
        <dt className="text-muted-foreground">PIM (SIGA)</dt>
        <dd className="text-right tabular-nums">{formatearMoneda(item.pim, true)}</dd>
        <dt className="text-muted-foreground" title="Fase previa al devengado">
          Certificado (SIGA)
        </dt>
        <dd className="text-right tabular-nums text-muted-foreground">
          {formatearMoneda(item.certificado, true)}
        </dd>
        <dt className="text-muted-foreground" title="Fase previa al devengado">
          Comprometido (SIGA)
        </dt>
        <dd className="text-right tabular-nums text-muted-foreground">
          {formatearMoneda(item.comprometido_anual, true)}
        </dd>
      </dl>

      <EnlaceCruce secFunc={item.sec_func} />
    </div>
  );
}

export default TablaSaldos;
