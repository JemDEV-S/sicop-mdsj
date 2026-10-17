import { Link } from 'react-router-dom';
import { Building2, ArrowRight, ArrowUpRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface HeroExecutionCardProps {
  porcentaje: number | null;
  devengado: number | null;
  pim: number | null;
  certificado?: number | null;
  girado?: number | null;
  cargando?: boolean;
  anio?: number;
  className?: string;
}

function formatoMillones(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return '—';
  if (valor >= 1_000_000) return `S/ ${(valor / 1_000_000).toFixed(1)} M`;
  if (valor >= 1_000) return `S/ ${(valor / 1_000).toFixed(0)} mil`;
  return `S/ ${valor.toFixed(0)}`;
}

/**
 * Presentación ultra-minimalista del avance presupuestal y accesos del Hero.
 * Sin cajas, marcos ni fondos pesados: gráficos puros, tipografía y datos esenciales.
 */
export function HeroExecutionCard({
  porcentaje,
  devengado,
  pim,
  cargando = false,
  className,
}: HeroExecutionCardProps) {
  const pctClamped = porcentaje !== null ? Math.max(0, Math.min(100, porcentaje)) : 0;

  // Anillo gráfico SVG minimalista
  const size = 56;
  const strokeWidth = 4.5;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - pctClamped / 100);

  return (
    <div className={cn('w-full max-w-xl space-y-4 pt-1', className)}>
      {/* ─── Línea 1: Certificación oficial MEF ultra limpia ─── */}
      <div className="flex items-center gap-2 text-xs sm:text-sm font-medium text-muted-foreground/90">
        <span className="relative flex h-2 w-2 shrink-0">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
        </span>
        <span>Portal oficial de Transparencia Activa · Datos oficiales del MEF</span>
      </div>

      {/* ─── Línea 2: Gráfico de Avance + Datos Esenciales (Sin cuadro de fondo) ─── */}
      <Link
        to="/ejecucion"
        className="group/stat block py-1 transition-opacity hover:opacity-90"
        title="Ver dashboard detallado de ejecución presupuestal"
      >
        <div className="flex items-center gap-4">
          {/* Gráfico circular minimalista */}
          <div className="relative shrink-0 flex items-center justify-center">
            <svg
              width={size}
              height={size}
              viewBox={`0 0 ${size} ${size}`}
              className="transform -rotate-90"
              aria-hidden="true"
            >
              <defs>
                <linearGradient id="miniRingGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#10b981" />
                  <stop offset="100%" stopColor="#3484A5" />
                </linearGradient>
              </defs>

              {/* Pista base */}
              <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke="currentColor"
                strokeWidth={strokeWidth}
                className="text-zinc-200/80 dark:text-zinc-800"
              />

              {/* Trazo de avance con gradiente */}
              <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke="url(#miniRingGradient)"
                strokeWidth={strokeWidth}
                strokeDasharray={circumference}
                strokeDashoffset={cargando ? circumference : strokeDashoffset}
                strokeLinecap="round"
                className="transition-all duration-700 ease-out"
              />
            </svg>

            {/* Porcentaje en el centro del anillo */}
            <div className="absolute inset-0 flex items-center justify-center text-center">
              <span className="font-mono text-xs font-bold text-foreground">
                {porcentaje !== null ? `${Math.round(porcentaje)}%` : '—'}
              </span>
            </div>
          </div>

          {/* Cifras de ejecución y barra gráfica lineal */}
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
              <span className="font-mono text-xl sm:text-2xl font-bold tracking-tight text-foreground group-hover/stat:text-primary transition-colors">
                {porcentaje !== null ? `${porcentaje.toFixed(1)}%` : '—'}
              </span>
              <span className="text-sm font-medium text-foreground">
                PIM ejecutado
              </span>
              <span className="text-muted-foreground/60">·</span>
              <span className="font-mono text-base sm:text-lg font-semibold text-primary">
                {devengado !== null ? formatoMillones(devengado) : '—'}
              </span>
              <span className="text-xs text-muted-foreground font-normal">
                de {formatoMillones(pim)}
              </span>
            </div>

            {/* Barra lineal de progreso ultra fina (3px) */}
            <div className="mt-2 h-1.5 w-full max-w-sm rounded-full bg-zinc-200/80 dark:bg-zinc-800 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-teal-500 to-primary transition-all duration-700"
                style={{ width: `${pctClamped}%` }}
              />
            </div>
          </div>
        </div>
      </Link>

      {/* ─── Línea 3: Botones y Acciones ─── */}
      <div className="pt-2 flex flex-wrap items-center gap-4">
        <Button
          asChild
          size="lg"
          className="rounded-xl px-6 py-3 text-sm sm:text-base font-medium shadow-xs hover:shadow-md transition-all gap-2.5 bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <Link to="/obras" className="inline-flex items-center gap-2.5">
            <Building2 className="w-4 h-4 sm:w-5 sm:h-5" aria-hidden="true" />
            <span>Ver obras públicas</span>
            <ArrowRight className="w-4 h-4 sm:w-5 sm:h-5 ml-0.5" aria-hidden="true" />
          </Link>
        </Button>

        <Link
          to="/ejecucion"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-primary transition-colors py-2 px-1"
        >
          <span>Ver ejecución presupuestal</span>
          <ArrowUpRight className="w-4 h-4 opacity-70" aria-hidden="true" />
        </Link>
      </div>
    </div>
  );
}

export default HeroExecutionCard;
