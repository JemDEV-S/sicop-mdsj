import { useMemo } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { type EjecucionPorFuente } from '../types';
import { parseMonto, calcularPorcentaje, formatearMoneda } from '../utils';

interface GraficoFuenteProps {
  data?: EjecucionPorFuente[];
  isLoading: boolean;
}

// Colores institucionales / complementarios
const COLORS = [
  'var(--chart-1)', 
  'var(--chart-2)', 
  'var(--chart-3)', 
  'var(--chart-4)', 
  'var(--chart-5)'
];

export default function GraficoFuente({ data, isLoading }: GraficoFuenteProps) {
  const chartData = useMemo(() => {
    if (!data) return [];
    
    // Filtramos las fuentes que tienen PIM válido
    const validos = data
      .map(d => ({
        nombre: d.fuente_nombre || 'Desconocido',
        pim: parseMonto(d.pim),
      }))
      .filter(d => d.pim !== null && d.pim > 0);
      
    const totalPim = validos.reduce((acc, curr) => acc + (curr.pim as number), 0);
    
    return validos.map(d => ({
      ...d,
      porcentaje: calcularPorcentaje(d.pim, totalPim)
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
        No hay datos de presupuesto por fuente disponibles
      </div>
    );
  }

  return (
    <div className="h-[400px] w-full border rounded-lg bg-card p-4">
      <h3 className="text-lg font-semibold mb-4 text-card-foreground">PIM por Fuente de Financiamiento</h3>
      <ResponsiveContainer width="100%" height="90%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={80}
            outerRadius={120}
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
            contentStyle={{ backgroundColor: 'var(--card)', color: 'var(--card-foreground)', borderRadius: '8px' }}
          />
          <Legend layout="horizontal" verticalAlign="bottom" align="center" wrapperStyle={{ fontSize: '12px' }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
