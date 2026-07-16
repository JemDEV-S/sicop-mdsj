/**
 * Página Pipeline de Pedidos (HU-09, T-45).
 *
 * Ruta: /interno/pipeline
 * Protegida por RequireAuth.
 */
import { PageHeader } from '@/components/layout/PageHeader';
import { useContextoInterno } from '@/store/contexto-interno';
import PipelineKanban from '@/features/pipeline/secciones/PipelineKanban';

export default function Pipeline() {
  const año = useContextoInterno((s) => s.añoActivo);
  const cc = useContextoInterno((s) => s.ccActivo);

  const contexto = cc
    ? `${cc.nombre}${cc.codigo ? ` (${cc.codigo})` : ''} · Año ${año}`
    : `Año ${año}`;

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Pipeline de pedidos"
        descripcion={
          <>
            Vista completa por macrofase del SIGA. {contexto}.
          </>
        }
      />
      <PipelineKanban />
    </div>
  );
}
