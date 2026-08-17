// Gráfico de dona (SVG) con leyenda, para la distribución de requerimientos por
// estado en el modal de reporte. Colores de series derivados de los tokens
// institucionales (var(--chart-*)); centro con el total.

export interface SegmentoDona {
  label: string;
  n: number;
  color: string; // clase de color de texto (para leyenda) o var CSS
}

const R = 42;
const CIRC = 2 * Math.PI * R;

export function Dona({
  segmentos,
  total,
  unidad = 'requerimientos',
}: {
  segmentos: SegmentoDona[];
  total: number;
  unidad?: string;
}) {
  let acumulado = 0;
  const arcos = segmentos.map((s) => {
    const frac = total > 0 ? s.n / total : 0;
    const dash = `${(frac * CIRC).toFixed(1)} ${CIRC.toFixed(1)}`;
    const offset = (-(acumulado / (total || 1)) * CIRC).toFixed(1);
    acumulado += s.n;
    return { ...s, dash, offset };
  });

  return (
    <div className="flex flex-wrap items-center gap-4">
      <svg viewBox="0 0 100 100" className="h-[126px] w-[126px] shrink-0" role="img" aria-label={`Distribución por ${unidad}`}>
        <circle cx="50" cy="50" r={R} fill="none" stroke="var(--muted)" strokeWidth="15" />
        {arcos.map((a) => (
          <circle
            key={a.label}
            cx="50"
            cy="50"
            r={R}
            fill="none"
            stroke={a.color}
            strokeWidth="15"
            strokeDasharray={a.dash}
            strokeDashoffset={a.offset}
            transform="rotate(-90 50 50)"
          />
        ))}
        <text x="50" y="47" textAnchor="middle" fontSize="17" fontWeight="600" fontFamily="IBM Plex Mono" fill="var(--foreground)">
          {total}
        </text>
        <text x="50" y="60" textAnchor="middle" fontSize="7.5" fontFamily="IBM Plex Sans" fill="var(--muted-foreground)">
          {unidad}
        </text>
      </svg>
      <div className="flex min-w-[150px] flex-1 flex-col gap-1.5">
        {arcos.map((a) => (
          <div key={a.label} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-[2px]" style={{ background: a.color }} aria-hidden="true" />
            <span className="flex-1 text-[11.5px]">{a.label}</span>
            <span className="font-mono text-[11.5px] text-muted-foreground">{a.n}</span>
            <span className="w-10 text-right font-mono text-[10.5px] text-muted-foreground/80">
              {total > 0 ? Math.round((a.n / total) * 100) : 0}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Dona;
