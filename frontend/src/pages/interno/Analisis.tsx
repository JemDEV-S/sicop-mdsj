/**
 * Página Análisis por meta + Cruce SIAF ↔ SIGA — Panel Interno v2.
 *
 * Rutas: /interno/analisis y /interno/cruce (misma página, distinta vista
 * inicial según la ruta). Protegida por RequireAuth.
 *
 * Dos vistas de los mismos datos (comparten año + CC de la barra superior):
 *   - Análisis por meta — el detalle: barra de ámbito (buscar meta ·
 *     Producto/Proyecto · metas frecuentes), tarjetas KPI, y una sección con
 *     pestañas (Requerimientos · O/C · O/S · PECOSAS · Clasificadores).
 *   - Cruce SIAF ↔ SIGA — dinero oficial del MEF frente al trámite operativo
 *     del SIGA, lado a lado, con las llaves de cruce por pedido.
 *
 * Acepta ?meta=<sec_func> para prefiltrar (viene del Panel/Cruce) y ?vista=
 * (analisis|cruce) para la vista inicial.
 */
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useContextoInterno } from '@/store/contexto-interno';
import AnalisisPorMeta from '@/features/pipeline/secciones/analisis/AnalisisPorMeta';
import CruceSiafSiga from '@/features/pipeline/secciones/CruceSiafSiga';

type Vista = 'meta' | 'cruce';

const VISTAS: { valor: Vista; label: string }[] = [
  { valor: 'meta', label: 'Análisis por meta' },
  { valor: 'cruce', label: 'Cruce SIAF ↔ SIGA' },
];

const DESCRIPCION: Record<Vista, string> = {
  meta: 'Detalle por meta: presupuesto MEF y trámite operativo del SIGA.',
  cruce: 'Dinero oficial del MEF frente al trámite operativo del SIGA, lado a lado.',
};

export default function Analisis({ vistaInicial = 'meta' }: { vistaInicial?: Vista }) {
  const [params, setParams] = useSearchParams();
  const año = useContextoInterno((s) => s.añoActivo);
  const cc = useContextoInterno((s) => s.ccActivo);

  const metaParam = params.get('meta');
  const metaSel = metaParam != null && metaParam !== '' ? Number(metaParam) : null;

  const [vista, setVista] = useState<Vista>(vistaInicial);

  const contexto = cc
    ? `${cc.nombre}${cc.codigo ? ` (${cc.codigo})` : ''} · Año ${año}`
    : `Año ${año}`;

  const irAMeta = (secFunc: number) => {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set('meta', String(secFunc));
        return next;
      },
      { replace: true },
    );
    setVista('meta');
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">Análisis por meta</h1>
        <p className="text-[12.5px] text-muted-foreground">
          {DESCRIPCION[vista]} {contexto}.
        </p>
      </div>

      <SegmentedVistas vista={vista} onChange={setVista} />

      {vista === 'meta' ? (
        <AnalisisPorMeta metaInicial={metaSel} />
      ) : (
        <CruceSiafSiga metaInicial={metaSel} onAbrirMeta={irAMeta} />
      )}
    </div>
  );
}

// ─── Segmentado de vistas (Análisis / Cruce) ─────────────────────────────

function SegmentedVistas({ vista, onChange }: { vista: Vista; onChange: (v: Vista) => void }) {
  return (
    <div
      role="tablist"
      aria-label="Vista del análisis"
      className="inline-flex flex-wrap gap-1 rounded-md border border-border bg-card p-1"
    >
      {VISTAS.map((opt) => {
        const activo = vista === opt.valor;
        return (
          <button
            key={opt.valor}
            type="button"
            role="tab"
            aria-selected={activo}
            onClick={() => onChange(opt.valor)}
            className={cn(
              'rounded px-3.5 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              activo ? 'bg-primary text-primary-foreground' : 'text-foreground hover:bg-muted',
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
