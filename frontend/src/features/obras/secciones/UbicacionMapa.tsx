import type { ObraDetalleResponse } from '../types';
import WrapperMapa from '../../../components/mapa/WrapperMapa';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';

export const ZOOM_DEFAULT_FICHA = 15;

const defaultIcon = new L.Icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

export function UbicacionMapa({ obra }: { obra: ObraDetalleResponse }) {
  if (
    obra.latitud == null || obra.longitud == null ||
    (obra.latitud === 0 && obra.longitud === 0)
  ) {
    return (
      <div className="bg-white border border-gray-200 shadow-sm p-4 rounded-sm flex items-center justify-center h-full min-h-[300px]">
        <p className="text-gray-500">No hay coordenadas de ubicación registradas para esta obra.</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 shadow-sm p-4 rounded-sm h-full flex flex-col">
      <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wider">Ubicación</h3>
      <div className="flex-1 min-h-[300px] border border-gray-200 rounded-sm overflow-hidden">
        <WrapperMapa 
          center={[obra.latitud, obra.longitud]} 
          zoom={ZOOM_DEFAULT_FICHA}
        >
          <Marker position={[obra.latitud, obra.longitud]} icon={defaultIcon}>
            <Popup>
              <strong>{obra.nombre_inversion || 'Obra'}</strong><br />
              CUI: {obra.codigo_unico}
            </Popup>
          </Marker>
        </WrapperMapa>
      </div>
    </div>
  );
}
