import { Landmark, TrendingUp, Wallet, AlertTriangle } from 'lucide-react';
import { KpiCard } from '@/components/KpiCard';
import Semaforo from '@/components/Semaforo';
import { formatearMoneda, formatPorcentaje } from '@/lib/formatters';
import type { SaldosResumen } from '@/features/dashboard/types';
import { mapSemaforo, etiquetaSemaforoGlobal } from '../lib';
import type { SemaforoSaldo } from '../types';

interface KpisSaldosProps {
  resumen: SaldosResumen;
}

/**
 * Fila de KPIs del resumen de saldos. El número protagonista es el DEVENGADO
 * OFICIAL (MEF) — el mismo que ve el ciudadano en el portal público. El bloque
 * SIGA (PIM asignado, saldo disponible) es la referencia operativa de la unidad.
 *
 * El % y el semáforo salen de `devengado_mef / pim_mef` (nunca de cert+compr).
 */
export function KpisSaldos({ resumen }: KpisSaldosProps) {
  const mef = resumen.mef;
  const semEstado = mapSemaforo(resumen.semaforo as SemaforoSaldo);

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {mef ? (
        <KpiCard
          label="Devengado oficial (MEF)"
          valor={formatearMoneda(mef.devengado)}
          tono="primario"
          icono={TrendingUp}
          ayuda={
            <span title="Fuente: portal MEF (Consulta amigable). Es el mismo número que ve el ciudadano.">
              {formatPorcentaje(mef.porcentaje_devengado)} del PIM oficial
            </span>
          }
          semaforo={
            semEstado ? (
              <Semaforo
                estado={semEstado}
                texto={etiquetaSemaforoGlobal(resumen.semaforo as SemaforoSaldo)}
              />
            ) : undefined
          }
        />
      ) : (
        <KpiCard
          label="% Ejecución (MEF)"
          valor={formatPorcentaje(resumen.porcentaje_devengado)}
          tono="primario"
          icono={TrendingUp}
          ayuda="Devengado real sobre el PIM oficial"
          semaforo={
            semEstado ? (
              <Semaforo
                estado={semEstado}
                texto={etiquetaSemaforoGlobal(resumen.semaforo as SemaforoSaldo)}
              />
            ) : undefined
          }
        />
      )}

      <KpiCard
        label="PIM asignado (SIGA)"
        valor={formatearMoneda(resumen.pim)}
        tono="neutro"
        icono={Landmark}
        ayuda={
          <span title="Presupuesto Institucional Modificado según el SIGA a nivel meta, filtrado por unidad. Puede diferir del PIM oficial MEF: no todo el techo del pliego está desagregado a metas.">
            PIM del pliego (MEF): {mef ? formatearMoneda(mef.pim) : 'ND'}
          </span>
        }
      />

      <KpiCard
        label="Saldo disponible (SIGA)"
        valor={formatearMoneda(resumen.saldo_disponible)}
        tono="secundario"
        icono={Wallet}
        ayuda="Techo aún no comprometido en la unidad"
      />

      <KpiCard
        label="Metas de la unidad"
        valor={resumen.metas_total.toLocaleString('es-PE')}
        tono={resumen.metas_criticas > 0 ? 'destructivo' : 'neutro'}
        icono={AlertTriangle}
        ayuda={
          resumen.metas_criticas > 0 ? (
            <span className="text-destructive font-medium">
              {resumen.metas_criticas} en riesgo (&lt;30% devengado)
            </span>
          ) : (
            'Ninguna meta en riesgo'
          )
        }
      />
    </div>
  );
}

export default KpisSaldos;
