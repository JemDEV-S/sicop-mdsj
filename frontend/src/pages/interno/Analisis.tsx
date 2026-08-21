/**
 * Página Análisis por meta / Cruce SIAF ↔ SIGA — Panel Interno v2.
 *
 * Rutas: /interno/analisis y /interno/cruce. Cada una es una entrada propia del
 * sidebar, así que la navegación entre ambas se hace por el sidebar (no hay
 * toggle interno). `vistaInicial` viene de la ruta y decide qué se monta.
 * Protegida por RequireAuth.
 *
 *   - Análisis por meta — el detalle: barra de ámbito (naturaleza del gasto ·
 *     buscar meta · metas frecuentes), tarjetas KPI, y una sección con pestañas
 *     (Requerimientos · O/C · O/S · PECOSAS · Clasificadores).
 *   - Cruce SIAF ↔ SIGA — dinero oficial del MEF frente al trámite operativo
 *     del SIGA, lado a lado, con las llaves de cruce por pedido.
 *
 * Acepta ?meta=<sec_func> para prefiltrar (viene del Panel/Cruce).
 */
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useContextoInterno } from '@/store/contexto-interno';
import AnalisisPorMeta from '@/features/pipeline/secciones/analisis/AnalisisPorMeta';
import CruceSiafSiga from '@/features/pipeline/secciones/CruceSiafSiga';
import EjecucionSiafReporte from '@/features/pipeline/secciones/analisis/EjecucionSiafReporte';

type Vista = 'meta' | 'cruce' | 'ejecucion';

const TITULO: Record<Vista, string> = {
  meta: 'Análisis por meta',
  cruce: 'Cruce SIAF ↔ SIGA',
  ejecucion: 'Ejecución SIAF',
};

const DESCRIPCION: Record<Vista, string> = {
  meta: 'Detalle por meta: presupuesto MEF y trámite operativo del SIGA.',
  cruce: 'Dinero oficial del MEF frente al trámite operativo del SIGA, lado a lado.',
  ejecucion: 'Gasto por proveedor, clasificador y fuente — el detalle que la API MEF no publica.',
};

export default function Analisis({ vistaInicial = 'meta' }: { vistaInicial?: Vista }) {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const año = useContextoInterno((s) => s.añoActivo);
  const cc = useContextoInterno((s) => s.ccActivo);

  const metaParam = params.get('meta');
  const metaSel = metaParam != null && metaParam !== '' ? Number(metaParam) : null;

  const contexto = cc
    ? `${cc.nombre}${cc.codigo ? ` (${cc.codigo})` : ''} · Año ${año}`
    : `Año ${año}`;

  // Desde el Cruce se puede saltar a analizar una meta: se navega a la ruta de
  // Análisis con ?meta (el sidebar ya marca la entrada correcta).
  const irAMeta = (secFunc: number) => {
    navigate(`/interno/analisis?meta=${secFunc}`);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">{TITULO[vistaInicial]}</h1>
        <p className="text-[12.5px] text-muted-foreground">
          {DESCRIPCION[vistaInicial]} {contexto}.
        </p>
      </div>

      {vistaInicial === 'meta' ? (
        <AnalisisPorMeta metaInicial={metaSel} />
      ) : vistaInicial === 'cruce' ? (
        <CruceSiafSiga metaInicial={metaSel} onAbrirMeta={irAMeta} />
      ) : (
        <EjecucionSiafReporte />
      )}
    </div>
  );
}
