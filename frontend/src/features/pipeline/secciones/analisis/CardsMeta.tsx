// Fila de tarjetas KPI del ámbito (plantilla v2 · cardsMeta). Reusa el KpiTile
// compartido del Panel v2 para mantener una sola identidad visual.
//
// Regla de oro (§7): el dinero es del MEF, 1× por meta. Nunca se suma el
// devengado por pedido. Los conteos SIGA (requerimientos, órdenes, PECOSAS)
// son trámite, no presupuesto.

import { formatearMoneda, formatearNumero } from '@/lib/formatters';
import { KpiTile } from '@/features/panel/ui/primitivas';
import type { AgregadoAmbito } from './datos';

export function CardsMeta({
  agregado,
  avanceEsperado,
  nEstancados,
}: {
  agregado: AgregadoAmbito;
  avanceEsperado: number;
  nEstancados: number;
}) {
  const { pim, devengado, pct, n_metas, n_pedidos, n_ordenes, n_pecosas } = agregado;
  const saldo = pim - devengado;
  const rezago = pct != null ? Math.round((avanceEsperado - pct) * 10) / 10 : null;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
      <KpiTile
        label="Monto ejecutado"
        fuente="SIAF"
        valor={formatearMoneda(devengado, true)}
        valorClass="text-primary"
        ayuda={
          pct != null
            ? `${formatearNumero(pct, 1)}% del PIM · esperado ${formatearNumero(avanceEsperado, 1)}%`
            : 'Sin PIM para calcular avance'
        }
        chip={
          rezago != null && rezago > 0
            ? { texto: `Atrasado ${formatearNumero(rezago, 1)} pts`, tono: 'critico' }
            : rezago != null
              ? { texto: 'Al día', tono: 'ok' }
              : undefined
        }
      />
      <KpiTile
        label="PIM"
        fuente="SIAF"
        valor={formatearMoneda(pim, true)}
        ayuda={`Techo vigente · ${n_metas} meta${n_metas === 1 ? '' : 's'}`}
      />
      <KpiTile
        label="Saldo por ejecutar"
        fuente="SIAF"
        valor={formatearMoneda(saldo, true)}
        valorClass="text-destructive"
        ayuda="PIM − devengado"
      />
      <KpiTile
        label="Requerimientos"
        fuente="SIGA"
        valor={String(n_pedidos)}
        ayuda={
          nEstancados > 0
            ? `${nEstancados} estancado${nEstancados === 1 ? '' : 's'} · trámite operativo`
            : 'Pedidos del ámbito · trámite operativo'
        }
        chip={nEstancados > 0 ? { texto: 'Requiere acción', tono: 'alerta' } : undefined}
      />
      <KpiTile
        label="Órdenes y PECOSAS"
        fuente="SIGA"
        valor={`${n_ordenes} / ${n_pecosas}`}
        ayuda="Órdenes emitidas / despachos de almacén"
      />
    </div>
  );
}
