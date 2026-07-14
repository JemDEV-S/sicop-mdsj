import { useMemo, useState } from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { Link } from 'react-router-dom';
import { Camera, ChevronLeft, ChevronRight, ArrowRight, Wallet, Navigation } from 'lucide-react';
import WrapperMapa from '@/components/mapa/WrapperMapa';
import { Button } from '@/components/ui/button';
import { ZOOM_DEFAULT_MAPA_GENERAL } from './constants';
import { useFotosObra } from './media/hooks';
import { urlDescargaMedia } from './media/api';
import { etiquetaEtapaAvance } from './utils';
import { formatearMoneda } from '@/lib/formatters';
import type { ObraMapaItem } from './types';

interface MapaObrasProps {
  items: ObraMapaItem[];
  isLoading?: boolean;
  height?: string | number;
}

// --- Estilos globales del marcador (inyectados una sola vez por módulo) ---
const MARKER_STYLES = `
  .leaflet-marker-icon.custom-leaflet-icon { background: none !important; border: none !important; }
  .mapa-marker-obra {
    position: relative;
    width: 44px;
    height: 54px;
    filter: drop-shadow(0 4px 6px rgba(15, 23, 42, 0.25));
    transition: transform .18s ease, filter .18s ease;
    transform-origin: 50% 100%;
    cursor: pointer;
  }
  .mapa-marker-obra:hover {
    transform: translateY(-2px) scale(1.08);
    filter: drop-shadow(0 8px 12px rgba(15, 23, 42, 0.35));
    z-index: 1000 !important;
  }
  .mapa-marker-obra .marker-inner-icon {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 8px;
    color: white;
    pointer-events: none;
  }
  .mapa-marker-obra .marker-inner-icon svg { width: 18px; height: 18px; }
  .mapa-marker-obra .marker-pct {
    position: absolute;
    top: -6px;
    right: -6px;
    background: white;
    color: var(--foreground);
    border: 1.5px solid var(--border);
    border-radius: 999px;
    font-size: 9.5px;
    font-weight: 700;
    padding: 1px 5px;
    line-height: 1.2;
    font-family: ui-sans-serif, system-ui, sans-serif;
    box-shadow: 0 1px 2px rgba(0,0,0,.12);
    letter-spacing: -0.02em;
  }
  /* Popup — quitar el "salto" y suavizar apariencia */
  .leaflet-popup.mapa-popup-obra .leaflet-popup-content-wrapper {
    border-radius: 14px;
    padding: 0;
    box-shadow: 0 10px 30px rgba(15,23,42,.18), 0 2px 6px rgba(15,23,42,.08);
    overflow: hidden;
  }
  .leaflet-popup.mapa-popup-obra .leaflet-popup-content {
    margin: 12px;
    line-height: 1.35;
  }
  .leaflet-popup.mapa-popup-obra .leaflet-popup-tip {
    box-shadow: 0 2px 6px rgba(15,23,42,.12);
  }
  .leaflet-popup.mapa-popup-obra .leaflet-popup-close-button {
    top: 8px;
    right: 8px;
    color: var(--muted-foreground);
    font-size: 20px;
    padding: 4px 7px;
  }
`;

if (typeof document !== 'undefined' && !document.getElementById('mapa-obras-styles')) {
  const style = document.createElement('style');
  style.id = 'mapa-obras-styles';
  style.textContent = MARKER_STYLES;
  document.head.appendChild(style);
}

// --- Utilidades visuales del pin ---

/**
 * Interpola color del pin entre dos tonos primarios (claro → oscuro).
 * Sin rojos ni amarillos: solo intensidad. Avance nulo = neutro (slate).
 */
function colorPinPorAvance(avance: number | null): string {
  if (avance == null) return '#94a3b8'; // slate-400 — neutro para "sin dato"
  // Rango: 8FA4D9 (lavanda claro, avance 0) → 1E3A8A (indigo profundo, avance 100)
  const t = Math.min(1, Math.max(0, avance / 100));
  const start = { r: 0x8f, g: 0xa4, b: 0xd9 };
  const end = { r: 0x1e, g: 0x3a, b: 0x8a };
  const r = Math.round(start.r + (end.r - start.r) * t);
  const g = Math.round(start.g + (end.g - start.g) * t);
  const b = Math.round(start.b + (end.b - start.b) * t);
  return `rgb(${r},${g},${b})`;
}

