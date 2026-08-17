// Sección "Pipeline por macrofase": conteo de requerimientos por macrofase del
// trámite SIGA, con barra proporcional. Fuente: kanban del pipeline.

import { formatearMoneda } from '@/lib/formatters';
import type { KanbanResponse, Macrofase } from '@/features/dashboard/types';
import { BarraFase, PanelSection } from '../ui/primitivas';

// Gradación de color por avance, consistente con el widget del dashboard.
const BARRA_MACROFASE: Record<Macrofase, string> = {
  solicitud: 'bg-primary/25',
  programacion: 'bg-primary/45',
  certificacion: 'bg-primary/65',
  contratacion: 'bg-primary/85',
  ejecucion: 'bg-secondary',
  cierre: 'bg-muted-foreground/50',
};

export function PipelineMacrofase({ kanban }: { kanban: KanbanResponse }) {
  const max = Math.max(1, ...kanban.macrofases.map((m) => m.conteo));
  return (
    <PanelSection
      titulo="Pipeline por macrofase"
      aside="n° de pedidos · trámite SIGA"
      nota="Conteo de requerimientos por macrofase; el monto es el SIGA solicitado (trámite, no presupuesto)."
    >
      {kanban.macrofases.map((m) => (
        <BarraFase
          key={m.macrofase}
          label={m.macrofase_label}
          ancho={(m.conteo / max) * 100}
          barraClass={BARRA_MACROFASE[m.macrofase]}
          valorTexto={String(m.conteo)}
          pctTexto={formatearMoneda(m.monto, true)}
        />
      ))}
    </PanelSection>
  );
}

export default PipelineMacrofase;
