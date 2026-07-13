import { MapPin } from 'lucide-react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import WrapperMapa from '@/components/mapa/WrapperMapa';
import type { ObraDetalleResponse } from '../types';

export const ZOOM_DEFAULT_FICHA = 15;

const defaultIcon = new L.Icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

export function UbicacionMapa({ obra }: { obra: ObraDetalleResponse }) {
  const sinCoords =
    obra.latitud == null ||
    obra.longitud == null ||
    (obra.latitud === 0 && obra.longitud === 0);

  return (
    <div className="rounded-2xl bg-card border border-border overflow-hidden">
      <header className="flex items-center gap-2 px-6 py-4 border-b border-border bg-muted/40">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <MapPin className="w-4 h-4" aria-hidden="true" />
        </span>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-foreground">Ubicación</h3>
          <p className="text-xs text-muted-foreground">
            {obra.distrito || obra.provincia || obra.departamento
              ? [obra.distrito, obra.provincia, obra.departamento].filter(Boolean).join(' · ')
              : 'Ubicación registrada en Invierte.pe'}
          </p>
        </div>
        {obra.ubigeo ? (
          <span className="font-mono text-xs text-muted-foreground shrink-0">
            UBIGEO {obra.ubigeo}
          </span>
        ) : null}
      </header>

      {sinCoords ? (
        <div className="p-10 text-center">
          <MapPin className="w-8 h-8 text-muted-foreground mx-auto mb-3" aria-hidden="true" />
          <p className="text-sm font-medium text-foreground">Sin coordenadas registradas</p>
          <p className="mt-1 text-xs text-muted-foreground max-w-sm mx-auto">
            Esta obra no tiene latitud/longitud en el sistema. La ubicación administrativa se muestra en el encabezado.
          </p>
        </div>
      ) : (
        <div className="h-[360px] w-full">
          <WrapperMapa center={[obra.latitud!, obra.longitud!]} zoom={ZOOM_DEFAULT_FICHA}>
            <Marker position={[obra.latitud!, obra.longitud!]} icon={defaultIcon}>
              <Popup>
                <strong>{obra.nombre_inversion || 'Obra'}</strong>
                <br />
                CUI: {obra.codigo_unico}
              </Popup>
            </Marker>
          </WrapperMapa>
        </div>
      )}
    </div>
  );
}
