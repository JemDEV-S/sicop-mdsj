// Fila de KPIs del Panel de decisión.
//
// El dinero es oficial del MEF (bloque `mef` del resumen de saldos) cuando el
// usuario ve el pliego; si está restringido a un subárbol de CC, cae al PIM/
// saldo SIGA de su ámbito (mismo criterio que WidgetSaldos). Los conteos de
// trámite (requerimientos, estancados) vienen del kanban.

import { formatearMoneda, formatearNumero } from '@/lib/formatters';
import type { KanbanResponse, SaldosResumen } from '@/features/dashboard/types';
import { KpiTile } from '../ui/primitivas';
import { chipSemaforoTemporal } from '../lib/semaforo';

export function KpisPanel({
  resumen,
  kanban,
  estancados,
}: {
  resumen: SaldosResumen;
  kanban: KanbanResponse | undefined;
  estancados: number;
}) {
  const mef = resumen.mef;
  const pim = mef?.pim ?? resumen.pim;
  const devengado = mef?.devengado ?? null;
  const saldo = mef?.saldo_disponible ?? resumen.saldo_disponible;
  const pctDev = mef?.porcentaje_devengado ?? resumen.porcentaje_devengado ?? null;

  const totalPedidos = kanban
    ? kanban.macrofases.reduce((a, m) => a + m.conteo, 0)
    : 0;
  const activos = kanban
    ? kanban.macrofases.filter((m) => m.macrofase !== 'cierre').reduce((a, m) => a + m.conteo, 0)
    : 0;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="PIM vigente"
        fuente="SIAF"
        valor={formatearMoneda(pim, true)}
        ayuda={`${resumen.metas_total} meta${resumen.metas_total === 1 ? '' : 's'} activa${resumen.metas_total === 1 ? '' : 's'}`}
      />
      <KpiTile
        label="Devengado"
        fuente="SIAF"
        valor={devengado != null ? formatearMoneda(devengado, true) : '—'}
        valorClass="text-primary"
        ayuda={
          pctDev != null
            ? `${formatearNumero(pctDev, 1)}% del PIM · esperado ${resumen.avance_esperado}%`
            : 'Sin visión del devengado oficial en este ámbito'
        }
        chip={chipSemaforoTemporal(pctDev, resumen.avance_esperado)}
      />
      <KpiTile
        label="Saldo por ejecutar"
        fuente="SIAF"
        valor={formatearMoneda(saldo, true)}
        valorClass="text-destructive"
        ayuda="PIM − devengado"
      />
      <KpiTile
        label="Requerimientos activos"
        fuente="SIGA"
        valor={String(activos)}
        ayuda={`${totalPedidos} en total · ${estancados} estancado${estancados === 1 ? '' : 's'}`}
        chip={estancados > 0 ? { texto: 'Requiere acción', tono: 'accent' } : undefined}
      />
    </div>
  );
}

export default KpisPanel;
