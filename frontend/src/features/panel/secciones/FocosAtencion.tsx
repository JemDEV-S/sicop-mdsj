// Focos de atención: las metas más críticas (mayor PIM, menor avance) del
// resumen de saldos. Clic → analizar la meta. El % y el semáforo son del MEF.

import { formatearMoneda, formatearNumero } from '@/lib/formatters';
import type { MetaCritica } from '@/features/dashboard/types';
import { EstadoChip, PanelSection } from '../ui/primitivas';
import { tonoDeColor, ETIQUETA_SEMAFORO } from '../lib/semaforo';

export function FocosAtencion({
  metas,
  onAnalizarMeta,
}: {
  metas: MetaCritica[];
  onAnalizarMeta: (secFunc: number) => void;
}) {
  return (
    <PanelSection titulo="Focos de atención — mayor PIM, menor avance" aside="clic: analizar la meta">
      {metas.length === 0 ? (
        <p className="rounded border border-dashed border-border px-3 py-6 text-center text-sm text-muted-foreground">
          Sin metas críticas en el ámbito visible.
        </p>
      ) : (
        metas.map((m) => {
          const pct = m.porcentaje_devengado;
          const w = Math.min(100, Math.max(0, pct));
          const tono = tonoDeColor(m.semaforo);
          return (
            <button
              key={m.sec_func}
              type="button"
              onClick={() => onAnalizarMeta(m.sec_func)}
              className="flex items-center gap-3 rounded-md border border-border bg-card px-3 py-2 text-left transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span className="shrink-0 font-mono text-[11px] text-muted-foreground">
                {String(m.sec_func).padStart(4, '0')}
              </span>
              <span className="flex min-w-0 flex-1 flex-col gap-1">
                <span className="truncate text-[12.5px] font-medium text-foreground">
                  {m.nombre_meta ?? `Meta ${m.sec_func}`}
                </span>
                <span className="flex items-center gap-2">
                  <span className="h-1.5 min-w-[60px] flex-1 overflow-hidden rounded-full bg-muted">
                    <span className="block h-full rounded-full bg-primary" style={{ width: `${w}%` }} />
                  </span>
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {formatearNumero(pct, 1)}%
                  </span>
                </span>
              </span>
              <span className="flex shrink-0 flex-col items-end gap-1">
                <span className="font-mono text-[11.5px] tabular-nums text-foreground">
                  {formatearMoneda(m.pim, true)}
                </span>
                <EstadoChip tono={tono} tamano="xs">
                  {ETIQUETA_SEMAFORO[tono]}
                </EstadoChip>
              </span>
            </button>
          );
        })
      )}
    </PanelSection>
  );
}

export default FocosAtencion;
