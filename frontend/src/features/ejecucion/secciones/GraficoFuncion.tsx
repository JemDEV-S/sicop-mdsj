import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { BarChart3 } from 'lucide-react';
import { SectionCard } from '@/components/layout/SectionCard';
import { SkeletonGrafico } from '@/components/layout/LoadingSkeleton';
import { EmptyState } from '@/components/layout/EmptyState';
import { parseMonto, calcularPorcentaje, formatearMoneda } from '@/lib/formatters';
import type { EjecucionPorFuncion } from '../types';

interface GraficoFuncionProps {
  data?: EjecucionPorFuncion[];
  isLoading: boolean;
}

export default function GraficoFuncion({ data, isLoading }: GraficoFuncionProps) {
  const chartData = useMemo(() => {
    if (!data) return [];
    return data
      .map((d) => {
        const pim = parseMonto(d.pim);
        const devengado = parseMonto(d.devengado);
        return {
          nombre: d.funcion_nombre || 'Desconocido',
          pim,
          devengado,
          porcentaje: calcularPorcentaje(devengado, pim),
        };
      })
      .filter((d) => d.pim !== null);
  }, [data]);

  if (isLoading) {
    return <SkeletonGrafico alto={340} />;
  }

  if (chartData.length === 0) {
    return (
      <SectionCard titulo="Ejecución por función" icono={BarChart3}>
        <EmptyState
          icono={BarChart3}
          titulo="Sin datos"
          descripcion="No hay ejecución por función disponible para el año seleccionado."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard titulo="Ejecución por función" icono={BarChart3}>
      <div className="h-[340px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              horizontal={true}
              vertical={false}
              stroke="var(--border)"
              opacity={0.6}
            />
            <XAxis
              type="number"
              tickFormatter={(val) => formatearMoneda(val, true)}
              tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }}
              stroke="var(--border)"
            />
            <YAxis
              type="category"
              dataKey="nombre"
              width={100}
              tick={{ fill: 'var(--foreground)', fontSize: 11 }}
              stroke="var(--border)"
            />
            <Tooltip
              formatter={(value: any, name: any, props: any) => {
                if (name === 'Devengado') {
                  const pct = props.payload.porcentaje;
                  return [`${formatearMoneda(value)} (${pct === null ? 'ND' : pct}%)`, name];
                }
                return [formatearMoneda(value), name];
              }}
              contentStyle={{
                backgroundColor: 'var(--card)',
                color: 'var(--card-foreground)',
                border: '1px solid var(--border)',
                borderRadius: '6px',
              }}
              cursor={{ fill: 'var(--muted)' }}
            />
            <Bar
              dataKey="devengado"
              name="Devengado"
              fill="var(--chart-1)"
              radius={[0, 4, 4, 0]}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}
