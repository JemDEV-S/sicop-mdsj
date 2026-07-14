import { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { parseMonto, formatearMoneda } from '@/lib/formatters';
import type { EjecucionMensualAcumulado } from '@/features/ejecucion/types';

interface GraficoAcumuladoProps {
  data?: EjecucionMensualAcumulado[];
  isLoading: boolean;
}

const NOMBRES_MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

/**
 * Gráfico de área acumulada del devengado por mes.
 *
 * Respeta el hallazgo de granularidad SIAF: los montos por mes son FLUJOS,
 * no acumulados. El backend hace la suma acumulativa; aquí solo lo
 * mostramos con etiqueta clara del último punto.
 */
export function GraficoAcumulado({ data, isLoading }: GraficoAcumuladoProps) {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];
    return data.map((d) => ({
      mes: NOMBRES_MESES[d.mes_eje - 1] ?? String(d.mes_eje),
      mesNum: d.mes_eje,
      acumulado: parseMonto(d.devengado_acumulado) ?? 0,
      mesFlujo: parseMonto(d.devengado_mes) ?? 0,
    }));
  }, [data]);

  const ultimo = chartData.length > 0 ? chartData[chartData.length - 1] : null;

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 md:p-8">
        <div className="h-6 w-64 bg-muted animate-pulse rounded mb-6" />
        <div className="h-[280px] w-full bg-muted animate-pulse rounded-lg" />
      </div>
    );
  }

  if (chartData.length === 0) {
    return (
      <div className="rounded-2xl border border-border bg-card p-8 text-center">
        <p className="text-sm text-muted-foreground">
          Aún no hay ejecución registrada para el año seleccionado.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-border bg-card p-6 md:p-8">
      {/* Etiqueta destacada del último mes */}
      {ultimo ? (
        <div className="mb-6 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              Total ejecutado hasta {ultimo.mes}
            </p>
            <p className="mt-1 text-3xl md:text-4xl font-bold text-foreground tabular-nums">
              {formatearMoneda(ultimo.acumulado, true)}
            </p>
          </div>
          <p className="text-xs text-muted-foreground max-w-sm sm:text-right">
            La línea muestra cuánto dinero se ha pagado en total, mes a mes, desde enero.
          </p>
        </div>
      ) : null}

      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="gradAcumulado" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.35} />
                <stop offset="100%" stopColor="var(--primary)" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="var(--border)"
              opacity={0.6}
            />
            <XAxis
              dataKey="mes"
              tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }}
              stroke="var(--border)"
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v) => formatearMoneda(v, true)}
              tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }}
              stroke="var(--border)"
              tickLine={false}
              axisLine={false}
              width={70}
            />
            <Tooltip
              cursor={{ stroke: 'var(--primary)', strokeWidth: 1, strokeDasharray: '3 3' }}
              contentStyle={{
                backgroundColor: 'var(--card)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                boxShadow: '0 1px 3px rgba(0,0,0,.06)',
              }}
              labelStyle={{ color: 'var(--foreground)', fontWeight: 600 }}
              formatter={(value: any, name: any) => {
                if (name === 'Total acumulado') {
                  return [formatearMoneda(value), name];
                }
                return [formatearMoneda(value), 'Ejecutado ese mes'];
              }}
            />
            {ultimo ? (
              <ReferenceLine
                x={ultimo.mes}
                stroke="var(--primary)"
                strokeDasharray="2 4"
                strokeOpacity={0.4}
              />
            ) : null}
            <Area
              type="monotone"
              dataKey="acumulado"
              name="Total acumulado"
              stroke="var(--primary)"
              strokeWidth={2.5}
              fill="url(#gradAcumulado)"
              isAnimationActive={false}
              dot={{ r: 3, fill: 'var(--primary)', strokeWidth: 0 }}
              activeDot={{ r: 5, fill: 'var(--primary)' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default GraficoAcumulado;
