import { type EjecucionResumen } from '../types';
import { parseMonto, formatearMoneda } from '../../../lib/formatters';

interface ResumenKpisProps {
  data?: EjecucionResumen;
  isLoading: boolean;
}

function KpiCard({ title, value, subtext }: { title: string; value: string; subtext?: string }) {
  return (
    <div className="bg-card text-card-foreground p-4 rounded-lg shadow border flex flex-col gap-1">
      <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
      <div className="text-2xl font-bold">{value}</div>
      {subtext && <p className="text-xs text-muted-foreground">{subtext}</p>}
    </div>
  );
}

function KpiSkeleton() {
  return (
    <div className="bg-card p-4 rounded-lg shadow border flex flex-col gap-2 animate-pulse">
      <div className="h-4 bg-muted rounded w-1/2"></div>
      <div className="h-8 bg-muted rounded w-3/4"></div>
    </div>
  );
}

export default function ResumenKpis({ data, isLoading }: ResumenKpisProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <KpiSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (!data) return null;

  const pim = parseMonto(data.pim);
  const certificado = parseMonto(data.certificado);
  const devengado = parseMonto(data.devengado);
  const girado = parseMonto(data.girado);
  
  // Porcentaje viene calculado por la DB, pero lo tratamos defensivamente
  const pctNum = parseMonto(data.porcentaje_ejecucion);
  const pctText = pctNum === null ? 'ND' : `${pctNum}%`;

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      <KpiCard 
        title="PIM" 
        value={formatearMoneda(pim, true)} 
        subtext="Presupuesto Institucional"
      />
      <KpiCard 
        title="Certificado" 
        value={formatearMoneda(certificado, true)} 
      />
      <KpiCard 
        title="Devengado" 
        value={formatearMoneda(devengado, true)} 
      />
      <KpiCard 
        title="Girado" 
        value={formatearMoneda(girado, true)} 
      />
      <KpiCard 
        title="% Ejecución" 
        value={pctText} 
        subtext="Avance Devengado/PIM"
      />
    </div>
  );
}
