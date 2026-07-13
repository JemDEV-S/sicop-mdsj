import MapaObras from '@/features/obras/MapaObras';
import { PageHeader } from '@/components/layout/PageHeader';

export default function Mapa() {
  return (
    <div className="mx-auto max-w-[1400px] px-4 md:px-6 py-8">
      <PageHeader
        titulo="Mapa de Obras Públicas"
        descripcion="Ubicación y estado de ejecución de las inversiones en el distrito de San Jerónimo. Los marcadores indican el avance físico mediante el semáforo institucional."
        densidad="publico"
      />
      <MapaObras />
    </div>
  );
}
