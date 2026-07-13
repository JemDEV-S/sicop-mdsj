import { Link } from 'react-router-dom';
import { Building2, BarChart3, Users, MapPin } from 'lucide-react';

export default function Home() {
  return (
    <div className="bg-gray-50 min-h-[calc(100vh-64px)]">
      {/* Hero Section */}
      <section className="bg-white border-b border-gray-200 py-16 px-4">
        <div className="max-w-5xl mx-auto text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            {/* TODO: confirmar copy institucional con la Municipalidad */}
            Portal de Transparencia y Obras Públicas
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            {/* TODO: confirmar copy institucional con la Municipalidad */}
            Consulta el estado de los proyectos, la ejecución presupuestal y el uso de los recursos de la Municipalidad Distrital de San Jerónimo.
          </p>
        </div>
      </section>

      {/* Grid de Módulos */}
      <section className="max-w-5xl mx-auto py-12 px-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Módulo Obras */}
          <Link 
            to="/obras" 
            className="group flex items-start p-6 bg-white border border-gray-200 rounded-lg shadow-sm hover:border-primary transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          >
            <div className="p-3 bg-blue-50 text-primary rounded-lg mr-4">
              <Building2 className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900 group-hover:text-primary transition-colors">
                Obras Públicas
              </h2>
              <p className="text-gray-600 mt-1">
                Explora el directorio de proyectos de inversión, con detalle de presupuesto, contratista y avance físico.
              </p>
            </div>
          </Link>

          {/* Módulo Ejecución */}
          <Link 
            to="/ejecucion" 
            className="group flex items-start p-6 bg-white border border-gray-200 rounded-lg shadow-sm hover:border-primary transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          >
            <div className="p-3 bg-blue-50 text-primary rounded-lg mr-4">
              <BarChart3 className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900 group-hover:text-primary transition-colors">
                Ejecución Presupuestal
              </h2>
              <p className="text-gray-600 mt-1">
                Sigue de cerca cómo se distribuye y gasta el presupuesto del distrito en tiempo real.
              </p>
            </div>
          </Link>

          {/* Módulo Proveedores */}
          <Link 
            to="/proveedores" 
            className="group flex items-start p-6 bg-white border border-gray-200 rounded-lg shadow-sm hover:border-primary transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          >
            <div className="p-3 bg-blue-50 text-primary rounded-lg mr-4">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900 group-hover:text-primary transition-colors">
                Proveedores
              </h2>
              <p className="text-gray-600 mt-1">
                Consulta el padrón de empresas e individuos que brindan bienes y servicios a la entidad.
              </p>
            </div>
          </Link>

          {/* Módulo Mapa */}
          <Link 
            to="/mapa" 
            className="group flex items-start p-6 bg-white border border-gray-200 rounded-lg shadow-sm hover:border-primary transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          >
            <div className="p-3 bg-blue-50 text-primary rounded-lg mr-4">
              <MapPin className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900 group-hover:text-primary transition-colors">
                Mapa del Distrito
              </h2>
              <p className="text-gray-600 mt-1">
                Visualiza la ubicación geográfica de las obras en ejecución a lo largo de San Jerónimo.
              </p>
            </div>
          </Link>
        </div>
      </section>

      {/* Call to Action Secundario */}
      <footer className="text-center py-8">
        <p className="text-gray-500 text-sm">
          ¿Eres funcionario?{' '}
          <Link to="/login" className="text-primary hover:underline focus:outline-none focus:underline">
            Ingresa al portal interno
          </Link>
        </p>
      </footer>
    </div>
  );
}
