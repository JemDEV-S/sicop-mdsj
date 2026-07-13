import { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { TrendingUp } from 'lucide-react';
import { SectionCard } from '@/components/layout/SectionCard';
import { SkeletonGrafico } from '@/components/layout/LoadingSkeleton';
import { EmptyState } from '@/components/layout/EmptyState';
import { parseMonto, formatearMoneda } from '@/lib/formatters';
import type { EjecucionMensual } from '../types';

interface GraficoMensualProps {
  data?: EjecucionMensual[];
  isLoading: boolean;
}

const NOMBRES_MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

export default function GraficoMensual({ data, isLoading }: GraficoMensualProps) {
  const chartData = useMemo(() => {
    if (!data) return [];
    return data.map((d) => ({
      mes: NOMBRES_MESES[d.mes_eje - 1] || String(d.mes_eje),
      pim: parseMonto(d.pim),
      devengado: parseMonto(d.devengado),
    }));
  }, [data]);

  if (isLoading) {
    return <SkeletonGrafico alto={340} />;
  }

  if (chartData.length === 0) {
    return (
      <SectionCard titulo="Evolución mensual" icono={TrendingUp}>
        <EmptyState
          icono={TrendingUp}
          titulo="Sin datos"
          descripcion="No hay datos mensuales disponibles para el año seleccionado."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard titulo="Evolución mensual" icono={TrendingUp}>
      <div className="h-[340px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 30, left: 30, bottom: 5 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="var(--border)"
              opacity={0.6}
            />
            <XAxis
              dataKey="mes"
              tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }}
              stroke="var(--border)"
            />
            <YAxis
              tickFormatter={(val) => formatearMoneda(val, true)}
              tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }}
              stroke="var(--border)"
            />
            <Tooltip
              formatter={(value: any, name: any) => [formatearMoneda(value), name]}
              contentStyle={{
                backgroundColor: 'var(--card)',
                color: 'var(--card-foreground)',
                border: '1px solid var(--border)',
                borderRadius: '6px',
              }}
              cursor={{ stroke: 'var(--muted-foreground)', strokeWidth: 1, strokeDasharray: '3 3' }}
            />
            <Legend wrapperStyle={{ fontSize: '12px', color: 'var(--muted-foreground)' }} />
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
              stroke="var(--chart-1)"
              strokeWidth={3}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}
