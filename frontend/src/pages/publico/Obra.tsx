import { useParams, Link } from 'react-router-dom';
import { useObra } from '../../features/obras/hooks';
import { Identificacion } from '../../features/obras/secciones/Identificacion';
import { AvancePresupuesto } from '../../features/obras/secciones/AvancePresupuesto';
import { Cronograma } from '../../features/obras/secciones/Cronograma';
import { UbicacionMapa } from '../../features/obras/secciones/UbicacionMapa';
import { Contratista, Documentos } from '../../features/obras/secciones/ContratistaDocumentos';
import { ArrowLeft } from 'lucide-react';

export default function Obra() {
  const { codigo } = useParams<{ codigo: string }>();
  const { data: obra, isLoading, isError } = useObra(codigo || '');

  if (!codigo) {
    return <div className="p-6">Código no especificado.</div>;
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="animate-pulse space-y-6">
          <div className="h-4 w-32 bg-gray-200 rounded"></div>
          <div className="h-48 bg-gray-200 rounded"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="h-64 bg-gray-200 rounded"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (isError || !obra) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="bg-red-50 text-red-700 p-4 rounded-sm border border-red-200">
          No se pudo cargar la información de la obra. Es posible que el código sea incorrecto o el servidor no esté disponible.
        </div>
        <Link to="/obras" className="mt-4 inline-flex items-center text-primary-600 hover:text-primary-700">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Volver al listado
        </Link>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      <div className="mb-6">
        <Link to="/obras" className="inline-flex items-center text-gray-500 hover:text-gray-900 transition-colors text-sm">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Volver al listado
        </Link>
      </div>

      <div className="space-y-6">
        {/* Identificación (Full width) */}
        <Identificacion obra={obra} />

        {/* Avance y Presupuesto (Grid interno) */}
        <AvancePresupuesto obra={obra} />

        {/* Cronograma y Mapa (Grid 2 columnas) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Cronograma obra={obra} />
          <UbicacionMapa obra={obra} />
        </div>

        {/* Contratista y Documentos (Ocultos hasta que API los soporte) */}
        <Contratista obra={obra} />
        <Documentos obra={obra} />
      </div>
    </div>
  );
}
