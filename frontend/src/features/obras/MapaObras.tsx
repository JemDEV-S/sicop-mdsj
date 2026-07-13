import { useState } from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { Link } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
import WrapperMapa from '../../components/mapa/WrapperMapa';
import { useObrasMapa } from './hooks';
import { ZOOM_DEFAULT_MAPA_GENERAL } from './constants';
import { semaforoToIconClass } from './utils';

// Función para generar un icono custom con Tailwind
const createCustomIcon = (semaforo: string) => {
  const cssClass = semaforoToIconClass(semaforo);
  // El anillo y color dependen de la clase asignada en utils
  const html = `
    <div class="relative flex h-6 w-6 items-center justify-center rounded-full ${cssClass} shadow-md border-2 border-white">
      <div class="h-2 w-2 rounded-full bg-white opacity-75"></div>
    </div>
  `;
  return L.divIcon({
    html,
    className: 'custom-leaflet-icon',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
  });
};

export default function MapaObras() {
  const [filtros, setFiltros] = useState<{ ano: number | '', funcion: string }>({ ano: '', funcion: '' });
  const { data, isLoading, isError } = useObrasMapa(
    // Solo enviar el año si tiene valor
    filtros.ano ? { ano: filtros.ano, funcion: filtros.funcion } : { funcion: filtros.funcion }
  );

  if (isLoading) {
    return <div className="flex h-[600px] items-center justify-center text-muted-foreground">Cargando mapa...</div>;
  }

  if (isError || !data) {
    return <div className="flex h-[600px] items-center justify-center text-destructive">Error al cargar datos del mapa.</div>;
  }

  // Separar items con coordenadas válidas de las inválidas (0,0 es Null Island)
  const itemsValidos = data.items.filter(obra => 
    obra.latitud != null && obra.longitud != null && 
    !(obra.latitud === 0 && obra.longitud === 0)
  );
  
  const itemsInvalidos = data.items.filter(obra => 
    obra.latitud == null || obra.longitud == null || 
    (obra.latitud === 0 && obra.longitud === 0)
  );

  const totalSinCoords = data.total_sin_coords + itemsInvalidos.length;
  // Convertimos los invalidos al tipo de sin coords para la UI
  const invalidosMapped = itemsInvalidos.map(obra => ({
    codigo_unico: obra.codigo_unico,
    nombre_inversion: obra.nombre_inversion,
    funcion: obra.funcion,
    avance_fisico: obra.avance_fisico?.toString() || null,
    pim_anio_actual: obra.pim_anio_actual?.toString() || null,
  }));
  const todasSinCoords = [...data.sin_coordenadas, ...invalidosMapped];

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-8rem)] min-h-[600px]">
      {/* Panel Lateral */}
      <div className="w-full lg:w-1/3 flex flex-col gap-4 overflow-hidden border rounded-lg bg-card text-card-foreground shadow-sm">
        <div className="p-4 border-b">
          <h2 className="text-xl font-semibold mb-2">Obras Públicas</h2>
          <div className="flex flex-col gap-3">
            <div>
              <label className="text-sm font-medium mb-1 block">Año Fiscal</label>
              <select 
                className="w-full border rounded-md p-2 text-sm bg-background"
                value={filtros.ano}
                onChange={(e) => setFiltros(prev => ({ ...prev, ano: e.target.value ? Number(e.target.value) : '' }))}
              >
                <option value="">Todos los años</option>
                <option value={2026}>2026</option>
                <option value={2025}>2025</option>
                <option value={2024}>2024</option>
              </select>
            </div>
            {/* Función omitida para simplificar, se puede agregar luego si hay datos de filtros */}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="mb-4">
            <h3 className="font-medium text-sm text-muted-foreground mb-1">
              En el Mapa ({itemsValidos.length})
            </h3>
            <p className="text-sm">Inversiones posicionadas correctamente.</p>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-2">
              <h3 className="font-medium text-sm text-muted-foreground">
                Sin Coordenadas o Inválidas ({totalSinCoords})
              </h3>
              <AlertCircle className="w-4 h-4 text-amber-500" />
            </div>
            {todasSinCoords.length === 0 ? (
              <p className="text-sm text-muted-foreground">Todas las obras tienen ubicación válida.</p>
            ) : (
              <div className="flex flex-col gap-3">
                {todasSinCoords.map(obra => (
                  <div key={obra.codigo_unico} className="p-3 border rounded-md bg-muted/30">
                    <div className="flex justify-between items-start mb-1">
                      <span className="font-mono text-xs text-muted-foreground">{obra.codigo_unico}</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${semaforoToIconClass(obra.avance_fisico ? 'desconocido' : 'desconocido')} border shadow-sm`}>
                        {obra.avance_fisico ? `${obra.avance_fisico}%` : 'S/D'}
                      </span>
                    </div>
                    <p className="text-sm font-medium line-clamp-2" title={obra.nombre_inversion || ''}>
                      {obra.nombre_inversion}
                    </p>
                    <Link to={`/obras/${obra.codigo_unico}`} className="text-xs text-primary hover:underline mt-2 inline-block">
                      Ver ficha completa &rarr;
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mapa Principal */}
      <div className="w-full lg:w-2/3 h-full rounded-lg overflow-hidden border shadow-sm">
        <WrapperMapa height="100%" zoom={ZOOM_DEFAULT_MAPA_GENERAL}>
          {itemsValidos.map(obra => (
            <Marker
              key={obra.codigo_unico}
              position={[obra.latitud!, obra.longitud!]}
              icon={createCustomIcon(obra.semaforo)}
            >
                <Popup>
                  <div className="max-w-[250px]">
                    <div className="mb-2">
                      <span className="font-mono text-xs text-gray-500">{obra.codigo_unico}</span>
                      <h4 className="font-semibold text-sm leading-tight mt-1 line-clamp-3">
                        {obra.nombre_inversion}
                      </h4>
                    </div>
                    <div className="flex items-center justify-between text-xs mb-3 bg-muted/50 p-2 rounded">
                      <span className="text-muted-foreground">Avance Físico:</span>
                      <span className="font-bold">{obra.avance_fisico != null ? `${obra.avance_fisico}%` : 'Sin datos'}</span>
                    </div>
                    <Link 
                      to={`/obras/${obra.codigo_unico}`}
                      className="block w-full text-center bg-primary text-primary-foreground py-1.5 px-3 rounded-md text-xs font-medium hover:bg-primary/90 transition-colors"
                    >
                      Ver Detalle
                    </Link>
                  </div>
                </Popup>
              </Marker>
          ))}
        </WrapperMapa>
      </div>
    </div>
  );
}
