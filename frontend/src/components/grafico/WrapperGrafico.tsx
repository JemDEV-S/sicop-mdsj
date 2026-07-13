import type { ReactNode } from 'react';
import { ResponsiveContainer } from 'recharts';

interface WrapperGraficoProps {
  children: ReactNode;
  height?: number | string;
  className?: string;
}

/**
 * Contenedor estándar para gráficos de Recharts.
 * Asegura la inyección correcta de la paleta institucional sin depender
 * de los colores por defecto de la librería.
 */
export default function WrapperGrafico({ children, height = 300, className }: WrapperGraficoProps) {
  return (
    <div className={`w-full bg-white p-4 rounded-lg border border-gray-200 shadow-sm ${className || ''}`} style={{ height }}>
      {/* 
        Inyectamos las variables globales explícitamente en el scope por si la librería
        no las hereda nativamente. Las gráficas usarán "var(--primary)", etc.
      */}
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}
