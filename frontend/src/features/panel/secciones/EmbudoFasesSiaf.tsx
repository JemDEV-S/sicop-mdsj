// Embudo de fases SIAF: dónde se detiene el gasto. Con el bloque MEF del
// resumen de saldos se muestran las cinco fases oficiales (PIM → Certificado →
// Comprometido → Devengado → Girado); si el usuario no tiene visión del MEF,
// cae a las fases del SIGA de su ámbito (PIM/Certificado/Comprometido) rotulado
// como referencia operativa. No se inventan fases que no existan en el dato.

import { formatearNumero } from '@/lib/formatters';
import type { SaldosResumen } from '@/features/dashboard/types';
import { BarraFase, PanelSection } from '../ui/primitivas';

interface FaseDef {
  label: string;
  valor: number;
  barra: string;
  saldoLabel: string | null;
  saldo: number | null;
}

export function EmbudoFasesSiaf({ resumen }: { resumen: SaldosResumen }) {
  const mef = resumen.mef;
  const oficial = mef != null;

  const pim = mef?.pim ?? resumen.pim;
  const fases: FaseDef[] = oficial
    ? [
        { label: 'PIM', valor: mef!.pim, barra: 'bg-primary', saldoLabel: 'Por certificar', saldo: mef!.pim - mef!.certificado },
        { label: 'Certificado', valor: mef!.certificado, barra: 'bg-primary/80', saldoLabel: 'Por comprometer', saldo: mef!.certificado - mef!.comprometido },
        { label: 'Comprometido', valor: mef!.comprometido, barra: 'bg-primary/60', saldoLabel: 'Por devengar', saldo: mef!.comprometido - mef!.devengado },
        { label: 'Devengado', valor: mef!.devengado, barra: 'bg-secondary', saldoLabel: 'Por girar', saldo: mef!.devengado - mef!.girado },
        { label: 'Girado', valor: mef!.girado, barra: 'bg-secondary/70', saldoLabel: null, saldo: null },
      ]
    : [
        { label: 'PIM', valor: resumen.pim, barra: 'bg-primary', saldoLabel: 'Por certificar', saldo: resumen.pim - resumen.certificado },
        { label: 'Certificado', valor: resumen.certificado, barra: 'bg-primary/80', saldoLabel: 'Por comprometer', saldo: resumen.certificado - resumen.comprometido },
        { label: 'Comprometido', valor: resumen.comprometido, barra: 'bg-primary/60', saldoLabel: null, saldo: null },
      ];

  return (
    <PanelSection
      titulo="Embudo de fases SIAF — ¿dónde se detiene el gasto?"
      aside={oficial ? 'base PIM · MEF oficial' : 'base PIM · referencia SIGA'}
      nota={
        oficial
          ? 'Cinco fases del snapshot MEF por meta. La brecha entre barras es el saldo que aún no pasa a la fase siguiente.'
          : 'Fases del SIGA a nivel meta (referencia operativa). El devengado oficial es el del MEF; este ámbito no lo expone.'
      }
    >
      {fases.map((f) => (
        <BarraFase
          key={f.label}
          label={f.label}
          ancho={pim > 0 ? (f.valor / pim) * 100 : 0}
          barraClass={f.barra}
          valorTexto={formatearNumero(f.valor, 0)}
          pctTexto={`${pim > 0 ? Math.round((f.valor / pim) * 100) : 0}%`}
          sub={
            f.saldoLabel && f.saldo != null && f.saldo > 0 ? (
              <span className="rounded border border-semaforo-critico/30 bg-semaforo-critico/10 px-1.5 py-px text-[10.5px] text-destructive">
                ↓ {f.saldoLabel} <span className="font-mono font-semibold">{formatearNumero(f.saldo, 0)}</span>
              </span>
            ) : undefined
          }
        />
      ))}
    </PanelSection>
  );
}

export default EmbudoFasesSiaf;
