import type { ReactNode } from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

interface WrapperMapaProps {
  children?: ReactNode;
  center?: [number, number];
  zoom?: number;
  height?: string | number;
  className?: string;
}

/**
 * Contenedor estándar para mapas con react-leaflet.
 * Importa su propio CSS aislado (leaflet.css).
 */
export default function WrapperMapa({
  children,
  center = [-13.5358, -71.8797], // Default: San Jerónimo, Cusco aprox
  zoom = 13,
  height = 400,
  className
}: WrapperMapaProps) {
  return (
    <div className={`w-full rounded-lg overflow-hidden border border-gray-200 z-0 relative ${className || ''}`} style={{ height }}>
      <MapContainer 
        center={center} 
        zoom={zoom} 
        scrollWheelZoom={false}
        style={{ height: '100%', width: '100%', zIndex: 0 }} // zIndex bajo para no pisar modales
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {children}
      </MapContainer>
    </div>
  );
}