/**
 * Devuelve un path SVG (viewBox 24x24) con un ícono representativo del sector.
 */
function iconoSectorSvg(funcion: string | null | undefined): string {
  const key = (funcion ?? '').toLowerCase();
  if (/educaci|escolar|escuela|colegio/.test(key)) {
    // Graduation cap
    return '<path d="M22 10L12 5 2 10l10 5 10-5zM6 12v5c0 1 3 3 6 3s6-2 6-3v-5" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>';
  }
  if (/salud|hospital|posta|m[eé]dic/.test(key)) {
    return '<path d="M12 3v18M3 12h18" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>';
  }
  if (/transporte|vial|v[ií]a|pista|calle|puente|carret/.test(key)) {
    // Road
    return '<path d="M4 21l4-18M20 21l-4-18M12 4v3M12 11v3M12 18v3" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>';
  }
  if (/saneamiento|agua|desag|alcantar/.test(key)) {
    // Droplet
    return '<path d="M12 2s6 7 6 12a6 6 0 11-12 0c0-5 6-12 6-12z" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/>';
  }
  if (/deporte|recre|parque|plaza|estadio/.test(key)) {
    // Tree/park
    return '<circle cx="12" cy="9" r="6" stroke="currentColor" stroke-width="2" fill="none"/><path d="M12 15v6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>';
  }
  if (/cultura|patrimonio|turism/.test(key)) {
    // Landmark/museum
    return '<path d="M3 21h18M4 21V9m4 12V9m4 12V9m4 12V9m4 12V9M12 3l9 6H3l9-6z" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/>';
  }
  if (/seguridad|orden|serenaz|polic/.test(key)) {
    // Shield
    return '<path d="M12 3l8 3v6c0 5-4 8-8 9-4-1-8-4-8-9V6l8-3z" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/>';
  }
  if (/ambient|residuo|ecol/.test(key)) {
    // Leaf
    return '<path d="M4 20c8-2 14-8 16-16-8 0-14 6-16 14v2z" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/>';
  }
  if (/agr[ií]|riego|pecuari|rural/.test(key)) {
    // Wheat / sprout
    return '<path d="M12 22V11M8 15c0-3 4-4 4-4s4 1 4 4M6 10c0-3 6-5 6-5s6 2 6 5" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>';
  }
  // Default: building
  return '<path d="M4 21V6l8-3 8 3v15M9 21V12h6v9M4 21h16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>';
}

/**
 * Construye el HTML del marcador tipo pin con anillo de progreso
 * dibujado sobre el contorno mismo del pin.
 */
function crearIconoPin(obra: ObraMapaItem): L.DivIcon {
  const avance =
    obra.avance_fisico != null ? Math.min(100, Math.max(0, Number(obra.avance_fisico))) : null;
  const color = colorPinPorAvance(avance);
  const iconoSector = iconoSectorSvg(obra.funcion);

  // Trazamos el pin dos veces: el "fondo" claro y el "progreso" al color.
  // Path del contorno del pin (mismo path, viewBox 44x54).
  // Longitud aproximada del path para stroke-dasharray dinámico.
  const pathPin =
    'M22 2 C10 2 3 10.5 3 20.5 C3 33 22 51 22 51 C22 51 41 33 41 20.5 C41 10.5 34 2 22 2 Z';
  const perimetro = 138; // longitud aproximada del path
  const dashLen = avance != null ? (perimetro * avance) / 100 : 0;
  const dashGap = perimetro - dashLen;
  const badgePct = avance != null ? `<span class="marker-pct">${avance.toFixed(0)}%</span>` : '';

  return L.divIcon({
    html: `
      <div class="mapa-marker-obra" role="button" tabindex="-1">
        <svg viewBox="0 0 44 54" width="44" height="54" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <defs>
            <linearGradient id="glow-${obra.codigo_unico}" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stop-color="${color}" stop-opacity="1"/>
              <stop offset="100%" stop-color="${color}" stop-opacity="0.85"/>
            </linearGradient>
          </defs>
          <!-- Sombra base clara del pin -->
          <path d="${pathPin}" fill="url(#glow-${obra.codigo_unico})" stroke="white" stroke-width="2"/>
          <!-- Aro de progreso: recorre el contorno del pin -->
          ${
            avance != null
              ? `<path d="${pathPin}" fill="none" stroke="white" stroke-width="2.5"
                   stroke-dasharray="${dashLen} ${dashGap}"
                   stroke-dashoffset="0"
                   stroke-linecap="round" opacity="0.95"/>`
              : ''
          }
        </svg>
        <div class="marker-inner-icon">
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            ${iconoSector}
          </svg>
        </div>
        ${badgePct}
      </div>
    `,
    className: 'custom-leaflet-icon',
    iconSize: [44, 54],
    iconAnchor: [22, 52],
    popupAnchor: [0, -46],
  });
}

