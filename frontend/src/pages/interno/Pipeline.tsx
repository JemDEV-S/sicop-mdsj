/**
 * Página Pipeline de Pedidos (HU-09, T-45).
 *
 * Ruta: /interno/pipeline
 * Protegida por RequireAuth.
 *
 * Dos vistas de los mismos datos, alternables con un toggle (mantiene el año y
 * CC del topbar):
 *   - Kanban: tablero por macrofase (operativo).
 *   - Reporte profesional: pivote Meta → Clasificador → Pedido con el cruce
 *     SIGA × SIAF por clasificador de gasto, exportable (para economistas).
 */
import { useState } from 'react';
import { PageHeader } from '@/components/layout/PageHeader';
import { cn } from '@/lib/utils';
import { useContextoInterno } from '@/store/contexto-interno';
import PipelineKanban from '@/features/pipeline/secciones/PipelineKanban';
import PipelineReporte from '@/features/pipeline/secciones/PipelineReporte';

type Vista = 'kanban' | 'reporte';

export default function Pipeline() {
  const año = useContextoInterno((s) => s.añoActivo);
  const cc = useContextoInterno((s) => s.ccActivo);
  const [vista, setVista] = useState<Vista>('kanban');

  const contexto = cc
    ? `${cc.nombre}${cc.codigo ? ` (${cc.codigo})` : ''} · Año ${año}`
    : `Año ${año}`;

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Pipeline de pedidos"
        descripcion={
          <>
            {vista === 'kanban'
              ? 'Vista completa por macrofase del SIGA.'
              : 'Reporte por meta y clasificador de gasto (cruce SIGA × SIAF).'}{' '}
            {contexto}.
          </>
        }
        acciones={<ToggleVista vista={vista} onChange={setVista} />}
      />
      {vista === 'kanban' ? <PipelineKanban /> : <PipelineReporte />}
    </div>
  );
}

function ToggleVista({
  vista,
  onChange,
}: {
  vista: Vista;
  onChange: (v: Vista) => void;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Cambiar vista del pipeline"
      className="inline-flex overflow-hidden rounded-md border border-border"
    >
      {(
        [
          { valor: 'kanban', label: 'Tablero' },
          { valor: 'reporte', label: 'Reporte profesional' },
        ] as const
      ).map((opt) => {
        const activo = vista === opt.valor;
        return (
          <button
            key={opt.valor}
            type="button"
            role="radio"
            aria-checked={activo}
            onClick={() => onChange(opt.valor)}
            className={cn(
              'px-3.5 py-2 text-sm font-medium transition-colors focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              activo
                ? 'bg-primary text-primary-foreground'
                : 'bg-card text-foreground hover:bg-muted',
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
