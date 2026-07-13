import { cn } from '@/lib/utils';

interface ProgresoAnilloProps {
  /** Valor entre 0 y 100. */
  valor: number;
  /** Diámetro en px. */
  size?: number;
  /** Grosor del anillo. */
  grosor?: number;
  className?: string;
  /** Texto grande dentro del anillo. Si se omite, muestra `${valor}%`. */
  centro?: React.ReactNode;
  /** Etiqueta pequeña debajo del centro. */
  etiqueta?: React.ReactNode;
  /** Color del track de progreso. Default primary. */
  color?: 'primary' | 'secondary' | 'accent';
}

const colorMap: Record<NonNullable<ProgresoAnilloProps['color']>, string> = {
  primary: 'text-primary',
  secondary: 'text-secondary',
  accent: 'text-accent',
};

/**
 * Anillo circular de progreso. Usado como pieza destacada en el hero.
 * Sobrio, un solo color, sin gradientes ni brillos.
 */
export function ProgresoAnillo({
  valor,
  size = 200,
  grosor = 12,
  className,
  centro,
  etiqueta,
  color = 'primary',
}: ProgresoAnilloProps) {
  const clamped = Math.max(0, Math.min(100, valor));
  const radio = (size - grosor) / 2;
  const circunferencia = 2 * Math.PI * radio;
  const dashOffset = circunferencia * (1 - clamped / 100);

  return (
    <div
      className={cn('relative inline-flex items-center justify-center', className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Progreso: ${clamped.toFixed(1)}%`}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className={colorMap[color]}
        aria-hidden="true"
      >
        {/* Track de fondo */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radio}
          fill="none"
          stroke="currentColor"
          strokeOpacity="0.12"
          strokeWidth={grosor}
        />
        {/* Progreso */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radio}
          fill="none"
          stroke="currentColor"
          strokeWidth={grosor}
          strokeLinecap="round"
          strokeDasharray={circunferencia}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dashoffset 600ms ease-out' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-4">
        <div className="text-4xl md:text-5xl font-bold text-foreground tabular-nums leading-none">
          {centro ?? `${clamped.toFixed(1)}%`}
        </div>
        {etiqueta ? (
          <div className="mt-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            {etiqueta}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default ProgresoAnillo;