export default function MapaObras({ items, isLoading = false, height = '100%' }: MapaObrasProps) {
  const marcadores = useMemo(
    () => items.map((obra) => ({ obra, icon: crearIconoPin(obra) })),
    [items],
  );

  if (isLoading) {
    return (
      <div
        className="flex h-full w-full items-center justify-center rounded-2xl border border-border bg-muted/30 text-sm text-muted-foreground"
        style={{ height }}
      >
        Cargando mapa…
      </div>
    );
  }

  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl border border-border shadow-lg ring-1 ring-black/5">
      <WrapperMapa height={height} zoom={ZOOM_DEFAULT_MAPA_GENERAL} estilo="voyager">
        {marcadores.map(({ obra, icon }) => (
          <Marker key={obra.codigo_unico} position={[obra.latitud!, obra.longitud!]} icon={icon}>
            <Popup
              maxWidth={340}
              minWidth={300}
              className="mapa-popup-obra"
              autoPan={false}
              closeButton
            >
              <PopupContenido obra={obra} />
            </Popup>
          </Marker>
        ))}
      </WrapperMapa>

      {/* Leyenda flotante — intensidad de color = avance físico */}
      <div className="pointer-events-none absolute bottom-4 left-4 z-[500] rounded-xl border border-border bg-card/95 px-3 py-2.5 shadow-md backdrop-blur">
        <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Avance físico
        </p>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold text-muted-foreground">0%</span>
          <span
            className="h-2 w-28 rounded-full"
            style={{
              background: 'linear-gradient(to right, #8fa4d9, #1e3a8a)',
            }}
            aria-hidden="true"
          />
          <span className="text-[10px] font-semibold text-muted-foreground">100%</span>
        </div>
        <p className="mt-1.5 text-[10px] leading-tight text-muted-foreground">
          El color varía según el avance reportado.
        </p>
      </div>
    </div>
  );
}

// --- Popup enriquecido ---

