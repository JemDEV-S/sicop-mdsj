import { useMemo } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { PieChart as PieChartIcon } from 'lucide-react';
import { SectionCard } from '@/components/layout/SectionCard';
import { SkeletonGrafico } from '@/components/layout/LoadingSkeleton';
import { EmptyState } from '@/components/layout/EmptyState';
import { parseMonto, calcularPorcentaje, formatearMoneda } from '@/lib/formatters';
import type { EjecucionPorFuente } from '../types';

interface GraficoFuenteProps {
  data?: EjecucionPorFuente[];
  isLoading: boolean;
}

const COLORS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
];

export default function GraficoFuente({ data, isLoading }: GraficoFuenteProps) {
  const chartData = useMemo(() => {
    if (!data) return [];
    const validos = data
      .map((d) => ({
        nombre: d.fuente_nombre || 'Desconocido',
        pim: parseMonto(d.pim),
      }))
      .filter((d) => d.pim !== null && d.pim > 0);

    const totalPim = validos.reduce((acc, curr) => acc + (curr.pim as number), 0);

    return validos.map((d) => ({
      ...d,
      porcentaje: calcularPorcentaje(d.pim, totalPim),
    }));
  }, [data]);

  if (isLoading) {
    return <SkeletonGrafico alto={340} />;
  }

  if (chartData.length === 0) {
    return (
      <SectionCard titulo="PIM por fuente de financiamiento" icono={PieChartIcon}>
        <EmptyState
          icono={PieChartIcon}
          titulo="Sin datos"
          descripcion="No hay presupuesto por fuente disponible para el año seleccionado."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard titulo="PIM por fuente de financiamiento" icono={PieChartIcon}>
      <div className="h-[340px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={70}
              outerRadius={110}
              paddingAngle={2}
              dataKey="pim"
              nameKey="nombre"
              stroke="var(--card)"
              isAnimationActive={false}
            >
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: any, name: any, props: any) => {
                const pct = props.payload.porcentaje;
                return [`${formatearMoneda(value)} (${pct === null ? 'ND' : pct}%)`, name];
              }}
              contentStyle={{
                backgroundColor: 'var(--card)',
                color: 'var(--card-foreground)',
                border: '1px solid var(--border)',
                borderRadius: '6px',
              }}
            />
            <Legend
              layout="horizontal"
              verticalAlign="bottom"
              align="center"
              wrapperStyle={{ fontSize: '12px', color: 'var(--muted-foreground)' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}
