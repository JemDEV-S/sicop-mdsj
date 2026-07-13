import { Wallet } from 'lucide-react';
import { formatearMoneda } from '@/lib/formatters';
import { BarraEjecucion } from '@/components/publico/BarraEjecucion';
import { cn } from '@/lib/utils';
import type { ObraDetalleResponse } from '../types';

export function AvancePresupuesto({ obra }: { obra: ObraDetalleResponse }) {
  const m = obra.montos_ejecucion;
  const pim = m.pim;

  const filas = [
    { label: 'PIA', valor: m.pia, ayuda: 'Presupuesto Inicial Asignado' },
    { label: 'PIM', valor: m.pim, ayuda: 'Presupuesto Institucional Modificado' },
    { label: 'Certificado', valor: m.certificado, ayuda: 'Reservado para un fin específico' },
    { label: 'Comprometido', valor: m.comprometido_anual, ayuda: 'Con contrato u orden firmada' },
    { label: 'Devengado', valor: m.devengado, ayuda: 'Obligación reconocida por la entidad' },
    { label: 'Girado', valor: m.girado, ayuda: 'Efectivamente pagado' },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-6">
      {/* Barra + narrativa */}
      <div className="rounded-2xl bg-card border border-border p-6 md:p-8">
        <div className="flex items-center gap-2 mb-6">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Wallet className="w-4 h-4" aria-hidden="true" />
          </span>
          <div>
            <h3 className="text-sm font-semibold text-foreground">Etapas de ejecución</h3>
            <p className="text-xs text-muted-foreground">
              Cada capa muestra qué porcentaje del PIM ha avanzado.
            </p>
          </div>
        </div>

        {pim > 0 ? (
          <BarraEjecucion
            pim={pim}
            certificado={m.certificado}
            comprometido={m.comprometido_anual}
            devengado={m.devengado}
            girado={m.girado}
            formatoMonto={(v) => formatearMoneda(v)}
          />
        ) : (
          <div className="rounded-lg bg-muted/40 border border-border p-6 text-center">
            <p className="text-sm text-muted-foreground">
              Esta obra aún no tiene presupuesto (PIM) asignado en el ejercicio vigente.
            </p>
          </div>
        )}
      </div>

      {/* Detalle numérico */}
      <div className="rounded-2xl bg-card border border-border p-6 md:p-8">
        <h3 className="text-sm font-semibold text-foreground mb-4">Detalle en soles</h3>
        <dl className="space-y-3">
          {filas.map((fila, idx) => {
            const esDestacado = fila.label === 'PIM' || fila.label === 'Devengado';
            return (
              <div
                key={fila.label}
                className={cn(
                  'flex items-baseline justify-between gap-4',
                  idx < filas.length - 1 ? 'pb-3 border-b border-border' : '',
                )}
              >
                <div className="min-w-0">
                  <dt className={cn(
                    'text-sm',
                    esDestacado ? 'font-semibold text-foreground' : 'text-muted-foreground',
                  )}>
                    {fila.label}
                  </dt>
                  <p className="text-[11px] text-muted-foreground truncate">{fila.ayuda}</p>
                </div>
                <dd
                  className={cn(
                    'shrink-0 tabular-nums',
                    esDestacado ? 'text-base font-bold text-foreground' : 'text-sm font-medium text-foreground',
                  )}
                >
                  {formatearMoneda(fila.valor)}
                </dd>
              </div>
            );
          })}
        </dl>
      </div>
    </div>
  );
}
