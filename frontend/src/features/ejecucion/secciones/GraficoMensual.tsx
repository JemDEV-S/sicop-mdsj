import { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { type EjecucionMensual } from '../types';
import { parseMonto, formatearMoneda } from '../../../lib/formatters';

interface GraficoMensualProps {
  data?: EjecucionMensual[];
  isLoading: boolean;
}

const NOMBRES_MESES = [
  'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
  'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'
];

export default function GraficoMensual({ data, isLoading }: GraficoMensualProps) {
  const chartData = useMemo(() => {
    if (!data) return [];
    
    // El backend devuelve mes_eje de 1 a 12
    return data.map(d => ({
      mes: NOMBRES_MESES[d.mes_eje - 1] || String(d.mes_eje),
      // Mantenemos null si no hay datos para que Recharts dibuje el gap
      pim: parseMonto(d.pim),
      devengado: parseMonto(d.devengado),
    }));
  }, [data]);

  if (isLoading) {
    return (
      <div className="h-[400px] w-full bg-muted animate-pulse rounded-lg flex items-center justify-center">
        <span className="text-muted-foreground">Cargando gráfico...</span>
      </div>
    );
  }

  if (chartData.length === 0) {
    return (
      <div className="h-[400px] w-full border rounded-lg flex items-center justify-center bg-card text-muted-foreground">
        No hay datos mensuales disponibles
      </div>
    );
  }

  return (
    <div className="h-[400px] w-full border rounded-lg bg-card p-4">
      <h3 className="text-lg font-semibold mb-4 text-card-foreground">Evolución Mensual Acumulada</h3>
      <ResponsiveContainer width="100%" height="90%">
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 30, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.2} />
          <XAxis 
            dataKey="mes" 
            className="text-xs" 
            tick={{ fill: 'var(--foreground)' }}
          />
          <YAxis 
            tickFormatter={(val) => formatearMoneda(val, true)} 
            className="text-xs font-medium"
            tick={{ fill: 'var(--foreground)' }}
          />
          <Tooltip 
            formatter={(value: any, name: any) => [formatearMoneda(value), name]}
            contentStyle={{ backgroundColor: 'var(--card)', color: 'var(--card-foreground)', borderRadius: '8px' }}
          />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
          <Line 
            type="monotone" 
            dataKey="pim" 
            name="PIM" 
            stroke="var(--muted-foreground)" 
            strokeWidth={2}
            dot={false}
            strokeDasharray="5 5"
            connectNulls={false}
            isAnimationActive={false}
          />
          <Line 
            type="monotone" 
            dataKey="devengado" 
            name="Devengado" 
            stroke="var(--primary)" 
            strokeWidth={3}
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
            connectNulls={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
