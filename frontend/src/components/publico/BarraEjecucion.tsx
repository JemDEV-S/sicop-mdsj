import { cn } from '@/lib/utils';

interface BarraEjecucionProps {
  pim: number;
  certificado: number | null;
  comprometido: number | null;
  devengado: number | null;
  girado?: number | null;
  className?: string;
  /** Formato de montos para las etiquetas debajo. */
  formatoMonto: (v: number | null) => string;
  /** Etiqueta accesible. */
  ariaLabel?: string;
}

/**
 * Barra de ejecución escalonada del presupuesto.
 * Muestra Certificado → Comprometido → Devengado → Girado como capas
 * apiladas de mayor a menor porcentaje, sobre el fondo del PIM.
 * Debajo, marcadores puntuales con el porcentaje respectivo.
 */
export function BarraEjecucion({
  pim,
  certificado,
  comprometido,
  devengado,
  girado = null,
  className,
  formatoMonto,
  ariaLabel = 'Avance de ejecución presupuestal',
}: BarraEjecucionProps) {
  const pct = (v: number | null) =>
    v === null || pim <= 0 ? 0 : Math.min(100, Math.max(0, (v / pim) * 100));

  const pCer = pct(certificado);
  const pCom = pct(comprometido);
  const pDev = pct(devengado);
  const pGir = pct(girado);

  const etapas = [
    { key: 'cer', label: 'Certificado', pct: pCer, monto: certificado, color: 'bg-accent', text: 'text-accent-foreground' },
    { key: 'com', label: 'Comprometido', pct: pCom, monto: comprometido, color: 'bg-secondary/60', text: 'text-secondary' },
    { key: 'dev', label: 'Devengado', pct: pDev, monto: devengado, color: 'bg-primary', text: 'text-primary' },
    { key: 'gir', label: 'Girado', pct: pGir, monto: girado, color: 'bg-primary/70', text: 'text-primary' },
  ].filter((e) => e.monto !== null);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Barra */}
      <div
        className="relative h-4 w-full rounded-full bg-muted overflow-hidden ring-1 ring-border"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(pDev)}
        aria-label={ariaLabel}
      >
        {/* Se pintan de mayor a menor porcentaje para que las capas superiores no tapen las inferiores */}
        {[...etapas].sort((a, b) => b.pct - a.pct).map((etapa) => (
          <div
            key={etapa.key}
            className={cn('absolute inset-y-0 left-0 transition-all', etapa.color)}
            style={{ width: `${etapa.pct}%` }}
            aria-hidden="true"
          />
        ))}
      </div>

      {/* Etiquetas debajo, alineadas por porcentaje real */}
      <div className="relative h-14 hidden sm:block" aria-hidden="true">
        {etapas.map((etapa) => (
          <MarcadorEtapa
            key={etapa.key}
            porcentaje={etapa.pct}
            label={etapa.label}
            monto={formatoMonto(etapa.monto)}
            colorTexto={etapa.text}
          />
        ))}
      </div>

      {/* Versión móvil apilada */}
      <ul className="sm:hidden space-y-2 text-sm">
        {etapas.map((etapa) => (
          <li key={etapa.key} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2 text-muted-foreground">
              <span className={cn('inline-block w-2.5 h-2.5 rounded-full', etapa.color)} aria-hidden="true" />
              {etapa.label}
            </span>
            <span className="font-medium text-foreground tabular-nums">
              {etapa.pct.toFixed(1)}% <span className="text-muted-foreground font-normal">· {formatoMonto(etapa.monto)}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

interface MarcadorEtapaProps {
  porcentaje: number;
  label: string;
  monto: string;
  colorTexto: string;
}

function MarcadorEtapa({ porcentaje, label, monto, colorTexto }: MarcadorEtapaProps) {
  // Anclamos por la izquierda excepto al extremo derecho donde flipeamos.
  const flipDerecha = porcentaje > 85;
  return (
    <div
      className="absolute top-0 flex flex-col text-xs"
      style={{
        left: `${porcentaje}%`,
        transform: flipDerecha ? 'translateX(-100%)' : 'translateX(-1px)',
      }}
    >
      <span className={cn('h-2 w-px bg-border')} aria-hidden="true" />
      <span className={cn('mt-1 font-semibold tabular-nums text-foreground')}>
        {porcentaje.toFixed(1)}%
      </span>
      <span className={cn('font-medium', colorTexto)}>{label}</span>
      <span className="text-muted-foreground tabular-nums">{monto}</span>
    </div>
  );
}

export default BarraEjecucion;
