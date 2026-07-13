import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { type EjecucionPorFuncion } from '../types';
import { parseMonto, calcularPorcentaje, formatearMoneda } from '../../../lib/formatters';

interface GraficoFuncionProps {
  data?: EjecucionPorFuncion[];
  isLoading: boolean;
}

export default function GraficoFuncion({ data, isLoading }: GraficoFuncionProps) {
  const chartData = useMemo(() => {
    if (!data) return [];
    
    return data
      .map(d => {
        const pim = parseMonto(d.pim);
        const devengado = parseMonto(d.devengado);
        
        return {
          nombre: d.funcion_nombre || 'Desconocido',
          pim,
          devengado,
          // Porcentaje de ejecución de esta función
          porcentaje: calcularPorcentaje(devengado, pim)
        };
      })
      // Filtrar categorías que no tienen PIM (dato faltante)
      .filter(d => d.pim !== null);
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
        No hay datos de ejecución por función disponibles
      </div>
    );
  }

  return (
    <div className="h-[400px] w-full border rounded-lg bg-card p-4">
      <h3 className="text-lg font-semibold mb-4 text-card-foreground">Ejecución por Función</h3>
      <ResponsiveContainer width="100%" height="90%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} opacity={0.2} />
          <XAxis 
            type="number" 
            tickFormatter={(val) => formatearMoneda(val, true)}
            className="text-xs"
          />
          <YAxis 
            type="category" 
            dataKey="nombre" 
            width={100}
            className="text-xs font-medium"
            tick={{ fill: 'var(--foreground)' }}
          />
          <Tooltip 
            formatter={(value: any, name: any, props: any) => {
              if (name === 'Devengado') {
                const pct = props.payload.porcentaje;
                return [`${formatearMoneda(value)} (${pct === null ? 'ND' : pct}%)`, name];
              }
              return [formatearMoneda(value), name];
            }}
            contentStyle={{ backgroundColor: 'var(--card)', color: 'var(--card-foreground)', borderRadius: '8px' }}
            cursor={{ fill: 'var(--muted)' }}
          />
          {/* El PIM va de fondo, el Devengado va encima si es BarChart superpuesto.
              Para horizontal, podemos graficar el devengado directamente. */}
          <Bar dataKey="devengado" name="Devengado" fill="var(--primary)" radius={[0, 4, 4, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
