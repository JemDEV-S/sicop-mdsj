import type { ReactNode } from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

type EstiloMapa = 'osm' | 'voyager' | 'positron';

interface WrapperMapaProps {
  children?: ReactNode;
  center?: [number, number];
  zoom?: number;
  height?: string | number;
  className?: string;
  /** Estilo de tiles. `voyager` = look moderno y limpio (CartoDB). */
  estilo?: EstiloMapa;
  scrollWheelZoom?: boolean;
}

const TILES: Record<EstiloMapa, { url: string; attribution: string }> = {
  osm: {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
  voyager: {
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
  positron: {
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
};

/**
 * Contenedor estándar para mapas con react-leaflet.
 * Importa su propio CSS aislado (leaflet.css).
 */
export default function WrapperMapa({
  children,
  center = [-13.5358, -71.8797], // Default: San Jerónimo, Cusco aprox
  zoom = 13,
  height = 400,
  className,
  estilo = 'osm',
  scrollWheelZoom = false,
}: WrapperMapaProps) {
  const tile = TILES[estilo];
  return (
    <div
      className={`relative z-0 w-full overflow-hidden rounded-md border border-border ${className || ''}`}
      style={{ height }}
    >
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={scrollWheelZoom}
        style={{ height: '100%', width: '100%', zIndex: 0 }}
      >
        <TileLayer attribution={tile.attribution} url={tile.url} />
        {children}
      </MapContainer>
    </div>
  );
}
