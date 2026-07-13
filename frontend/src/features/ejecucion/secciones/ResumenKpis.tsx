import { Wallet, ShieldCheck, CircleDollarSign, Send, Percent } from 'lucide-react';
import { KpiCard } from '@/components/KpiCard';
import { SkeletonKPI } from '@/components/layout/LoadingSkeleton';
import { parseMonto, formatearMoneda } from '@/lib/formatters';
import type { EjecucionResumen } from '../types';

interface ResumenKpisProps {
  data?: EjecucionResumen;
  isLoading: boolean;
}

export default function ResumenKpis({ data, isLoading }: ResumenKpisProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <SkeletonKPI key={i} />
        ))}
      </div>
    );
  }

  if (!data) return null;

  const pim = parseMonto(data.pim);
  const certificado = parseMonto(data.certificado);
  const devengado = parseMonto(data.devengado);
  const girado = parseMonto(data.girado);

  const pctNum = parseMonto(data.porcentaje_ejecucion);
  const pctText = pctNum === null ? 'ND' : `${pctNum}%`;

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      <KpiCard
        label="PIM"
        valor={formatearMoneda(pim, true)}
        ayuda="Presupuesto Institucional Modificado"
        icono={Wallet}
        tono="primario"
      />
      <KpiCard
        label="Certificado"
        valor={formatearMoneda(certificado, true)}
        icono={ShieldCheck}
        tono="secundario"
      />
      <KpiCard
        label="Devengado"
        valor={formatearMoneda(devengado, true)}
        icono={CircleDollarSign}
        tono="primario"
      />
      <KpiCard
        label="Girado"
        valor={formatearMoneda(girado, true)}
        icono={Send}
        tono="neutro"
      />
      <KpiCard
        label="% Ejecución"
        valor={pctText}
        ayuda="Devengado sobre PIM"
        icono={Percent}
        tono="acento"
      />
    </div>
  );
}