function PopupContenido({ obra }: { obra: ObraMapaItem }) {
  const { data: fotos, isLoading: cargandoFotos } = useFotosObra(obra.codigo_unico);
  const [idxFoto, setIdxFoto] = useState(0);

  const fotosDisponibles = fotos && fotos.length > 0 ? fotos.slice(0, 5) : [];
  const fotoActual = fotosDisponibles[idxFoto];
  const totalFotos = fotosDisponibles.length;
  const tieneFotos = totalFotos > 0;

  const etapa = etiquetaEtapaAvance(obra.avance_fisico);
  const monto = obra.pim_anio_actual != null ? Number(obra.pim_anio_actual) : null;

  const urlNavegacion =
    obra.latitud != null && obra.longitud != null
      ? `https://www.google.com/maps/dir/?api=1&destination=${obra.latitud},${obra.longitud}`
      : null;
  const coordFmt =
    obra.latitud != null && obra.longitud != null
      ? `${obra.latitud.toFixed(5)}, ${obra.longitud.toFixed(5)}`
      : null;

  return (
    <div className="w-[320px] font-sans">
      {/* Carrusel de fotos — solo si hay algo que mostrar (o mientras carga) */}
      {cargandoFotos || tieneFotos ? (
        <div className="relative -m-3 mb-3 overflow-hidden rounded-t-md bg-muted">
          <div className="aspect-[16/10] w-full bg-muted">
            {cargandoFotos ? (
              <div className="flex h-full w-full items-center justify-center">
                <div className="h-8 w-8 animate-pulse rounded-full bg-muted-foreground/20" />
              </div>
            ) : fotoActual ? (
              <img
                src={urlDescargaMedia(fotoActual.ruta_relativa)}
                alt={fotoActual.nombre_original}
                className="h-full w-full object-cover"
                loading="lazy"
              />
            ) : null}
          </div>

          {totalFotos > 1 ? (
            <>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIdxFoto((idx) => (idx - 1 + totalFotos) % totalFotos);
                }}
                className="absolute left-2 top-1/2 -translate-y-1/2 inline-flex h-7 w-7 items-center justify-center rounded-full bg-black/40 text-white transition hover:bg-black/60"
                aria-label="Foto anterior"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIdxFoto((idx) => (idx + 1) % totalFotos);
                }}
                className="absolute right-2 top-1/2 -translate-y-1/2 inline-flex h-7 w-7 items-center justify-center rounded-full bg-black/40 text-white transition hover:bg-black/60"
                aria-label="Foto siguiente"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
              <div className="absolute bottom-2 left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-full bg-black/50 px-2 py-1 text-[10px] font-medium text-white">
                <Camera className="h-3 w-3" aria-hidden="true" />
                <span>
                  {idxFoto + 1} / {totalFotos}
                </span>
              </div>
            </>
          ) : null}
        </div>
      ) : null}

      {/* Contenido textual */}
      <div className="px-1 pb-1">
        <span className="font-mono text-[10px] tracking-tight text-muted-foreground">
          {obra.codigo_unico}
        </span>
        <h4 className="mt-0.5 break-words text-[13.5px] font-semibold leading-snug text-foreground">
          {obra.nombre_inversion ?? 'Obra sin nombre registrado'}
        </h4>

        {obra.funcion ? (
          <p className="mt-1 line-clamp-1 text-[11px] text-muted-foreground">{obra.funcion}</p>
        ) : null}

        {/* Estado + avance neutral */}
        <div className="mt-3 rounded-lg border border-border bg-muted/40 p-2.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              Estado de la obra
            </span>
            {obra.avance_fisico != null ? (
              <span className="text-[11px] font-bold tabular-nums text-foreground">
                {Number(obra.avance_fisico).toFixed(0)}%
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-[12px] font-semibold text-foreground">{etapa.titulo}</p>
          <p className="text-[10.5px] leading-relaxed text-muted-foreground">
            {etapa.descripcion}
          </p>
          {obra.avance_fisico != null ? (
            <div
              className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted"
              aria-hidden="true"
            >
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${Math.min(100, Math.max(0, Number(obra.avance_fisico)))}%` }}
              />
            </div>
          ) : null}
        </div>

        {/* Costo + ubicación */}
        <div className="mt-2 grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-border bg-card p-2.5">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Wallet className="h-3 w-3" aria-hidden="true" />
              <span className="text-[9.5px] font-semibold uppercase tracking-wide">
                Presupuesto {new Date().getFullYear()}
              </span>
            </div>
            <p className="mt-1 text-[12.5px] font-bold tabular-nums text-foreground">
              {monto != null ? formatearMoneda(monto, true) : 'Sin dato'}
            </p>
          </div>

          <div className="rounded-lg border border-border bg-card p-2.5">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Navigation className="h-3 w-3" aria-hidden="true" />
              <span className="text-[9.5px] font-semibold uppercase tracking-wide">
                Ubicación
              </span>
            </div>
            {urlNavegacion ? (
              <a
                href={urlNavegacion}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-1 inline-flex items-center gap-1 text-[11.5px] font-semibold text-primary hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                Cómo llegar
                <ArrowRight className="h-3 w-3" aria-hidden="true" />
              </a>
            ) : (
              <p className="mt-1 text-[11px] text-muted-foreground">No disponible</p>
            )}
            {coordFmt ? (
              <p className="mt-0.5 font-mono text-[9.5px] leading-tight text-muted-foreground">
                {coordFmt}
              </p>
            ) : null}
          </div>
        </div>

        <Button
          asChild
          size="sm"
          variant="outline"
          className="mt-3 w-full border-primary/40 text-primary hover:bg-primary hover:text-primary-foreground"
        >
          <Link to={`/obras/${obra.codigo_unico}`}>
            Ver ficha completa
            <ArrowRight className="ml-1 h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </Button>
      </div>
    </div>
  );
}
