import {
  TrendingUp,
  Wallet,
  AlertTriangle,
  CreditCard,
  FileCheck2,
  Landmark,
} from 'lucide-react';
import { KpiCard } from '@/components/KpiCard';
import Semaforo from '@/components/Semaforo';
import { formatearMoneda, formatPorcentaje } from '@/lib/formatters';
import type { SaldosResumen } from '@/features/dashboard/types';
import { mapSemaforo, etiquetaSemaforoGlobal } from '../lib';
import type { SemaforoSaldo } from '../types';

interface KpisSaldosProps {
  resumen: SaldosResumen;
}

const MESES_ABREV = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'setiembre', 'octubre', 'noviembre', 'diciembre',
];

/**
 * KPIs del resumen de saldos. Toda cifra es la oficial del SIAF/MEF (el PIM SIGA
 * no se usa como presupuesto). El semáforo es TEMPORAL: contrasta el avance
 * devengado real contra el esperado por el mes de corte del snapshot, para no
 * alarmar por el rezago propio del backup.
 */
export function KpisSaldos({ resumen }: KpisSaldosProps) {
  const mef = resumen.mef;
  const semEstado = mapSemaforo(resumen.semaforo as SemaforoSaldo);
  const mesCorte = resumen.mes_corte;
  const mesNombre = MESES_ABREV[Math.min(11, Math.max(0, mesCorte - 1))] ?? '';
  const esperado = resumen.avance_esperado;

  // Saldos oficiales a partir del bloque MEF.
  const porEjecutar = mef ? mef.pim - mef.devengado : null; // PIM − devengado
  const porPagar = mef ? mef.devengado - mef.girado : null; // devengado − girado

  const ayudaAvance =
    mef && mesCorte > 0 ? (
      <span title={`Avance esperado a ${mesNombre}: ${formatPorcentaje(esperado)} del PIM. El estado compara el real contra ese esperado.`}>
        {formatPorcentaje(mef.porcentaje_devengado)} real · esperado{' '}
        {formatPorcentaje(esperado)} a {mesNombre}
      </span>
    ) : (
      <>Devengado real sobre el PIM oficial</>
    );

  return (
    <div className="flex flex-col gap-4">
      {/* Fila 1 — ejecución oficial y saldos */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Devengado oficial (SIAF)"
          valor={mef ? formatearMoneda(mef.devengado) : formatPorcentaje(resumen.porcentaje_devengado)}
          tono="primario"
          icono={TrendingUp}
          ayuda={ayudaAvance}
          semaforo={
            semEstado ? (
              <Semaforo
                estado={semEstado}
                texto={etiquetaSemaforoGlobal(resumen.semaforo as SemaforoSaldo)}
              />
            ) : undefined
          }
        />

        <KpiCard
          label="Saldo por ejecutar"
          valor={porEjecutar != null ? formatearMoneda(porEjecutar) : 'ND'}
          tono="secundario"
          icono={Wallet}
          ayuda="PIM oficial − devengado: cuánto falta por ejecutar"
        />

        <KpiCard
          label="Girado (pagado)"
          valor={mef ? formatearMoneda(mef.girado) : 'ND'}
          tono="neutro"
          icono={CreditCard}
          ayuda={
            <span title="Fase de pago del gasto. Nace del devengado.">
              {mef && mef.pim > 0
                ? `${formatPorcentaje((mef.girado / mef.pim) * 100)} del PIM pagado`
                : 'ND'}
            </span>
          }
        />

        <KpiCard
          label="Devengado por pagar"
          valor={porPagar != null ? formatearMoneda(porPagar) : 'ND'}
          tono="neutro"
          icono={FileCheck2}
          ayuda="Obligación reconocida (devengada) aún no girada"
        />
      </div>

      {/* Fila 2 — cadena previa + metas */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="PIM oficial (SIAF)"
          valor={mef ? formatearMoneda(mef.pim) : 'ND'}
          tono="neutro"
          icono={Landmark}
          ayuda="Presupuesto Institucional Modificado del pliego según el MEF"
        />

        <KpiCard
          label="Certificado (SIAF)"
          valor={mef ? formatearMoneda(mef.certificado) : 'ND'}
          tono="neutro"
          icono={FileCheck2}
          ayuda="Crédito certificado disponible para comprometer"
        />

        <KpiCard
          label="Comprometido (SIAF)"
          valor={mef ? formatearMoneda(mef.comprometido) : 'ND'}
          tono="neutro"
          icono={FileCheck2}
          ayuda="Gasto comprometido (fase previa al devengado)"
        />

        <KpiCard
          label="Metas de la unidad"
          valor={resumen.metas_total.toLocaleString('es-PE')}
          tono={resumen.metas_criticas > 0 ? 'destructivo' : 'neutro'}
          icono={AlertTriangle}
          ayuda={
            resumen.metas_criticas > 0 ? (
              <span className="text-destructive font-medium">
                {resumen.metas_criticas} con rezago severo
              </span>
            ) : (
              'Ninguna meta con rezago severo'
            )
          }
        />
      </div>
    </div>
  );
}

export default KpisSaldos;
